import getpass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from typer.testing import CliRunner

from forsa_dev.cli import app
from forsa_dev.list_status import check_status, format_uptime
from forsa_dev.state import Environment, save_state

runner = CliRunner()
USER = getpass.getuser()


def _env(name: str, user: str, port: int, url: str | None, state_dir: Path) -> Environment:
    worktree = Path(f"/tmp/worktrees/{name}")
    return Environment(
        name=name, user=user, branch=name,
        worktree=worktree,
        tmux_session=f"{user}-{name}",
        compose_file=worktree / "docker-compose.dev.yml",
        port=port, url=url,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None,
    )


def test_list_empty(tmp_path):
    cfg_file = tmp_path / "config.toml"
    state_dir = tmp_path / "state"
    cfg_file.write_text(
        f'repo = "/tmp/repo"\nworktree_dir = "/tmp/worktrees"\ndata_dir = "/data/dev"\n'
        f'state_dir = "{state_dir}"\nbase_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\nport_range_start = 3000\nport_range_end = 3099\n'
    )
    result = runner.invoke(app, ["list", "--config", str(cfg_file)])
    assert result.exit_code == 0
    assert "No environments" in result.output


def test_list_shows_environments(tmp_path):
    state_dir = tmp_path / "state"
    save_state(
        _env("ticket-42", USER, 3002, "optbox.example.ts.net/ticket-42/", state_dir),
        state_dir,
    )
    save_state(_env("experiment", USER, 3003, None, state_dir), state_dir)
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f'repo = "/tmp/repo"\nworktree_dir = "/tmp/worktrees"\ndata_dir = "/data/dev"\n'
        f'state_dir = "{state_dir}"\nbase_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\nport_range_start = 3000\nport_range_end = 3099\n'
    )
    result = runner.invoke(app, ["list", "--config", str(cfg_file)])
    assert result.exit_code == 0
    assert "ticket-42" in result.output
    assert "experiment" in result.output


# Pure logic tests — no subprocess needed
def test_check_status_tmux_missing_port_closed():
    status = check_status(tmux_status="missing", served=False, port_open=False)
    assert status.tmux == "missing"
    assert status.server == "stopped"


def test_check_status_tmux_active_served_port_open():
    status = check_status(tmux_status="active", served=True, port_open=True)
    assert status.tmux == "active"
    assert status.server == "running"


def test_check_status_tmux_detached_not_served():
    status = check_status(tmux_status="detached", served=False, port_open=False)
    assert status.tmux == "detached"
    assert status.server == "stopped"


def test_check_status_served_port_closed():
    status = check_status(tmux_status="active", served=True, port_open=False)
    assert status.tmux == "active"
    assert status.server == "crashed"


# format_uptime unit tests
def test_format_uptime_none():
    assert format_uptime(None) == "-"


def test_format_uptime_minutes():
    served_at = datetime.now(tz=timezone.utc) - timedelta(minutes=42)
    assert format_uptime(served_at) == "42m"


def test_format_uptime_zero_minutes():
    served_at = datetime.now(tz=timezone.utc) - timedelta(seconds=30)
    assert format_uptime(served_at) == "0m"


def test_format_uptime_hours():
    served_at = datetime.now(tz=timezone.utc) - timedelta(hours=2, minutes=15)
    assert format_uptime(served_at) == "2h 15m"


def test_format_uptime_exactly_one_hour():
    served_at = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    assert format_uptime(served_at) == "1h 0m"


def test_format_uptime_days():
    served_at = datetime.now(tz=timezone.utc) - timedelta(days=3, hours=7)
    assert format_uptime(served_at) == "3d 7h"
