from __future__ import annotations

import asyncio
import grp
import logging
import os
import pwd
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
from fastapi import Cookie, Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from forsa_dev import agents, git, tmux, ttyd
from forsa_dev.config import Config, load_config
from forsa_dev.list_status import check_status, format_uptime, port_is_open
from forsa_dev.operations import (
    compose_cmd,
    down_env,
    repo_compose_env,
    restart_env,
    serve_env,
    stop_env,
    up_env,
)
from forsa_dev.ports import allocate_ports
from forsa_dev.state import Environment, list_states, load_state, save_state

logger = logging.getLogger(__name__)


def discover_users() -> dict[str, Config]:
    """Find all forsa-devs group members and load their configs."""
    try:
        group = grp.getgrnam("forsa-devs")
    except KeyError:
        return {}
    configs: dict[str, Config] = {}
    for username in group.gr_mem:
        try:
            user_info = pwd.getpwnam(username)
            config_path = Path(user_info.pw_dir) / ".config" / "forsa" / "config.toml"
            if config_path.exists():
                configs[username] = load_config(config_path)
        except (KeyError, FileNotFoundError, PermissionError):
            continue
    return configs


class CreateEnvRequest(BaseModel):
    name: str
    from_branch: str = "main"
    with_claude: bool = True
    data_dir: str | None = None
    existing_branch: str | None = None


class SendKeysRequest(BaseModel):
    key: str


