from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Environment:
    name: str
    user: str
    branch: str
    worktree: Path
    tmux_session: str
    compose_file: Path
    port: int
    url: str | None
    created_at: datetime
    served_at: datetime | None
    ttyd_port: int | None = None
    ttyd_pid: int | None = None


def _state_path(user: str, name: str, state_dir: Path) -> Path:
    return state_dir / f"{user}-{name}.json"


def _serialize(env: Environment) -> dict:
    d = asdict(env)
    # Path and datetime fields must be serialised to strings for JSON
    d["worktree"] = str(env.worktree)
    d["compose_file"] = str(env.compose_file)
    d["created_at"] = env.created_at.isoformat()
    d["served_at"] = env.served_at.isoformat() if env.served_at else None
    return d


def _deserialize(data: dict) -> Environment:
    return Environment(
        name=data["name"],
        user=data["user"],
        branch=data["branch"],
        worktree=Path(data["worktree"]),
        tmux_session=data["tmux_session"],
        compose_file=Path(data["compose_file"]),
        port=data["port"],
        url=data["url"],
        created_at=datetime.fromisoformat(data["created_at"]),
        served_at=datetime.fromisoformat(data["served_at"]) if data["served_at"] else None,
        ttyd_port=data.get("ttyd_port"),
        ttyd_pid=data.get("ttyd_pid"),
    )


def save_state(env: Environment, state_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = _state_path(env.user, env.name, state_dir)
    path.write_text(json.dumps(_serialize(env), indent=2))


def load_state(user: str, name: str, state_dir: Path) -> Environment:
    path = _state_path(user, name, state_dir)
    if not path.exists():
        raise FileNotFoundError(f"No environment '{user}-{name}' found.")
    return _deserialize(json.loads(path.read_text()))


def delete_state(user: str, name: str, state_dir: Path) -> None:
    _state_path(user, name, state_dir).unlink()


def list_states(state_dir: Path) -> list[Environment]:
    if not state_dir.exists():
        return []
    envs = []
    for p in sorted(state_dir.glob("*.json")):
        try:
            envs.append(_deserialize(json.loads(p.read_text())))
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping malformed state file: %s", p)
    return envs
