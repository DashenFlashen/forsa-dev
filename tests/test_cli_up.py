import getpass
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from forsa_dev.cli import app
from forsa_dev.state import load_state

runner = CliRunner()


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


def test_up_creates_worktree_state_and_compose(config_file, tmp_path):
    user = getpass.getuser()
    with patch("forsa_dev.tmux.attach_session"), patch("forsa_dev.tmux.create_session"):
        result = runner.invoke(app, ["up", "feature-x", "--config", str(config_file)])

    assert result.exit_code == 0, result.output

    # Check state file
    state_dir = tmp_path / "state"
    env = load_state(user, "feature-x", state_dir)
    assert env.name == "feature-x"
    assert env.branch == "feature-x"
    assert env.port == 3000
    assert env.url is None

    # Check worktree exists
    worktree = tmp_path / "worktrees" / "feature-x"
    assert worktree.exists()

    # Check compose file
    assert (worktree / "docker-compose.dev.yml").exists()


def test_up_fails_if_environment_already_exists(config_file, tmp_path):
    with patch("forsa_dev.tmux.attach_session"), patch("forsa_dev.tmux.create_session"):
        runner.invoke(app, ["up", "feature-x", "--config", str(config_file)])
        result = runner.invoke(app, ["up", "feature-x", "--config", str(config_file)])
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_up_rolls_back_on_tmux_failure(config_file, tmp_path):
    user = getpass.getuser()
    state_dir = tmp_path / "state"
    worktree_dir = tmp_path / "worktrees"
    with patch("forsa_dev.tmux.create_session", side_effect=RuntimeError("tmux failed")):
        result = runner.invoke(app, ["up", "feature-x", "--config", str(config_file)])
    assert result.exit_code != 0
    assert not (state_dir / f"{user}-feature-x.json").exists()
    assert not (worktree_dir / "feature-x").exists()
