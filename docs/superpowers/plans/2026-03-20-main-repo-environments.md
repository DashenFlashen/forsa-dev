# Main Repo Environments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface each user's main FORSA repo as a first-class environment in the dashboard, with the same serve/stop/restart and terminal controls as worktree environments.

**Architecture:** Add a `type` field to the `Environment` dataclass to distinguish `"repo"` from `"worktree"` environments. The dashboard auto-discovers repo environments on startup from each user's config. A checked-in `docker-compose.dev.yml` in the FORSA repo (prerequisite) replaces compose generation for repo environments; forsa-dev passes deployment-specific values via shell environment variables.

**Tech Stack:** Python (FastAPI, dataclasses), React (JSX), Docker Compose variable substitution

**Spec:** `docs/superpowers/specs/2026-03-20-main-repo-environments-design.md`

---

## File Map

**Modify:**
- `src/forsa_dev/state.py` — Add `type` field to `Environment`, update `_deserialize`
- `src/forsa_dev/operations.py` — Add `down_env` guard, reserve name `"main"`, add env var builder for repo compose calls, modify `serve_env`/`stop_env`/`restart_env`
- `src/forsa_dev/git.py` — Add `current_branch()` function
- `src/forsa_dev/dashboard/server.py` — Auto-discovery, ensure functions, visibility filtering, branch refresh, delete guard
- `dashboard/src/App.jsx` — Split envs into workspace/worktree, pass to new section
- `dashboard/src/components/EnvironmentTable.jsx` — Rename/clarify as worktree-only
- `dashboard/src/components/EnvironmentCard.jsx` — Hide delete for repo type
- `dashboard/src/components/EnvironmentRow.jsx` — Hide delete for repo type

**Create:**
- `dashboard/src/components/WorkspaceCard.jsx` — Dedicated card for the user's main repo environment

**Test:**
- `tests/test_state.py` — Type field serialization/deserialization
- `tests/test_operations.py` — Reserved name, down_env guard, env var builder
- `tests/test_git.py` — current_branch function
- `tests/test_dashboard_server.py` — Auto-discovery, visibility filtering, delete guard, branch refresh

---

### Task 1: Add `type` field to Environment

**Files:**
- Modify: `src/forsa_dev/state.py:13-26` (Environment dataclass)
- Modify: `src/forsa_dev/state.py:42-56` (`_deserialize`)
- Test: `tests/test_state.py`

- [ ] **Step 1: Write failing test for type field default**

Add to `tests/test_state.py`:

```python
def test_deserialize_state_without_type_field(tmp_path):
    """State files written before type support must still load as worktree."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    old_data = {
        "name": "ticket-42", "user": "anders", "branch": "ticket-42",
        "worktree": str(tmp_path / "wt"), "tmux_session": "anders-ticket-42",
        "compose_file": str(tmp_path / "compose.yml"),
        "port": 3002, "url": None,
        "created_at": "2026-03-07T22:00:00+00:00", "served_at": None,
    }
    (state_dir / "anders-ticket-42.json").write_text(json.dumps(old_data))
    env = load_state("anders", "ticket-42", state_dir)
    assert env.type == "worktree"


def test_state_roundtrip_with_type_field(tmp_path):
    state_dir = tmp_path / "state"
    env = Environment(
        name="main", user="anders", branch="main",
        worktree=tmp_path / "repo", tmux_session="anders-main",
        compose_file=tmp_path / "compose.yml",
        port=3002, url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None, type="repo",
    )
    save_state(env, state_dir)
    loaded = load_state("anders", "main", state_dir)
    assert loaded.type == "repo"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_state.py::test_deserialize_state_without_type_field tests/test_state.py::test_state_roundtrip_with_type_field -v`
Expected: FAIL — `Environment` has no `type` field

- [ ] **Step 3: Add type field to Environment and update _deserialize**

In `src/forsa_dev/state.py`, add `type: str = "worktree"` to the `Environment` dataclass (after `ttyd_pid`). In `_deserialize`, add `type=data.get("type", "worktree")` to the constructor call.

```python
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
    ttyd_port: int | None = None
    ttyd_pid: int | None = None
    type: str = "worktree"
```

