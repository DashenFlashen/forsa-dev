from __future__ import annotations

import asyncio
import getpass
from pathlib import Path
from typing import Any

import psutil
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from forsa_dev import git, tmux, ttyd
from forsa_dev.config import Config
from forsa_dev.list_status import check_status, format_uptime, port_is_open
from forsa_dev.operations import compose_cmd, down_env, restart_env, serve_env, stop_env, up_env
from forsa_dev.state import list_states, load_state


class CreateEnvRequest(BaseModel):
    name: str
    from_branch: str = "main"
    with_claude: bool = True
    data_dir: str | None = None
    existing_branch: str | None = None


def create_app(user_configs: dict[str, Config]) -> FastAPI:
    if not user_configs:
        raise ValueError("user_configs must not be empty")

    state_dirs = {cfg.state_dir for cfg in user_configs.values()}
    if len(state_dirs) > 1:
        raise ValueError(f"All users must share the same state_dir, got: {state_dirs}")
    state_dir = state_dirs.pop()
    base_url = next(iter(user_configs.values())).base_url

    app = FastAPI()

    @app.get("/api/environments")
    def get_environments() -> list[dict[str, Any]]:
        envs = list_states(state_dir)
        result = []
        for env in envs:
            tmux_stat = tmux.session_status(env.tmux_session)
            port_open = port_is_open(env.port)
            status = check_status(
                tmux_status=tmux_stat, served=env.url is not None, port_open=port_open
            )
            ttyd_alive = ttyd.ttyd_is_alive(env.ttyd_pid) if env.ttyd_pid is not None else False
            result.append({
                "name": env.name,
                "user": env.user,
                "branch": env.branch,
                "port": env.port,
                "ttyd_port": env.ttyd_port,
                "url": env.url or f"http://{base_url}:{env.port}",
                "created_at": env.created_at.isoformat(),
                "served_at": env.served_at.isoformat() if env.served_at else None,
                "status": {
                    "tmux": status.tmux,
                    "server": status.server,
                    "ttyd": "alive" if ttyd_alive else "dead",
                },
                "uptime": format_uptime(env.served_at),
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

    @app.post("/api/environments/{name}/serve")
    def post_serve(name: str) -> dict[str, str]:
        user = getpass.getuser()
        cfg = user_configs[user]
        try:
            serve_env(cfg, user, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"status": "ok"}

    @app.post("/api/environments/{name}/stop")
    def post_stop(name: str) -> dict[str, str]:
        user = getpass.getuser()
        cfg = user_configs[user]
        try:
            stop_env(cfg, user, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"status": "ok"}

    @app.post("/api/environments/{name}/restart")
    def post_restart(name: str) -> dict[str, str]:
        user = getpass.getuser()
        cfg = user_configs[user]
        try:
            restart_env(cfg, user, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"status": "ok"}

    @app.get("/api/config")
    def get_config() -> dict[str, Any]:
        user = getpass.getuser()
        cfg = user_configs[user]
        return {"data_dir": str(cfg.data_dir)}

    @app.get("/api/branches")
    def get_branches() -> dict[str, list[str]]:
        user = getpass.getuser()
        cfg = user_configs[user]
        try:
            branches = git.list_branches(cfg.repo)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"branches": branches}

    @app.post("/api/environments")
    def post_create_environment(body: CreateEnvRequest) -> dict[str, Any]:
        user = getpass.getuser()
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

    @app.delete("/api/environments/{name}")
    def delete_environment(name: str, force: bool = False) -> dict[str, str]:
        user = getpass.getuser()
        cfg = user_configs[user]
        try:
            down_env(cfg, user, name, force=force)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return {"status": "ok"}

    @app.get("/api/environments/{name}/logs")
    async def stream_logs(name: str) -> StreamingResponse:
        user = getpass.getuser()
        try:
            env = load_state(user, name, state_dir)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")

        cmd = compose_cmd(env, "logs", "-f", "--tail=100")

        async def generate():
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                async for line in proc.stdout:
                    yield f"data: {line.decode(errors='replace').rstrip()}\n\n"
            finally:
                proc.kill()
                await proc.wait()

        return StreamingResponse(generate(), media_type="text/event-stream")

    # Serve built React app — mounted last so API routes take precedence
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists() and any(static_dir.iterdir()):
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
