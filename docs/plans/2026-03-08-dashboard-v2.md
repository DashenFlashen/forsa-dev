# Dashboard V2: ttyd, Create/Delete, Terminal View

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Extend the existing `forsa-dev` dashboard with environment creation/deletion, embedded ttyd web terminal, and the `--with-claude` flag for tmux sessions.

**Architecture:** All business logic lives in `operations.py` (and new `ttyd.py`). FastAPI `server.py` and `cli.py` are thin wrappers. React frontend gains a create form, delete buttons, and a split-pane iframe terminal.

**Tech Stack:** Python/FastAPI/dataclasses (backend), React/Vite/Tailwind (frontend), ttyd (terminal server), existing `ports.py` allocator.

---

## Current state (do not re-implement)

The following is already done and MUST keep passing throughout all tasks:
- `operations.py`: `compose_cmd`, `serve_env`, `stop_env`, `restart_env`
- `dashboard/server.py`: GET `/api/environments`, GET `/api/health`, POST `/{name}/serve`, POST `/{name}/stop`, POST `/{name}/restart`
- React components: `HealthBar`, `EnvironmentTable`, `EnvironmentRow`, `ActionButtons`, `ErrorBanner`
- `App.jsx` polling (envs every 3s, health every 10s)
- 72 tests passing

---

## Task 1: State + Config additions

**Files:**
- Modify: `src/forsa_dev/state.py`
- Modify: `src/forsa_dev/config.py`
- Modify: `src/forsa_dev/cli.py` (init command only)
- Modify: `tests/test_state.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_cli_init.py`

**Context:** `Environment` dataclass needs two new optional fields for ttyd. `Config` needs the ttyd port range. Both must be backward-compatible (old state files and config files without these fields must still load).

**Step 1: Write failing tests for state backward compat**

In `tests/test_state.py`, add:

```python
def test_deserialize_state_without_ttyd_fields(tmp_path):
    """State files written before ttyd support must still load."""
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
    assert env.ttyd_port is None
    assert env.ttyd_pid is None


def test_state_roundtrip_with_ttyd_fields(tmp_path):
    state_dir = tmp_path / "state"
    env = Environment(
        name="ticket-42", user="anders", branch="ticket-42",
        worktree=tmp_path / "wt", tmux_session="anders-ticket-42",
        compose_file=tmp_path / "compose.yml",
        port=3002, url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None, ttyd_port=7602, ttyd_pid=12345,
    )
    save_state(env, state_dir)
    loaded = load_state("anders", "ticket-42", state_dir)
    assert loaded.ttyd_port == 7602
    assert loaded.ttyd_pid == 12345
```

**Step 2: Run tests, confirm they fail**

```
cd /Users/andersnordmark/work/personal/forsa-dev
uv run pytest tests/test_state.py -k "ttyd" -v
```
Expected: AttributeError or similar (fields don't exist yet).

**Step 3: Add ttyd fields to `state.py`**

In `src/forsa_dev/state.py`, add two optional fields to `Environment`:

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
```

Update `_deserialize` to use `.get()` for the new fields:

```python
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
        ttyd_port=data.get("ttyd_port"),
        ttyd_pid=data.get("ttyd_pid"),
    )
