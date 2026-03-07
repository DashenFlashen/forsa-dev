from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Environment):
            return NotImplemented
        return asdict(self) == asdict(other)


def _state_path(user: str, name: str, state_dir: Path) -> Path:
    return state_dir / f"{user}-{name}.json"


def _serialize(env: Environment) -> dict:
    d = asdict(env)
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
    return [
        _deserialize(json.loads(p.read_text()))
        for p in sorted(state_dir.glob("*.json"))
    ]
