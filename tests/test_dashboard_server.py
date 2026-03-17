from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from forsa_dev.config import Config, save_config
from forsa_dev.dashboard.server import create_app, discover_users
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


# --- GET /api/users ---


def test_create_app_rejects_mismatched_state_dirs(tmp_path):
    cfg1 = Config(
        repo=tmp_path, worktree_dir=tmp_path, data_dir=Path("/data/dev"),
        state_dir=tmp_path / "state-a", base_url="localhost",
        docker_image="forsa:latest", gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
    )
    cfg2 = Config(
        repo=tmp_path, worktree_dir=tmp_path, data_dir=Path("/data/dev"),
        state_dir=tmp_path / "state-b", base_url="localhost",
        docker_image="forsa:latest", gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
    )
    with pytest.raises(ValueError, match="state_dir"):
        create_app({"alice": cfg1, "bob": cfg2})


def test_create_app_rejects_mismatched_base_urls(tmp_path):
    state_dir = tmp_path / "state"
    cfg1 = Config(
        repo=tmp_path, worktree_dir=tmp_path, data_dir=Path("/data/dev"),
        state_dir=state_dir, base_url="host-a.ts.net",
        docker_image="forsa:latest", gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
    )
    cfg2 = Config(
        repo=tmp_path, worktree_dir=tmp_path, data_dir=Path("/data/dev"),
        state_dir=state_dir, base_url="host-b.ts.net",
        docker_image="forsa:latest", gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
    )
    with pytest.raises(ValueError, match="base_url"):
        create_app({"alice": cfg1, "bob": cfg2})


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
    with patch("forsa_dev.dashboard.server.agents"):
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.get("/api/users")
    assert response.status_code == 200
    names = [u["name"] for u in response.json()]
    assert "anders" in names
    assert "hanna" in names


# --- GET /api/environments ---


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


def test_get_environments_includes_worktree(setup):
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
    assert "worktree" in data[0]
    assert data[0]["worktree"].endswith("/worktrees/ticket-42")


# --- GET /api/health ---


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


# --- Cookie auth (401 tests) ---


