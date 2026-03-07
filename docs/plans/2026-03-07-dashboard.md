# Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `forsa-dev dashboard` command that starts a FastAPI web server with a React UI showing all environments and serve/stop/restart controls.

**Architecture:** `operations.py` extracts serve/stop/restart logic so both CLI and dashboard share it. FastAPI backend in `src/forsa_dev/dashboard/server.py`. React/Vite frontend built to `src/forsa_dev/dashboard/static/` and committed to repo.

**Tech Stack:** FastAPI, uvicorn, psutil, React 18, Vite, Tailwind CSS

---

### Task 1: Add `dashboard_port` to Config

**Files:**
- Modify: `src/forsa_dev/config.py`
- Modify: `src/forsa_dev/cli.py` (init command)
- Modify: `tests/test_config.py`
- Modify: `tests/test_cli_init.py`

**Step 1: Write the failing test for backward-compatible load**

In `tests/test_config.py`, add after the existing tests:

```python
def test_load_config_without_dashboard_port_defaults_to_8080(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'repo = "/home/anders/forsa"\n'
        'worktree_dir = "/home/anders/worktrees"\n'
        'data_dir = "/data/dev"\n'
        'state_dir = "/var/lib/forsa-dev"\n'
        'base_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\n"
        "port_range_end = 3099\n"
    )
    config = load_config(config_file)
    assert config.dashboard_port == 8080
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/andersnordmark/work/personal/forsa-dev
uv run pytest tests/test_config.py::test_load_config_without_dashboard_port_defaults_to_8080 -v
```

Expected: `AttributeError: 'Config' object has no attribute 'dashboard_port'`

**Step 3: Implement the config changes**

In `src/forsa_dev/config.py`:

1. Add `dashboard_port: int = 8080` as the last field in `Config`:
```python
@dataclass(frozen=True)
class Config:
    repo: Path
    worktree_dir: Path
    data_dir: Path
    state_dir: Path
    base_url: str
    docker_image: str
    gurobi_lic: Path
    port_range_start: int
    port_range_end: int
    dashboard_port: int = 8080
```

2. In `load_config`, add `dashboard_port=int(data.get("dashboard_port", 8080)),` as the last line before the closing `)`:
```python
    return Config(
        repo=Path(data["repo"]),
        worktree_dir=Path(data["worktree_dir"]),
        data_dir=Path(data["data_dir"]),
        state_dir=Path(data["state_dir"]),
        base_url=data["base_url"],
        docker_image=data["docker_image"],
        gurobi_lic=Path(data["gurobi_lic"]),
        port_range_start=int(data["port_range_start"]),
        port_range_end=int(data["port_range_end"]),
        dashboard_port=int(data.get("dashboard_port", 8080)),
    )
```

3. In `save_config`, add `"dashboard_port": config.dashboard_port,` to the data dict:
```python
    data: dict[str, Any] = {
        "repo": str(config.repo),
        "worktree_dir": str(config.worktree_dir),
        "data_dir": str(config.data_dir),
        "state_dir": str(config.state_dir),
        "base_url": config.base_url,
        "docker_image": config.docker_image,
        "gurobi_lic": str(config.gurobi_lic),
        "port_range_start": config.port_range_start,
        "port_range_end": config.port_range_end,
        "dashboard_port": config.dashboard_port,
    }
```

**Step 4: Update existing Config() calls in test_config.py and test_cli_init.py**

In `tests/test_config.py`, the `test_save_config_roundtrip` test creates a `Config(...)` without `dashboard_port`. Since `dashboard_port` has a default value this will still work. But add `assert loaded.dashboard_port == 8080` to that test to verify the field round-trips.

In `tests/test_cli_init.py`:
- Add `"8080"` to the `inputs` list (after `"3099"`)
- Add `assert cfg.dashboard_port == 8080` at the end

**Step 5: Update the `init` command in cli.py**

Add this prompt before `cfg = Config(...)`:
```python
    dashboard_port = typer.prompt("Dashboard port", default=8080)
```

Add `dashboard_port=int(dashboard_port),` to the `Config(...)` constructor call.