def create_app(user_configs: dict[str, Config]) -> FastAPI:
    if not user_configs:
        raise ValueError("user_configs must not be empty")

    state_dirs = {cfg.state_dir for cfg in user_configs.values()}
    if len(state_dirs) > 1:
        raise ValueError(f"All users must share the same state_dir, got: {state_dirs}")
    state_dir = state_dirs.pop()

    base_urls = {cfg.base_url for cfg in user_configs.values()}
    if len(base_urls) > 1:
        raise ValueError(f"All users must share the same base_url, got: {base_urls}")
    base_url = base_urls.pop()

    app = FastAPI()

    agent_ttyd_ports = {"claude-root": 7698, "claude-forsa-dev": 7699}
    if "anders" in user_configs:
        try:
            agents.ensure_agents(agent_ttyd_ports)
        except Exception:
            pass  # agent startup failure shouldn't block dashboard

    # Auto-discover main repo environments
    for username, cfg in user_configs.items():
        try:
            load_state(username, "main", state_dir)
        except FileNotFoundError:
            compose_file = cfg.repo / "docker-compose.dev.yml"
            if not compose_file.exists():
                logger.warning(
                    "Skipping repo env for %s: %s not found", username, compose_file
                )
                continue
            ranges = (
                (cfg.port_range_start, cfg.port_range_end),
                (cfg.ttyd_port_range_start, cfg.ttyd_port_range_end),
            )
            with allocate_ports(state_dir, *ranges) as (port, ttyd_port):
                env = Environment(
                    name="main",
                    user=username,
                    branch=git.current_branch(cfg.repo) or "",
                    worktree=cfg.repo,
                    tmux_session=f"{username}-main",
                    compose_file=compose_file,
                    port=port,
                    url=None,
                    created_at=datetime.now(tz=timezone.utc),
                    served_at=None,
                    ttyd_port=ttyd_port,
                    type="repo",
                )
                save_state(env, state_dir)

    # Ensure tmux and ttyd for repo environments
    for username, cfg in user_configs.items():
        try:
            env = load_state(username, "main", state_dir)
        except FileNotFoundError:
            continue
        if env.type != "repo":
            continue
        if not tmux.session_exists(env.tmux_session):
            shell = os.environ.get("SHELL", "/bin/bash")
            command = (
                f"{shell} -i -c 'claude --dangerously-skip-permissions"
                f" --effort max; exec {shell}'"
            )
            try:
                tmux.create_session(env.tmux_session, env.worktree, command=command)
            except RuntimeError:
                pass
        if env.ttyd_port and not ttyd.ttyd_is_alive(env.ttyd_pid):
            try:
                pid = ttyd.start_ttyd(env.ttyd_port, env.tmux_session)
                updated = replace(env, ttyd_pid=pid)
                save_state(updated, state_dir)
            except Exception:
                pass

    def get_user(forsa_user: str = Cookie(default=None)) -> str:
        if not forsa_user or forsa_user not in user_configs:
            raise HTTPException(status_code=401, detail="No user selected")
        return forsa_user

    def _get_owner_cfg(owner: str) -> Config:
        if owner not in user_configs:
            raise HTTPException(status_code=404, detail=f"Unknown user '{owner}'")
        return user_configs[owner]

    @app.get("/api/users")
    def get_users() -> list[dict[str, str]]:
        return [{"name": name} for name in user_configs]

    @app.get("/api/environments")
    def get_environments(forsa_user: str = Cookie(default=None)) -> list[dict[str, Any]]:
        envs = list_states(state_dir)
        result = []
        for env in envs:
            # Repo environments are only visible to their owner
            if env.type == "repo" and env.user != forsa_user:
                continue

            # Refresh branch for repo environments
            branch = env.branch
            if env.type == "repo":
                current = git.current_branch(env.worktree)
                if current is not None:
                    branch = current

            tmux_stat = tmux.session_status(env.tmux_session)
            port_open = port_is_open(env.port)
            status = check_status(
                tmux_status=tmux_stat, served=env.url is not None, port_open=port_open
            )
            ttyd_alive = (
                ttyd.ttyd_port_is_open(env.ttyd_port) if env.ttyd_port is not None
                else False
            )
            result.append({
                "name": env.name,
                "user": env.user,
                "branch": branch,
                "worktree": str(env.worktree),
                "port": env.port,
                "ttyd_port": env.ttyd_port,
                "tmux_session": env.tmux_session,
                "url": env.url or f"http://{base_url}:{env.port}",
                "created_at": env.created_at.isoformat(),
                "served_at": env.served_at.isoformat() if env.served_at else None,
                "status": {
                    "tmux": status.tmux,
                    "server": status.server,
                    "ttyd": "alive" if ttyd_alive else "dead",
                },
                "uptime": format_uptime(env.served_at),
                "type": env.type,
            })
        return result

    @app.get("/api/health")
    def get_health() -> dict[str, Any]:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_percent": cpu,
            "cpu_count": psutil.cpu_count(),
            "ram_used_gb": round(mem.used / 1e9, 1),
            "ram_total_gb": round(mem.total / 1e9, 1),
            "disk_used_gb": round(disk.used / 1e9, 0),
            "disk_total_gb": round(disk.total / 1e9, 0),
        }

    @app.get("/api/config")
    def get_config(user: str = Depends(get_user)) -> dict[str, Any]:
        cfg = user_configs[user]
        return {"data_dir": str(cfg.data_dir)}

    @app.get("/api/branches")
    def get_branches(user: str = Depends(get_user)) -> dict[str, list[str]]:
        cfg = user_configs[user]
        try:
            branches = git.list_branches(cfg.repo)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"branches": branches}

    @app.post("/api/environments")
    def post_create_environment(
        body: CreateEnvRequest, user: str = Depends(get_user),
    ) -> dict[str, Any]:
        cfg = user_configs[user]
        data_dir = Path(body.data_dir) if body.data_dir else None
        try:
            env = up_env(
                cfg, user, body.name,
                from_branch=body.from_branch,
                with_claude=body.with_claude,
                data_dir=data_dir,
                existing_branch=body.existing_branch,
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"name": env.name, "port": env.port, "ttyd_port": env.ttyd_port}

    @app.post("/api/environments/{owner}/{name}/serve")
    def post_serve(owner: str, name: str, _user: str = Depends(get_user)) -> dict[str, str]:
        cfg = _get_owner_cfg(owner)
        try:
            serve_env(cfg, owner, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"status": "ok"}

    @app.post("/api/environments/{owner}/{name}/stop")
    def post_stop(owner: str, name: str, _user: str = Depends(get_user)) -> dict[str, str]:
        cfg = _get_owner_cfg(owner)
        try:
            stop_env(cfg, owner, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"status": "ok"}

    @app.post("/api/environments/{owner}/{name}/restart")
    def post_restart(owner: str, name: str, _user: str = Depends(get_user)) -> dict[str, str]:
        cfg = _get_owner_cfg(owner)
        try:
            restart_env(cfg, owner, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"status": "ok"}

    @app.delete("/api/environments/{owner}/{name}")
    def delete_environment(
        owner: str, name: str, force: bool = False, _user: str = Depends(get_user),
    ) -> dict[str, str]:
        cfg = _get_owner_cfg(owner)
        try:
            down_env(cfg, owner, name, force=force)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return {"status": "ok"}

    @app.get("/api/environments/{owner}/{name}/logs")
    async def stream_logs(owner: str, name: str) -> StreamingResponse:
        cfg = _get_owner_cfg(owner)
        try:
            env = load_state(owner, name, state_dir)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")

        cmd = compose_cmd(env, "logs", "-f", "--tail=100")
        run_env = repo_compose_env(cfg, env) if env.type == "repo" else None

        async def generate():
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=run_env,
            )
            try:
                async for line in proc.stdout:
                    yield f"data: {line.decode(errors='replace').rstrip()}\n\n"
            finally:
                proc.kill()
                await proc.wait()

        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.post("/api/tmux/{session}/keys")
    def post_send_keys(session: str, body: SendKeysRequest) -> dict[str, str]:
        if not tmux.session_exists(session):
            raise HTTPException(status_code=404, detail=f"Session '{session}' not found")
        try:
            tmux.send_keys(session, body.key)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"status": "ok"}

    @app.get("/api/agents")
    def get_agents(forsa_user: str = Cookie(default=None)) -> list[dict[str, Any]]:
        if forsa_user != "anders" or "anders" not in user_configs:
            return []
        return agents.agent_status(agent_ttyd_ports)

    # Serve built React app — mounted last so API routes take precedence
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists() and any(static_dir.iterdir()):
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