```

`_serialize` needs no change: `asdict(env)` already includes the new fields, and `int | None` is JSON-native.

**Step 4: Run state tests**

```
uv run pytest tests/test_state.py -v
```
Expected: all pass.

**Step 5: Write failing tests for config ttyd range**

In `tests/test_config.py`, add:

```python
def test_load_config_without_ttyd_range_uses_defaults(tmp_path):
    """Configs without ttyd range fall back to defaults."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        'repo = "/r"\nworktree_dir = "/w"\ndata_dir = "/d"\n'
        'state_dir = "/s"\nbase_url = "localhost"\n'
        'docker_image = "img"\ngurobi_lic = "/g"\n'
        'port_range_start = 3000\nport_range_end = 3099\n'
    )
    cfg = load_config(cfg_file)
    assert cfg.ttyd_port_range_start == 7600
    assert cfg.ttyd_port_range_end == 7699


def test_config_ttyd_range_roundtrip(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg = Config(
        repo=Path("/r"), worktree_dir=Path("/w"), data_dir=Path("/d"),
        state_dir=Path("/s"), base_url="localhost",
        docker_image="img", gurobi_lic=Path("/g"),
        port_range_start=3000, port_range_end=3099,
        ttyd_port_range_start=7600, ttyd_port_range_end=7699,
    )
    save_config(cfg, cfg_file)
    loaded = load_config(cfg_file)
    assert loaded.ttyd_port_range_start == 7600
    assert loaded.ttyd_port_range_end == 7699
```

**Step 6: Run new config tests, confirm they fail**

```
uv run pytest tests/test_config.py -k "ttyd" -v
```

**Step 7: Add ttyd range to `config.py`**

Add module-level defaults:
```python
_DEFAULT_TTYD_PORT_RANGE_START = 7600
_DEFAULT_TTYD_PORT_RANGE_END = 7699
```

Add fields to `Config` (with defaults, so existing callers without these args still work):
```python
@dataclass(frozen=True)
class Config:
    ...
    ttyd_port_range_start: int = _DEFAULT_TTYD_PORT_RANGE_START
    ttyd_port_range_end: int = _DEFAULT_TTYD_PORT_RANGE_END
```

Update `load_config`:
```python
ttyd_port_range_start=int(data.get("ttyd_port_range_start", _DEFAULT_TTYD_PORT_RANGE_START)),
ttyd_port_range_end=int(data.get("ttyd_port_range_end", _DEFAULT_TTYD_PORT_RANGE_END)),
```

Update `save_config` to write them:
```python
"ttyd_port_range_start": config.ttyd_port_range_start,
"ttyd_port_range_end": config.ttyd_port_range_end,
```

Update `init` in `cli.py` to prompt for them and pass to `Config(...)`:
```python
ttyd_port_start = typer.prompt("ttyd port range start", default=7600)
ttyd_port_end = typer.prompt("ttyd port range end", default=7699)
...
cfg = Config(
    ...
    ttyd_port_range_start=int(ttyd_port_start),
    ttyd_port_range_end=int(ttyd_port_end),
)
```

Also update `test_cli_init.py` to assert the new prompts appear or supply them.

**Step 8: Run all tests**

```
uv run pytest -v
```
Expected: all 72+ tests pass.

**Step 9: Commit**

```
git add src/forsa_dev/state.py src/forsa_dev/config.py src/forsa_dev/cli.py \
        tests/test_state.py tests/test_config.py tests/test_cli_init.py
git commit -m "feat: add ttyd_port/ttyd_pid to state, ttyd port range to config"
```

---

## Task 2: ttyd.py + ports.py multi-range allocator

**Files:**
- Create: `src/forsa_dev/ttyd.py`
- Create: `tests/test_ttyd.py`
- Modify: `src/forsa_dev/ports.py`
- Modify: `tests/test_ports.py`

**Context:** `ttyd.py` wraps subprocess calls for starting/stopping/checking ttyd processes. It must be thin enough to mock in tests. `ports.py` needs to allocate two ports atomically (server + ttyd) under a single lock. The existing `allocate_port` API is preserved; a new `allocate_ports` handles multi-range allocation.

**Step 1: Write failing tests for ttyd.py**

Create `tests/test_ttyd.py`:

```python
import signal
from unittest.mock import MagicMock, patch

import pytest

from forsa_dev.ttyd import start_ttyd, stop_ttyd, ttyd_is_alive


def test_start_ttyd_launches_process_and_returns_pid():
    mock_proc = MagicMock()
    mock_proc.pid = 42
    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        pid = start_ttyd(7682, "anders-ticket-42")
    assert pid == 42
    mock_popen.assert_called_once()
    cmd = mock_popen.call_args[0][0]
    assert "ttyd" in cmd
    assert "-W" in cmd
    assert "-p" in cmd
    assert "7682" in cmd or 7682 in cmd
    assert "tmux" in cmd
    assert "anders-ticket-42" in cmd


def test_stop_ttyd_sends_sigterm():
    with patch("os.kill") as mock_kill:
        stop_ttyd(42)
    mock_kill.assert_called_once_with(42, signal.SIGTERM)


def test_stop_ttyd_ignores_process_not_found():
    with patch("os.kill", side_effect=ProcessLookupError):
        stop_ttyd(99999)  # should not raise


def test_ttyd_is_alive_returns_true_for_live_process():
    with patch("os.kill", return_value=None):  # kill(pid, 0) succeeds
        assert ttyd_is_alive(42) is True


def test_ttyd_is_alive_returns_false_for_dead_process():
    with patch("os.kill", side_effect=ProcessLookupError):
        assert ttyd_is_alive(42) is False
```

**Step 2: Run tests, confirm they fail**

```
uv run pytest tests/test_ttyd.py -v
```
Expected: ModuleNotFoundError.

**Step 3: Create `src/forsa_dev/ttyd.py`**

```python
from __future__ import annotations

import os
import signal
import subprocess


def start_ttyd(port: int, session: str) -> int:
    """Start a ttyd process for the given tmux session. Returns the PID."""
    proc = subprocess.Popen(
        ["ttyd", "-W", "-p", str(port), "tmux", "attach", "-t", session]
    )
    return proc.pid


def stop_ttyd(pid: int) -> None:
    """Send SIGTERM to a ttyd process. Ignores errors if already gone."""
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def ttyd_is_alive(pid: int) -> bool:
    """Return True if the process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
```

**Step 4: Run ttyd tests**

```
uv run pytest tests/test_ttyd.py -v
```
Expected: all pass.

**Step 5: Write failing tests for multi-range port allocator**

In `tests/test_ports.py`, add:

```python
def test_allocate_ports_returns_one_port_per_range(tmp_path):
    from forsa_dev.ports import allocate_ports
    with allocate_ports(tmp_path, (3000, 3099), (7600, 7699)) as (srv, ttyd):
        assert 3000 <= srv <= 3099
        assert 7600 <= ttyd <= 7699


def test_allocate_ports_no_double_allocation(tmp_path):
    """Two ports from the same range must not overlap within a single call."""
    from forsa_dev.ports import allocate_ports
    # Use two adjacent ranges that share no ports
    with allocate_ports(tmp_path, (3000, 3000), (3001, 3001)) as (a, b):
        assert a != b


