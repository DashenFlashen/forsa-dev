import getpass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from forsa_dev.cli import app
from forsa_dev.state import Environment, load_state

runner = CliRunner()
USER = getpass.getuser()


@pytest.fixture()
def config_file(tmp_path, git_repo):
    cfg = tmp_path / "config.toml"
    worktree_dir = tmp_path / "worktrees"
    state_dir = tmp_path / "state"
    cfg.write_text(
        f'repo = "{git_repo}"\n'
        f'worktree_dir = "{worktree_dir}"\n'
        f'data_dir = "/data/dev"\n'
        f'state_dir = "{state_dir}"\n'
        'base_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\n"
        "port_range_end = 3099\n"
    )
    return cfg


def _make_env(name: str, worktree: Path, state_dir: Path) -> Environment:
    return Environment(
        name=name,
        user=USER,
        branch=name,
        worktree=worktree,
        tmux_session=f"{USER}-{name}",
        compose_file=worktree / "docker-compose.dev.yml",
        port=3000,
        ttyd_port=7600,
        ttyd_pid=12345,
        url=None,
        created_at=datetime(2026, 3, 8, 0, 0, 0, tzinfo=timezone.utc),
        served_at=None,
    )


def test_up_creates_worktree_state_and_compose(config_file, tmp_path):
    worktree = tmp_path / "worktrees" / "feature-x"
    env = _make_env("feature-x", worktree, tmp_path / "state")
    with patch("forsa_dev.cli.up_env", return_value=env) as mock_up, \
         patch("forsa_dev.tmux.attach_session"):
        result = runner.invoke(app, ["up", "feature-x", "--config", str(config_file)])

    assert result.exit_code == 0, result.output
    mock_up.assert_called_once()
    assert mock_up.call_args.args[2] == "feature-x"


def test_up_fails_if_environment_already_exists(config_file, tmp_path):
    with patch("forsa_dev.cli.up_env", side_effect=ValueError("already exists")):
        result = runner.invoke(app, ["up", "feature-x", "--config", str(config_file)])
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_up_rolls_back_on_tmux_failure(config_file, tmp_path):
    with patch("forsa_dev.cli.up_env", side_effect=RuntimeError("tmux failed")):
        result = runner.invoke(app, ["up", "feature-x", "--config", str(config_file)])
    assert result.exit_code != 0


def test_up_with_claude_passes_flag(config_file, tmp_path):
    worktree = tmp_path / "worktrees" / "feature-x"
    env = _make_env("feature-x", worktree, tmp_path / "state")
    with patch("forsa_dev.cli.up_env", return_value=env) as mock_up, \
         patch("forsa_dev.tmux.attach_session"):
        result = runner.invoke(
            app, ["up", "feature-x", "--with-claude", "--config", str(config_file)]
        )
    assert result.exit_code == 0, result.output
    assert mock_up.call_args.kwargs["with_claude"] is True
