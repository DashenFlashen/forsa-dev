import getpass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from forsa_dev.config import Config
from forsa_dev.dashboard.server import create_app
from forsa_dev.state import Environment, save_state

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
        base_url="localhost",
        docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000,
        port_range_end=3099,
    )
    return cfg, env


def test_get_environments_returns_list(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.dashboard.server.tmux") as mock_tmux, \
         patch("forsa_dev.dashboard.server.port_is_open", return_value=False):
        mock_tmux.session_status.return_value = "active"
        app = create_app(cfg)
        client = TestClient(app)
        response = client.get("/api/environments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "ticket-42"
    assert data[0]["user"] == USER
    assert data[0]["port"] == 3002
    assert data[0]["status"]["tmux"] == "active"
    assert data[0]["status"]["server"] == "stopped"


def test_get_environments_empty_state_dir(tmp_path):
    cfg = Config(
        repo=tmp_path,
        worktree_dir=tmp_path,
        data_dir=Path("/data/dev"),
        state_dir=tmp_path / "nonexistent",
        base_url="localhost",
        docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000,
        port_range_end=3099,
    )
    app = create_app(cfg)
    client = TestClient(app)
    response = client.get("/api/environments")
    assert response.status_code == 200
    assert response.json() == []


def test_get_health_returns_system_info(cfg_and_env):
    cfg, _ = cfg_and_env
    app = create_app(cfg)
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "cpu_percent" in data
    assert "cpu_count" in data
    assert "ram_used_gb" in data
    assert "ram_total_gb" in data
    assert "disk_used_gb" in data
    assert "disk_total_gb" in data


def test_post_serve_calls_serve_env(cfg_and_env):
    cfg, _ = cfg_and_env
    app = create_app(cfg)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.serve_env") as mock_serve:
        response = client.post("/api/environments/ticket-42/serve")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_serve.assert_called_once_with(cfg, USER, "ticket-42")


def test_post_serve_404_when_not_found(cfg_and_env):
    cfg, _ = cfg_and_env
    app = create_app(cfg)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.serve_env", side_effect=FileNotFoundError()):
        response = client.post("/api/environments/nonexistent/serve")
    assert response.status_code == 404


def test_post_serve_500_on_runtime_error(cfg_and_env):
    cfg, _ = cfg_and_env
    app = create_app(cfg)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.serve_env", side_effect=RuntimeError("compose failed")):
        response = client.post("/api/environments/ticket-42/serve")
    assert response.status_code == 500


def test_post_stop_calls_stop_env(cfg_and_env):
    cfg, _ = cfg_and_env
    app = create_app(cfg)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.stop_env") as mock_stop:
        response = client.post("/api/environments/ticket-42/stop")
    assert response.status_code == 200
    mock_stop.assert_called_once_with(cfg, USER, "ticket-42")


def test_post_stop_404_when_not_found(cfg_and_env):
    cfg, _ = cfg_and_env
    app = create_app(cfg)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.stop_env", side_effect=FileNotFoundError()):
        response = client.post("/api/environments/nonexistent/stop")
    assert response.status_code == 404


def test_post_restart_calls_restart_env(cfg_and_env):
    cfg, _ = cfg_and_env
    app = create_app(cfg)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.restart_env") as mock_restart:
        response = client.post("/api/environments/ticket-42/restart")
    assert response.status_code == 200
    mock_restart.assert_called_once_with(cfg, USER, "ticket-42")