In `_deserialize`, add the field:

```python
        ttyd_port=data.get("ttyd_port"),
        ttyd_pid=data.get("ttyd_pid"),
        type=data.get("type", "worktree"),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_state.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `uv run pytest`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/forsa_dev/state.py tests/test_state.py
git commit -m "feat: add type field to Environment dataclass"
```

---

### Task 2: Reserve the name "main" in up_env

**Files:**
- Modify: `src/forsa_dev/operations.py:53-66` (`up_env`)
- Test: `tests/test_operations.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_operations.py`:

```python
def test_up_env_rejects_reserved_name_main(up_cfg):
    cfg = up_cfg
    with pytest.raises(ValueError, match="reserved"):
        up_env(cfg, USER, "main")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_operations.py::test_up_env_rejects_reserved_name_main -v`
Expected: FAIL — "main" passes the regex check and tries to create a worktree

- [ ] **Step 3: Add guard in up_env**

In `src/forsa_dev/operations.py`, add after the `_NAME_RE` check in `up_env`:

```python
    if name == "main":
        raise ValueError(
            "The name 'main' is reserved for main repo environments."
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_operations.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/forsa_dev/operations.py tests/test_operations.py
git commit -m "feat: reserve 'main' name for repo environments"
```

---

### Task 3: Add down_env guard for repo environments

**Files:**
- Modify: `src/forsa_dev/operations.py:195-223` (`down_env`)
- Test: `tests/test_operations.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_operations.py`:

```python
def test_down_env_raises_for_repo_type(tmp_path):
    state_dir = tmp_path / "state"
    cfg = Config(
        repo=tmp_path / "repo", worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"), state_dir=state_dir,
        base_url="optbox.example.ts.net", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
        ttyd_port_range_start=7600, ttyd_port_range_end=7699,
    )
    env = Environment(
        name="main", user=USER, branch="main",
        worktree=tmp_path / "repo", tmux_session=f"{USER}-main",
        compose_file=tmp_path / "repo" / "docker-compose.dev.yml",
        port=3002, url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None, type="repo",
    )
    save_state(env, state_dir)
    with pytest.raises(ValueError, match="Cannot delete"):
        down_env(cfg, USER, "main")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_operations.py::test_down_env_raises_for_repo_type -v`
Expected: FAIL — `down_env` tries to process the environment normally

- [ ] **Step 3: Add guard in down_env**

In `src/forsa_dev/operations.py`, add at the start of `down_env` after loading state:

```python
def down_env(cfg: Config, user: str, name: str, force: bool = False) -> None:
    env = load_state(user, name, cfg.state_dir)

    if env.type == "repo":
        raise ValueError("Cannot delete repo environments.")

    # ... rest of function unchanged
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_operations.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/forsa_dev/operations.py tests/test_operations.py
git commit -m "feat: prevent deletion of repo environments"
```

---

### Task 4: Add current_branch to git module

**Files:**
- Modify: `src/forsa_dev/git.py`
- Test: `tests/test_git.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_git.py`:

```python
def test_current_branch_returns_branch_name(git_repo):
    assert current_branch(git_repo) == "main"


def test_current_branch_after_checkout(git_repo):
    subprocess.run(["git", "checkout", "-b", "feature"], check=True, capture_output=True, cwd=git_repo)
    assert current_branch(git_repo) == "feature"


def test_current_branch_returns_head_when_detached(git_repo):
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=git_repo)
    sha = result.stdout.strip()
    subprocess.run(["git", "checkout", sha], check=True, capture_output=True, cwd=git_repo)
    assert current_branch(git_repo) == "HEAD"


def test_current_branch_returns_none_for_invalid_repo(tmp_path):
    assert current_branch(tmp_path) is None
```

Update the import at top of `tests/test_git.py` to include `current_branch`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_git.py::test_current_branch_returns_branch_name -v`
Expected: FAIL — `current_branch` doesn't exist

- [ ] **Step 3: Implement current_branch**

Add to `src/forsa_dev/git.py`:

```python
def current_branch(repo: Path) -> str | None:
    """Return the current branch name, 'HEAD' if detached, or None if not a repo."""
    result = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    if result.returncode != 0:
        return None
    return result.stdout.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_git.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/forsa_dev/git.py tests/test_git.py
