import getpass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forsa_dev.config import Config
from forsa_dev.operations import down_env, restart_env, serve_env, stop_env, up_env
from forsa_dev.state import Environment, load_state, save_state

USER = getpass.getuser()


@pytest.fixture()
def cfg_and_env(tmp_path):
    state_dir = tmp_path / "state"
    worktree = tmp_path / "worktrees" / "ticket-42"
    worktree.mkdir(parents=True)
    compose_file = worktree / "docker-compose.dev.yml"
    compose_file.write_text("services: {}")
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
    cfg = Config(
        repo=tmp_path / "repo",
        worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"),
        state_dir=state_dir,
        base_url="optbox.example.ts.net",
        docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000,
        port_range_end=3099,
        ttyd_port_range_start=7600,
        ttyd_port_range_end=7699,
    )
    return cfg, env


def test_serve_env_updates_state(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        serve_env(cfg, USER, "ticket-42")
    updated = load_state(USER, "ticket-42", cfg.state_dir)
    assert updated.url == "http://optbox.example.ts.net:3002"
    assert updated.served_at is not None


def test_serve_env_raises_on_compose_failure(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        with pytest.raises(RuntimeError):
            serve_env(cfg, USER, "ticket-42")


def test_stop_env_clears_state(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        stop_env(cfg, USER, "ticket-42")
    updated = load_state(USER, "ticket-42", cfg.state_dir)
    assert updated.url is None
    assert updated.served_at is None


def test_restart_env_calls_compose_restart(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        restart_env(cfg, USER, "ticket-42")
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "restart" in cmd


@pytest.fixture()
def up_cfg(tmp_path, git_repo):
    state_dir = tmp_path / "state"
    cfg = Config(
        repo=git_repo,
        worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"),
        state_dir=state_dir,
        base_url="optbox.example.ts.net",
        docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000,
        port_range_end=3099,
        ttyd_port_range_start=7600,
        ttyd_port_range_end=7699,
    )
    return cfg


def test_up_env_creates_environment(up_cfg):
    cfg = up_cfg
    with patch("forsa_dev.operations.tmux.create_session"), \
         patch("forsa_dev.operations.ttyd.start_ttyd", return_value=12345):
        env = up_env(cfg, USER, "new-feature")
    assert env.name == "new-feature"
    assert env.user == USER
    assert env.branch == "new-feature"
    assert env.port == 3000
    assert env.ttyd_port == 7600
    assert env.ttyd_pid == 12345
    # State was persisted
    saved = load_state(USER, "new-feature", cfg.state_dir)
    assert saved.ttyd_pid == 12345


def test_up_env_with_claude_passes_command_to_tmux(up_cfg):
    cfg = up_cfg
    with patch("forsa_dev.operations.tmux.create_session") as mock_create, \
         patch("forsa_dev.operations.ttyd.start_ttyd", return_value=99):
        up_env(cfg, USER, "new-feature", with_claude=True)
    assert mock_create.call_args.kwargs["command"] is not None
    assert "claude" in mock_create.call_args.kwargs["command"]
    assert "zsh" in mock_create.call_args.kwargs["command"]


def test_up_env_raises_if_already_exists(cfg_and_env):
    cfg, _ = cfg_and_env
    with pytest.raises(ValueError, match="already exists"):
        up_env(cfg, USER, "ticket-42")


@pytest.mark.parametrize("bad_name", [
    "Testing", "Ticket-42", "UPPER", "ticket 42", "ticket.42", "-ticket",
])
def test_up_env_rejects_invalid_name(up_cfg, bad_name):
    cfg = up_cfg
    with pytest.raises(ValueError, match="Invalid environment name"):
        up_env(cfg, USER, bad_name)


def test_down_env_cleans_up(cfg_and_env, git_repo):
    cfg, env = cfg_and_env
    # Give the env a ttyd_pid
    from dataclasses import replace
    env_with_pid = replace(env, ttyd_pid=9999)
    save_state(env_with_pid, cfg.state_dir)

    with patch("forsa_dev.operations.git.branch_is_pushed", return_value=True), \
         patch("subprocess.run", return_value=MagicMock(returncode=0)), \
         patch("forsa_dev.operations.tmux.kill_session"), \
         patch("forsa_dev.operations.ttyd.stop_ttyd") as mock_stop, \
         patch("forsa_dev.operations.git.remove_worktree"), \
         patch("forsa_dev.operations.git.delete_branch"):
        down_env(cfg, USER, "ticket-42")

    mock_stop.assert_called_once_with(9999)
    from forsa_dev.state import _state_path
    assert not _state_path(USER, "ticket-42", cfg.state_dir).exists()


def test_down_env_raises_if_branch_not_pushed(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.operations.git.branch_is_pushed", return_value=False):
        with pytest.raises(RuntimeError, match="not been pushed"):
            down_env(cfg, USER, "ticket-42")


def test_up_env_rolls_back_on_ttyd_failure(up_cfg):
    cfg = up_cfg
    with patch("forsa_dev.operations.tmux.create_session"), \
         patch("forsa_dev.operations.ttyd.start_ttyd", side_effect=RuntimeError("ttyd failed")), \
         patch("forsa_dev.operations.tmux.kill_session") as mock_kill, \
         patch("forsa_dev.operations.git.remove_worktree"), \
         patch("forsa_dev.operations.git.delete_branch"):
        with pytest.raises(RuntimeError, match="ttyd failed"):
            up_env(cfg, USER, "new-feature")

    mock_kill.assert_called_once_with(f"{USER}-new-feature")
    from forsa_dev.state import _state_path
    assert not _state_path(USER, "new-feature", cfg.state_dir).exists()


def test_up_env_rolls_back_on_port_allocation_failure(up_cfg):
    cfg = up_cfg
    with patch("forsa_dev.operations.allocate_ports", side_effect=RuntimeError("No free ports")), \
         patch("forsa_dev.operations.git.remove_worktree") as mock_remove, \
         patch("forsa_dev.operations.git.delete_branch") as mock_delete:
        with pytest.raises(RuntimeError, match="No free ports"):
            up_env(cfg, USER, "new-feature")

    mock_remove.assert_called_once()
    mock_delete.assert_called_once()
    from forsa_dev.state import _state_path
    assert not _state_path(USER, "new-feature", cfg.state_dir).exists()


def test_up_env_rolls_back_on_tmux_failure(up_cfg):
    cfg = up_cfg
    tmux_exc = RuntimeError("tmux failed")
    with patch("forsa_dev.operations.tmux.create_session", side_effect=tmux_exc), \
         patch("forsa_dev.operations.git.remove_worktree") as mock_remove, \
         patch("forsa_dev.operations.git.delete_branch") as mock_delete:
        with pytest.raises(RuntimeError, match="tmux failed"):
            up_env(cfg, USER, "new-feature")

    mock_remove.assert_called_once()
    mock_delete.assert_called_once()
    from forsa_dev.state import _state_path
    assert not _state_path(USER, "new-feature", cfg.state_dir).exists()


def test_compose_cmd_format(cfg_and_env):
    from forsa_dev.operations import compose_cmd
    cfg, env = cfg_and_env
    cmd = compose_cmd(env, "up", "-d")
    assert cmd[0:2] == ["docker", "compose"]
    assert "-p" in cmd
    assert f"{USER}-ticket-42" in cmd
    assert "-f" in cmd
    assert str(env.compose_file) in cmd
    assert "up" in cmd
    assert "-d" in cmd
