from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from forsa_dev.config import Config
from forsa_dev.dashboard.server import create_app
from forsa_dev.state import Environment, save_state

TEST_USER = "testuser"


@pytest.fixture()
def setup(tmp_path):
    state_dir = tmp_path / "state"
    worktree = tmp_path / "worktrees" / "ticket-42"
    worktree.mkdir(parents=True)
    compose_file = worktree / "docker-compose.dev.yml"
    compose_file.write_text("services: {}")
    env = Environment(
        name="ticket-42",
        user=TEST_USER,
        branch="ticket-42",
        worktree=worktree,
        tmux_session=f"{TEST_USER}-ticket-42",
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
        ttyd_port_range_start=7600,
        ttyd_port_range_end=7699,
    )
    user_configs = {TEST_USER: cfg}
    return user_configs, cfg, env


def test_get_users_returns_configured_users(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    response = client.get("/api/users")
    assert response.status_code == 200
    assert response.json() == [{"name": TEST_USER}]


def test_get_users_multiple_users(tmp_path):
    state_dir = tmp_path / "state"
    cfg1 = Config(
        repo=tmp_path, worktree_dir=tmp_path, data_dir=Path("/data/dev"),
        state_dir=state_dir, base_url="localhost", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"), port_range_start=3000, port_range_end=3099,
    )
    cfg2 = Config(
        repo=tmp_path, worktree_dir=tmp_path / "other", data_dir=Path("/data/dev"),
        state_dir=state_dir, base_url="localhost", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"), port_range_start=3000, port_range_end=3099,
    )
    user_configs = {"anders": cfg1, "hanna": cfg2}
    app = create_app(user_configs)
    client = TestClient(app)
    response = client.get("/api/users")
    assert response.status_code == 200
    names = [u["name"] for u in response.json()]
    assert "anders" in names
    assert "hanna" in names


def test_get_environments_returns_list(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.tmux") as mock_tmux, \
         patch("forsa_dev.dashboard.server.port_is_open", return_value=False), \
         patch("forsa_dev.dashboard.server.ttyd") as mock_ttyd:
        mock_tmux.session_status.return_value = "active"
        mock_ttyd.ttyd_is_alive.return_value = False
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.get("/api/environments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "ticket-42"
    assert data[0]["user"] == TEST_USER
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
    app = create_app({TEST_USER: cfg})
    client = TestClient(app)
    response = client.get("/api/environments")
    assert response.status_code == 200
    assert response.json() == []


def test_get_health_returns_system_info(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
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


def test_post_serve_calls_serve_env(setup):
    user_configs, cfg, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.serve_env") as mock_serve, \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        response = client.post("/api/environments/ticket-42/serve")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_serve.assert_called_once_with(cfg, TEST_USER, "ticket-42")


def test_post_serve_404_when_not_found(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.serve_env", side_effect=FileNotFoundError()), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        response = client.post("/api/environments/nonexistent/serve")
    assert response.status_code == 404


def test_post_serve_500_on_runtime_error(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.serve_env", side_effect=RuntimeError("compose failed")), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        response = client.post("/api/environments/ticket-42/serve")
    assert response.status_code == 500


def test_post_stop_calls_stop_env(setup):
    user_configs, cfg, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.stop_env") as mock_stop, \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        response = client.post("/api/environments/ticket-42/stop")
    assert response.status_code == 200
    mock_stop.assert_called_once_with(cfg, TEST_USER, "ticket-42")


def test_post_stop_404_when_not_found(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.stop_env", side_effect=FileNotFoundError()), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        response = client.post("/api/environments/nonexistent/stop")
    assert response.status_code == 404


def test_post_stop_500_on_runtime_error(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.stop_env", side_effect=RuntimeError("compose failed")), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        response = client.post("/api/environments/ticket-42/stop")
    assert response.status_code == 500


def test_post_restart_calls_restart_env(setup):
    user_configs, cfg, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.restart_env") as mock_restart, \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        response = client.post("/api/environments/ticket-42/restart")
    assert response.status_code == 200
    mock_restart.assert_called_once_with(cfg, TEST_USER, "ticket-42")


def test_post_restart_404_when_not_found(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.restart_env", side_effect=FileNotFoundError()), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        response = client.post("/api/environments/nonexistent/restart")
    assert response.status_code == 404


def test_post_restart_500_on_runtime_error(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    with patch("forsa_dev.dashboard.server.restart_env", side_effect=RuntimeError("compose failed")), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        response = client.post("/api/environments/ticket-42/restart")
    assert response.status_code == 500


def test_get_environments_includes_ttyd_port(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.tmux") as mock_tmux, \
         patch("forsa_dev.dashboard.server.port_is_open", return_value=False), \
         patch("forsa_dev.dashboard.server.ttyd") as mock_ttyd:
        mock_tmux.session_status.return_value = "active"
        mock_ttyd.ttyd_is_alive.return_value = False
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.get("/api/environments")
    assert response.status_code == 200
    data = response.json()
    assert "ttyd_port" in data[0]
    assert "ttyd" in data[0]["status"]


def test_post_create_environment_calls_up_env(setup):
    user_configs, cfg, _ = setup
    mock_env = MagicMock()
    mock_env.name = "new-env"
    mock_env.port = 3003
    mock_env.ttyd_port = 7603
    with patch("forsa_dev.dashboard.server.up_env", return_value=mock_env) as mock_up, \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.post("/api/environments", json={"name": "new-env", "from_branch": "main"})
    assert response.status_code == 200
    mock_up.assert_called_once_with(
        cfg, TEST_USER, "new-env", from_branch="main", with_claude=True, data_dir=None,
        existing_branch=None,
    )


def test_post_create_environment_respects_with_claude_false(setup):
    user_configs, cfg, _ = setup
    mock_env = MagicMock()
    mock_env.name = "new-env"
    mock_env.port = 3003
    mock_env.ttyd_port = 7603
    payload = {"name": "new-env", "from_branch": "main", "with_claude": False}
    with patch("forsa_dev.dashboard.server.up_env", return_value=mock_env) as mock_up, \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.post("/api/environments", json=payload)
    assert response.status_code == 200
    mock_up.assert_called_once_with(
        cfg, TEST_USER, "new-env", from_branch="main", with_claude=False, data_dir=None,
        existing_branch=None,
    )


def test_post_create_environment_409_if_exists(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.up_env", side_effect=ValueError("already exists")), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.post(
            "/api/environments", json={"name": "ticket-42", "from_branch": "main"}
        )
    assert response.status_code == 409


def test_post_create_environment_500_on_runtime_error(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.up_env", side_effect=RuntimeError("git failed")), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.post("/api/environments", json={"name": "new", "from_branch": "main"})
    assert response.status_code == 500


def test_delete_environment_calls_down_env(setup):
    user_configs, cfg, _ = setup
    with patch("forsa_dev.dashboard.server.down_env") as mock_down, \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.delete("/api/environments/ticket-42")
    assert response.status_code == 200
    mock_down.assert_called_once_with(cfg, TEST_USER, "ticket-42", force=False)


def test_delete_environment_force_param(setup):
    user_configs, cfg, _ = setup
    with patch("forsa_dev.dashboard.server.down_env") as mock_down, \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.delete("/api/environments/ticket-42?force=true")
    assert response.status_code == 200
    mock_down.assert_called_once_with(cfg, TEST_USER, "ticket-42", force=True)


def test_delete_environment_404_when_not_found(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.down_env", side_effect=FileNotFoundError()), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.delete("/api/environments/nonexistent")
    assert response.status_code == 404


def test_delete_environment_409_on_unpushed_branch(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.down_env", side_effect=RuntimeError("not been pushed")), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.delete("/api/environments/ticket-42")
    assert response.status_code == 409


def test_get_branches_returns_list(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.git.list_branches", return_value=["feature-a", "feature-b"]), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.get("/api/branches")
    assert response.status_code == 200
    assert response.json() == {"branches": ["feature-a", "feature-b"]}


def test_get_branches_500_on_runtime_error(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.git.list_branches", side_effect=RuntimeError("git failed")), \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.get("/api/branches")
    assert response.status_code == 500


def test_post_create_environment_with_existing_branch(setup):
    user_configs, cfg, _ = setup
    mock_env = MagicMock()
    mock_env.name = "my-feature"
    mock_env.port = 3003
    mock_env.ttyd_port = 7603
    payload = {"name": "my-feature", "from_branch": "main", "existing_branch": "feature/my-feature"}
    with patch("forsa_dev.dashboard.server.up_env", return_value=mock_env) as mock_up, \
         patch("forsa_dev.dashboard.server.getpass") as mock_getpass:
        mock_getpass.getuser.return_value = TEST_USER
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.post("/api/environments", json=payload)
    assert response.status_code == 200
    mock_up.assert_called_once_with(
        cfg, TEST_USER, "my-feature",
        from_branch="main",
        with_claude=True,
        data_dir=None,
        existing_branch="feature/my-feature",
    )
