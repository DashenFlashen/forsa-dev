import getpass
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from forsa_dev.cli import app
from forsa_dev.state import Environment, save_state

runner = CliRunner()
USER = getpass.getuser()


@pytest.fixture()
def env_setup(tmp_path):
    worktree = tmp_path / "worktrees" / "ticket-42"
    worktree.mkdir(parents=True)
    state_dir = tmp_path / "state"
    env = Environment(
        name="ticket-42", user=USER, branch="ticket-42",
        worktree=worktree, tmux_session=f"{USER}-ticket-42",
        compose_file=worktree / "docker-compose.dev.yml",
        port=3002, url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None,
    )
    save_state(env, state_dir)
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        f'repo = "/tmp/repo"\nworktree_dir = "{tmp_path / "worktrees"}"\n'
        f'data_dir = "/data/dev"\nstate_dir = "{state_dir}"\n'
        'caddy_admin = "http://localhost:2019"\nbase_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\ngurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\nport_range_end = 3099\n"
    )
    return cfg


def test_logs_invokes_docker_compose(env_setup):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["logs", "ticket-42", "--config", str(env_setup)])
    assert result.exit_code == 0
    call_args = mock_run.call_args[0][0]
    assert "logs" in call_args
    assert "-f" in call_args


def test_restart_invokes_docker_compose(env_setup):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["restart", "ticket-42", "--config", str(env_setup)])
    assert result.exit_code == 0
    call_args = mock_run.call_args[0][0]
    assert "restart" in call_args
    assert f"{USER}-ticket-42" in call_args


def test_attach_calls_tmux(env_setup):
    with patch("forsa_dev.tmux.attach_session") as mock_attach:
        result = runner.invoke(app, ["attach", "ticket-42", "--config", str(env_setup)])
    assert result.exit_code == 0
    mock_attach.assert_called_once_with(f"{USER}-ticket-42")
