from __future__ import annotations
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli_w


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "forsa" / "config.toml"


@dataclass(frozen=True)
class Config:
    repo: Path
    worktree_dir: Path
    data_dir: Path
    state_dir: Path
    caddy_admin: str
    base_url: str
    docker_image: str
    gurobi_lic: Path
    port_range_start: int
    port_range_end: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Config):
            return NotImplemented
        return (
            self.repo == other.repo
            and self.worktree_dir == other.worktree_dir
            and self.data_dir == other.data_dir
            and self.state_dir == other.state_dir
            and self.caddy_admin == other.caddy_admin
            and self.base_url == other.base_url
            and self.docker_image == other.docker_image
            and self.gurobi_lic == other.gurobi_lic
            and self.port_range_start == other.port_range_start
            and self.port_range_end == other.port_range_end
        )


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}\nRun `forsa-dev init` to create it.")
    with path.open("rb") as f:
        data = tomllib.load(f)
    return Config(
        repo=Path(data["repo"]),
        worktree_dir=Path(data["worktree_dir"]),
        data_dir=Path(data["data_dir"]),
        state_dir=Path(data["state_dir"]),
        caddy_admin=data["caddy_admin"],
        base_url=data["base_url"],
        docker_image=data["docker_image"],
        gurobi_lic=Path(data["gurobi_lic"]),
        port_range_start=int(data["port_range_start"]),
        port_range_end=int(data["port_range_end"]),
    )


def save_config(config: Config, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "repo": str(config.repo),
        "worktree_dir": str(config.worktree_dir),
        "data_dir": str(config.data_dir),
        "state_dir": str(config.state_dir),
        "caddy_admin": config.caddy_admin,
        "base_url": config.base_url,
        "docker_image": config.docker_image,
        "gurobi_lic": str(config.gurobi_lic),
        "port_range_start": config.port_range_start,
        "port_range_end": config.port_range_end,
    }
    with path.open("wb") as f:
        tomli_w.dump(data, f)
