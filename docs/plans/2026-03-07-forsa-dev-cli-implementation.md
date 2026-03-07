# forsa-dev CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python CLI tool that manages FORSA development environments: git worktrees, Docker containers, tmux sessions, and Caddy routing.

**Architecture:** Typer-based CLI with one module per concern (config, state, ports, compose, git, tmux, caddy). Commands are thin orchestrators that call into these modules. State is persisted as JSON files in a shared directory. Port allocation uses flock for atomicity.

**Tech Stack:** Python 3.11+, Typer, Rich, requests, tomli-w, pytest

**Design doc:** `docs/plans/2026-03-07-forsa-dev-cli-design.md`

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/forsa_dev/__init__.py`
- Create: `src/forsa_dev/cli.py`
- Create: `tests/__init__.py`

**Step 1: Create `pyproject.toml`**

```toml
[project]
name = "forsa-dev"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "rich>=13",
    "requests>=2.32",
    "tomli-w>=1.1",
]

[project.scripts]
forsa-dev = "forsa_dev.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/forsa_dev"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-httpserver>=1.1",
]
```

**Step 2: Create `src/forsa_dev/__init__.py`** (empty)

**Step 3: Create `src/forsa_dev/cli.py`**

```python
import typer

app = typer.Typer(help="Manage FORSA development environments.")


@app.command()
def version():
    """Print version."""
    typer.echo("forsa-dev 0.1.0")
```

**Step 4: Create `tests/__init__.py`** (empty)

**Step 5: Install and verify**

```bash
uv sync
uv run forsa-dev --help
```

Expected output: Typer help text with `version` command listed.

**Step 6: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: scaffold forsa-dev project"
```

---

### Task 2: Config module

The config is loaded from `~/.config/forsa/config.toml`. All fields have defaults so the tool works for local development without a config file.

**Files:**
- Create: `src/forsa_dev/config.py`
- Create: `tests/test_config.py`

**Step 1: Write failing tests**

```python
# tests/test_config.py
import tomllib
from pathlib import Path
import pytest
from forsa_dev.config import Config, load_config, save_config


def test_load_config_from_file(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'repo = "/home/anders/forsa"\n'
        'worktree_dir = "/home/anders/worktrees"\n'
        'data_dir = "/data/dev"\n'
        'state_dir = "/var/lib/forsa-dev"\n'
        'caddy_admin = "http://localhost:2019"\n'
        'base_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\n"
        "port_range_end = 3099\n"
    )
    config = load_config(config_file)
    assert config.repo == Path("/home/anders/forsa")
    assert config.worktree_dir == Path("/home/anders/worktrees")
    assert config.port_range_start == 3000
    assert config.port_range_end == 3099


def test_load_config_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.toml")


def test_save_config_roundtrip(tmp_path):
    config_file = tmp_path / "config.toml"
    config = Config(
        repo=Path("/home/anders/forsa"),
        worktree_dir=Path("/home/anders/worktrees"),
        data_dir=Path("/data/dev"),
        state_dir=Path("/tmp/forsa-dev"),
        caddy_admin="http://localhost:2019",
        base_url="optbox.example.ts.net",
        docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000,
        port_range_end=3099,
    )
    save_config(config, config_file)
    loaded = load_config(config_file)
    assert loaded == config
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py -v
```

Expected: ImportError or AttributeError — `config` module doesn't exist yet.

**Step 3: Create `src/forsa_dev/config.py`**

```python
from __future__ import annotations
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli_w


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "forsa" / "config.toml"


@dataclass(frozen=True)
class Config:
    repo: Path
    worktree_dir: Path
    data_dir: Path
    state_dir: Path
    caddy_admin: str
    base_url: str
    docker_image: str
    gurobi_lic: Path
    port_range_start: int
    port_range_end: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Config):
            return NotImplemented
        return (
            self.repo == other.repo
            and self.worktree_dir == other.worktree_dir
            and self.data_dir == other.data_dir
            and self.state_dir == other.state_dir
            and self.caddy_admin == other.caddy_admin
            and self.base_url == other.base_url
            and self.docker_image == other.docker_image
            and self.gurobi_lic == other.gurobi_lic
            and self.port_range_start == other.port_range_start
            and self.port_range_end == other.port_range_end
        )


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}\nRun `forsa-dev init` to create it.")
    with path.open("rb") as f:
        data = tomllib.load(f)
    return Config(
        repo=Path(data["repo"]),
        worktree_dir=Path(data["worktree_dir"]),
        data_dir=Path(data["data_dir"]),
        state_dir=Path(data["state_dir"]),
        caddy_admin=data["caddy_admin"],
        base_url=data["base_url"],
        docker_image=data["docker_image"],
        gurobi_lic=Path(data["gurobi_lic"]),
        port_range_start=int(data["port_range_start"]),
        port_range_end=int(data["port_range_end"]),
    )


def save_config(config: Config, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "repo": str(config.repo),
        "worktree_dir": str(config.worktree_dir),
        "data_dir": str(config.data_dir),
        "state_dir": str(config.state_dir),
        "caddy_admin": config.caddy_admin,
        "base_url": config.base_url,
        "docker_image": config.docker_image,
        "gurobi_lic": str(config.gurobi_lic),
        "port_range_start": config.port_range_start,
        "port_range_end": config.port_range_end,
    }
    with path.open("wb") as f:
        tomli_w.dump(data, f)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add src/forsa_dev/config.py tests/test_config.py
git commit -m "feat: add config module"
```

---

### Task 3: State module

State files live at `{state_dir}/{user}-{name}.json`. Port is always set after `up`. URL is null when not serving.

**Files:**
- Create: `src/forsa_dev/state.py`
- Create: `tests/test_state.py`

**Step 1: Write failing tests**

