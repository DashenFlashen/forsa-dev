from __future__ import annotations

import subprocess
from dataclasses import replace
from datetime import datetime, timezone

from forsa_dev.config import Config
from forsa_dev.state import Environment, load_state, save_state


def compose_cmd(env: Environment, *args: str) -> list[str]:
    return [
        "docker", "compose",
        "-p", f"{env.user}-{env.name}",
        "-f", str(env.compose_file),
        *args,
    ]


def serve_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    result = subprocess.run(compose_cmd(env, "up", "-d"), check=False)
    if result.returncode != 0:
        raise RuntimeError("docker compose up failed")
    url = f"http://{cfg.base_url}:{env.port}"
    updated = replace(env, url=url, served_at=datetime.now(tz=timezone.utc))
    save_state(updated, cfg.state_dir)


def stop_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    subprocess.run(compose_cmd(env, "down"), check=False)
    updated = replace(env, url=None, served_at=None)
    save_state(updated, cfg.state_dir)


def restart_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    subprocess.run(compose_cmd(env, "restart"), check=False)
