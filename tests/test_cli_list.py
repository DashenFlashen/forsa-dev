import getpass
from datetime import datetime, timezone
from pathlib import Path
import pytest
from typer.testing import CliRunner
from forsa_dev.cli import app
from forsa_dev.state import Environment, save_state
from forsa_dev.list_status import check_status, Status


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
        f'state_dir = "{state_dir}"\ncaddy_admin = "http://localhost:2019"\n'
        'base_url = "optbox.example.ts.net"\ndocker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\nport_range_start = 3000\nport_range_end = 3099\n'
    )
    result = runner.invoke(app, ["list", "--config", str(cfg_file)])
    assert result.exit_code == 0
    assert "No environments" in result.output


def test_list_shows_environments(tmp_path):
    state_dir = tmp_path / "state"
    save_state(_env("ticket-42", USER, 3002, "optbox.example.ts.net/ticket-42/", state_dir), state_dir)
    save_state(_env("experiment", USER, 3003, None, state_dir), state_dir)
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f'repo = "/tmp/repo"\nworktree_dir = "/tmp/worktrees"\ndata_dir = "/data/dev"\n'
        f'state_dir = "{state_dir}"\ncaddy_admin = "http://localhost:2019"\n'
        'base_url = "optbox.example.ts.net"\ndocker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\nport_range_start = 3000\nport_range_end = 3099\n'
    )
    result = runner.invoke(app, ["list", "--config", str(cfg_file)])
    assert result.exit_code == 0
    assert "ticket-42" in result.output
    assert "experiment" in result.output


# Pure logic test — no subprocess needed
def test_check_status_tmux_missing_port_closed():
    status = check_status(tmux_exists=False, port_open=False)
    assert status.tmux == "missing"
    assert status.server == "stopped"


def test_check_status_tmux_exists_port_open():
    status = check_status(tmux_exists=True, port_open=True)
    assert status.tmux == "active"
    assert status.server == "running"


def test_check_status_tmux_exists_port_closed():
    status = check_status(tmux_exists=True, port_open=False)
    assert status.tmux == "active"
    assert status.server == "stopped"
