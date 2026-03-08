from __future__ import annotations

import getpass
from pathlib import Path
from typing import Any

import psutil
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from forsa_dev import tmux, ttyd
from forsa_dev.config import Config
from forsa_dev.list_status import check_status, format_uptime, port_is_open
from forsa_dev.operations import down_env, restart_env, serve_env, stop_env, up_env
from forsa_dev.state import list_states


class CreateEnvRequest(BaseModel):
    name: str
    from_branch: str = "main"


def create_app(cfg: Config) -> FastAPI:
    app = FastAPI()

    @app.get("/api/environments")
    def get_environments() -> list[dict[str, Any]]:
        envs = list_states(cfg.state_dir)
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
                "url": env.url or f"http://{cfg.base_url}:{env.port}",
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
        try:
            stop_env(cfg, user, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        return {"status": "ok"}

    @app.post("/api/environments/{name}/restart")
    def post_restart(name: str) -> dict[str, str]:
        user = getpass.getuser()
        try:
            restart_env(cfg, user, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        return {"status": "ok"}

    @app.post("/api/environments")
    def post_create_environment(body: CreateEnvRequest) -> dict[str, Any]:
        user = getpass.getuser()
        try:
            env = up_env(cfg, user, body.name, from_branch=body.from_branch, with_claude=True)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"name": env.name, "port": env.port, "ttyd_port": env.ttyd_port}

    @app.delete("/api/environments/{name}")
    def delete_environment(name: str, force: bool = False) -> dict[str, str]:
        user = getpass.getuser()
        try:
            down_env(cfg, user, name, force=force)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return {"status": "ok"}

    # Serve built React app — mounted last so API routes take precedence
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists() and any(static_dir.iterdir()):
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