def test_allocate_port_still_works_after_refactor(tmp_path):
    """Existing single-port API unchanged."""
    from forsa_dev.ports import allocate_port
    with allocate_port(tmp_path, 3000, 3099) as port:
        assert 3000 <= port <= 3099


def test_allocate_port_skips_used_ttyd_port(tmp_path):
    """allocate_port should not return a port already used as a ttyd_port."""
    from forsa_dev.state import Environment, save_state
    from forsa_dev.ports import allocate_port
    from datetime import datetime, timezone
    # Create an env whose ttyd_port is 3000 (to test cross-field awareness)
    env = Environment(
        name="x", user="u", branch="x",
        worktree=tmp_path / "w", tmux_session="u-x",
        compose_file=tmp_path / "c.yml",
        port=3001, url=None,
        created_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
        served_at=None, ttyd_port=3000, ttyd_pid=None,
    )
    save_state(env, tmp_path)
    with allocate_port(tmp_path, 3000, 3099) as port:
        assert port != 3000  # 3000 is taken by ttyd_port
        assert port != 3001  # 3001 is taken by port
```

**Step 6: Run new port tests, confirm they fail**

```
uv run pytest tests/test_ports.py -k "ttyd or multi or pair or after_refactor" -v
```

**Step 7: Update `ports.py`**

Replace the contents of `src/forsa_dev/ports.py`:

```python
from __future__ import annotations

import fcntl
from contextlib import contextmanager
from pathlib import Path

from forsa_dev.state import list_states


def _used_ports(state_dir: Path) -> set[int]:
    used = set()
    for env in list_states(state_dir):
        used.add(env.port)
        if env.ttyd_port is not None:
            used.add(env.ttyd_port)
    return used


