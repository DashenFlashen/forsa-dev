from datetime import datetime, timezone
from pathlib import Path
import pytest
from forsa_dev.ports import allocate_port
from forsa_dev.state import Environment, save_state


def _env(name: str, port: int, state_dir: Path) -> Environment:
    return Environment(
        name=name,
        user="anders",
        branch=name,
        worktree=Path(f"/tmp/{name}"),
        tmux_session=f"anders-{name}",
        compose_file=Path(f"/tmp/{name}/docker-compose.dev.yml"),
        port=port,
        url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None,
    )


def test_allocate_first_port_in_range(tmp_path):
    port = allocate_port(tmp_path, start=3000, end=3099)
    assert port == 3000


def test_allocate_skips_used_ports(tmp_path):
    save_state(_env("one", 3000, tmp_path), tmp_path)
    save_state(_env("two", 3001, tmp_path), tmp_path)
    port = allocate_port(tmp_path, start=3000, end=3099)
    assert port == 3002


def test_allocate_raises_when_range_exhausted(tmp_path):
    for i in range(3):
        save_state(_env(f"env-{i}", 3000 + i, tmp_path), tmp_path)
    with pytest.raises(RuntimeError, match="No free ports"):
        allocate_port(tmp_path, start=3000, end=3002)
