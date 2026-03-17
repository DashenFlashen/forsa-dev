# Dashboard Improvements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the forsa-dev dashboard UX with a fullscreen terminal overlay, unified create form, larger buttons, VSCode integration, a lightweight CLI run command, and `--effort max` for Claude sessions.

**Architecture:** Seven independent changes, ordered by dependency and risk. Frontend changes are pure React/Tailwind (no test framework — verify visually with `forsa-tester`). Backend changes have pytest coverage. The CLI `run` command requires extracting port allocation into a reusable function.

**Tech Stack:** React 18 + Tailwind CSS + lucide-react (frontend), Python + FastAPI + typer (backend), pytest (tests)

**Spec:** `docs/superpowers/specs/2026-03-17-dashboard-improvements-design.md`

---

### Task 1: Button sizing

Increase desktop button sizes for better click targets. Mobile stays unchanged.

**Files:**
- Modify: `dashboard/src/components/ActionButtons.jsx`
- Modify: `dashboard/src/components/EnvironmentRow.jsx`

- [ ] **Step 1: Update ActionButtons.jsx**

In `ActionBtn` (line 12), change the className:
- `lg:p-1.5` → `lg:p-2`
- `lg:h-3.5 lg:w-3.5` → `lg:h-4 lg:w-4` (both the loading spinner and the icon, lines 14-16)

In the outer `div` (line 27), change `gap-1` → `gap-1.5`.

- [ ] **Step 2: Update EnvironmentRow.jsx**

Terminal button (line 63): change `p-1.5` → `p-2`
Terminal icon (line 69): change `h-3.5 w-3.5` → `h-4 w-4`
Delete button (line 76): change `p-1.5` → `p-2`
Delete icon (line 78): change `h-3.5 w-3.5` → `h-4 w-4`
Actions container (line 56): change `gap-1` → `gap-1.5`

- [ ] **Step 3: Verify visually**

Run: `forsa-tester` or manually check the dashboard. Confirm desktop buttons are larger and mobile buttons are unchanged.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/ActionButtons.jsx dashboard/src/components/EnvironmentRow.jsx
git commit -m "ui: increase desktop button sizes for better click targets"
```

---

### Task 2: Add `--effort max` to Claude sessions

One-line change in `operations.py`.

**Files:**
- Modify: `src/forsa_dev/operations.py:121`
- Modify: `tests/test_operations.py`

- [ ] **Step 1: Update the existing test to expect --effort max**

In `tests/test_operations.py`, find `test_up_env_with_claude_passes_command_to_tmux` (line 137). Add an assertion that the command includes `--effort`:

```python
def test_up_env_with_claude_passes_command_to_tmux(up_cfg):
    cfg = up_cfg
    with patch("forsa_dev.operations.tmux.create_session") as mock_create, \
         patch("forsa_dev.operations.ttyd.start_ttyd", return_value=99):
        up_env(cfg, USER, "new-feature", with_claude=True)
    assert mock_create.call_args.kwargs["command"] is not None
    assert "claude" in mock_create.call_args.kwargs["command"]
    assert "--effort max" in mock_create.call_args.kwargs["command"]
    assert os.environ.get("SHELL", "sh") in mock_create.call_args.kwargs["command"]
```

- [ ] **Step 2: Run test — should fail**

Run: `uv run pytest tests/test_operations.py::test_up_env_with_claude_passes_command_to_tmux -v`
Expected: FAIL — `--effort max` not in current command string.

- [ ] **Step 3: Update operations.py**

In `src/forsa_dev/operations.py` line 121, change:
```python
f"{shell} -i -c 'claude --dangerously-skip-permissions || exec {shell}'"
```
to:
```python
f"{shell} -i -c 'claude --dangerously-skip-permissions --effort max || exec {shell}'"
```

- [ ] **Step 4: Run test — should pass**

Run: `uv run pytest tests/test_operations.py::test_up_env_with_claude_passes_command_to_tmux -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/forsa_dev/operations.py tests/test_operations.py
git commit -m "feat: add --effort max to Claude sessions"
```

---

### Task 3: User header styling

Add `UserInitials` avatar to the header for better user visibility.

**Files:**
- Modify: `dashboard/src/App.jsx:159-178` (header section)

- [ ] **Step 1: Add UserInitials import**

In `App.jsx`, add to the imports (after line 8):
```jsx
import UserInitials from './components/UserInitials'
```

- [ ] **Step 2: Update header user display**

Replace the header user section (lines 167-176) with:

```jsx
<div className="ml-auto flex items-center gap-3 text-sm text-gray-400">
  <UserInitials user={user} className="h-8 w-8 text-sm" />
  <span className="font-medium text-gray-200 capitalize">{user}</span>
  <button
    onClick={handleSwitchUser}
    className="text-blue-400 hover:text-blue-300 hover:underline"
  >
    switch
  </button>