@contextmanager
def allocate_ports(state_dir: Path, *ranges: tuple[int, int]):
    """Atomically allocate one port from each range under a single lock.

    Yields a list of allocated ports in the same order as the input ranges.
    The lock is held until the with-block exits so callers can write state
    before any concurrent allocation sees the new ports as free.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / ".port.lock"
    with lock_path.open("a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            used = _used_ports(state_dir)
            allocated = []
            for start, end in ranges:
                port = next(
                    (p for p in range(start, end + 1) if p not in used), None
                )
                if port is None:
                    raise RuntimeError(f"No free ports in range {start}-{end}.")
                used.add(port)
                allocated.append(port)
            yield allocated
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


@contextmanager
def allocate_port(state_dir: Path, start: int, end: int):
    """Convenience wrapper: allocate a single port from [start, end]."""
    with allocate_ports(state_dir, (start, end)) as ports:
        yield ports[0]
```

**Step 8: Run all ports tests**

```
uv run pytest tests/test_ports.py -v
```
Expected: all pass.

**Step 9: Run full test suite**

```
uv run pytest -v
```
Expected: all pass.

**Step 10: Commit**

```
git add src/forsa_dev/ttyd.py src/forsa_dev/ports.py \
        tests/test_ttyd.py tests/test_ports.py
git commit -m "feat: add ttyd.py and multi-range port allocator"
```

---

## Task 3: tmux command param + up_env + down_env in operations.py

**Files:**
- Modify: `src/forsa_dev/tmux.py`
- Modify: `tests/test_tmux.py`
- Modify: `src/forsa_dev/operations.py`
- Modify: `tests/test_operations.py`
- Modify: `src/forsa_dev/cli.py` (up + down commands refactored to thin wrappers)
- Modify: `tests/test_cli_up.py`
- Modify: `tests/test_cli_down.py`

**Context:** `tmux.create_session` needs an optional `command` arg to support `--with-claude`. `up_env` and `down_env` are extracted from `cli.py` so both CLI and dashboard share them. The `cli.py` `up` and `down` commands become thin wrappers. Add `--with-claude` flag to `forsa-dev up`.

**Step 1: Write failing tests for tmux command param**

In `tests/test_tmux.py`, add:

```python
def test_create_session_with_command():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        create_session("my-session", Path("/workdir"), command="claude --resume foo || bash")
    cmd = mock_run.call_args[0][0]
    assert "claude --resume foo || bash" in cmd


def test_create_session_without_command_has_no_trailing_arg():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        create_session("my-session", Path("/workdir"))
    cmd = mock_run.call_args[0][0]
    # No command appended
    assert cmd[-1] != "bash"
    assert "claude" not in " ".join(str(c) for c in cmd)
```

**Step 2: Run tmux tests, confirm they fail**

```
uv run pytest tests/test_tmux.py -k "command" -v
```

**Step 3: Update `tmux.py`**

```python
def create_session(session: str, cwd: Path, command: str | None = None) -> None:
    """Create a detached tmux session. Raises RuntimeError if it fails."""
    cmd = ["tmux", "new-session", "-d", "-s", session, "-c", str(cwd)]
    if command:
        cmd.append(command)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"tmux new-session failed: {result.stderr}")
```

**Step 4: Run tmux tests**

```
uv run pytest tests/test_tmux.py -v
```

**Step 5: Write failing tests for up_env + down_env**

In `tests/test_operations.py`, add:

```python
def test_up_env_creates_environment(cfg_and_env, tmp_path):
    """up_env creates a branch, worktree, compose file, tmux session, ttyd, saves state."""
    cfg, _ = cfg_and_env
    new_cfg = dataclasses.replace(
        cfg,
        state_dir=tmp_path / "fresh_state",
        ttyd_port_range_start=7600,
        ttyd_port_range_end=7699,
    )
    with patch("forsa_dev.operations.git") as mock_git, \
         patch("forsa_dev.operations.generate_compose", return_value=tmp_path / "compose.yml") as mock_compose, \
         patch("forsa_dev.operations.tmux") as mock_tmux, \
         patch("forsa_dev.operations.ttyd") as mock_ttyd:
        mock_ttyd.start_ttyd.return_value = 9999
        env = up_env(new_cfg, USER, "new-env", from_branch="main")
    assert env.name == "new-env"
    assert env.port is not None
    assert env.ttyd_port is not None
    assert env.ttyd_pid == 9999
    mock_git.create_branch_and_worktree.assert_called_once()
    mock_tmux.create_session.assert_called_once()
    mock_ttyd.start_ttyd.assert_called_once_with(env.ttyd_port, f"{USER}-new-env")
    # State persisted
    loaded = load_state(USER, "new-env", new_cfg.state_dir)
    assert loaded.ttyd_pid == 9999


def test_up_env_with_claude_passes_command_to_tmux(cfg_and_env, tmp_path):
    cfg, _ = cfg_and_env
    new_cfg = dataclasses.replace(
        cfg,
        state_dir=tmp_path / "fresh_state2",
        ttyd_port_range_start=7600,
        ttyd_port_range_end=7699,
    )
    with patch("forsa_dev.operations.git"), \
         patch("forsa_dev.operations.generate_compose", return_value=tmp_path / "c.yml"), \
         patch("forsa_dev.operations.tmux") as mock_tmux, \
         patch("forsa_dev.operations.ttyd") as mock_ttyd:
        mock_ttyd.start_ttyd.return_value = 1
        up_env(new_cfg, USER, "claude-env", with_claude=True)
    create_call_kwargs = mock_tmux.create_session.call_args
    command_arg = create_call_kwargs[1].get("command") or create_call_kwargs[0][2] if len(create_call_kwargs[0]) > 2 else create_call_kwargs[1].get("command")
    assert command_arg is not None
    assert "claude" in command_arg
    assert "bash" in command_arg


def test_up_env_raises_if_already_exists(cfg_and_env):
    cfg, env = cfg_and_env
    # ticket-42 already exists in cfg_and_env fixture
    with pytest.raises(ValueError, match="already exists"):
        up_env(cfg, USER, "ticket-42")


def test_down_env_cleans_up(cfg_and_env):
    cfg, env = cfg_and_env
    # Give it a ttyd_pid for the kill test
    from forsa_dev.state import save_state
    from dataclasses import replace as dc_replace
    env_with_ttyd = dc_replace(env, ttyd_pid=12345, ttyd_port=7602)
    save_state(env_with_ttyd, cfg.state_dir)

    with patch("subprocess.run") as mock_run, \
         patch("forsa_dev.operations.git") as mock_git, \
         patch("forsa_dev.operations.tmux") as mock_tmux, \
         patch("forsa_dev.operations.ttyd") as mock_ttyd:
        mock_run.return_value = MagicMock(returncode=0)
        down_env(cfg, USER, "ticket-42", force=True)
    mock_ttyd.stop_ttyd.assert_called_once_with(12345)
    mock_tmux.kill_session.assert_called_once()
    mock_git.remove_worktree.assert_called_once()
    mock_git.delete_branch.assert_called_once()
    # State file deleted
    with pytest.raises(FileNotFoundError):
        load_state(USER, "ticket-42", cfg.state_dir)


def test_down_env_raises_if_branch_not_pushed(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.operations.git") as mock_git:
        mock_git.branch_is_pushed.return_value = False
        with pytest.raises(RuntimeError, match="not been pushed"):
            down_env(cfg, USER, "ticket-42", force=False)
```

Note: `test_operations.py` will need `import dataclasses` and imports for `up_env`, `down_env`.

**Step 6: Run new tests, confirm they fail**

```
uv run pytest tests/test_operations.py -k "up_env or down_env" -v
```

**Step 7: Add `up_env` and `down_env` to `operations.py`**

Add at the top of `operations.py`:
```python
from forsa_dev import git, tmux, ttyd
from forsa_dev.compose import generate_compose
from forsa_dev.ports import allocate_ports
from forsa_dev.state import Environment, delete_state, load_state, save_state
```

(Keep existing imports for Config etc.)

Add the functions:

```python
def up_env(
    cfg: Config,
    user: str,
    name: str,
    from_branch: str = "main",
    with_claude: bool = False,
) -> Environment:
    full_name = f"{user}-{name}"
    worktree = cfg.worktree_dir / name

    try:
        load_state(user, name, cfg.state_dir)
        raise ValueError(f"Environment '{full_name}' already exists.")
    except FileNotFoundError:
        pass

    git.create_branch_and_worktree(cfg.repo, name, worktree, from_branch)

    ranges = (
        (cfg.port_range_start, cfg.port_range_end),
        (cfg.ttyd_port_range_start, cfg.ttyd_port_range_end),
    )
    with allocate_ports(cfg.state_dir, *ranges) as (port, ttyd_port):
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
            ttyd_port=ttyd_port,
        )
        save_state(env, cfg.state_dir)

    command = f"claude --resume {name} || bash" if with_claude else None
    try:
        tmux.create_session(full_name, worktree, command=command)
    except RuntimeError:
        delete_state(user, name, cfg.state_dir)
        git.remove_worktree(cfg.repo, worktree)
        git.delete_branch(cfg.repo, name, force=True)
        raise

    pid = ttyd.start_ttyd(ttyd_port, full_name)
    updated = replace(env, ttyd_pid=pid)
    save_state(updated, cfg.state_dir)
    return updated


def down_env(cfg: Config, user: str, name: str, force: bool = False) -> None:
    env = load_state(user, name, cfg.state_dir)

    if not force and not git.branch_is_pushed(cfg.repo, env.branch):
        raise RuntimeError(
            f"Branch '{env.branch}' has not been pushed or merged. Use force=True to delete anyway."
        )

    subprocess.run(compose_cmd(env, "down"), check=False)

    try:
        tmux.kill_session(env.tmux_session)
    except RuntimeError:
        pass

    if env.ttyd_pid is not None:
        ttyd.stop_ttyd(env.ttyd_pid)

    try:
        git.remove_worktree(cfg.repo, env.worktree)
    except RuntimeError:
        pass

    try:
        git.delete_branch(cfg.repo, env.branch, force=force)
    except RuntimeError:
        pass

    delete_state(user, name, cfg.state_dir)
```

**Step 8: Update `cli.py` `up` and `down` to thin wrappers**

Replace the `up` command body with:

```python
@app.command()
def up(
    name: str,
    from_branch: Annotated[str, typer.Option("--from", help="Branch to create from.")] = "main",
    with_claude: Annotated[bool, typer.Option("--with-claude", help="Start tmux with Claude Code.")] = False,
    config: ConfigOption = None,
):
    """Create a git worktree, compose file, and tmux session."""
    cfg = _load(config)
    user = getpass.getuser()
    full_name = _full_name(user, name)
    try:
        env = up_env(cfg, user, name, from_branch=from_branch, with_claude=with_claude)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if os.environ.get("TMUX"):
        typer.echo(f"Ready. Run 'forsa-dev attach {name}' to switch to the session.")
    else:
        typer.echo(f"Ready. Attaching to '{full_name}'...")
        tmux.attach_session(env.tmux_session)
```

Replace the `down` command body with:

```python
@app.command()
def down(
    name: str,
    force: Annotated[bool, typer.Option("--force", help="Skip branch-push check.")] = False,
    config: ConfigOption = None,
):
    """Stop server, kill tmux, kill ttyd, remove worktree. Checks branch is pushed first."""
    cfg = _load(config)
    user = getpass.getuser()
    try:
        down_env(cfg, user, name, force=force)
    except FileNotFoundError:
        typer.echo(f"Error: environment '{_full_name(user, name)}' not found.", err=True)
        raise typer.Exit(1)
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Environment '{_full_name(user, name)}' removed.")
```

Update imports in `cli.py` to include `up_env`, `down_env`:
```python
from forsa_dev.operations import compose_cmd, down_env, restart_env, serve_env, stop_env, up_env
```

Also remove the now-unused imports from `cli.py` that were only used in `up`/`down` (e.g., `git`, `generate_compose`, `allocate_port`, `Environment`, `delete_state`, `save_state` — but be careful: check what else uses them before removing).

Actually, after moving logic to operations.py, check which of these `cli.py` still needs directly:
- `git`: used in `up`? No → moved. Still in `down`? No → moved. Can be removed from cli.py if not used elsewhere.
- `tmux`: still used in `up` (attach_session), `attach` command, `list_envs`
- `compose_cmd`: `logs` command uses it
- `generate_compose`: moved → remove from cli.py imports
- `allocate_port`: moved → remove from cli.py imports
- `Environment`, `delete_state`, `save_state`: check what's left in cli.py
  - `load_state`: used in `serve` (before delegating to serve_env) and `down` (now moved) and `logs`, `attach`, `list_envs`
  - `list_states`: used in `list_envs`
  - `delete_state`, `save_state`: no longer needed if down is moved → can remove

Clean up `cli.py` imports accordingly.

**Step 9: Run all tests**

```
uv run pytest -v
```
Expected: all pass. Pay close attention to `test_cli_up.py` and `test_cli_down.py` — they mock at the cli level. Check that mocks are still patched in the right place after the refactor.

**Step 10: Commit**

```
git add src/forsa_dev/tmux.py src/forsa_dev/operations.py src/forsa_dev/cli.py \
        tests/test_tmux.py tests/test_operations.py tests/test_cli_up.py tests/test_cli_down.py
git commit -m "feat: add up_env/down_env, --with-claude flag, tmux command param"
```

---

## Task 4: FastAPI server — create + delete endpoints + updated GET response

**Files:**
- Modify: `src/forsa_dev/dashboard/server.py`
- Modify: `tests/test_dashboard_server.py`

**Context:** Add `POST /api/environments` (calls `up_env`) and `DELETE /api/environments/{name}` (calls `down_env`). Update `GET /api/environments` response to include `ttyd_port` and `status.ttyd`. `ttyd_is_alive` is used to determine ttyd status.

**Step 1: Write failing tests**

In `tests/test_dashboard_server.py`, add:

```python
def test_get_environments_includes_ttyd_port(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.dashboard.server.tmux") as mock_tmux, \
         patch("forsa_dev.dashboard.server.port_is_open", return_value=False), \
         patch("forsa_dev.dashboard.server.ttyd") as mock_ttyd:
        mock_tmux.session_status.return_value = "active"
        mock_ttyd.ttyd_is_alive.return_value = False
        app = create_app(cfg)
        client = TestClient(app)
        response = client.get("/api/environments")
    data = response.json()
    assert "ttyd_port" in data[0]
    assert "ttyd" in data[0]["status"]


def test_post_create_environment_calls_up_env(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.dashboard.server.up_env") as mock_up:
        mock_up.return_value = MagicMock(
            name="new-env", user=USER, branch="new-env", port=3003,
            ttyd_port=7603, url=None, created_at=datetime(2026,3,8,tzinfo=timezone.utc),
            served_at=None, ttyd_pid=None,
        )
        app = create_app(cfg)
        client = TestClient(app)
        response = client.post("/api/environments", json={"name": "new-env", "from_branch": "main"})
    assert response.status_code == 200
    mock_up.assert_called_once_with(cfg, USER, "new-env", from_branch="main", with_claude=True)


def test_post_create_environment_409_if_exists(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.dashboard.server.up_env", side_effect=ValueError("already exists")):
        app = create_app(cfg)
        client = TestClient(app)
        response = client.post("/api/environments", json={"name": "ticket-42", "from_branch": "main"})
    assert response.status_code == 409


def test_post_create_environment_500_on_runtime_error(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.dashboard.server.up_env", side_effect=RuntimeError("git failed")):
        app = create_app(cfg)
        client = TestClient(app)
        response = client.post("/api/environments", json={"name": "new", "from_branch": "main"})
    assert response.status_code == 500


def test_delete_environment_calls_down_env(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.dashboard.server.down_env") as mock_down:
        app = create_app(cfg)
        client = TestClient(app)
        response = client.delete("/api/environments/ticket-42")
    assert response.status_code == 200
    mock_down.assert_called_once_with(cfg, USER, "ticket-42", force=False)


def test_delete_environment_force_param(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.dashboard.server.down_env") as mock_down:
        app = create_app(cfg)
        client = TestClient(app)
        response = client.delete("/api/environments/ticket-42?force=true")
    assert response.status_code == 200
    mock_down.assert_called_once_with(cfg, USER, "ticket-42", force=True)


def test_delete_environment_404_when_not_found(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.dashboard.server.down_env", side_effect=FileNotFoundError()):
        app = create_app(cfg)
        client = TestClient(app)
        response = client.delete("/api/environments/nonexistent")
    assert response.status_code == 404


def test_delete_environment_409_on_unpushed_branch(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.dashboard.server.down_env", side_effect=RuntimeError("not been pushed")):
        app = create_app(cfg)
        client = TestClient(app)
        response = client.delete("/api/environments/ticket-42")
    assert response.status_code == 409
```

Note: the existing `cfg_and_env` fixture creates `Environment` without `ttyd_port/ttyd_pid` — they default to None, which is fine.

**Step 2: Run new tests, confirm they fail**

```
uv run pytest tests/test_dashboard_server.py -k "ttyd or create or delete" -v
```

**Step 3: Update `server.py`**

Add imports:
```python
from forsa_dev import ttyd
from forsa_dev.operations import down_env, restart_env, serve_env, stop_env, up_env
from pydantic import BaseModel
```

Update `GET /api/environments` to include `ttyd_port` and `status.ttyd`:
```python
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
        ttyd_alive = ttyd.ttyd_is_alive(env.ttyd_pid) if env.ttyd_pid is not None else False
        result.append({
            "name": env.name,
            "user": env.user,
            "branch": env.branch,
            "port": env.port,
            "ttyd_port": env.ttyd_port,
            "url": env.url or f"http://{cfg.base_url}:{env.port}",
            "created_at": env.created_at.isoformat(),
            "served_at": env.served_at.isoformat() if env.served_at else None,
            "status": {
                "tmux": status.tmux,
                "server": status.server,
                "ttyd": "alive" if ttyd_alive else "dead",
            },
            "uptime": format_uptime(env.served_at),
        })
    return result
```

Add request body model and new endpoints:
```python
class CreateEnvRequest(BaseModel):
    name: str
    from_branch: str = "main"


@app.post("/api/environments")
def post_create_environment(body: CreateEnvRequest) -> dict[str, Any]:
    user = getpass.getuser()
    try:
        env = up_env(cfg, user, body.name, from_branch=body.from_branch, with_claude=True)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"name": env.name, "port": env.port, "ttyd_port": env.ttyd_port}


@app.delete("/api/environments/{name}")
def delete_environment(name: str, force: bool = False) -> dict[str, str]:
    user = getpass.getuser()
    try:
        down_env(cfg, user, name, force=force)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Environment '{name}' not found")
    except RuntimeError as e:
        # Branch not pushed → 409 Conflict
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "ok"}
```

**Step 4: Run all tests**

```
uv run pytest -v
```
Expected: all pass.

**Step 5: Commit**

```
git add src/forsa_dev/dashboard/server.py tests/test_dashboard_server.py
git commit -m "feat: add create/delete endpoints and ttyd status to GET /api/environments"
```

---

## Task 5: React — create form, delete button, terminal split view

**Files:**
- Create: `dashboard/src/hooks/useInterval.js`
- Create: `dashboard/src/components/CreateEnvironment.jsx`
- Create: `dashboard/src/components/TerminalView.jsx`
- Modify: `dashboard/src/components/EnvironmentRow.jsx`
- Modify: `dashboard/src/components/EnvironmentTable.jsx`
- Modify: `dashboard/src/App.jsx`
- Run: `scripts/build_dashboard.sh`

**Context:** The dashboard gains three new capabilities:
1. **Create form**: Name input + Create button at the top. Calls POST /api/environments.
2. **Delete**: Trash icon button on each row. Confirms before deleting. If backend returns 409, shows "Force delete" option.
3. **Terminal view**: Click a row → split view with env list on left, ttyd iframe on right. Click same row or Close → back to full-width table. Mobile: full-screen iframe with back button.

No tests for React (manual testing per original design doc).

**Step 1: Create `useInterval.js`**

```
dashboard/src/hooks/useInterval.js
```

```js
import { useEffect, useRef } from 'react'

export default function useInterval(callback, delay) {
  const savedCallback = useRef(callback)
  useEffect(() => { savedCallback.current = callback }, [callback])
  useEffect(() => {
    if (delay === null) return
    const id = setInterval(() => savedCallback.current(), delay)
    return () => clearInterval(id)
  }, [delay])
}
```

**Step 2: Create `CreateEnvironment.jsx`**

```jsx
import { useState } from 'react'

export default function CreateEnvironment({ onCreate }) {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    try {
      await onCreate(name.trim())
      setName('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 flex gap-2">
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Environment name (e.g. ticket-42)"
        className="flex-1 rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
      />
      <button
        type="submit"
        disabled={loading || !name.trim()}
        className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Creating…' : 'Create'}
      </button>
    </form>
  )
}
```

**Step 3: Create `TerminalView.jsx`**

```jsx
export default function TerminalView({ env, host, onClose }) {
  const src = `http://${host}:${env.ttyd_port}`
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-2">
        <span className="font-mono text-sm text-gray-300">{env.name}</span>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-100"
          aria-label="Close terminal"
        >
          ✕
        </button>
      </div>
      <iframe
        src={src}
        className="flex-1 w-full border-0"
        title={`Terminal: ${env.name}`}
      />
    </div>
  )
}
```

**Step 4: Update `EnvironmentRow.jsx` — add click handler + delete button**

The row needs to be clickable (to open terminal) and have a delete button. Receive new props: `onSelect`, `isSelected`, `onDelete`, `loadingDelete`.

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

const TTYD_COLORS = {
  alive: 'text-green-400',
  dead: 'text-gray-400',
}

export default function EnvironmentRow({ env, onAction, loadingAction, onSelect, isSelected, onDelete, loadingDelete }) {
  return (
    <tr
      className={`border-t border-gray-800 cursor-pointer hover:bg-gray-900 ${isSelected ? 'bg-gray-900' : ''}`}
      onClick={() => onSelect(env)}
    >
      <td className="px-4 py-3 font-mono text-sm">{env.name}</td>
      <td className="px-4 py-3 text-sm text-gray-400">{env.user}</td>
      <td className="px-4 py-3 font-mono text-sm text-gray-400">{env.branch}</td>
      <td className={`px-4 py-3 text-sm ${SERVER_COLORS[env.status.server] ?? 'text-gray-400'}`}>
        {env.status.server}
      </td>
      <td className={`px-4 py-3 text-sm ${TMUX_COLORS[env.status.tmux] ?? 'text-gray-400'}`}>
        {env.status.tmux}
      </td>
      <td className={`px-4 py-3 text-sm ${TTYD_COLORS[env.status.ttyd] ?? 'text-gray-400'}`}>
        {env.status.ttyd ?? '-'}
      </td>
      <td className="px-4 py-3 text-sm">
        <a
          href={env.url}
          target="_blank"
          rel="noreferrer"
          className="text-blue-400 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          :{env.port}
        </a>
      </td>
      <td className="px-4 py-3 text-sm text-gray-400">{env.uptime}</td>
      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2">
          <ActionButtons env={env} onAction={onAction} loading={loadingAction} />
          <button
            onClick={() => onDelete(env.name)}
            disabled={loadingDelete}
            className="text-gray-500 hover:text-red-400 disabled:opacity-50"
            title="Delete environment"
          >
            {loadingDelete ? '…' : '🗑'}
          </button>
        </div>
      </td>
    </tr>
  )
}
```

**Step 5: Update `EnvironmentTable.jsx` — pass new props, add Ttyd column header**

```jsx
import EnvironmentRow from './EnvironmentRow'

export default function EnvironmentTable({ envs, onAction, loadingActions, onSelect, selectedEnv, onDelete, loadingDeletes }) {
  if (envs.length === 0) {
    return (
      <p className="text-center text-gray-500 py-8">
        No environments found. Use the form above to create one.
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
            <th className="px-4 py-3">Ttyd</th>
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
              onSelect={onSelect}
              isSelected={selectedEnv?.name === env.name}
              onDelete={onDelete}
              loadingDelete={!!loadingDeletes[env.name]}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

**Step 6: Update `App.jsx`**

Replace `App.jsx` with the full updated version that:
- Imports `CreateEnvironment`, `TerminalView`, `useInterval`
- Adds `selectedEnv` state (null = table-only, non-null = split view)
- Adds `loadingDeletes` state
- Adds `handleCreate(name)` that calls `POST /api/environments`
- Adds `handleDelete(name)` that calls `DELETE /api/environments/{name}`, with 409 → force confirm
- Adds `handleSelect(env)` / `handleCloseTerminal()` for split view
- Uses `useInterval` for polling instead of inline `setInterval`
- Renders split view: `lg:flex` with table (left, narrower when terminal open) + TerminalView (right, wider)

```jsx
import { useCallback, useState } from 'react'
import CreateEnvironment from './components/CreateEnvironment'
import EnvironmentTable from './components/EnvironmentTable'
import ErrorBanner from './components/ErrorBanner'
import HealthBar from './components/HealthBar'
import TerminalView from './components/TerminalView'
import useInterval from './hooks/useInterval'

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
  const [loadingDeletes, setLoadingDeletes] = useState({})
  const [selectedEnv, setSelectedEnv] = useState(null)

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

  // Initial fetch
  useState(() => { fetchEnvs(); fetchHealth() })

  useInterval(fetchEnvs, ENV_POLL_MS)
  useInterval(fetchHealth, HEALTH_POLL_MS)

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

  const handleCreate = useCallback(async (name) => {
    try {
      await apiFetch('/api/environments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, from_branch: 'main' }),
      })
      await fetchEnvs()
    } catch (e) {
      setError(e.message)
    }
  }, [fetchEnvs])

  const handleDelete = useCallback(async (name, force = false) => {
    setLoadingDeletes((prev) => ({ ...prev, [name]: true }))
    try {
      const url = force ? `/api/environments/${name}?force=true` : `/api/environments/${name}`
      await apiFetch(url, { method: 'DELETE' })
      if (selectedEnv?.name === name) setSelectedEnv(null)
      await fetchEnvs()
    } catch (e) {
      if (e.message.includes('409')) {
        if (window.confirm(`Branch '${name}' has not been pushed. Force delete?`)) {
          await handleDelete(name, true)
        }
      } else {
        setError(e.message)
      }
    } finally {
      setLoadingDeletes((prev) => ({ ...prev, [name]: false }))
    }
  }, [fetchEnvs, selectedEnv])

  const handleSelect = useCallback((env) => {
    setSelectedEnv((prev) => prev?.name === env.name ? null : env)
  }, [])

  const handleCloseTerminal = useCallback(() => setSelectedEnv(null), [])

  // Derive host from current page (works for both localhost and Tailscale)
  const host = window.location.hostname

  return (
    <div className="mx-auto max-w-7xl p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-100">forsa-dev</h1>
      <ErrorBanner message={error} />
      <HealthBar health={health} />
      <CreateEnvironment onCreate={handleCreate} />
      <div className={`flex gap-4 ${selectedEnv ? 'lg:flex-row' : ''}`}>
        <div className={selectedEnv ? 'lg:w-1/3' : 'w-full'}>
          <EnvironmentTable
            envs={envs}
            onAction={handleAction}
            loadingActions={loadingActions}
            onSelect={handleSelect}
            selectedEnv={selectedEnv}
            onDelete={handleDelete}
            loadingDeletes={loadingDeletes}
          />
        </div>
        {selectedEnv && (
          <div className="flex-1 lg:h-[600px] rounded-lg border border-gray-800 overflow-hidden">
            <TerminalView env={selectedEnv} host={host} onClose={handleCloseTerminal} />
          </div>
        )}
      </div>
      {/* Mobile: full-screen terminal overlay */}
      {selectedEnv && (
        <div className="fixed inset-0 z-50 flex flex-col bg-gray-950 lg:hidden">
          <TerminalView env={selectedEnv} host={host} onClose={handleCloseTerminal} />
        </div>
      )}
    </div>
  )
}
```

**Step 7: Rebuild frontend**

```
bash /Users/andersnordmark/work/personal/forsa-dev/scripts/build_dashboard.sh
```
Expected: build succeeds, files appear in `src/forsa_dev/dashboard/static/`.

**Step 8: Run all Python tests (frontend has no automated tests)**

```
uv run pytest -v
```
Expected: all pass.

**Step 9: Commit**

```
git add dashboard/src/ src/forsa_dev/dashboard/static/
git commit -m "feat: add create/delete UI, embedded ttyd terminal split view"
```

---

## Key constraints to enforce in every task

- All 72 existing tests must pass at the end of every task (no regressions)
- Never add backwards-compatibility shims — instead update all callers
- Mock subprocess/git/tmux/ttyd in tests — never call real processes
- `allocate_port` existing API unchanged (still a contextmanager yielding a single int)
- `ttyd.py` must be import-safe even if ttyd binary is not installed
- `server.py` stays a thin wrapper — no business logic, just HTTP↔operations translation
