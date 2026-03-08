import getpass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from forsa_dev.cli import app
from forsa_dev.state import Environment, save_state

runner = CliRunner()
USER = getpass.getuser()


@pytest.fixture()
def setup(tmp_path, git_repo):
    worktree = tmp_path / "worktrees" / "feature-x"
    import subprocess
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-x", str(worktree), "main"],
        cwd=git_repo, check=True, capture_output=True
    )
    state_dir = tmp_path / "state"
    env = Environment(
        name="feature-x",
        user=USER,
        branch="feature-x",
        worktree=worktree,
        tmux_session=f"{USER}-feature-x",
        compose_file=worktree / "docker-compose.dev.yml",
        port=3000,
        url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None,
    )
    save_state(env, state_dir)
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f'repo = "{git_repo}"\n'
        f'worktree_dir = "{tmp_path / "worktrees"}"\n'
        'data_dir = "/data/dev"\n'
        f'state_dir = "{state_dir}"\n'
        'base_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\n"
        "port_range_end = 3099\n"
    )
    return cfg_file, state_dir, env


def test_down_requires_force_when_branch_not_pushed(setup):
    cfg_file, state_dir, env = setup
    with patch("forsa_dev.cli.down_env", side_effect=RuntimeError("not been pushed")):
        result = runner.invoke(app, ["down", "feature-x", "--config", str(cfg_file)])
    assert result.exit_code != 0
    assert "not been pushed" in result.output or "pushed" in result.output


def test_down_force_removes_everything(setup):
    cfg_file, state_dir, env = setup
    with patch("forsa_dev.cli.down_env") as mock_down:
        result = runner.invoke(app, ["down", "feature-x", "--force", "--config", str(cfg_file)])
    assert result.exit_code == 0, result.output
    mock_down.assert_called_once()
    call_kwargs = mock_down.call_args[1] if mock_down.call_args[1] else {}
    assert call_kwargs.get("force") is True or mock_down.call_args[0][-1] is True


def test_down_not_found(setup):
    cfg_file, state_dir, _ = setup
    with patch("forsa_dev.cli.down_env", side_effect=FileNotFoundError("no env")):
        result = runner.invoke(app, ["down", "nonexistent", "--config", str(cfg_file)])
    assert result.exit_code != 0
    assert "not found" in result.output