def test_post_create_returns_401_without_cookie(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    response = client.post("/api/environments", json={"name": "new-env"})
    assert response.status_code == 401


def test_post_create_returns_401_with_invalid_user_cookie(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", "nonexistent")
    response = client.post("/api/environments", json={"name": "new-env"})
    assert response.status_code == 401


def test_post_serve_returns_401_without_cookie(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    response = client.post(f"/api/environments/{TEST_USER}/ticket-42/serve")
    assert response.status_code == 401


def test_get_config_returns_401_without_cookie(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 401


def test_get_branches_returns_401_without_cookie(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    response = client.get("/api/branches")
    assert response.status_code == 401


# --- POST /api/environments (create) ---


def test_post_create_environment_calls_up_env(setup):
    user_configs, cfg, _ = setup
    mock_env = MagicMock()
    mock_env.name = "new-env"
    mock_env.port = 3003
    mock_env.ttyd_port = 7603
    with patch("forsa_dev.dashboard.server.up_env", return_value=mock_env) as mock_up:
        app = create_app(user_configs)
        client = TestClient(app)
        client.cookies.set("forsa_user", TEST_USER)
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
    with patch("forsa_dev.dashboard.server.up_env", return_value=mock_env) as mock_up:
        app = create_app(user_configs)
        client = TestClient(app)
        client.cookies.set("forsa_user", TEST_USER)
        response = client.post("/api/environments", json=payload)
    assert response.status_code == 200
    mock_up.assert_called_once_with(
        cfg, TEST_USER, "new-env", from_branch="main", with_claude=False, data_dir=None,
        existing_branch=None,
    )


def test_post_create_environment_409_if_exists(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.up_env", side_effect=ValueError("already exists")):
        app = create_app(user_configs)
        client = TestClient(app)
        client.cookies.set("forsa_user", TEST_USER)
        response = client.post(
            "/api/environments", json={"name": "ticket-42", "from_branch": "main"}
        )
    assert response.status_code == 409


def test_post_create_environment_500_on_runtime_error(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.up_env", side_effect=RuntimeError("git failed")):
        app = create_app(user_configs)
        client = TestClient(app)
        client.cookies.set("forsa_user", TEST_USER)
        response = client.post("/api/environments", json={"name": "new", "from_branch": "main"})
    assert response.status_code == 500


def test_post_create_environment_with_existing_branch(setup):
    user_configs, cfg, _ = setup
    mock_env = MagicMock()
    mock_env.name = "my-feature"
    mock_env.port = 3003
    mock_env.ttyd_port = 7603
    payload = {"name": "my-feature", "from_branch": "main", "existing_branch": "feature/my-feature"}
    with patch("forsa_dev.dashboard.server.up_env", return_value=mock_env) as mock_up:
        app = create_app(user_configs)
        client = TestClient(app)
        client.cookies.set("forsa_user", TEST_USER)
        response = client.post("/api/environments", json=payload)
    assert response.status_code == 200
    mock_up.assert_called_once_with(
        cfg, TEST_USER, "my-feature",
        from_branch="main",
        with_claude=True,
        data_dir=None,
        existing_branch="feature/my-feature",
    )


# --- POST /api/environments/{owner}/{name}/serve ---


def test_post_serve_calls_serve_env(setup):
    user_configs, cfg, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.serve_env") as mock_serve:
        response = client.post(f"/api/environments/{TEST_USER}/ticket-42/serve")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_serve.assert_called_once_with(cfg, TEST_USER, "ticket-42")


def test_post_serve_unknown_owner_returns_404(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    response = client.post("/api/environments/nobody/ticket-42/serve")
    assert response.status_code == 404


def test_post_serve_404_when_not_found(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.serve_env", side_effect=FileNotFoundError()):
        response = client.post(f"/api/environments/{TEST_USER}/nonexistent/serve")
    assert response.status_code == 404


def test_post_serve_500_on_runtime_error(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.serve_env", side_effect=RuntimeError("compose failed")):
        response = client.post(f"/api/environments/{TEST_USER}/ticket-42/serve")
    assert response.status_code == 500


# --- POST /api/environments/{owner}/{name}/stop ---


def test_post_stop_calls_stop_env(setup):
    user_configs, cfg, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.stop_env") as mock_stop:
        response = client.post(f"/api/environments/{TEST_USER}/ticket-42/stop")
    assert response.status_code == 200
    mock_stop.assert_called_once_with(cfg, TEST_USER, "ticket-42")


def test_post_stop_404_when_not_found(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.stop_env", side_effect=FileNotFoundError()):
        response = client.post(f"/api/environments/{TEST_USER}/nonexistent/stop")
    assert response.status_code == 404


def test_post_stop_500_on_runtime_error(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.stop_env", side_effect=RuntimeError("compose failed")):
        response = client.post(f"/api/environments/{TEST_USER}/ticket-42/stop")
    assert response.status_code == 500


# --- POST /api/environments/{owner}/{name}/restart ---


def test_post_restart_calls_restart_env(setup):
    user_configs, cfg, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.restart_env") as mock_restart:
        response = client.post(f"/api/environments/{TEST_USER}/ticket-42/restart")
    assert response.status_code == 200
    mock_restart.assert_called_once_with(cfg, TEST_USER, "ticket-42")


def test_post_restart_404_when_not_found(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.restart_env", side_effect=FileNotFoundError()):
        response = client.post(f"/api/environments/{TEST_USER}/nonexistent/restart")
    assert response.status_code == 404


def test_post_restart_500_on_runtime_error(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch(
        "forsa_dev.dashboard.server.restart_env", side_effect=RuntimeError("compose failed"),
    ):
        response = client.post(f"/api/environments/{TEST_USER}/ticket-42/restart")
    assert response.status_code == 500


# --- DELETE /api/environments/{owner}/{name} ---


def test_delete_environment_calls_down_env(setup):
    user_configs, cfg, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.down_env") as mock_down:
        response = client.delete(f"/api/environments/{TEST_USER}/ticket-42")
    assert response.status_code == 200
    mock_down.assert_called_once_with(cfg, TEST_USER, "ticket-42", force=False)


def test_delete_environment_force_param(setup):
    user_configs, cfg, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.down_env") as mock_down:
        response = client.delete(f"/api/environments/{TEST_USER}/ticket-42?force=true")
    assert response.status_code == 200
    mock_down.assert_called_once_with(cfg, TEST_USER, "ticket-42", force=True)


def test_delete_environment_404_when_not_found(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.down_env", side_effect=FileNotFoundError()):
        response = client.delete(f"/api/environments/{TEST_USER}/nonexistent")
    assert response.status_code == 404


def test_delete_environment_409_on_unpushed_branch(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    with patch("forsa_dev.dashboard.server.down_env", side_effect=RuntimeError("not been pushed")):
        response = client.delete(f"/api/environments/{TEST_USER}/ticket-42")
    assert response.status_code == 409


# --- GET /api/config ---


def test_get_config_returns_cookie_users_data_dir(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json() == {"data_dir": "/data/dev"}


# --- GET /api/branches ---


def test_get_branches_returns_list(setup):
    user_configs, _, _ = setup
    with patch(
        "forsa_dev.dashboard.server.git.list_branches",
        return_value=["feature-a", "feature-b"],
    ):
        app = create_app(user_configs)
        client = TestClient(app)
        client.cookies.set("forsa_user", TEST_USER)
        response = client.get("/api/branches")
    assert response.status_code == 200
    assert response.json() == {"branches": ["feature-a", "feature-b"]}


def test_get_branches_500_on_runtime_error(setup):
    user_configs, _, _ = setup
    with patch(
        "forsa_dev.dashboard.server.git.list_branches",
        side_effect=RuntimeError("git failed"),
    ):
        app = create_app(user_configs)
        client = TestClient(app)
        client.cookies.set("forsa_user", TEST_USER)
        response = client.get("/api/branches")
    assert response.status_code == 500


# --- discover_users ---


def test_discover_users_loads_configs(tmp_path, monkeypatch):
    home = tmp_path / "home" / "alice"
    config_path = home / ".config" / "forsa" / "config.toml"
    config_path.parent.mkdir(parents=True)

    cfg = Config(
        repo=tmp_path / "repo", worktree_dir=tmp_path / "wt",
        data_dir=Path("/data/dev"), state_dir=tmp_path / "state",
        base_url="localhost", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
    )
    save_config(cfg, config_path)

    mock_group = MagicMock()
    mock_group.gr_mem = ["alice"]
    monkeypatch.setattr("forsa_dev.dashboard.server.grp.getgrnam", lambda name: mock_group)

    mock_pw = MagicMock()
    mock_pw.pw_dir = str(home)
    monkeypatch.setattr("forsa_dev.dashboard.server.pwd.getpwnam", lambda name: mock_pw)

    result = discover_users()
    assert "alice" in result
    assert result["alice"].base_url == "localhost"


def test_discover_users_skips_missing_config(tmp_path, monkeypatch):
    home = tmp_path / "home" / "bob"
    home.mkdir(parents=True)

    mock_group = MagicMock()
    mock_group.gr_mem = ["bob"]
    monkeypatch.setattr("forsa_dev.dashboard.server.grp.getgrnam", lambda name: mock_group)

    mock_pw = MagicMock()
    mock_pw.pw_dir = str(home)
    monkeypatch.setattr("forsa_dev.dashboard.server.pwd.getpwnam", lambda name: mock_pw)

    result = discover_users()
    assert "bob" not in result


def test_discover_users_skips_unreadable_config(tmp_path, monkeypatch):
    home = tmp_path / "home" / "carol"
    config_path = home / ".config" / "forsa" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("dummy")
    config_path.chmod(0o000)

    mock_group = MagicMock()
    mock_group.gr_mem = ["carol"]
    monkeypatch.setattr("forsa_dev.dashboard.server.grp.getgrnam", lambda name: mock_group)

    mock_pw = MagicMock()
    mock_pw.pw_dir = str(home)
    monkeypatch.setattr("forsa_dev.dashboard.server.pwd.getpwnam", lambda name: mock_pw)

    result = discover_users()
    assert "carol" not in result

    # Restore permissions so pytest can clean up tmp_path
    config_path.chmod(0o644)


def test_discover_users_returns_empty_when_group_missing(monkeypatch):
    monkeypatch.setattr(
        "forsa_dev.dashboard.server.grp.getgrnam",
        MagicMock(side_effect=KeyError("forsa-devs")),
    )
    result = discover_users()
    assert result == {}


# --- GET /api/agents ---


def test_get_agents_returns_empty_for_non_anders_user(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.agents") as mock_agents:
        app = create_app(user_configs)
        client = TestClient(app)
        client.cookies.set("forsa_user", TEST_USER)
        response = client.get("/api/agents")
    assert response.status_code == 200
    assert response.json() == []
    mock_agents.agent_status.assert_not_called()


def test_get_agents_returns_status_for_anders(tmp_path):
    state_dir = tmp_path / "state"
    cfg = Config(
        repo=tmp_path, worktree_dir=tmp_path, data_dir=Path("/data/dev"),
        state_dir=state_dir, base_url="localhost", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"), port_range_start=3000, port_range_end=3099,
    )
    user_configs = {"anders": cfg}
    mock_status = [
        {"name": "root-claude", "label": "Root Claude",
         "description": "General purpose", "cwd": "/home/anders",
         "ttyd_port": 7698, "tmux": "detached", "ttyd": "alive"},
        {"name": "forsa-dev-claude", "label": "forsa-dev Claude",
         "description": "Dashboard & CLI",
         "cwd": "/home/anders/repos/forsa-dev",
         "ttyd_port": 7699, "tmux": "detached", "ttyd": "alive"},
    ]
    with patch("forsa_dev.dashboard.server.agents") as mock_agents:
        mock_agents.agent_status.return_value = mock_status
        app = create_app(user_configs)
        client = TestClient(app)
        client.cookies.set("forsa_user", "anders")
        response = client.get("/api/agents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "root-claude"


def test_get_agents_no_auth_returns_empty(setup):
    user_configs, _, _ = setup
    app = create_app(user_configs)
    client = TestClient(app)
    response = client.get("/api/agents")
    assert response.status_code == 200
    assert response.json() == []