**Step 6: Run all config and init tests**

```bash
uv run pytest tests/test_config.py tests/test_cli_init.py -v
```

Expected: all PASS

**Step 7: Commit**

```bash
git add src/forsa_dev/config.py src/forsa_dev/cli.py tests/test_config.py tests/test_cli_init.py
git commit -m "feat: add dashboard_port to Config (default 8080)"
```

---

### Task 2: Create `operations.py`

Extract serve/stop/restart logic from cli.py into a reusable module. Move `_compose_cmd` and `_format_uptime` out of cli.py.

**Files:**
- Create: `src/forsa_dev/operations.py`
- Modify: `src/forsa_dev/cli.py`
- Create: `tests/test_operations.py`

**Step 1: Write the failing tests**

Create `tests/test_operations.py`:

```python
import getpass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forsa_dev.config import Config
from forsa_dev.operations import restart_env, serve_env, stop_env
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
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_operations.py -v
```

Expected: `ModuleNotFoundError: No module named 'forsa_dev.operations'`

**Step 3: Create `src/forsa_dev/operations.py`**

```python
from __future__ import annotations

import subprocess
from datetime import datetime, timezone

from forsa_dev.config import Config
from forsa_dev.state import Environment, load_state, save_state


def _compose_cmd(env: Environment, *args: str) -> list[str]:
    return [
        "docker", "compose",
        "-p", f"{env.user}-{env.name}",
        "-f", str(env.compose_file),
        *args,
    ]


def serve_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    result = subprocess.run(_compose_cmd(env, "up", "-d"), check=False)
    if result.returncode != 0:
        raise RuntimeError("docker compose up failed")
    url = f"http://{cfg.base_url}:{env.port}"
    updated = Environment(**{**env.__dict__, "url": url, "served_at": datetime.now(tz=timezone.utc)})
    save_state(updated, cfg.state_dir)


def stop_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    subprocess.run(_compose_cmd(env, "down"), check=False)
    updated = Environment(**{**env.__dict__, "url": None, "served_at": None})
    save_state(updated, cfg.state_dir)


def restart_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    subprocess.run(_compose_cmd(env, "restart"), check=False)
```

**Step 4: Run operations tests to verify they pass**

```bash
uv run pytest tests/test_operations.py -v
```

Expected: all 4 PASS

**Step 5: Update `cli.py` to use `operations.py`**

Replace the `_compose_cmd` function definition in `cli.py` with an import. The `down` command still needs `_compose_cmd` directly, so import it:

```python
from forsa_dev.operations import _compose_cmd, serve_env, stop_env, restart_env
```

Also add `_format_uptime` to `list_status.py` and import it in `cli.py`. Add to `src/forsa_dev/list_status.py`:

```python
from datetime import datetime, timezone


def format_uptime(served_at: datetime | None) -> str:
    if served_at is None:
        return "-"
    delta = datetime.now(tz=timezone.utc) - served_at
    seconds = int(delta.total_seconds())
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    return f"{seconds // 86400}d {(seconds % 86400) // 3600}h"
```

Replace the `serve`, `stop`, and `restart` command bodies in `cli.py` to delegate:

```python
@app.command()
def serve(
    name: str,
    config: ConfigOption = None,
):
    """Start the Docker server for an environment."""
    cfg = _load(config)
    user = getpass.getuser()
    env = load_state(user, name, cfg.state_dir)
    typer.echo(f"Starting server on port {env.port}...")
    try:
        serve_env(cfg, user, name)
    except RuntimeError:
        typer.echo("Error: docker compose up failed.", err=True)
        raise typer.Exit(1)
    updated = load_state(user, name, cfg.state_dir)
    typer.echo(f"Serving at {updated.url}")


@app.command()
def stop(
    name: str,
    config: ConfigOption = None,
):
    """Stop the Docker server. Tmux session is preserved."""
    cfg = _load(config)
    user = getpass.getuser()
    typer.echo("Stopping server...")
    stop_env(cfg, user, name)
    typer.echo("Server stopped. Tmux session preserved.")


@app.command()
def restart(
    name: str,
    config: ConfigOption = None,
):
    """Restart the Docker containers."""
    cfg = _load(config)
    user = getpass.getuser()
    typer.echo("Restarting...")
    restart_env(cfg, user, name)
    typer.echo("Done.")
```

