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
    with allocate_port(tmp_path, start=3000, end=3099) as port:
        assert port == 3000


def test_allocate_skips_used_ports(tmp_path):
    save_state(_env("one", 3000, tmp_path), tmp_path)
    save_state(_env("two", 3001, tmp_path), tmp_path)
    with allocate_port(tmp_path, start=3000, end=3099) as port:
        assert port == 3002


def test_allocate_raises_when_range_exhausted(tmp_path):
    for i in range(3):
        save_state(_env(f"env-{i}", 3000 + i, tmp_path), tmp_path)
    with pytest.raises(RuntimeError, match="No free ports"):
        with allocate_port(tmp_path, start=3000, end=3002):
            pass


def test_allocate_ports_returns_one_port_per_range(tmp_path):
    from forsa_dev.ports import allocate_ports

    with allocate_ports(tmp_path, (3000, 3099), (7600, 7699)) as ports:
        assert len(ports) == 2
        assert 3000 <= ports[0] <= 3099
        assert 7600 <= ports[1] <= 7699


def test_allocate_ports_no_double_allocation_within_call(tmp_path):
    """Two ports from the same range cannot collide within one call."""
    from forsa_dev.ports import allocate_ports

    with allocate_ports(tmp_path, (3000, 3000), (3001, 3001)) as ports:
        assert ports[0] != ports[1]


def test_allocate_port_still_works_after_refactor(tmp_path):
    """Existing single-port API must be unchanged."""
    with allocate_port(tmp_path, 3000, 3099) as port:
        assert 3000 <= port <= 3099


def test_allocate_port_skips_used_ttyd_port(tmp_path):
    """allocate_port must not return a port already used as ttyd_port."""
    import getpass
    from datetime import datetime, timezone

    from forsa_dev.state import Environment, save_state

    env = Environment(
        name="x",
        user=getpass.getuser(),
        branch="x",
        worktree=tmp_path / "w",
        tmux_session="u-x",
        compose_file=tmp_path / "c.yml",
        port=3001,
        url=None,
        created_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
        served_at=None,
        ttyd_port=3000,
        ttyd_pid=None,
    )
    save_state(env, tmp_path)
    with allocate_port(tmp_path, 3000, 3099) as port:
        assert port != 3000  # taken by ttyd_port
        assert port != 3001  # taken by port
