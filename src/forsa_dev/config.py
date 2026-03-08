from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli_w

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "forsa" / "config.toml"
_DEFAULT_DASHBOARD_PORT = 8080
_DEFAULT_TTYD_PORT_RANGE_START = 7600
_DEFAULT_TTYD_PORT_RANGE_END = 7699


@dataclass(frozen=True)
class Config:
    repo: Path
    worktree_dir: Path
    data_dir: Path
    state_dir: Path
    base_url: str
    docker_image: str
    gurobi_lic: Path
    port_range_start: int
    port_range_end: int
    dashboard_port: int = _DEFAULT_DASHBOARD_PORT
    ttyd_port_range_start: int = _DEFAULT_TTYD_PORT_RANGE_START
    ttyd_port_range_end: int = _DEFAULT_TTYD_PORT_RANGE_END


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\nRun `forsa-dev init` to create it."
        )
    with path.open("rb") as f:
        data = tomllib.load(f)
    return Config(
        repo=Path(data["repo"]),
        worktree_dir=Path(data["worktree_dir"]),
        data_dir=Path(data["data_dir"]),
        state_dir=Path(data["state_dir"]),
        base_url=data["base_url"],
        docker_image=data["docker_image"],
        gurobi_lic=Path(data["gurobi_lic"]),
        port_range_start=int(data["port_range_start"]),
        port_range_end=int(data["port_range_end"]),
        dashboard_port=int(data.get("dashboard_port", _DEFAULT_DASHBOARD_PORT)),
        ttyd_port_range_start=int(
            data.get("ttyd_port_range_start", _DEFAULT_TTYD_PORT_RANGE_START)
        ),
        ttyd_port_range_end=int(data.get("ttyd_port_range_end", _DEFAULT_TTYD_PORT_RANGE_END)),
    )


def save_config(config: Config, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "repo": str(config.repo),
        "worktree_dir": str(config.worktree_dir),
        "data_dir": str(config.data_dir),
        "state_dir": str(config.state_dir),
        "base_url": config.base_url,
        "docker_image": config.docker_image,
        "gurobi_lic": str(config.gurobi_lic),
        "port_range_start": config.port_range_start,
        "port_range_end": config.port_range_end,
        "dashboard_port": config.dashboard_port,
        "ttyd_port_range_start": config.ttyd_port_range_start,
        "ttyd_port_range_end": config.ttyd_port_range_end,
    }
    with path.open("wb") as f:
        tomli_w.dump(data, f)
