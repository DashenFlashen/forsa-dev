import getpass
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from forsa_dev.cli import app
from forsa_dev.state import Environment, load_state, save_state

runner = CliRunner()
USER = getpass.getuser()


@pytest.fixture()
def env_with_state(tmp_path):
    worktree = tmp_path / "worktrees" / "ticket-42"
    worktree.mkdir(parents=True)
    compose_file = worktree / "docker-compose.dev.yml"
    compose_file.write_text("services: {}")
    state_dir = tmp_path / "state"
    env = Environment(
        name="ticket-42",
        user=USER,
        branch="ticket-42",
        worktree=worktree,
        tmux_session=f"{USER}-ticket-42",
        compose_file=compose_file,
        port=3002,
        url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None,
    )
    save_state(env, state_dir)
    return tmp_path, state_dir, env


@pytest.fixture()
def config_file(tmp_path, env_with_state):
    data_tmp, state_dir, _ = env_with_state
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        f'repo = "{tmp_path / "repo"}"\n'
        f'worktree_dir = "{tmp_path / "worktrees"}"\n'
        'data_dir = "/data/dev"\n'
        f'state_dir = "{state_dir}"\n'
        'caddy_admin = "http://localhost:2019"\n'
        'base_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\n"
        "port_range_end = 3099\n"
    )
    return cfg


def test_serve_updates_state(config_file, env_with_state):
    data_tmp, state_dir, env = env_with_state
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["serve", "ticket-42", "--config", str(config_file)])
    assert result.exit_code == 0, result.output
    updated = load_state(USER, "ticket-42", state_dir)
    assert updated.url == "https://optbox.example.ts.net/ticket-42/"
    assert updated.served_at is not None


def test_stop_clears_state(config_file, env_with_state):
    data_tmp, state_dir, env = env_with_state
    # First set it as served
    served_env = Environment(**{**env.__dict__,
        "url": "optbox.example.ts.net/ticket-42/",
        "served_at": datetime(2026, 3, 7, 22, 5, 0, tzinfo=timezone.utc)
    })
    save_state(served_env, state_dir)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["stop", "ticket-42", "--config", str(config_file)])
    assert result.exit_code == 0, result.output
    updated = load_state(USER, "ticket-42", state_dir)
    assert updated.url is None
    assert updated.served_at is None