</div>
```

- [ ] **Step 3: Verify visually**

Check dashboard header shows the avatar circle next to the username.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/App.jsx
git commit -m "ui: add user avatar to header for better visibility"
```

---

### Task 4: Unified create environment form

Merge `CreateEnvironment` and `ImportBranch` into a single tabbed component.

**Files:**
- Rewrite: `dashboard/src/components/CreateEnvironment.jsx`
- Delete: `dashboard/src/components/ImportBranch.jsx`
- Modify: `dashboard/src/App.jsx`

- [ ] **Step 1: Rewrite CreateEnvironment.jsx**

Replace the entire file with a tabbed component. The component manages two tabs internally: "New" (creates from main) and "From branch" (imports existing branch). Branch list is fetched internally on mount.

```jsx
import { useEffect, useState } from 'react'
import { Plus, Download, RefreshCw } from 'lucide-react'
import CollapsibleSection from './CollapsibleSection'

const NAME_RE = /^[a-z0-9][a-z0-9_-]*$/

function deriveName(branch) {
  return branch.split('/').pop().toLowerCase().replace(/[^a-z0-9_-]/g, '-').replace(/^-+/, '')
}

export default function CreateEnvironment({ onCreate, defaultDataDir }) {
  const [tab, setTab] = useState('new')
  const [name, setName] = useState('')
  const [dataDir, setDataDir] = useState('')
  const [loading, setLoading] = useState(false)
  const [showOptions, setShowOptions] = useState(false)

  // "From branch" state
  const [branches, setBranches] = useState([])
  const [branch, setBranch] = useState('')
  const [branchName, setBranchName] = useState('')
  const [loadingBranches, setLoadingBranches] = useState(true)

  useEffect(() => {
    fetch('/api/branches')
      .then((r) => r.json())
      .then((d) => { setBranches(d.branches); setLoadingBranches(false) })
      .catch(() => setLoadingBranches(false))
  }, [])

  useEffect(() => {
    if (defaultDataDir && !dataDir) setDataDir(defaultDataDir)
  }, [defaultDataDir])

  function handleBranchChange(e) {
    const b = e.target.value
    setBranch(b)
    setBranchName(b ? deriveName(b) : '')
  }

  async function handleNewSubmit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    try {
      await onCreate(name.trim(), 'main', dataDir.trim() || null)
      setName('')
    } finally {
      setLoading(false)
    }
  }

  async function handleBranchSubmit(e) {
    e.preventDefault()
    if (!branch || !branchName.trim()) return
    setLoading(true)
    try {
      await onCreate(branchName.trim(), 'main', dataDir.trim() || null, branch)
      setBranch('')
      setBranchName('')
    } finally {
      setLoading(false)
    }
  }

  const branchNameValid = NAME_RE.test(branchName)

  return (
    <CollapsibleSection title="Create Environment">
      {/* Tabs */}
      <div className="mb-3 flex gap-1">
        {['new', 'branch'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
              tab === t
                ? 'bg-gray-700 text-gray-100'
                : 'text-gray-500 hover:bg-gray-800 hover:text-gray-300'
            }`}
          >
            {t === 'new' ? 'New' : 'From branch'}
          </button>
        ))}
      </div>

      {/* New tab */}
      {tab === 'new' && (
        <form onSubmit={handleNewSubmit} className="flex flex-col gap-2">
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Name (e.g. ticket-42)"
              className="flex-1 min-w-48 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
            />
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {loading ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="h-3.5 w-3.5" />
              )}
              {loading ? 'Creating…' : 'Create'}
            </button>
          </div>
          {showOptions ? (
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500 whitespace-nowrap w-16">Data dir</label>
              <input
                type="text"
                value={dataDir}
                onChange={(e) => setDataDir(e.target.value)}
                placeholder="/data/dev"
                className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm font-mono text-gray-300 placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowOptions(true)}
              className="self-start text-xs text-gray-500 hover:text-gray-400"
            >
              Options…
            </button>
          )}
        </form>
      )}

      {/* From branch tab */}
      {tab === 'branch' && (
        <form onSubmit={handleBranchSubmit} className="flex flex-col gap-2">
          <div className="flex flex-wrap gap-2">
            <select
              value={branch}
              onChange={handleBranchChange}
              disabled={loadingBranches}
              className="flex-1 min-w-48 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 disabled:opacity-50"
            >
              <option value="">{loadingBranches ? 'Loading…' : 'Select branch…'}</option>
              {branches.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
            <input
              type="text"
              value={branchName}
              onChange={(e) => setBranchName(e.target.value)}
              placeholder="Environment name"
              className={`flex-1 min-w-32 rounded-md border px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 ${
                branchName && !branchNameValid
                  ? 'border-red-500 bg-gray-800 focus:ring-red-500/50'
                  : 'border-gray-700 bg-gray-800 focus:border-blue-500 focus:ring-blue-500/50'
              }`}
            />
            <button
              type="submit"
              disabled={loading || !branch || !branchNameValid}
              className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {loading
                ? <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                : <Download className="h-3.5 w-3.5" />}
              {loading ? 'Importing…' : 'Import'}
            </button>
          </div>
          {showOptions ? (
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500 whitespace-nowrap w-16">Data dir</label>
              <input
                type="text"
                value={dataDir}
                onChange={(e) => setDataDir(e.target.value)}
                placeholder="/data/dev"
                className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm font-mono text-gray-300 placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowOptions(true)}
              className="self-start text-xs text-gray-500 hover:text-gray-400"
            >
              Options…
            </button>
          )}
        </form>
      )}
    </CollapsibleSection>
  )
}
```

- [ ] **Step 2: Update App.jsx — remove ImportBranch**

Remove the `ImportBranch` import (line 3) and its usage (line 184: `<ImportBranch onCreate={handleCreate} defaultDataDir={defaultDataDir} />`).

- [ ] **Step 3: Delete ImportBranch.jsx**

```bash
rm dashboard/src/components/ImportBranch.jsx
```

- [ ] **Step 4: Build and verify**

Run: `cd dashboard && npm run build` — should succeed with no errors.
Verify visually: the "Create Environment" section should have two tabs (New / From branch).

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/CreateEnvironment.jsx dashboard/src/App.jsx
git rm dashboard/src/components/ImportBranch.jsx
git commit -m "ui: unify create environment and import branch into tabbed form"
```