Remove the `_compose_cmd` function definition from `cli.py` (it's now imported from `operations`).

Remove the `_format_uptime` function definition from `cli.py`, import it from `list_status`:
```python
from forsa_dev.list_status import check_status, format_uptime, port_is_open
```

And in the `list_envs` command, change `_format_uptime(env.served_at)` to `format_uptime(env.served_at)`.

**Step 6: Run all tests to verify nothing broke**

```bash
uv run pytest -v
```

Expected: all PASS

**Step 7: Commit**

```bash
git add src/forsa_dev/operations.py src/forsa_dev/cli.py src/forsa_dev/list_status.py tests/test_operations.py
git commit -m "feat: extract operations.py with serve/stop/restart functions"
```

---

### Task 3: Add Python dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add dependencies**

In `pyproject.toml`, update `[project] dependencies`:

```toml
dependencies = [
    "typer>=0.12",
    "rich>=13",
    "requests>=2.32",
    "tomli-w>=1.1",
    "fastapi>=0.100",
    "uvicorn>=0.29",
    "psutil>=6",
]
```

In `[dependency-groups] dev`, add `"httpx>=0.27"` (required by FastAPI's TestClient):

```toml
[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-httpserver>=1.1",
    "pyyaml>=6",
    "ruff>=0.15.5",
    "httpx>=0.27",
]
```

**Step 2: Sync and verify**

```bash
cd /Users/andersnordmark/work/personal/forsa-dev
uv sync
```

Expected: packages installed without errors

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add fastapi, uvicorn, psutil deps for dashboard"
```

---

### Task 4: Create `dashboard/server.py`

**Files:**
- Create: `src/forsa_dev/dashboard/__init__.py`
- Create: `src/forsa_dev/dashboard/server.py`
- Create: `tests/test_dashboard_server.py`

**Step 1: Write the failing tests**

Create `tests/test_dashboard_server.py`:

```python
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
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_dashboard_server.py -v
```

Expected: `ModuleNotFoundError: No module named 'forsa_dev.dashboard'`

**Step 3: Create `src/forsa_dev/dashboard/__init__.py`**

Empty file:
```python
```

**Step 4: Create `src/forsa_dev/dashboard/server.py`**

```python
from __future__ import annotations

import getpass
from pathlib import Path
from typing import Any

import psutil
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from forsa_dev import tmux
from forsa_dev.config import Config
from forsa_dev.list_status import check_status, format_uptime, port_is_open
from forsa_dev.operations import restart_env, serve_env, stop_env
from forsa_dev.state import list_states


def create_app(cfg: Config) -> FastAPI:
    app = FastAPI()

    @app.get("/api/environments")
    def get_environments() -> list[dict[str, Any]]:
        envs = list_states(cfg.state_dir)
        result = []
        for env in envs:
            tmux_stat = tmux.session_status(env.tmux_session)
            port_open = port_is_open(env.port)
            status = check_status(
                tmux_status=tmux_stat, served=env.url is not None, port_open=port_open
            )
            result.append({
                "name": env.name,
                "user": env.user,
                "branch": env.branch,
                "port": env.port,
                "url": env.url or f"http://{cfg.base_url}:{env.port}",
                "created_at": env.created_at.isoformat(),
                "served_at": env.served_at.isoformat() if env.served_at else None,
                "status": {"tmux": status.tmux, "server": status.server},
                "uptime": format_uptime(env.served_at),
            })
        return result

    @app.get("/api/health")
    def get_health() -> dict[str, Any]:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_percent": cpu,
            "cpu_count": psutil.cpu_count(),
            "ram_used_gb": round(mem.used / 1e9, 1),
            "ram_total_gb": round(mem.total / 1e9, 1),
            "disk_used_gb": round(disk.used / 1e9, 0),
            "disk_total_gb": round(disk.total / 1e9, 0),
        }

    @app.post("/api/environments/{name}/serve")
    def post_serve(name: str) -> dict[str, str]:
        user = getpass.getuser()
        try:
            serve_env(cfg, user, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"status": "ok"}

    @app.post("/api/environments/{name}/stop")
    def post_stop(name: str) -> dict[str, str]:
        user = getpass.getuser()
        try:
            stop_env(cfg, user, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        return {"status": "ok"}

    @app.post("/api/environments/{name}/restart")
    def post_restart(name: str) -> dict[str, str]:
        user = getpass.getuser()
        try:
            restart_env(cfg, user, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        return {"status": "ok"}

    # Serve built React app — mounted last so API routes take precedence
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists() and any(static_dir.iterdir()):
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
```

**Step 5: Run tests**

```bash
uv run pytest tests/test_dashboard_server.py -v
```

Expected: all 9 PASS

**Step 6: Run full test suite**

```bash
uv run pytest -v
```

Expected: all PASS

**Step 7: Commit**

```bash
git add src/forsa_dev/dashboard/__init__.py src/forsa_dev/dashboard/server.py tests/test_dashboard_server.py
git commit -m "feat: add dashboard FastAPI server with environments and health endpoints"
```

---

### Task 5: Add `dashboard` CLI command

**Files:**
- Modify: `src/forsa_dev/cli.py`
- Create: `tests/test_cli_dashboard.py`

**Step 1: Write the failing test**

Create `tests/test_cli_dashboard.py`:

```python
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from forsa_dev.cli import app

runner = CliRunner()


def _make_config(tmp_path, dashboard_port=8080):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f'repo = "{tmp_path}"\n'
        f'worktree_dir = "{tmp_path}"\n'
        'data_dir = "/data/dev"\n'
        f'state_dir = "{tmp_path}"\n'
        'base_url = "localhost"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\n"
        "port_range_end = 3099\n"
        f"dashboard_port = {dashboard_port}\n"
    )
    return cfg_file


def test_dashboard_starts_uvicorn_on_config_port(tmp_path):
    cfg_file = _make_config(tmp_path, dashboard_port=8080)
    mock_app = MagicMock()
    with patch("forsa_dev.dashboard.server.create_app", return_value=mock_app), \
         patch("uvicorn.run") as mock_run:
        result = runner.invoke(app, ["dashboard", "--config", str(cfg_file)])
    assert result.exit_code == 0, result.output
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert kwargs["port"] == 8080


def test_dashboard_port_flag_overrides_config(tmp_path):
    cfg_file = _make_config(tmp_path, dashboard_port=8080)
    mock_app = MagicMock()
    with patch("forsa_dev.dashboard.server.create_app", return_value=mock_app), \
         patch("uvicorn.run") as mock_run:
        result = runner.invoke(app, ["dashboard", "--config", str(cfg_file), "--port", "9090"])
    assert result.exit_code == 0, result.output
    args, kwargs = mock_run.call_args
    assert kwargs["port"] == 9090
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_cli_dashboard.py -v
```

Expected: `Error: No such command 'dashboard'`

**Step 3: Add the command to `cli.py`**

Add this import near the top of cli.py:
```python
from typing import Annotated, Optional
```
(Already there, just verify it.)

Add the `dashboard` command at the end of cli.py (before the final `app` calls, after `list_envs`):

```python
@app.command()
def dashboard(
    config: ConfigOption = None,
    port: Annotated[Optional[int], typer.Option("--port", help="Override dashboard port.")] = None,
):
    """Start the web dashboard."""
    import uvicorn
    from forsa_dev.dashboard.server import create_app

    cfg = _load(config)
    actual_port = port if port is not None else cfg.dashboard_port
    app_instance = create_app(cfg)
    uvicorn.run(app_instance, host="0.0.0.0", port=actual_port)
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_cli_dashboard.py -v
```

Expected: both PASS

**Step 5: Run full test suite**

```bash
uv run pytest -v
```

Expected: all PASS

**Step 6: Commit**

```bash
git add src/forsa_dev/cli.py tests/test_cli_dashboard.py
git commit -m "feat: add forsa-dev dashboard CLI command"
```

---

### Task 6: Scaffold React/Vite frontend

**Files:**
- Create: `dashboard/package.json`
- Create: `dashboard/vite.config.js`
- Create: `dashboard/index.html`
- Create: `dashboard/src/main.jsx`
- Create: `dashboard/src/App.jsx`
- Create: `dashboard/tailwind.config.js`
- Create: `dashboard/postcss.config.js`
- Create: `dashboard/.gitignore`

**Step 1: Create `dashboard/package.json`**

```json
{
  "name": "forsa-dev-dashboard",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.14",
    "vite": "^5.4.10"
  }
}
```

**Step 2: Create `dashboard/vite.config.js`**

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
  build: {
    outDir: '../src/forsa_dev/dashboard/static',
    emptyOutDir: true,
  },
})
```

**Step 3: Create `dashboard/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**Step 4: Create `dashboard/postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

**Step 5: Create `dashboard/index.html`**

```html
<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>forsa-dev dashboard</title>
  </head>
  <body class="bg-gray-950 text-gray-100 min-h-screen">
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

**Step 6: Create `dashboard/src/main.jsx`**

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

**Step 7: Create `dashboard/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Step 8: Create `dashboard/src/App.jsx`** (minimal placeholder to verify build works)

```jsx
export default function App() {
  return <div className="p-4">Loading...</div>
}
```

**Step 9: Create `dashboard/.gitignore`**

```
node_modules/
dist/
```

**Step 10: Install deps and verify scaffold builds**

```bash
cd /Users/andersnordmark/work/personal/forsa-dev/dashboard
npm install
npm run build
```

Expected: build succeeds, `src/forsa_dev/dashboard/static/` contains `index.html` and assets.

**Step 11: Commit**

```bash
cd /Users/andersnordmark/work/personal/forsa-dev
git add dashboard/ src/forsa_dev/dashboard/static/
git commit -m "feat: scaffold React/Vite frontend for dashboard"
```

---

### Task 7: Implement React components

**Files:**
- Create: `dashboard/src/components/HealthBar.jsx`
- Create: `dashboard/src/components/EnvironmentTable.jsx`
- Create: `dashboard/src/components/EnvironmentRow.jsx`
- Create: `dashboard/src/components/ActionButtons.jsx`
- Create: `dashboard/src/components/ErrorBanner.jsx`
- Modify: `dashboard/src/App.jsx`

**Step 1: Create `dashboard/src/components/ErrorBanner.jsx`**

```jsx
export default function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <div className="mb-4 rounded border border-red-500 bg-red-950 px-4 py-3 text-red-200">
      {message}
    </div>
  )
}
```

**Step 2: Create `dashboard/src/components/HealthBar.jsx`**

```jsx
function Bar({ label, value, max, unit }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  const color = pct > 85 ? 'bg-red-500' : pct > 60 ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div className="flex items-center gap-3">
      <span className="w-28 shrink-0 text-sm text-gray-400">{label}</span>
      <div className="h-2 flex-1 overflow-hidden rounded bg-gray-700">
        <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-32 text-right text-sm text-gray-300">
        {value.toFixed(1)} / {max.toFixed(1)} {unit}
      </span>
    </div>
  )
}

export default function HealthBar({ health }) {
  if (!health) return null
  return (
    <div className="mb-6 rounded-lg border border-gray-800 bg-gray-900 p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
        System Health
      </h2>
      <div className="space-y-2">
        <Bar label={`CPU (${health.cpu_count} cores)`} value={health.cpu_percent} max={100} unit="%" />
        <Bar label="RAM" value={health.ram_used_gb} max={health.ram_total_gb} unit="GB" />
        <Bar label="Disk" value={health.disk_used_gb} max={health.disk_total_gb} unit="GB" />
      </div>
    </div>
  )
}
```

**Step 3: Create `dashboard/src/components/ActionButtons.jsx`**

```jsx
const STATUS_SHOW_SERVE = ['stopped', 'crashed']

export default function ActionButtons({ env, onAction, loading }) {
  const serverStatus = env.status.server

  async function handleClick(action) {
    onAction(env.name, action)
  }

  const btnBase = 'rounded px-3 py-1 text-sm font-medium transition-opacity disabled:opacity-50'

  return (
    <div className="flex gap-2">
      {STATUS_SHOW_SERVE.includes(serverStatus) && (
        <button
          className={`${btnBase} bg-green-700 hover:bg-green-600`}
          disabled={loading}
          onClick={() => handleClick('serve')}
        >
          {loading === 'serve' ? '...' : 'Serve'}
        </button>
      )}
      {serverStatus === 'running' && (
        <>
          <button
            className={`${btnBase} bg-gray-700 hover:bg-gray-600`}
            disabled={loading}
            onClick={() => handleClick('stop')}
          >
            {loading === 'stop' ? '...' : 'Stop'}
          </button>
          <button
            className={`${btnBase} bg-blue-700 hover:bg-blue-600`}
            disabled={loading}
            onClick={() => handleClick('restart')}
          >
            {loading === 'restart' ? '...' : 'Restart'}
          </button>
        </>
      )}
    </div>
  )
}
```

**Step 4: Create `dashboard/src/components/EnvironmentRow.jsx`**

Status colors:
- server: running → green, crashed → red, stopped → gray
- tmux: active → green, detached → yellow, missing → red

```jsx
import ActionButtons from './ActionButtons'

const SERVER_COLORS = {
  running: 'text-green-400',
  crashed: 'text-red-400',
  stopped: 'text-gray-400',
}

const TMUX_COLORS = {
  active: 'text-green-400',
  detached: 'text-yellow-400',
  missing: 'text-red-400',
}

export default function EnvironmentRow({ env, onAction, loadingAction }) {
  return (
    <tr className="border-t border-gray-800 hover:bg-gray-900">
      <td className="px-4 py-3 font-mono text-sm">{env.name}</td>
      <td className="px-4 py-3 text-sm text-gray-400">{env.user}</td>
      <td className="px-4 py-3 font-mono text-sm text-gray-400">{env.branch}</td>
      <td className={`px-4 py-3 text-sm ${SERVER_COLORS[env.status.server] ?? 'text-gray-400'}`}>
        {env.status.server}
      </td>
      <td className={`px-4 py-3 text-sm ${TMUX_COLORS[env.status.tmux] ?? 'text-gray-400'}`}>
        {env.status.tmux}
      </td>
      <td className="px-4 py-3 text-sm">
        <a
          href={env.url}
          target="_blank"
          rel="noreferrer"
          className="text-blue-400 hover:underline"
        >
          :{env.port}
        </a>
      </td>
      <td className="px-4 py-3 text-sm text-gray-400">{env.uptime}</td>
      <td className="px-4 py-3">
        <ActionButtons env={env} onAction={onAction} loading={loadingAction} />
      </td>
    </tr>
  )
}
```

**Step 5: Create `dashboard/src/components/EnvironmentTable.jsx`**

```jsx
import EnvironmentRow from './EnvironmentRow'

export default function EnvironmentTable({ envs, onAction, loadingActions }) {
  if (envs.length === 0) {
    return (
      <p className="text-center text-gray-500 py-8">
        No environments found. Run <code className="font-mono text-gray-300">forsa-dev up &lt;name&gt;</code> to create one.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-left">
        <thead className="bg-gray-900 text-xs uppercase tracking-wide text-gray-400">
          <tr>
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">User</th>
            <th className="px-4 py-3">Branch</th>
            <th className="px-4 py-3">Server</th>
            <th className="px-4 py-3">Tmux</th>
            <th className="px-4 py-3">Port</th>
            <th className="px-4 py-3">Uptime</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {envs.map((env) => (
            <EnvironmentRow
              key={`${env.user}-${env.name}`}
              env={env}
              onAction={onAction}
              loadingAction={loadingActions[env.name]}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

**Step 6: Replace `dashboard/src/App.jsx`**

```jsx
import { useCallback, useEffect, useState } from 'react'
import ErrorBanner from './components/ErrorBanner'
import EnvironmentTable from './components/EnvironmentTable'
import HealthBar from './components/HealthBar'

const ENV_POLL_MS = 3000
const HEALTH_POLL_MS = 10000

async function apiFetch(path, options) {
  const resp = await fetch(path, options)
  if (!resp.ok) throw new Error(`${options?.method ?? 'GET'} ${path} failed: ${resp.status}`)
  return resp.json()
}

export default function App() {
  const [envs, setEnvs] = useState([])
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)
  const [loadingActions, setLoadingActions] = useState({})

  const fetchEnvs = useCallback(async () => {
    try {
      const data = await apiFetch('/api/environments')
      setEnvs(data)
      setError(null)
    } catch {
      setError('Cannot reach dashboard API. Is the server running?')
    }
  }, [])

  const fetchHealth = useCallback(async () => {
    try {
      const data = await apiFetch('/api/health')
      setHealth(data)
    } catch {
      // health failures are non-critical
    }
  }, [])

  useEffect(() => {
    fetchEnvs()
    fetchHealth()
    const envTimer = setInterval(fetchEnvs, ENV_POLL_MS)
    const healthTimer = setInterval(fetchHealth, HEALTH_POLL_MS)
    return () => {
      clearInterval(envTimer)
      clearInterval(healthTimer)
    }
  }, [fetchEnvs, fetchHealth])

  const handleAction = useCallback(async (name, action) => {
    setLoadingActions((prev) => ({ ...prev, [name]: action }))
    try {
      await apiFetch(`/api/environments/${name}/${action}`, { method: 'POST' })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoadingActions((prev) => ({ ...prev, [name]: null }))
      fetchEnvs()
    }
  }, [fetchEnvs])

  return (
    <div className="mx-auto max-w-6xl p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-100">forsa-dev</h1>
      <ErrorBanner message={error} />
      <HealthBar health={health} />
      <EnvironmentTable envs={envs} onAction={handleAction} loadingActions={loadingActions} />
    </div>
  )
}
```

**Step 7: Build and verify**

```bash
cd /Users/andersnordmark/work/personal/forsa-dev/dashboard
npm run build
```

Expected: build succeeds, `src/forsa_dev/dashboard/static/index.html` exists

**Step 8: Test manually by starting the dashboard**

```bash
cd /Users/andersnordmark/work/personal/forsa-dev
uv run python -c "
from forsa_dev.config import load_config
from forsa_dev.dashboard.server import create_app
import uvicorn
cfg = load_config()
uvicorn.run(create_app(cfg), host='127.0.0.1', port=8080)
"
```

Open http://localhost:8080 in browser. Verify: environments listed, health bars visible, action buttons work.

**Step 9: Commit**

```bash
cd /Users/andersnordmark/work/personal/forsa-dev
git add dashboard/src/ src/forsa_dev/dashboard/static/
git commit -m "feat: implement React dashboard UI with environment table and health bars"
```

---

### Task 8: Build script and final integration

**Files:**
- Create: `scripts/build_dashboard.sh`
- Run full test suite

**Step 1: Create `scripts/build_dashboard.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Building React dashboard..."
cd "$REPO_ROOT/dashboard"
npm install
npm run build

echo "Static files written to src/forsa_dev/dashboard/static/"
echo "Done."
```

Make it executable:
```bash
chmod +x scripts/build_dashboard.sh
```

**Step 2: Run the build script to verify it works end-to-end**

```bash
cd /Users/andersnordmark/work/personal/forsa-dev
./scripts/build_dashboard.sh
```

Expected: output ends with "Done.", static files present in `src/forsa_dev/dashboard/static/`

**Step 3: Run full test suite**

```bash
uv run pytest -v
```

Expected: all tests PASS

**Step 4: Reinstall forsa-dev to pick up new dashboard command**

```bash
uv tool install --force /Users/andersnordmark/work/personal/forsa-dev
```

**Step 5: Smoke test the CLI**

```bash
forsa-dev dashboard --help
```

Expected: shows help with `--port` option

**Step 6: Commit and push**

```bash
git add scripts/build_dashboard.sh
git commit -m "feat: add build_dashboard.sh script"
git push
```