```python
# tests/test_state.py
from datetime import datetime, timezone
from pathlib import Path
import pytest
from forsa_dev.state import Environment, load_state, save_state, delete_state, list_states


def make_env(state_dir: Path) -> Environment:
    return Environment(
        name="ticket-42",
        user="anders",
        branch="ticket-42",
        worktree=Path("/home/anders/worktrees/ticket-42"),
        tmux_session="anders-ticket-42",
        compose_file=Path("/home/anders/worktrees/ticket-42/docker-compose.dev.yml"),
        port=3002,
        url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None,
    )


def test_save_and_load_state(tmp_path):
    env = make_env(tmp_path)
    save_state(env, tmp_path)
    loaded = load_state("anders", "ticket-42", tmp_path)
    assert loaded == env


def test_load_state_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_state("anders", "ticket-42", tmp_path)


def test_delete_state(tmp_path):
    env = make_env(tmp_path)
    save_state(env, tmp_path)
    delete_state("anders", "ticket-42", tmp_path)
    assert not (tmp_path / "anders-ticket-42.json").exists()


def test_list_states_empty(tmp_path):
    assert list_states(tmp_path) == []


def test_list_states_multiple(tmp_path):
    env1 = make_env(tmp_path)
    env2 = Environment(
        name="experiment",
        user="hanna",
        branch="experiment",
        worktree=Path("/home/hanna/worktrees/experiment"),
        tmux_session="hanna-experiment",
        compose_file=Path("/home/hanna/worktrees/experiment/docker-compose.dev.yml"),
        port=3003,
        url="optbox.example.ts.net/experiment/",
        created_at=datetime(2026, 3, 7, 23, 0, 0, tzinfo=timezone.utc),
        served_at=datetime(2026, 3, 7, 23, 5, 0, tzinfo=timezone.utc),
    )
    save_state(env1, tmp_path)
    save_state(env2, tmp_path)
    states = list_states(tmp_path)
    assert len(states) == 2
    names = {s.name for s in states}
    assert names == {"ticket-42", "experiment"}


def test_state_with_url_roundtrips(tmp_path):
    env = make_env(tmp_path)
    env_with_url = Environment(
        **{**env.__dict__, "url": "optbox.example.ts.net/ticket-42/", "served_at": datetime(2026, 3, 7, 22, 5, 0, tzinfo=timezone.utc)}
    )
    save_state(env_with_url, tmp_path)
    loaded = load_state("anders", "ticket-42", tmp_path)
    assert loaded.url == "optbox.example.ts.net/ticket-42/"
    assert loaded.served_at is not None
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_state.py -v
```

Expected: ImportError — `state` module doesn't exist yet.

**Step 3: Create `src/forsa_dev/state.py`**

```python
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Environment:
    name: str
    user: str
    branch: str
    worktree: Path
    tmux_session: str
    compose_file: Path
    port: int
    url: str | None
    created_at: datetime
    served_at: datetime | None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Environment):
            return NotImplemented
        return asdict(self) == asdict(other)


def _state_path(user: str, name: str, state_dir: Path) -> Path:
    return state_dir / f"{user}-{name}.json"


def _serialize(env: Environment) -> dict:
    d = asdict(env)
    d["worktree"] = str(env.worktree)
    d["compose_file"] = str(env.compose_file)
    d["created_at"] = env.created_at.isoformat()
    d["served_at"] = env.served_at.isoformat() if env.served_at else None
    return d


def _deserialize(data: dict) -> Environment:
    return Environment(
        name=data["name"],
        user=data["user"],
        branch=data["branch"],
        worktree=Path(data["worktree"]),
        tmux_session=data["tmux_session"],
        compose_file=Path(data["compose_file"]),
        port=data["port"],
        url=data["url"],
        created_at=datetime.fromisoformat(data["created_at"]),
        served_at=datetime.fromisoformat(data["served_at"]) if data["served_at"] else None,
    )


def save_state(env: Environment, state_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = _state_path(env.user, env.name, state_dir)
    path.write_text(json.dumps(_serialize(env), indent=2))


def load_state(user: str, name: str, state_dir: Path) -> Environment:
    path = _state_path(user, name, state_dir)
    if not path.exists():
        raise FileNotFoundError(f"No environment '{user}-{name}' found.")
    return _deserialize(json.loads(path.read_text()))


def delete_state(user: str, name: str, state_dir: Path) -> None:
    _state_path(user, name, state_dir).unlink()


def list_states(state_dir: Path) -> list[Environment]:
    if not state_dir.exists():
        return []
    return [
        _deserialize(json.loads(p.read_text()))
        for p in sorted(state_dir.glob("*.json"))
    ]
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_state.py -v
```

Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add src/forsa_dev/state.py tests/test_state.py
git commit -m "feat: add state module"
```

---

### Task 4: Port allocation

Atomic port allocation using `fcntl.flock`. Reads existing state files to find used ports, picks the lowest free one in range.

**Files:**
- Create: `src/forsa_dev/ports.py`
- Create: `tests/test_ports.py`

**Step 1: Write failing tests**

```python
# tests/test_ports.py
from datetime import datetime, timezone
from pathlib import Path
import pytest
from forsa_dev.ports import allocate_port
from forsa_dev.state import Environment, save_state


def _env(name: str, port: int, state_dir: Path) -> Environment:
    return Environment(
        name=name,
        user="anders",
        branch=name,
        worktree=Path(f"/tmp/{name}"),
        tmux_session=f"anders-{name}",
        compose_file=Path(f"/tmp/{name}/docker-compose.dev.yml"),
        port=port,
        url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None,
    )


def test_allocate_first_port_in_range(tmp_path):
    port = allocate_port(tmp_path, start=3000, end=3099)
    assert port == 3000


def test_allocate_skips_used_ports(tmp_path):
    save_state(_env("one", 3000, tmp_path), tmp_path)
    save_state(_env("two", 3001, tmp_path), tmp_path)
    port = allocate_port(tmp_path, start=3000, end=3099)
    assert port == 3002