---

### Task 5: Terminal fullscreen overlay

Replace the desktop side-panel terminal with a fullscreen overlay. Pass action buttons through to the terminal header.

**Files:**
- Modify: `dashboard/src/App.jsx`
- Modify: `dashboard/src/components/TerminalView.jsx`

- [ ] **Step 1: Update TerminalView to accept action props**

Add `onAction`, `loadingAction` to the props and add action buttons + status info to the header bar.

In `TerminalView.jsx`, update the component:

```jsx
import { useState } from 'react'
import { X, Terminal, ExternalLink } from 'lucide-react'
import ActionButtons from './ActionButtons'
import StatusBadge from './StatusBadge'
import LogsView from './LogsView'

export default function TerminalView({ env, host, onClose, onAction, loadingAction }) {
  const [tab, setTab] = useState('terminal')
  const src = env.ttyd_port ? `http://${host}:${env.ttyd_port}` : null

  return (
    <div className="flex h-full w-full flex-col bg-gray-950">
      <div className="flex items-center gap-2 border-b border-gray-800 bg-gray-900 px-3 py-2 lg:gap-3 lg:px-4 lg:py-2.5 shrink-0">
        <Terminal className="hidden h-4 w-4 shrink-0 text-gray-500 lg:block" />
        <span className="font-mono text-sm font-medium text-gray-100 truncate">{env.name}</span>
        <StatusBadge status={env.status.server} />
        <div className="flex gap-1">
          {['terminal', 'logs'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded px-2.5 py-1 text-xs font-medium capitalize transition-colors ${
                tab === t
                  ? 'bg-gray-700 text-gray-100'
                  : 'text-gray-500 hover:bg-gray-800 hover:text-gray-300'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="hidden lg:flex items-center gap-1">
          <ActionButtons env={env} onAction={onAction} loading={loadingAction} />
        </div>
        <div className="flex-1" />
        <a
          href={env.url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-blue-400 hover:bg-gray-800 hover:text-blue-300 transition-colors"
          onClick={(e) => e.stopPropagation()}
        >
          :{env.port}
          <ExternalLink className="h-3 w-3" />
        </a>
        <button
          onClick={onClose}
          className="rounded p-2 text-gray-500 hover:bg-gray-800 hover:text-gray-200 transition-colors"
          aria-label="Close terminal"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {tab === 'logs' ? (
        <LogsView envName={env.name} envUser={env.user} />
      ) : src ? (
        <iframe
          src={src}
          className="flex-1 w-full border-0"
          title={`Terminal: ${env.name}`}
          sandbox="allow-scripts allow-same-origin"
        />
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-gray-500">
          <Terminal className="h-8 w-8 text-gray-700" />
          <p className="text-sm">Terminal not available</p>
        </div>
      )}
    </div>
  )
}
```

Key changes: added `onAction`/`loadingAction` props, added `ActionButtons` to header, made close button slightly larger (`h-5 w-5`), always show status badge (removed `hidden lg:inline`), always show env name.

- [ ] **Step 2: Update App.jsx — fullscreen overlay for all screen sizes**

Replace the layout section (lines 185-208) with a unified fullscreen overlay:

```jsx
<EnvironmentTable
  envs={envs}
  onAction={handleAction}
  loadingActions={loadingActions}
  onSelect={handleSelect}
  selectedEnv={selectedEnv}
  onDelete={handleDelete}
  loadingDeletes={loadingDeletes}
/>
{/* Fullscreen terminal overlay — same for mobile and desktop */}
{selectedEnv && (
  <div className="fixed inset-0 z-50 flex flex-col bg-gray-950">
    <TerminalView
      env={selectedEnv}
      host={host}
      onClose={handleCloseTerminal}
      onAction={handleAction}
      loadingAction={loadingActions[`${selectedEnv.user}/${selectedEnv.name}`]}
    />
  </div>
)}
```

This removes the old desktop split layout (`flex gap-4`, `lg:flex-row`, `lg:w-1/3`, `h-[600px]`) and the separate mobile overlay block.

- [ ] **Step 3: Build and verify**

Run: `cd dashboard && npm run build`
Verify: clicking a terminal button should open a fullscreen overlay on both mobile and desktop. Close button returns to the dashboard. Action buttons visible in the terminal header.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/App.jsx dashboard/src/components/TerminalView.jsx
git commit -m "ui: replace terminal side panel with fullscreen overlay"
```

---

### Task 6: VSCode "Open in editor" link

Expose worktree path from the API and add a VSCode link to the UI.

**Files:**
- Modify: `src/forsa_dev/dashboard/server.py:92-107`
- Modify: `tests/test_dashboard_server.py`
- Modify: `dashboard/src/components/EnvironmentRow.jsx`
- Modify: `dashboard/src/components/EnvironmentCard.jsx`
- Modify: `dashboard/src/components/TerminalView.jsx`

- [ ] **Step 1: Write test for worktree in API response**

In `tests/test_dashboard_server.py`, add after `test_get_environments_includes_ttyd_port` (line 176):

```python
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
```

- [ ] **Step 2: Run test — should fail**

Run: `uv run pytest tests/test_dashboard_server.py::test_get_environments_includes_worktree -v`
Expected: FAIL — `worktree` key not in response.

- [ ] **Step 3: Add worktree to API response**

In `src/forsa_dev/dashboard/server.py`, in the `get_environments` function, add `"worktree"` to the result dict (after line 97, next to `"branch"`):

```python
"worktree": str(env.worktree),
```

- [ ] **Step 4: Run test — should pass**

Run: `uv run pytest tests/test_dashboard_server.py::test_get_environments_includes_worktree -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest`
Expected: All tests pass.

- [ ] **Step 6: Commit backend change**

```bash
git add src/forsa_dev/dashboard/server.py tests/test_dashboard_server.py
git commit -m "api: expose worktree path in environment response"
```

- [ ] **Step 7: Add VSCode link to EnvironmentRow.jsx**

Add `Code2` to the lucide-react import. Add a VSCode link button after the terminal button (before delete):

```jsx
<a
  href={`vscode://vscode-remote/ssh-remote+${window.location.hostname}${env.worktree}`}
  title="Open in VSCode"
  aria-label={`Open ${env.name} in VSCode`}
  className="rounded-md p-2 text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-200"
  onClick={(e) => e.stopPropagation()}
>
  <Code2 className="h-4 w-4" />
</a>
```

- [ ] **Step 8: Add VSCode link to EnvironmentCard.jsx**

Same pattern as Row — add `Code2` import and a link button in the actions row (between terminal and delete).

- [ ] **Step 9: Add VSCode link to TerminalView.jsx**

In the terminal header (next to the port link), add:

```jsx
<a
  href={`vscode://vscode-remote/ssh-remote+${host}${env.worktree}`}
  title="Open in VSCode"
  className="flex items-center gap-1 rounded px-2 py-1 text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-200 transition-colors"
  onClick={(e) => e.stopPropagation()}
>
  <Code2 className="h-3.5 w-3.5" />
  <span className="hidden lg:inline">VSCode</span>
</a>
```

- [ ] **Step 10: Build and verify**

Run: `cd dashboard && npm run build`
Verify: VSCode icon visible in environment rows and terminal header. Clicking opens VSCode (or prompts to allow the `vscode://` protocol).

- [ ] **Step 11: Commit frontend changes**

```bash
git add dashboard/src/components/EnvironmentRow.jsx dashboard/src/components/EnvironmentCard.jsx dashboard/src/components/TerminalView.jsx
git commit -m "ui: add VSCode 'open in editor' link to environments"
```

---

### Task 7: CLI `run` command

Add `forsa-dev run` for running a FORSA server from any directory without worktree management.

**Files:**
- Modify: `src/forsa_dev/operations.py`
- Modify: `src/forsa_dev/cli.py`
- Create: `tests/test_cli_run.py`

- [ ] **Step 1: Write test for the run operation**

Create `tests/test_cli_run.py`:

```python
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forsa_dev.config import Config
from forsa_dev.operations import run_local


@pytest.fixture()
def run_cfg(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    return Config(
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


def test_run_local_generates_compose_and_runs(run_cfg, tmp_path):
    work_dir = tmp_path / "my-repo"
    work_dir.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        run_local(run_cfg, work_dir)
    compose_file = work_dir / "docker-compose.dev.yml"
    assert compose_file.exists()
    # Called twice: docker compose up, then docker compose down
    assert mock_run.call_count == 2
    up_cmd = mock_run.call_args_list[0][0][0]
    assert "docker" in up_cmd[0]
    assert "up" in up_cmd
    down_cmd = mock_run.call_args_list[1][0][0]
    assert "down" in down_cmd


def test_run_local_allocates_port_in_range(run_cfg, tmp_path):
    work_dir = tmp_path / "my-repo"
    work_dir.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        run_local(run_cfg, work_dir)
    compose_content = (work_dir / "docker-compose.dev.yml").read_text()
    assert "3000" in compose_content
```

- [ ] **Step 2: Run tests — should fail**

Run: `uv run pytest tests/test_cli_run.py -v`
Expected: FAIL — `run_local` not defined.

- [ ] **Step 3: Implement `run_local` in operations.py**

Add to `src/forsa_dev/operations.py`:

```python
def run_local(cfg: Config, work_dir: Path, data_dir: Path | None = None) -> None:
    """Run a FORSA server from an arbitrary directory. Foreground, no state file."""
    # Allocate port under lock, write a temporary state file so concurrent
    # allocations see this port as taken, then release the lock before
    # running compose (which blocks indefinitely).
    with allocate_ports(cfg.state_dir, (cfg.port_range_start, cfg.port_range_end)) as (port,):
        compose_file = generate_compose(
            worktree=work_dir,
            user="local",
            name="run",
            port=port,
            data_dir=data_dir or cfg.data_dir,
            docker_image=cfg.docker_image,
            gurobi_lic=cfg.gurobi_lic,
        )
        # Write temporary state so the port stays reserved after lock release
        env = Environment(
            name="run",
            user="local",
            branch="",
            worktree=work_dir,
            tmux_session="",
            compose_file=compose_file,
            port=port,
            url=f"http://{cfg.base_url}:{port}",
            created_at=datetime.now(tz=timezone.utc),
            served_at=datetime.now(tz=timezone.utc),
        )
        save_state(env, cfg.state_dir)
    # Lock is released — other allocations can proceed
    try:
        print(f"Serving at http://{cfg.base_url}:{port}")
        print("Press Ctrl+C to stop.")
        subprocess.run(
            ["docker", "compose", "-p", "forsa-run", "-f", str(compose_file), "up"],
            check=False,
        )
    finally:
        subprocess.run(
            ["docker", "compose", "-p", "forsa-run", "-f", str(compose_file), "down"],
            check=False,
        )
        delete_state("local", "run", cfg.state_dir)
```

The temporary state file (`local-run.json`) reserves the port so concurrent `allocate_ports` calls see it as taken. The `finally` block ensures cleanup (compose down + state deletion) even on Ctrl+C.

- [ ] **Step 4: Run tests — should pass**

Run: `uv run pytest tests/test_cli_run.py -v`
Expected: PASS

- [ ] **Step 5: Add CLI `run` command**

In `src/forsa_dev/cli.py`, add after the `logs` command:

```python
@app.command()
def run(
    directory: Annotated[
        Path, typer.Argument(help="Directory to serve from.", show_default=False)
    ] = Path("."),
    data_dir: Annotated[
        Path | None, typer.Option("--data-dir", help="Override data directory.")
    ] = None,
    config: ConfigOption = None,
):
    """Run a FORSA server from any directory (no worktree needed)."""
    cfg = _load(config)
    work_dir = directory.resolve()
    if not work_dir.is_dir():
        typer.echo(f"Error: {work_dir} is not a directory.", err=True)
        raise typer.Exit(1)
    try:
        run_local(cfg, work_dir, data_dir=data_dir)
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
```

Add the import at the top of the file (with the other operations imports on line 15):
```python
from forsa_dev.operations import compose_cmd, down_env, restart_env, run_local, serve_env, stop_env, up_env
```

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/forsa_dev/operations.py src/forsa_dev/cli.py tests/test_cli_run.py
git commit -m "feat: add 'forsa-dev run' for serving from any directory"
```

---

### Task 8: Build dashboard production assets

After all frontend changes are done, rebuild the production bundle.

**Files:**
- Modify: `src/forsa_dev/dashboard/static/` (generated)

- [ ] **Step 1: Build production assets**

```bash
cd dashboard && npm run build
```

- [ ] **Step 2: Commit built assets**

```bash
git add src/forsa_dev/dashboard/static/
git commit -m "build: update dashboard production assets"
```

---

### Task 9: Final verification

- [ ] **Step 1: Run full Python test suite**

Run: `uv run pytest`
Expected: All tests pass.

- [ ] **Step 2: Run linter**

Run: `uv run ruff check src/ tests/`
Expected: No errors.

- [ ] **Step 3: Visual verification**

Start the dashboard and verify:
- Buttons are larger on desktop
- Create environment has two tabs (New / From branch)
- Terminal opens as fullscreen overlay
- Action buttons visible in terminal header
- VSCode link visible and generates correct URI
- User avatar shown in header