git commit -m "feat: add current_branch function to git module"
```

---

### Task 5: Add compose env var builder for repo environments

**Files:**
- Modify: `src/forsa_dev/operations.py`
- Test: `tests/test_operations.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_operations.py`:

```python
from forsa_dev.operations import repo_compose_env


def test_repo_compose_env_builds_correct_dict(cfg_and_env):
    cfg, env = cfg_and_env
    from dataclasses import replace
    repo_env = replace(env, name="main", type="repo")
    result = repo_compose_env(cfg, repo_env)
    assert result["FORSA_DEV_PORT"] == str(repo_env.port)
    assert result["FORSA_DEV_DATA"] == str(cfg.data_dir)
    assert result["FORSA_DEV_CONTAINER"] == f"forsa-{repo_env.user}-main"
    assert result["FORSA_DEV_IMAGE"] == cfg.docker_image
    assert result["FORSA_DEV_GUROBI_LIC"] == str(cfg.gurobi_lic)
    # Must also contain inherited os.environ keys
    assert "PATH" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_operations.py::test_repo_compose_env_builds_correct_dict -v`
Expected: FAIL — `repo_compose_env` doesn't exist

- [ ] **Step 3: Implement repo_compose_env**

Add to `src/forsa_dev/operations.py`:

```python
def repo_compose_env(cfg: Config, env: Environment) -> dict[str, str]:
    """Build environment variables for docker compose with a repo environment."""
    return {
        **os.environ,
        "FORSA_DEV_PORT": str(env.port),
        "FORSA_DEV_DATA": str(cfg.data_dir),
        "FORSA_DEV_CONTAINER": f"forsa-{env.user}-{env.name}",
        "FORSA_DEV_IMAGE": cfg.docker_image,
        "FORSA_DEV_GUROBI_LIC": str(cfg.gurobi_lic),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_operations.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/forsa_dev/operations.py tests/test_operations.py
git commit -m "feat: add repo_compose_env for repo environment docker calls"
```

---

### Task 6: Modify serve/stop/restart to pass env vars for repo environments

**Files:**
- Modify: `src/forsa_dev/operations.py:31-50` (`serve_env`, `stop_env`, `restart_env`)
- Test: `tests/test_operations.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_operations.py`:

```python
def test_serve_env_passes_env_vars_for_repo_type(tmp_path):
    state_dir = tmp_path / "state"
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    compose_file = repo_dir / "docker-compose.dev.yml"
    compose_file.write_text("services: {}")
    env = Environment(
        name="main", user=USER, branch="main",
        worktree=repo_dir, tmux_session=f"{USER}-main",
        compose_file=compose_file,
        port=3002, url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None, type="repo",
    )
    save_state(env, state_dir)
    cfg = Config(
        repo=repo_dir, worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"), state_dir=state_dir,
        base_url="optbox.example.ts.net", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
        ttyd_port_range_start=7600, ttyd_port_range_end=7699,
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        serve_env(cfg, USER, "main")
    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs.get("env") is not None
    assert call_kwargs.kwargs["env"]["FORSA_DEV_PORT"] == "3002"


def test_stop_env_passes_env_vars_for_repo_type(tmp_path):
    state_dir = tmp_path / "state"
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    compose_file = repo_dir / "docker-compose.dev.yml"
    compose_file.write_text("services: {}")
    env = Environment(
        name="main", user=USER, branch="main",
        worktree=repo_dir, tmux_session=f"{USER}-main",
        compose_file=compose_file,
        port=3002, url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None, type="repo",
    )
    save_state(env, state_dir)
    cfg = Config(
        repo=repo_dir, worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"), state_dir=state_dir,
        base_url="optbox.example.ts.net", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
        ttyd_port_range_start=7600, ttyd_port_range_end=7699,
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        stop_env(cfg, USER, "main")
    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs.get("env") is not None
    assert call_kwargs.kwargs["env"]["FORSA_DEV_PORT"] == "3002"


def test_restart_env_passes_env_vars_for_repo_type(tmp_path):
    state_dir = tmp_path / "state"
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    compose_file = repo_dir / "docker-compose.dev.yml"
    compose_file.write_text("services: {}")
    env = Environment(
        name="main", user=USER, branch="main",
        worktree=repo_dir, tmux_session=f"{USER}-main",
        compose_file=compose_file,
        port=3002, url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None, type="repo",
    )
    save_state(env, state_dir)
    cfg = Config(
        repo=repo_dir, worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"), state_dir=state_dir,
        base_url="optbox.example.ts.net", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
        ttyd_port_range_start=7600, ttyd_port_range_end=7699,
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        restart_env(cfg, USER, "main")
    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs.get("env") is not None
    assert call_kwargs.kwargs["env"]["FORSA_DEV_PORT"] == "3002"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_operations.py::test_serve_env_passes_env_vars_for_repo_type tests/test_operations.py::test_stop_env_passes_env_vars_for_repo_type tests/test_operations.py::test_restart_env_passes_env_vars_for_repo_type -v`
Expected: FAIL — `subprocess.run` called without `env` kwarg

- [ ] **Step 3: Modify serve_env, stop_env, restart_env**

Update the three functions in `src/forsa_dev/operations.py` to conditionally pass `env` to `subprocess.run`:

```python
def serve_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    run_env = repo_compose_env(cfg, env) if env.type == "repo" else None
    result = subprocess.run(compose_cmd(env, "up", "-d"), check=False, env=run_env)
    if result.returncode != 0:
        raise RuntimeError("docker compose up failed")
    url = f"http://{cfg.base_url}:{env.port}"
    updated = replace(env, url=url, served_at=datetime.now(tz=timezone.utc))
    save_state(updated, cfg.state_dir)


def stop_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    run_env = repo_compose_env(cfg, env) if env.type == "repo" else None
    subprocess.run(compose_cmd(env, "down"), check=False, env=run_env)
    updated = replace(env, url=None, served_at=None)
    save_state(updated, cfg.state_dir)


def restart_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    run_env = repo_compose_env(cfg, env) if env.type == "repo" else None
    subprocess.run(compose_cmd(env, "restart"), check=False, env=run_env)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_operations.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/forsa_dev/operations.py tests/test_operations.py
git commit -m "feat: pass FORSA_DEV env vars for repo compose calls"
```

---

### Task 7: Auto-discovery and ensure functions in dashboard server

**Files:**
- Modify: `src/forsa_dev/dashboard/server.py:22-37` (`discover_users`), `server.py:52-265` (`create_app`)
- Test: `tests/test_dashboard_server.py`

- [ ] **Step 1: Write failing tests for auto-discovery**

Add to `tests/test_dashboard_server.py`:

```python
def test_auto_discovery_creates_repo_environment_state(tmp_path):
    """Dashboard startup creates state for main repo environments."""
    state_dir = tmp_path / "state"
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    compose_file = repo_dir / "docker-compose.dev.yml"
    compose_file.write_text("services: {}")
    cfg = Config(
        repo=repo_dir, worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"), state_dir=state_dir,
        base_url="localhost", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
        ttyd_port_range_start=7600, ttyd_port_range_end=7699,
    )
    with patch("forsa_dev.dashboard.server.tmux") as mock_tmux, \
         patch("forsa_dev.dashboard.server.ttyd") as mock_ttyd:
        mock_tmux.session_exists.return_value = False
        mock_ttyd.start_ttyd.return_value = 11111
        mock_ttyd.ttyd_is_alive.return_value = True
        mock_ttyd.ttyd_port_is_open.return_value = True
        app = create_app({TEST_USER: cfg})
    # State file should exist
    env = load_state(TEST_USER, "main", state_dir)
    assert env.type == "repo"
    assert env.name == "main"
    assert env.worktree == repo_dir
    assert env.compose_file == compose_file


def test_auto_discovery_skips_when_compose_missing(tmp_path):
    """If docker-compose.dev.yml doesn't exist in repo, skip auto-discovery."""
    state_dir = tmp_path / "state"
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    # No compose file created
    cfg = Config(
        repo=repo_dir, worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"), state_dir=state_dir,
        base_url="localhost", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
        ttyd_port_range_start=7600, ttyd_port_range_end=7699,
    )
    app = create_app({TEST_USER: cfg})
    with pytest.raises(FileNotFoundError):
        load_state(TEST_USER, "main", state_dir)


def test_auto_discovery_does_not_recreate_existing_state(tmp_path):
    """If state already exists, don't overwrite it."""
    state_dir = tmp_path / "state"
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    compose_file = repo_dir / "docker-compose.dev.yml"
    compose_file.write_text("services: {}")
    env = Environment(
        name="main", user=TEST_USER, branch="main",
        worktree=repo_dir, tmux_session=f"{TEST_USER}-main",
        compose_file=compose_file,
        port=3050, url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None, type="repo",
    )
    save_state(env, state_dir)
    cfg = Config(
        repo=repo_dir, worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"), state_dir=state_dir,
        base_url="localhost", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
        ttyd_port_range_start=7600, ttyd_port_range_end=7699,
    )
    with patch("forsa_dev.dashboard.server.tmux") as mock_tmux, \
         patch("forsa_dev.dashboard.server.ttyd") as mock_ttyd:
        mock_tmux.session_exists.return_value = True
        mock_ttyd.ttyd_is_alive.return_value = True
        mock_ttyd.ttyd_port_is_open.return_value = True
        app = create_app({TEST_USER: cfg})
    # Port should not have changed
    loaded = load_state(TEST_USER, "main", state_dir)
    assert loaded.port == 3050
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dashboard_server.py::test_auto_discovery_creates_repo_environment_state -v`
Expected: FAIL — no auto-discovery logic exists

- [ ] **Step 3: Implement auto-discovery and ensure functions**

Add to `src/forsa_dev/dashboard/server.py`, inside `create_app`, before the route definitions:

```python
    from forsa_dev.ports import allocate_ports
    from forsa_dev.state import save_state, load_state as _load_state

    # Auto-discover main repo environments
    for username, cfg in user_configs.items():
        try:
            _load_state(username, "main", state_dir)
        except FileNotFoundError:
            compose_file = cfg.repo / "docker-compose.dev.yml"
            if not compose_file.exists():
                import logging
                logging.getLogger(__name__).warning(
                    "Skipping repo env for %s: %s not found", username, compose_file
                )
                continue
            ranges = (
                (cfg.port_range_start, cfg.port_range_end),
                (cfg.ttyd_port_range_start, cfg.ttyd_port_range_end),
            )
            with allocate_ports(state_dir, *ranges) as (port, ttyd_port):
                env = Environment(
                    name="main",
                    user=username,
                    branch=git.current_branch(cfg.repo) or "",
                    worktree=cfg.repo,
                    tmux_session=f"{username}-main",
                    compose_file=compose_file,
                    port=port,
                    url=None,
                    created_at=datetime.now(tz=timezone.utc),
                    served_at=None,
                    ttyd_port=ttyd_port,
                    type="repo",
                )
                save_state(env, state_dir)

    # Ensure tmux and ttyd for repo environments
    for username, cfg in user_configs.items():
        try:
            env = _load_state(username, "main", state_dir)
        except FileNotFoundError:
            continue
        if env.type != "repo":
            continue
        if not tmux.session_exists(env.tmux_session):
            shell = os.environ.get("SHELL", "/bin/bash")
            command = f"{shell} -i -c 'claude --dangerously-skip-permissions --effort max; exec {shell}'"
            try:
                tmux.create_session(env.tmux_session, env.worktree, command=command)
            except RuntimeError:
                pass
        if env.ttyd_port and not ttyd.ttyd_is_alive(env.ttyd_pid):
            try:
                pid = ttyd.start_ttyd(env.ttyd_port, env.tmux_session)
                from dataclasses import replace
                updated = replace(env, ttyd_pid=pid)
                save_state(updated, state_dir)
            except Exception:
                pass
```

Add missing imports at top of `server.py`:

```python
import os
from datetime import datetime, timezone
from forsa_dev.state import Environment, list_states, load_state, save_state
```

(Replace the existing `from forsa_dev.state import list_states, load_state` import.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dashboard_server.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/forsa_dev/dashboard/server.py tests/test_dashboard_server.py
git commit -m "feat: auto-discover repo environments on dashboard startup"
```

---

### Task 8: Visibility filtering and branch refresh in GET /api/environments

**Files:**
- Modify: `src/forsa_dev/dashboard/server.py:89-121` (`get_environments`)
- Test: `tests/test_dashboard_server.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_dashboard_server.py`:

```python
def test_get_environments_hides_other_users_repo_envs(tmp_path):
    """Repo envs are only visible to their owner."""
    state_dir = tmp_path / "state"
    cfg = Config(
        repo=tmp_path / "repo", worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"), state_dir=state_dir,
        base_url="localhost", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
        ttyd_port_range_start=7600, ttyd_port_range_end=7699,
    )
    # Create a repo env for "other_user"
    repo_env = Environment(
        name="main", user="other_user", branch="main",
        worktree=tmp_path / "other-repo", tmux_session="other_user-main",
        compose_file=tmp_path / "other-repo" / "docker-compose.dev.yml",
        port=3050, url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None, type="repo",
    )
    save_state(repo_env, state_dir)
    # Create a worktree env for "other_user" (should still be visible)
    wt_env = Environment(
        name="ticket-42", user="other_user", branch="ticket-42",
        worktree=tmp_path / "worktrees" / "ticket-42",
        tmux_session="other_user-ticket-42",
        compose_file=tmp_path / "worktrees" / "ticket-42" / "docker-compose.dev.yml",
        port=3051, url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None, type="worktree",
    )
    save_state(wt_env, state_dir)
    user_configs = {TEST_USER: cfg, "other_user": cfg}
    with patch("forsa_dev.dashboard.server.tmux") as mock_tmux, \
         patch("forsa_dev.dashboard.server.port_is_open", return_value=False), \
         patch("forsa_dev.dashboard.server.ttyd") as mock_ttyd:
        mock_tmux.session_status.return_value = "missing"
        mock_tmux.session_exists.return_value = True
        mock_ttyd.ttyd_is_alive.return_value = True
        mock_ttyd.ttyd_port_is_open.return_value = False
        mock_ttyd.start_ttyd.return_value = 1
        app = create_app(user_configs)
        client = TestClient(app)
        client.cookies.set("forsa_user", TEST_USER)
        response = client.get("/api/environments")
    data = response.json()
    names = [(e["user"], e["name"]) for e in data]
    # other_user's worktree should be visible
    assert ("other_user", "ticket-42") in names
    # other_user's repo env should NOT be visible
    assert ("other_user", "main") not in names


def test_get_environments_includes_type_field(setup):
    user_configs, _, _ = setup
    with patch("forsa_dev.dashboard.server.tmux") as mock_tmux, \
         patch("forsa_dev.dashboard.server.port_is_open", return_value=False), \
         patch("forsa_dev.dashboard.server.ttyd") as mock_ttyd:
        mock_tmux.session_status.return_value = "active"
        mock_ttyd.ttyd_is_alive.return_value = False
        mock_ttyd.ttyd_port_is_open.return_value = False
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.get("/api/environments")
    data = response.json()
    assert data[0]["type"] == "worktree"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dashboard_server.py::test_get_environments_hides_other_users_repo_envs tests/test_dashboard_server.py::test_get_environments_includes_type_field -v`
Expected: FAIL

- [ ] **Step 3: Modify get_environments**

Update `get_environments` in `src/forsa_dev/dashboard/server.py` to add `type` to the response, filter repo envs by the requesting user cookie, and refresh branches for repo envs:

```python
    @app.get("/api/environments")
    def get_environments(forsa_user: str = Cookie(default=None)) -> list[dict[str, Any]]:
        envs = list_states(state_dir)
        result = []
        for env in envs:
            # Filter: repo environments only visible to their owner
            if env.type == "repo" and env.user != forsa_user:
                continue

            # Refresh branch for repo environments
            branch = env.branch
            if env.type == "repo":
                current = git.current_branch(env.worktree)
                if current is not None:
                    branch = current

            tmux_stat = tmux.session_status(env.tmux_session)
            port_open = port_is_open(env.port)
            status = check_status(
                tmux_status=tmux_stat, served=env.url is not None, port_open=port_open
            )
            ttyd_alive = (
                ttyd.ttyd_port_is_open(env.ttyd_port) if env.ttyd_port is not None
                else False
            )
            result.append({
                "name": env.name,
                "user": env.user,
                "branch": branch,
                "worktree": str(env.worktree),
                "port": env.port,
                "ttyd_port": env.ttyd_port,
                "tmux_session": env.tmux_session,
                "url": env.url or f"http://{base_url}:{env.port}",
                "created_at": env.created_at.isoformat(),
                "served_at": env.served_at.isoformat() if env.served_at else None,
                "status": {
                    "tmux": status.tmux,
                    "server": status.server,
                    "ttyd": "alive" if ttyd_alive else "dead",
                },
                "uptime": format_uptime(env.served_at),
                "type": env.type,
            })
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dashboard_server.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/forsa_dev/dashboard/server.py tests/test_dashboard_server.py
git commit -m "feat: filter repo envs by owner and add type/branch refresh"
```

---

### Task 9: Add delete guard in dashboard API

**Files:**
- Modify: `src/forsa_dev/dashboard/server.py:204-215` (`delete_environment`)
- Test: `tests/test_dashboard_server.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_dashboard_server.py`:

```python
def test_delete_returns_400_for_repo_environment(tmp_path):
    state_dir = tmp_path / "state"
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    compose_file = repo_dir / "docker-compose.dev.yml"
    compose_file.write_text("services: {}")
    env = Environment(
        name="main", user=TEST_USER, branch="main",
        worktree=repo_dir, tmux_session=f"{TEST_USER}-main",
        compose_file=compose_file,
        port=3050, url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None, type="repo",
    )
    save_state(env, state_dir)
    cfg = Config(
        repo=repo_dir, worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"), state_dir=state_dir,
        base_url="localhost", docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000, port_range_end=3099,
        ttyd_port_range_start=7600, ttyd_port_range_end=7699,
    )
    with patch("forsa_dev.dashboard.server.tmux") as mock_tmux, \
         patch("forsa_dev.dashboard.server.ttyd") as mock_ttyd:
        mock_tmux.session_exists.return_value = True
        mock_ttyd.ttyd_is_alive.return_value = True
        mock_ttyd.ttyd_port_is_open.return_value = True
        app = create_app({TEST_USER: cfg})
    client = TestClient(app)
    client.cookies.set("forsa_user", TEST_USER)
    response = client.delete(f"/api/environments/{TEST_USER}/main")
    assert response.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dashboard_server.py::test_delete_returns_400_for_repo_environment -v`
Expected: FAIL — `down_env` raises `ValueError` which isn't caught as 400

- [ ] **Step 3: Update delete endpoint to catch ValueError**

In `src/forsa_dev/dashboard/server.py`, update the `delete_environment` handler:

```python
    @app.delete("/api/environments/{owner}/{name}")
    def delete_environment(
        owner: str, name: str, force: bool = False, _user: str = Depends(get_user),
    ) -> dict[str, str]:
        cfg = _get_owner_cfg(owner)
        try:
            down_env(cfg, owner, name, force=force)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return {"status": "ok"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dashboard_server.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/forsa_dev/dashboard/server.py tests/test_dashboard_server.py
git commit -m "feat: return 400 when trying to delete repo environment"
```

---

### Task 10: Frontend — WorkspaceCard component

**Files:**
- Create: `dashboard/src/components/WorkspaceCard.jsx`

- [ ] **Step 1: Create WorkspaceCard component**

This is a dedicated card for the user's main repo environment. It reuses the same action buttons and status badges but has no delete button.

Create `dashboard/src/components/WorkspaceCard.jsx`:

```jsx
import ActionButtons from './ActionButtons'
import StatusBadge from './StatusBadge'

export default function WorkspaceCard({ env, onAction, loading, onSelect }) {
  if (!env) return null

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-200">Workspace</h3>
          <p className="text-xs text-gray-500 font-mono mt-0.5">{env.branch}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={env.status.server} />
          <StatusBadge status={env.status.tmux} />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <ActionButtons
          env={env}
          onAction={onAction}
          loading={loading}
        />
        {env.status.ttyd === 'alive' && (
          <button
            onClick={() => onSelect(env)}
            className="rounded bg-gray-700 px-3 py-1.5 text-xs font-medium text-gray-200 hover:bg-gray-600"
          >
            Terminal
          </button>
        )}
        {env.uptime && (
          <span className="text-xs text-gray-500 ml-auto">{env.uptime}</span>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/components/WorkspaceCard.jsx
git commit -m "feat: add WorkspaceCard component for repo environments"
```

---

### Task 11: Frontend — Split environments into workspace and worktrees in App.jsx

**Files:**
- Modify: `dashboard/src/App.jsx`

- [ ] **Step 1: Update App.jsx to separate repo and worktree environments**

In `dashboard/src/App.jsx`:

1. Add import for `WorkspaceCard`
2. Derive `workspaceEnv` and `worktreeEnvs` from the envs array
3. Render `WorkspaceCard` above `CreateEnvironment`

```jsx
import WorkspaceCard from './components/WorkspaceCard'
```

In the render, before `<CreateEnvironment>`:

```jsx
const workspaceEnv = envs.find((e) => e.type === 'repo' && e.user === user)
const worktreeEnvs = envs.filter((e) => e.type !== 'repo')
```

Replace the main content area with:

```jsx
<main className="mx-auto max-w-7xl px-4 py-4 lg:px-6 lg:py-6 space-y-6">
  <HealthPanel health={health} />
  <WorkspaceCard
    env={workspaceEnv}
    onAction={handleAction}
    loading={workspaceEnv ? loadingActions[`${workspaceEnv.user}/${workspaceEnv.name}`] : null}
    onSelect={handleSelect}
  />
  <CreateEnvironment onCreate={handleCreate} defaultDataDir={defaultDataDir} />
  <EnvironmentTable
    envs={worktreeEnvs}
    onAction={handleAction}
    loadingActions={loadingActions}
    onSelect={handleSelect}
    selectedEnv={selectedEnv}
    onDelete={handleDelete}
    loadingDeletes={loadingDeletes}
  />
  ...terminal overlays unchanged...
</main>
```

- [ ] **Step 2: Verify it renders correctly**

Run: `cd dashboard && npm run build`
Expected: BUILD SUCCESS with no errors

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/App.jsx
git commit -m "feat: split dashboard into workspace and worktrees sections"
```

---

### Task 12: Frontend — Hide delete button for repo environments in card/row

**Files:**
- Modify: `dashboard/src/components/EnvironmentCard.jsx`
- Modify: `dashboard/src/components/EnvironmentRow.jsx`

- [ ] **Step 1: Read both files and identify delete button locations**

Read `EnvironmentCard.jsx` and `EnvironmentRow.jsx` to find the delete buttons.

- [ ] **Step 2: Add type guard to delete buttons**

In both components, wrap the delete button with `{env.type !== 'repo' && (... delete button ...)}`.

This is a safety net — repo environments should already be filtered out of the EnvironmentTable, but the guard prevents accidental deletion if the filtering logic changes.

- [ ] **Step 3: Build frontend**

Run: `cd dashboard && npm run build`
Expected: BUILD SUCCESS

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/EnvironmentCard.jsx dashboard/src/components/EnvironmentRow.jsx
git commit -m "feat: hide delete button for repo environments"
```

---

### Task 13: Build production dashboard assets

**Files:**
- Modify: `src/forsa_dev/dashboard/static/` (build output)

- [ ] **Step 1: Build and copy production assets**

```bash
cd dashboard && npm run build
rm -rf ../src/forsa_dev/dashboard/static/*
cp -r dist/* ../src/forsa_dev/dashboard/static/
```

- [ ] **Step 2: Commit**

```bash
git add src/forsa_dev/dashboard/static/
git commit -m "build: update dashboard production assets"
```

---

### Task 14: Full test suite and lint

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: ALL PASS

- [ ] **Step 2: Run linter**

Run: `uv run ruff check src/ tests/`
Expected: No errors

- [ ] **Step 3: Fix any issues found**

- [ ] **Step 4: Final commit if needed**

```bash
git add -u
git commit -m "fix: address lint and test issues"
```