def test_allocate_raises_when_range_exhausted(tmp_path):
    for i in range(3):
        save_state(_env(f"env-{i}", 3000 + i, tmp_path), tmp_path)
    with pytest.raises(RuntimeError, match="No free ports"):
        allocate_port(tmp_path, start=3000, end=3002)
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_ports.py -v
```

Expected: ImportError — `ports` module doesn't exist yet.

**Step 3: Create `src/forsa_dev/ports.py`**

```python
from __future__ import annotations
import fcntl
from pathlib import Path

from forsa_dev.state import list_states


def allocate_port(state_dir: Path, start: int, end: int) -> int:
    """Atomically allocate the lowest free port in [start, end] inclusive."""
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / ".port.lock"
    with lock_path.open("a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            used = {env.port for env in list_states(state_dir)}
            for port in range(start, end + 1):
                if port not in used:
                    return port
            raise RuntimeError(f"No free ports in range {start}-{end}.")
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_ports.py -v
```

Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add src/forsa_dev/ports.py tests/test_ports.py
git commit -m "feat: add atomic port allocation"
```

---

### Task 5: Compose file generation

Generate `docker-compose.dev.yml` from a template. Only port, data_dir, gurobi_lic, docker_image, user, and name vary.

**Files:**
- Create: `src/forsa_dev/compose.py`
- Create: `tests/test_compose.py`

**Step 1: Write failing tests**

```python
# tests/test_compose.py
from pathlib import Path
import yaml
import pytest
from forsa_dev.compose import generate_compose


@pytest.fixture()
def compose_content(tmp_path):
    worktree = tmp_path / "ticket-42"
    worktree.mkdir()
    generate_compose(
        worktree=worktree,
        user="anders",
        name="ticket-42",
        port=3002,
        data_dir=Path("/data/dev"),
        docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
    )
    compose_file = worktree / "docker-compose.dev.yml"
    assert compose_file.exists()
    with compose_file.open() as f:
        return yaml.safe_load(f)


def test_compose_port(compose_content):
    ports = compose_content["services"]["forsa"]["ports"]
    assert "3002:8000" in ports


def test_compose_image(compose_content):
    assert compose_content["services"]["forsa"]["image"] == "forsa:latest"


def test_compose_container_name(compose_content):
    assert compose_content["services"]["forsa"]["container_name"] == "forsa-anders-ticket-42"


def test_compose_source_volume(compose_content):
    volumes = compose_content["services"]["forsa"]["volumes"]
    assert "./src:/app/src" in volumes


def test_compose_data_volume(compose_content):
    volumes = compose_content["services"]["forsa"]["volumes"]
    assert "/data/dev:/app/data" in volumes


def test_compose_gurobi_volume(compose_content):
    volumes = compose_content["services"]["forsa"]["volumes"]
    assert "/opt/gurobi/gurobi.lic:/opt/gurobi/gurobi.lic" in volumes


def test_compose_required_env_vars(compose_content):
    env = compose_content["services"]["forsa"]["environment"]
    assert env["FORSA_DATA_PATH"] == "/app/data"
    assert env["FORSA_WEBSERVER_PORT"] == 8000
    assert env["JULIA_PROJECT"] == "/app/src/julia/forsa-env"
    assert env["GRB_LICENSE_FILE"] == "/opt/gurobi/gurobi.lic"
```

**Step 2: Add yaml to dev dependencies in pyproject.toml**

```toml
[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-httpserver>=1.1",
    "pyyaml>=6",
]
```

Run `uv sync`.

**Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_compose.py -v
```

Expected: ImportError — `compose` module doesn't exist yet.

**Step 4: Create `src/forsa_dev/compose.py`**

```python
from __future__ import annotations
from pathlib import Path


_TEMPLATE = """\
services:
  forsa:
    image: {docker_image}
    container_name: forsa-{user}-{name}
    ports:
      - "{port}:8000"
    volumes:
      - ./src:/app/src
      - {data_dir}:/app/data
      - ./logs:/app/src/python/webserver/.local/webserver_logs
      - {gurobi_lic}:/opt/gurobi/gurobi.lic
    environment:
      FORSA_DATA_PATH: /app/data
      FORSA_WEBSERVER_PATH: /app/src/python/webserver
      FORSA_OPTIMIZER_PATH: /app/src/julia
      JULIA_PROJECT: /app/src/julia/forsa-env
      FORSA_WEBSERVER_PORT: 8000
      FORSA_JULIA_BACKEND: juliacall
      FORSA_BIDDING_ZONE_PATH: /app/data/elomraden.xlsx
      FORSA_SPOT_PRICE_PATH: /app/data/elspot_prices.xlsx
      PYTHON: /usr/bin/python3
      GRB_LICENSE_FILE: /opt/gurobi/gurobi.lic
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/ready')"]
      interval: 10s
      timeout: 5s
      start_period: 120s
      retries: 3
    restart: "no"
"""


def generate_compose(
    worktree: Path,
    user: str,
    name: str,
    port: int,
    data_dir: Path,
    docker_image: str,
    gurobi_lic: Path,
) -> Path:
    """Write docker-compose.dev.yml into the worktree. Returns the file path."""
    content = _TEMPLATE.format(
        docker_image=docker_image,
        user=user,
        name=name,
        port=port,
        data_dir=data_dir,
        gurobi_lic=gurobi_lic,
    )
    compose_file = worktree / "docker-compose.dev.yml"
    compose_file.write_text(content)
    return compose_file
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_compose.py -v
```

Expected: All 7 tests PASS.

**Step 6: Commit**

```bash
git add src/forsa_dev/compose.py tests/test_compose.py pyproject.toml uv.lock
git commit -m "feat: add compose file generator"
```

---

### Task 6: Caddy module

Register and deregister path-based routes via Caddy admin API. Must fail gracefully if Caddy is unreachable.

**Files:**
- Create: `src/forsa_dev/caddy.py`
- Create: `tests/test_caddy.py`

**Step 1: Write failing tests**

```python
# tests/test_caddy.py
import pytest
from pytest_httpserver import HTTPServer
from forsa_dev.caddy import register_route, deregister_route, CaddyError


def test_register_route_success(httpserver: HTTPServer):
    httpserver.expect_request(
        "/config/apps/http/servers/srv0/routes/",
        method="POST",
    ).respond_with_data("", status=200)

    register_route(
        caddy_admin=httpserver.url_for(""),
        name="ticket-42",
        port=3002,
    )
    # No exception raised — success


def test_deregister_route_success(httpserver: HTTPServer):
    httpserver.expect_request(
        "/id/forsa-ticket-42",
        method="DELETE",
    ).respond_with_data("", status=200)

    deregister_route(
        caddy_admin=httpserver.url_for(""),
        name="ticket-42",
    )
    # No exception raised — success


def test_register_route_unreachable_warns(caplog):
    import logging
    with caplog.at_level(logging.WARNING):
        register_route(
            caddy_admin="http://localhost:19999",  # nothing listening here
            name="ticket-42",
            port=3002,
        )
    assert "Caddy" in caplog.text


def test_deregister_route_unreachable_warns(caplog):
    import logging
    with caplog.at_level(logging.WARNING):
        deregister_route(
            caddy_admin="http://localhost:19999",
            name="ticket-42",
        )
    assert "Caddy" in caplog.text
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_caddy.py -v
```

Expected: ImportError — `caddy` module doesn't exist yet.

**Step 3: Create `src/forsa_dev/caddy.py`**

```python
from __future__ import annotations
import json
import logging

import requests

logger = logging.getLogger(__name__)


def _route_id(name: str) -> str:
    return f"forsa-{name}"


def register_route(caddy_admin: str, name: str, port: int) -> None:
    """Add a path-based reverse proxy route to Caddy. Warns if Caddy is unreachable."""
    route = {
        "@id": _route_id(name),
        "match": [{"path": [f"/{name}/*"]}],
        "handle": [
            {
                "handler": "reverse_proxy",
                "upstreams": [{"dial": f"localhost:{port}"}],
            }
        ],
    }
    try:
        admin_url = caddy_admin.rstrip("/")
        resp = requests.post(
            f"{admin_url}/config/apps/http/servers/srv0/routes/",
            json=route,
            timeout=5,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Caddy registration failed (continuing without it): %s", exc)


def deregister_route(caddy_admin: str, name: str) -> None:
    """Remove a route from Caddy by ID. Warns if Caddy is unreachable."""
    try:
        admin_url = caddy_admin.rstrip("/")
        resp = requests.delete(
            f"{admin_url}/id/{_route_id(name)}",
            timeout=5,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Caddy deregistration failed (continuing without it): %s", exc)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_caddy.py -v
```

Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
git add src/forsa_dev/caddy.py tests/test_caddy.py
git commit -m "feat: add Caddy admin API integration"
```

---

### Task 7: Git module

Thin wrappers around git commands for branch and worktree management. Tests use a real temporary git repository.

**Files:**
- Create: `src/forsa_dev/git.py`
- Create: `tests/test_git.py`
- Create: `tests/conftest.py`

**Step 1: Create `tests/conftest.py` with a git repo fixture**

```python
# tests/conftest.py
import subprocess
from pathlib import Path
import pytest


@pytest.fixture()
def git_repo(tmp_path):
    """A real git repo with one commit on main, ready for worktrees."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], check=True, capture_output=True, cwd=repo)
    subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True, cwd=repo)
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], check=True, capture_output=True, cwd=repo)
    subprocess.run(["git", "commit", "-m", "init"], check=True, capture_output=True, cwd=repo)
    return repo
```

**Step 2: Write failing tests**

```python
# tests/test_git.py
import subprocess
from pathlib import Path
import pytest
from forsa_dev.git import create_branch_and_worktree, remove_worktree, branch_is_pushed


def test_create_branch_and_worktree(git_repo, tmp_path):
    worktree_path = tmp_path / "worktrees" / "feature-x"
    create_branch_and_worktree(
        repo=git_repo,
        branch="feature-x",
        worktree=worktree_path,
        from_branch="main",
    )
    assert worktree_path.exists()
    result = subprocess.run(
        ["git", "branch", "--list", "feature-x"],
        capture_output=True, text=True, cwd=git_repo
    )
    assert "feature-x" in result.stdout


def test_create_branch_fails_if_branch_exists(git_repo, tmp_path):
    worktree_path = tmp_path / "worktrees" / "main-copy"
    with pytest.raises(RuntimeError, match="already exists"):
        create_branch_and_worktree(
            repo=git_repo,
            branch="main",
            worktree=worktree_path,
            from_branch="main",
        )


def test_remove_worktree(git_repo, tmp_path):
    worktree_path = tmp_path / "worktrees" / "feature-y"
    create_branch_and_worktree(git_repo, "feature-y", worktree_path, "main")
    assert worktree_path.exists()
    remove_worktree(repo=git_repo, worktree=worktree_path)
    assert not worktree_path.exists()


def test_branch_is_pushed_false_for_local_branch(git_repo, tmp_path):
    worktree_path = tmp_path / "worktrees" / "feature-z"
    create_branch_and_worktree(git_repo, "feature-z", worktree_path, "main")
    assert not branch_is_pushed(repo=git_repo, branch="feature-z")
```

**Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_git.py -v
```

Expected: ImportError — `git` module doesn't exist yet.

**Step 4: Create `src/forsa_dev/git.py`**

```python
from __future__ import annotations
import subprocess
from pathlib import Path


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def create_branch_and_worktree(
    repo: Path,
    branch: str,
    worktree: Path,
    from_branch: str = "main",
) -> None:
    """Create a new git branch and check it out as a worktree."""
    # Check branch doesn't already exist
    result = _git(["branch", "--list", branch], repo)
    if result.stdout.strip():
        raise RuntimeError(f"Branch '{branch}' already exists.")

    worktree.parent.mkdir(parents=True, exist_ok=True)
    result = _git(
        ["worktree", "add", "-b", branch, str(worktree), from_branch],
        repo,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {result.stderr}")


def remove_worktree(repo: Path, worktree: Path) -> None:
    """Remove a git worktree and prune the worktree list."""
    result = _git(["worktree", "remove", "--force", str(worktree)], repo)
    if result.returncode != 0:
        raise RuntimeError(f"git worktree remove failed: {result.stderr}")


def branch_is_pushed(repo: Path, branch: str) -> bool:
    """Return True if the branch has a remote tracking ref."""
    result = _git(["branch", "-r", "--contains", branch], repo)
    return bool(result.stdout.strip())
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_git.py -v
```

Expected: All 4 tests PASS.

**Step 6: Commit**

```bash
git add src/forsa_dev/git.py tests/test_git.py tests/conftest.py
git commit -m "feat: add git worktree module"
```

---

### Task 8: Tmux module

Thin wrappers for tmux session management. Tests verify commands succeed against a real tmux server.

Note: These tests require tmux to be installed. They are skipped automatically if tmux is not available.

**Files:**
- Create: `src/forsa_dev/tmux.py`
- Create: `tests/test_tmux.py`

**Step 1: Write failing tests**

```python
# tests/test_tmux.py
import subprocess
import pytest
from forsa_dev.tmux import create_session, kill_session, session_exists


pytestmark = pytest.mark.skipif(
    subprocess.run(["which", "tmux"], capture_output=True).returncode != 0,
    reason="tmux not installed",
)

SESSION = "forsa-dev-test-session"


@pytest.fixture(autouse=True)
def cleanup_session():
    yield
    subprocess.run(["tmux", "kill-session", "-t", SESSION], capture_output=True)


def test_create_and_detect_session(tmp_path):
    create_session(session=SESSION, cwd=tmp_path)
    assert session_exists(SESSION)


def test_kill_session(tmp_path):
    create_session(session=SESSION, cwd=tmp_path)
    kill_session(SESSION)
    assert not session_exists(SESSION)


def test_session_exists_false_when_missing():
    assert not session_exists("forsa-dev-nonexistent-xyz")
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_tmux.py -v
```

Expected: ImportError — `tmux` module doesn't exist yet.

**Step 3: Create `src/forsa_dev/tmux.py`**

```python
from __future__ import annotations
import os
import subprocess
from pathlib import Path


def create_session(session: str, cwd: Path) -> None:
    """Create a detached tmux session. Raises RuntimeError if it fails."""
    result = subprocess.run(
        ["tmux", "new-session", "-d", "-s", session, "-c", str(cwd)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux new-session failed: {result.stderr}")


def kill_session(session: str) -> None:
    """Kill a tmux session. Raises RuntimeError if it fails."""
    result = subprocess.run(
        ["tmux", "kill-session", "-t", session],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux kill-session failed: {result.stderr}")


def session_exists(session: str) -> bool:
    """Return True if the tmux session exists."""
    result = subprocess.run(
        ["tmux", "has-session", "-t", session],
        capture_output=True,
    )
    return result.returncode == 0


def attach_session(session: str) -> None:
    """Attach to a tmux session. Replaces the current process.
    Uses switch-client if already inside tmux, attach-session otherwise."""
    if os.environ.get("TMUX"):
        os.execvp("tmux", ["tmux", "switch-client", "-t", session])
    else:
        os.execvp("tmux", ["tmux", "attach-session", "-t", session])
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_tmux.py -v
```

Expected: All 3 tests PASS (or SKIP if tmux not installed).

**Step 5: Commit**

```bash
git add src/forsa_dev/tmux.py tests/test_tmux.py
git commit -m "feat: add tmux session module"
```

---

### Task 9: `init` and `up` commands

Wire the modules together into the first two user-facing commands.

**Files:**
- Modify: `src/forsa_dev/cli.py`
- Create: `tests/test_cli_up.py`

**Step 1: Write a failing test for `up`**

This test uses a real git repo fixture but avoids actually running tmux (skips attach for non-interactive test).

```python
# tests/test_cli_up.py
import getpass
from pathlib import Path
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
        'caddy_admin = "http://localhost:2019"\n'
        'base_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\n"
        "port_range_end = 3099\n"
    )
    return cfg


def test_up_creates_worktree_state_and_compose(config_file, tmp_path):
    user = getpass.getuser()
    with patch("forsa_dev.tmux.attach_session"):  # don't actually attach in tests
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
    user = getpass.getuser()
    with patch("forsa_dev.tmux.attach_session"):
        runner.invoke(app, ["up", "feature-x", "--config", str(config_file)])
        result = runner.invoke(app, ["up", "feature-x", "--config", str(config_file)])
    assert result.exit_code != 0
    assert "already exists" in result.output
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_cli_up.py -v
```

Expected: Error — `--config` option not recognised (cli.py needs updating).

**Step 3: Rewrite `src/forsa_dev/cli.py` with `init` and `up`**

```python
from __future__ import annotations
import getpass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import typer

from forsa_dev import caddy, git, tmux
from forsa_dev.compose import generate_compose
from forsa_dev.config import DEFAULT_CONFIG_PATH, Config, load_config, save_config
from forsa_dev.ports import allocate_port
from forsa_dev.state import Environment, delete_state, list_states, load_state, save_state

app = typer.Typer(help="Manage FORSA development environments.")

ConfigOption = Annotated[
    Optional[Path],
    typer.Option("--config", help="Path to config file.", show_default=False),
]


def _load(config_path: Optional[Path]) -> Config:
    return load_config(config_path or DEFAULT_CONFIG_PATH)


def _full_name(user: str, name: str) -> str:
    return f"{user}-{name}"


@app.command()
def init(
    config: ConfigOption = None,
):
    """Interactive setup — creates ~/.config/forsa/config.toml."""
    config_path = config or DEFAULT_CONFIG_PATH
    typer.echo("Setting up forsa-dev configuration.")
    repo = typer.prompt("Path to your FORSA git repo", default=str(Path.home() / "forsa"))
    worktree_dir = typer.prompt("Directory for git worktrees", default=str(Path.home() / "worktrees"))
    data_dir = typer.prompt("Default data directory", default="/data/dev")
    state_dir = typer.prompt("Shared state directory", default="/var/lib/forsa-dev")
    caddy_admin = typer.prompt("Caddy admin API URL", default="http://localhost:2019")
    base_url = typer.prompt("Base URL (e.g. optbox.tailnet.ts.net)")
    docker_image = typer.prompt("Docker image name", default="forsa:latest")
    gurobi_lic = typer.prompt("Path to gurobi.lic on this machine", default="/opt/gurobi/gurobi.lic")
    port_start = typer.prompt("Port range start", default=3000)
    port_end = typer.prompt("Port range end", default=3099)

    cfg = Config(
        repo=Path(repo),
        worktree_dir=Path(worktree_dir),
        data_dir=Path(data_dir),
        state_dir=Path(state_dir),
        caddy_admin=caddy_admin,
        base_url=base_url,
        docker_image=docker_image,
        gurobi_lic=Path(gurobi_lic),
        port_range_start=int(port_start),
        port_range_end=int(port_end),
    )
    save_config(cfg, config_path)
    typer.echo(f"Config written to {config_path}")


@app.command()
def up(
    name: str,
    from_branch: Annotated[str, typer.Option("--from", help="Branch to create from.")] = "main",
    config: ConfigOption = None,
):
    """Create a git worktree, compose file, and tmux session."""
    cfg = _load(config)
    user = getpass.getuser()
    full_name = _full_name(user, name)
    worktree = cfg.worktree_dir / name

    # Guard: already exists
    try:
        load_state(user, name, cfg.state_dir)
        typer.echo(f"Error: environment '{full_name}' already exists. Use `forsa-dev down {name}` first.", err=True)
        raise typer.Exit(1)
    except FileNotFoundError:
        pass

    typer.echo(f"Creating branch '{name}' from '{from_branch}'...")
    git.create_branch_and_worktree(cfg.repo, name, worktree, from_branch)

    typer.echo("Allocating port...")
    port = allocate_port(cfg.state_dir, cfg.port_range_start, cfg.port_range_end)

    typer.echo(f"Generating docker-compose.dev.yml (port {port})...")
    compose_file = generate_compose(
        worktree=worktree,
        user=user,
        name=name,
        port=port,
        data_dir=cfg.data_dir,
        docker_image=cfg.docker_image,
        gurobi_lic=cfg.gurobi_lic,
    )

    env = Environment(
        name=name,
        user=user,
        branch=name,
        worktree=worktree,
        tmux_session=full_name,
        compose_file=compose_file,
        port=port,
        url=None,
        created_at=datetime.now(tz=timezone.utc),
        served_at=None,
    )
    save_state(env, cfg.state_dir)

    typer.echo(f"Starting tmux session '{full_name}'...")
    tmux.create_session(full_name, worktree)

    typer.echo(f"Ready. Attaching to '{full_name}'...")
    tmux.attach_session(full_name)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_cli_up.py -v
```

Expected: Both tests PASS.

**Step 5: Commit**

```bash
git add src/forsa_dev/cli.py tests/test_cli_up.py
git commit -m "feat: add init and up commands"
```

---

### Task 10: `serve`, `stop`, and `restart` commands

**Files:**
- Modify: `src/forsa_dev/cli.py`
- Create: `tests/test_cli_serve_stop.py`

**Step 1: Write failing tests**

```python
# tests/test_cli_serve_stop.py
import getpass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner
from forsa_dev.cli import app
from forsa_dev.state import Environment, save_state, load_state


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
    assert updated.url is not None
    assert "ticket-42" in updated.url
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
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_cli_serve_stop.py -v
```

Expected: Error — `serve` and `stop` commands not defined.

**Step 3: Add `serve`, `stop`, `restart` to `src/forsa_dev/cli.py`**

Add after the `up` command:

```python
def _compose_cmd(env: Environment, *args: str) -> list[str]:
    return [
        "docker", "compose",
        "-p", env.tmux_session,
        "-f", str(env.compose_file),
        *args,
    ]


@app.command()
def serve(
    name: str,
    config: ConfigOption = None,
):
    """Start the Docker server for an environment."""
    import subprocess
    cfg = _load(config)
    user = getpass.getuser()
    env = load_state(user, name, cfg.state_dir)

    typer.echo(f"Starting server on port {env.port}...")
    result = subprocess.run(_compose_cmd(env, "up", "-d"), check=False)
    if result.returncode != 0:
        typer.echo("Error: docker compose up failed.", err=True)
        raise typer.Exit(1)

    url = f"{cfg.base_url}/{name}/"
    caddy.register_route(cfg.caddy_admin, name, env.port)

    updated = Environment(
        **{**env.__dict__,
           "url": url,
           "served_at": datetime.now(tz=timezone.utc)}
    )
    save_state(updated, cfg.state_dir)
    typer.echo(f"Serving at {url}")


@app.command()
def stop(
    name: str,
    config: ConfigOption = None,
):
    """Stop the Docker server. Tmux session is preserved."""
    import subprocess
    cfg = _load(config)
    user = getpass.getuser()
    env = load_state(user, name, cfg.state_dir)

    typer.echo("Stopping server...")
    subprocess.run(_compose_cmd(env, "down"), check=False)
    caddy.deregister_route(cfg.caddy_admin, name)

    updated = Environment(
        **{**env.__dict__, "url": None, "served_at": None}
    )
    save_state(updated, cfg.state_dir)
    typer.echo("Server stopped. Tmux session preserved.")


@app.command()
def restart(
    name: str,
    config: ConfigOption = None,
):
    """Restart the Docker containers without changing port or Caddy registration."""
    import subprocess
    cfg = _load(config)
    user = getpass.getuser()
    env = load_state(user, name, cfg.state_dir)
    typer.echo("Restarting...")
    subprocess.run(_compose_cmd(env, "restart"), check=False)
    typer.echo("Done.")
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_cli_serve_stop.py -v
```

Expected: Both tests PASS.

**Step 5: Commit**

```bash
git add src/forsa_dev/cli.py tests/test_cli_serve_stop.py
git commit -m "feat: add serve, stop, restart commands"
```

---

### Task 11: `down` command

Destructive command: stops server, kills tmux, removes worktree, deletes state. Checks branch is pushed first.

**Files:**
- Modify: `src/forsa_dev/cli.py`
- Create: `tests/test_cli_down.py`

**Step 1: Write failing tests**

```python
# tests/test_cli_down.py
import getpass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner
from forsa_dev.cli import app
from forsa_dev.state import Environment, save_state


runner = CliRunner()
USER = getpass.getuser()


@pytest.fixture()
def setup(tmp_path, git_repo):
    worktree = tmp_path / "worktrees" / "feature-x"
    # Create a real worktree so git worktree remove works
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
        'caddy_admin = "http://localhost:2019"\n'
        'base_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\n"
        "port_range_end = 3099\n"
    )
    return cfg_file, state_dir, env


def test_down_requires_force_when_branch_not_pushed(setup):
    cfg_file, state_dir, env = setup
    result = runner.invoke(app, ["down", "feature-x", "--config", str(cfg_file)])
    assert result.exit_code != 0
    assert "not been pushed" in result.output or "pushed" in result.output
    # State file should still exist
    assert (state_dir / f"{USER}-feature-x.json").exists()


def test_down_force_removes_everything(setup):
    cfg_file, state_dir, env = setup
    with patch("forsa_dev.tmux.kill_session"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["down", "feature-x", "--force", "--config", str(cfg_file)])
    assert result.exit_code == 0, result.output
    assert not (state_dir / f"{USER}-feature-x.json").exists()
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_cli_down.py -v
```

Expected: Error — `down` command not defined.

**Step 3: Add `down` to `src/forsa_dev/cli.py`**

Add after the `restart` command:

```python
@app.command()
def down(
    name: str,
    force: Annotated[bool, typer.Option("--force", help="Skip branch-push check.")] = False,
    config: ConfigOption = None,
):
    """Stop server, kill tmux, remove worktree. Checks branch is pushed first."""
    import subprocess
    cfg = _load(config)
    user = getpass.getuser()
    env = load_state(user, name, cfg.state_dir)

    if not force and not git.branch_is_pushed(cfg.repo, env.branch):
        typer.echo(
            f"Error: branch '{env.branch}' has not been pushed or merged.\n"
            "Use --force to delete anyway.",
            err=True,
        )
        raise typer.Exit(1)

    # Stop server if running
    if env.url:
        typer.echo("Stopping server...")
        subprocess.run(_compose_cmd(env, "down"), check=False)
        caddy.deregister_route(cfg.caddy_admin, name)

    # Kill tmux
    typer.echo("Killing tmux session...")
    try:
        tmux.kill_session(env.tmux_session)
    except RuntimeError:
        pass  # session may already be gone

    # Remove worktree
    typer.echo("Removing worktree...")
    git.remove_worktree(cfg.repo, env.worktree)

    # Delete state
    delete_state(user, name, cfg.state_dir)
    typer.echo(f"Environment '{_full_name(user, name)}' removed.")
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_cli_down.py -v
```

Expected: Both tests PASS.

**Step 5: Commit**

```bash
git add src/forsa_dev/cli.py tests/test_cli_down.py
git commit -m "feat: add down command"
```

---

### Task 12: `list` command

Read all state files, live-check each (tmux session + port), print Rich table.

**Files:**
- Modify: `src/forsa_dev/cli.py`
- Create: `tests/test_cli_list.py`

**Step 1: Write failing tests**

The `list` output goes to stdout. Test the logic that determines status, and that the command runs without error.

```python
# tests/test_cli_list.py
import getpass
from datetime import datetime, timezone
from pathlib import Path
import pytest
from typer.testing import CliRunner
from forsa_dev.cli import app
from forsa_dev.state import Environment, save_state
from forsa_dev.list_status import check_status, Status


runner = CliRunner()
USER = getpass.getuser()


def _env(name: str, user: str, port: int, url: str | None, state_dir: Path) -> Environment:
    worktree = Path(f"/tmp/worktrees/{name}")
    return Environment(
        name=name, user=user, branch=name,
        worktree=worktree,
        tmux_session=f"{user}-{name}",
        compose_file=worktree / "docker-compose.dev.yml",
        port=port, url=url,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None,
    )


def test_list_empty(tmp_path):
    cfg_file = tmp_path / "config.toml"
    state_dir = tmp_path / "state"
    cfg_file.write_text(
        f'repo = "/tmp/repo"\nworktree_dir = "/tmp/worktrees"\ndata_dir = "/data/dev"\n'
        f'state_dir = "{state_dir}"\ncaddy_admin = "http://localhost:2019"\n'
        'base_url = "optbox.example.ts.net"\ndocker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\nport_range_start = 3000\nport_range_end = 3099\n'
    )
    result = runner.invoke(app, ["list", "--config", str(cfg_file)])
    assert result.exit_code == 0
    assert "No environments" in result.output


def test_list_shows_environments(tmp_path):
    state_dir = tmp_path / "state"
    save_state(_env("ticket-42", USER, 3002, "optbox.example.ts.net/ticket-42/", state_dir), state_dir)
    save_state(_env("experiment", USER, 3003, None, state_dir), state_dir)
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f'repo = "/tmp/repo"\nworktree_dir = "/tmp/worktrees"\ndata_dir = "/data/dev"\n'
        f'state_dir = "{state_dir}"\ncaddy_admin = "http://localhost:2019"\n'
        'base_url = "optbox.example.ts.net"\ndocker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\nport_range_start = 3000\nport_range_end = 3099\n'
    )
    result = runner.invoke(app, ["list", "--config", str(cfg_file)])
    assert result.exit_code == 0
    assert "ticket-42" in result.output
    assert "experiment" in result.output


# Pure logic test — no subprocess needed
def test_check_status_tmux_missing_port_closed():
    status = check_status(tmux_exists=False, port_open=False)
    assert status.tmux == "missing"
    assert status.server == "stopped"


def test_check_status_tmux_exists_port_open():
    status = check_status(tmux_exists=True, port_open=True)
    assert status.tmux == "active"
    assert status.server == "running"


def test_check_status_tmux_exists_port_closed():
    status = check_status(tmux_exists=True, port_open=False)
    assert status.tmux == "active"
    assert status.server == "stopped"
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_cli_list.py -v
```

Expected: ImportError.

**Step 3: Create `src/forsa_dev/list_status.py`**

```python
from __future__ import annotations
import socket
from dataclasses import dataclass


@dataclass
class Status:
    tmux: str   # "active" | "missing"
    server: str  # "running" | "stopped" | "crashed"


def check_status(tmux_exists: bool, port_open: bool) -> Status:
    return Status(
        tmux="active" if tmux_exists else "missing",
        server="running" if port_open else "stopped",
    )


def port_is_open(port: int, host: str = "localhost") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0
```

**Step 4: Add `list` command to `src/forsa_dev/cli.py`**

Add at the top: `from forsa_dev.list_status import Status, check_status, port_is_open`

Add after `down`:

```python
@app.command(name="list")
def list_envs(
    config: ConfigOption = None,
):
    """List all environments with live status."""
    from rich.console import Console
    from rich.table import Table

    cfg = _load(config)
    envs = list_states(cfg.state_dir)

    console = Console()

    if not envs:
        console.print("No environments found.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("NAME")
    table.add_column("USER")
    table.add_column("TMUX")
    table.add_column("SERVER")
    table.add_column("PORT")
    table.add_column("URL")

    for env in envs:
        tmux_alive = tmux.session_exists(env.tmux_session)
        port_open = port_is_open(env.port)
        status = check_status(tmux_exists=tmux_alive, port_open=port_open)

        table.add_row(
            env.name,
            env.user,
            status.tmux,
            status.server,
            str(env.port),
            env.url or "-",
        )

    console.print(table)
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_cli_list.py -v
```

Expected: All tests PASS.

**Step 6: Commit**

```bash
git add src/forsa_dev/cli.py src/forsa_dev/list_status.py tests/test_cli_list.py
git commit -m "feat: add list command"
```

---

### Task 13: `logs` and `attach` commands

Simple passthrough commands — minimal testing needed.

**Files:**
- Modify: `src/forsa_dev/cli.py`
- Create: `tests/test_cli_passthrough.py`

**Step 1: Write failing tests**

```python
# tests/test_cli_passthrough.py
import getpass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
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


def test_attach_calls_tmux(env_setup):
    with patch("forsa_dev.tmux.attach_session") as mock_attach:
        result = runner.invoke(app, ["attach", "ticket-42", "--config", str(env_setup)])
    assert result.exit_code == 0
    mock_attach.assert_called_once_with(f"{USER}-ticket-42")
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_cli_passthrough.py -v
```

Expected: Error — commands not defined.

**Step 3: Add `logs` and `attach` to `src/forsa_dev/cli.py`**

```python
@app.command()
def logs(
    name: str,
    config: ConfigOption = None,
):
    """Stream Docker logs for an environment."""
    import subprocess
    cfg = _load(config)
    user = getpass.getuser()
    env = load_state(user, name, cfg.state_dir)
    subprocess.run(_compose_cmd(env, "logs", "-f"))


@app.command()
def attach(
    name: str,
    config: ConfigOption = None,
):
    """Attach to the tmux session for an environment."""
    cfg = _load(config)
    user = getpass.getuser()
    env = load_state(user, name, cfg.state_dir)
    tmux.attach_session(env.tmux_session)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_cli_passthrough.py -v
```

Expected: Both tests PASS.

**Step 5: Run the full test suite**

```bash
uv run pytest -v
```

Expected: All tests PASS.

**Step 6: Commit**

```bash
git add src/forsa_dev/cli.py tests/test_cli_passthrough.py
git commit -m "feat: add logs and attach commands"
```

---

### Task 14: Smoke test the CLI end-to-end

Verify all commands appear in help and the CLI is installable.

**Step 1: Verify help output**

```bash
uv run forsa-dev --help
uv run forsa-dev up --help
uv run forsa-dev serve --help
uv run forsa-dev stop --help
uv run forsa-dev down --help
uv run forsa-dev list --help
uv run forsa-dev logs --help
uv run forsa-dev attach --help
uv run forsa-dev restart --help
uv run forsa-dev init --help
```

Expected: All commands listed and each shows its options.

**Step 2: Run full test suite one final time**

```bash
uv run pytest -v
```

Expected: All tests PASS, no warnings.

**Step 3: Final commit**

```bash
git add .
git status  # verify only expected files
git commit -m "feat: forsa-dev CLI complete (phase 1)"
```
