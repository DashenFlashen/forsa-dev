# Agent Sessions & Dashboard Visual Refresh Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two always-on Claude agent sessions accessible from the dashboard header, and refresh the dashboard visuals.

**Architecture:** New `agents.py` backend module handles tmux/ttyd lifecycle. New API endpoint serves agent status. New `AgentButtons` React component renders a popover in the header. `TerminalView` gains an `agent` prop for simplified rendering. The visual refresh is a CSS-only pass across existing components.

**Tech Stack:** Python/FastAPI, React/Vite, Tailwind CSS, tmux, ttyd, lucide-react

---

### Task 1: Backend — `agents.py` module

**Files:**
- Create: `src/forsa_dev/agents.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Write failing tests for `ensure_agents` and `agent_status`**

```python
# tests/test_agents.py
from __future__ import annotations

from unittest.mock import call, patch

from forsa_dev.agents import AGENTS, agent_status, ensure_agents


TTYD_PORTS = {"claude-root": 7698, "claude-forsa-dev": 7699}


def test_agents_config_has_two_entries():
    assert len(AGENTS) == 2
    names = [a["session"] for a in AGENTS]
    assert "claude-root" in names
    assert "claude-forsa-dev" in names


def test_ensure_agents_creates_missing_sessions():
    with patch("forsa_dev.agents.tmux") as mock_tmux, \
         patch("forsa_dev.agents.ttyd") as mock_ttyd:
        mock_tmux.session_exists.return_value = False
        mock_ttyd.ttyd_port_is_open.return_value = False
        mock_ttyd.start_ttyd.return_value = 12345

        pids = ensure_agents(TTYD_PORTS)

        assert mock_tmux.create_session.call_count == 2
        assert mock_ttyd.start_ttyd.call_count == 2
        assert len(pids) == 2


def test_ensure_agents_skips_existing_sessions():
    with patch("forsa_dev.agents.tmux") as mock_tmux, \
         patch("forsa_dev.agents.ttyd") as mock_ttyd:
        mock_tmux.session_exists.return_value = True
        mock_ttyd.ttyd_port_is_open.return_value = True

        pids = ensure_agents(TTYD_PORTS)

        mock_tmux.create_session.assert_not_called()
        mock_ttyd.start_ttyd.assert_not_called()
        assert len(pids) == 2


def test_ensure_agents_starts_ttyd_if_port_not_open():
    with patch("forsa_dev.agents.tmux") as mock_tmux, \
         patch("forsa_dev.agents.ttyd") as mock_ttyd:
        mock_tmux.session_exists.return_value = True
        mock_ttyd.ttyd_port_is_open.return_value = False
        mock_ttyd.start_ttyd.return_value = 99999

        pids = ensure_agents(TTYD_PORTS)

        mock_tmux.create_session.assert_not_called()
        assert mock_ttyd.start_ttyd.call_count == 2


def test_agent_status_returns_live_status():
    with patch("forsa_dev.agents.tmux") as mock_tmux, \
         patch("forsa_dev.agents.ttyd") as mock_ttyd:
        mock_tmux.session_status.return_value = "detached"
        mock_ttyd.ttyd_port_is_open.return_value = True

        result = agent_status(TTYD_PORTS)

        assert len(result) == 2
        assert result[0]["tmux"] == "detached"
        assert result[0]["ttyd"] == "alive"
        assert result[0]["ttyd_port"] == 7698


def test_agent_status_reports_dead_ttyd():
    with patch("forsa_dev.agents.tmux") as mock_tmux, \
         patch("forsa_dev.agents.ttyd") as mock_ttyd:
        mock_tmux.session_status.return_value = "missing"
        mock_ttyd.ttyd_port_is_open.return_value = False

        result = agent_status(TTYD_PORTS)

        assert result[0]["tmux"] == "missing"
        assert result[0]["ttyd"] == "dead"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_agents.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forsa_dev.agents'`

- [ ] **Step 3: Implement `agents.py`**

```python
# src/forsa_dev/agents.py
from __future__ import annotations

from pathlib import Path

from forsa_dev import tmux, ttyd

AGENTS = [
    {
        "name": "root-claude",
        "label": "Root Claude",
        "description": "General purpose",
        "session": "claude-root",
        "cwd": Path.home(),
        "command": "claude --effort max",
    },
    {
        "name": "forsa-dev-claude",
        "label": "forsa-dev Claude",
        "description": "Dashboard & CLI",
        "session": "claude-forsa-dev",
        "cwd": Path.home() / "repos" / "forsa-dev",
        "command": "claude --effort max",
    },
]


def ensure_agents(ttyd_ports: dict[str, int]) -> dict[str, int | None]:
    """Ensure agent tmux sessions and ttyd processes are running.

    Returns a dict mapping session name to ttyd PID (None if already running).
    """
    pids: dict[str, int | None] = {}
    for agent in AGENTS:
        session = agent["session"]
        if not tmux.session_exists(session):
            tmux.create_session(session, agent["cwd"], agent["command"])

        port = ttyd_ports[session]
        if ttyd.ttyd_port_is_open(port):
            pids[session] = None
        else:
            pids[session] = ttyd.start_ttyd(port, session)
    return pids


def agent_status(ttyd_ports: dict[str, int]) -> list[dict]:
    """Return current status for each agent."""
    result = []
    for agent in AGENTS:
        session = agent["session"]
        port = ttyd_ports[session]
        result.append({
            "name": agent["name"],
            "label": agent["label"],
            "description": agent["description"],
            "cwd": str(agent["cwd"]),
            "ttyd_port": port,
            "tmux": tmux.session_status(session),
            "ttyd": "alive" if ttyd.ttyd_port_is_open(port) else "dead",
        })
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_agents.py -v`
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/forsa_dev/agents.py tests/test_agents.py
git commit -m "feat: add agents module for persistent Claude sessions"
```

---

### Task 2: Shrink ttyd port range to reserve agent ports

**Files:**
- Modify: `src/forsa_dev/config.py:13`

This is a one-line constant change — no TDD loop needed.

- [ ] **Step 1: Change the default ttyd port range end**

In `src/forsa_dev/config.py:13`:
```python
# Before:
_DEFAULT_TTYD_PORT_RANGE_END = 7699
# After:
_DEFAULT_TTYD_PORT_RANGE_END = 7697
```

- [ ] **Step 2: Run all tests**

Run: `uv run pytest -v`
Expected: all PASS. Existing tests use explicit port ranges in fixtures so this default change won't break them.

- [ ] **Step 3: Commit**

```bash
git add src/forsa_dev/config.py
git commit -m "fix: reserve ttyd ports 7698-7699 for agent sessions"
```

---

### Task 3: API endpoint — `GET /api/agents`

**Files:**
- Modify: `src/forsa_dev/dashboard/server.py:15,48-62,109`
- Test: `tests/test_dashboard_server.py`

- [ ] **Step 1: Write failing tests for the agents endpoint**

Add to `tests/test_dashboard_server.py`:

```python
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
        {"name": "root-claude", "label": "Root Claude", "description": "General purpose",
         "cwd": "/home/anders", "ttyd_port": 7698, "tmux": "detached", "ttyd": "alive"},
        {"name": "forsa-dev-claude", "label": "forsa-dev Claude", "description": "Dashboard & CLI",
         "cwd": "/home/anders/repos/forsa-dev", "ttyd_port": 7699, "tmux": "detached", "ttyd": "alive"},
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dashboard_server.py::test_get_agents_returns_empty_for_non_anders_user -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 3: Add the agents endpoint and startup to `server.py`**

In `server.py`, add import:
```python
from forsa_dev import agents, git, tmux, ttyd
```

In `create_app()`, after `app = FastAPI()` and before defining routes, add agent startup:
```python
    agent_ttyd_ports = {"claude-root": 7698, "claude-forsa-dev": 7699}
    if "anders" in user_configs:
        try:
            agents.ensure_agents(agent_ttyd_ports)
        except Exception:
            pass  # agent startup failure shouldn't block dashboard
```

**Important:** The existing `test_get_users_multiple_users` test creates `user_configs = {"anders": ..., "hanna": ...}`, which will trigger `ensure_agents` at `create_app()` time without a mock. Add the agents mock to that test:

```python
def test_get_users_multiple_users(tmp_path):
    # ... existing setup code ...
    user_configs = {"anders": cfg1, "hanna": cfg2}
    with patch("forsa_dev.dashboard.server.agents"):
        app = create_app(user_configs)
        client = TestClient(app)
        response = client.get("/api/users")
    assert response.status_code == 200
    names = [u["name"] for u in response.json()]
    assert "anders" in names
    assert "hanna" in names
```

Any future tests that include `"anders"` in `user_configs` must also mock `agents` to prevent real tmux/ttyd calls.

Add the endpoint (before the static mount):
```python
    @app.get("/api/agents")
    def get_agents(forsa_user: str = Cookie(default=None)) -> list[dict[str, Any]]:
        if forsa_user != "anders" or "anders" not in user_configs:
            return []
        return agents.agent_status(agent_ttyd_ports)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dashboard_server.py -v`
Expected: all PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/forsa_dev/dashboard/server.py tests/test_dashboard_server.py
git commit -m "feat: add GET /api/agents endpoint with startup lifecycle"
```

---

### Task 4: Frontend — `AgentButtons` component

**Files:**
- Create: `dashboard/src/components/AgentButtons.jsx`
- Modify: `dashboard/src/App.jsx`

- [ ] **Step 1: Create `AgentButtons.jsx`**

```jsx
import { useState, useEffect, useRef } from 'react'
import { Terminal, ChevronDown, Wrench } from 'lucide-react'

export default function AgentButtons({ onSelectAgent }) {
  const [agents, setAgents] = useState([])
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    fetch('/api/agents')
      .then((r) => r.json())
      .then(setAgents)
      .catch(() => {})
  }, [])

  // Poll every 10s
  useEffect(() => {
    const id = setInterval(() => {
      fetch('/api/agents')
        .then((r) => r.json())
        .then(setAgents)
        .catch(() => {})
    }, 10000)
    return () => clearInterval(id)
  }, [])

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('click', handleClick, true)
    return () => document.removeEventListener('click', handleClick, true)
  }, [open])

  if (agents.length === 0) return null

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-200 ${
          open
            ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-200 shadow-[0_0_20px_rgba(99,102,241,0.2)]'
            : 'bg-indigo-500/10 border-indigo-500/20 text-indigo-300 hover:bg-indigo-500/15 hover:border-indigo-500/30 hover:text-indigo-200 hover:-translate-y-px hover:shadow-[0_4px_20px_rgba(99,102,241,0.15)]'
        } border`}
      >
        <svg className={`h-3.5 w-3.5 transition-transform duration-300 ${open ? 'rotate-[20deg] scale-110' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3v1m0 16v1m-8-9H3m18 0h-1m-2.636-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707.707"/>
          <circle cx="12" cy="12" r="4"/>
        </svg>
        Agents
        <ChevronDown className={`h-3 w-3 opacity-50 transition-transform duration-200 ${open ? 'rotate-180 opacity-80' : ''}`} />
      </button>

      <div className={`absolute right-0 top-full mt-2 w-72 rounded-xl border border-indigo-500/15 bg-gradient-to-b from-gray-900 via-gray-900 to-gray-950 p-1.5 shadow-[0_20px_60px_rgba(0,0,0,0.5),0_0_40px_rgba(99,102,241,0.08)] transition-all duration-200 ${
        open
          ? 'opacity-100 translate-y-0 scale-100 pointer-events-auto'
          : 'opacity-0 -translate-y-2 scale-[0.96] pointer-events-none'
      } z-50`}>
        <div className="px-3 pt-2 pb-1 text-[0.65rem] font-semibold uppercase tracking-widest text-gray-500">
          Active Agents
        </div>
        {agents.map((agent, i) => (
          <div key={agent.name}>
            {i > 0 && <div className="mx-3 h-px bg-gradient-to-r from-transparent via-indigo-500/10 to-transparent" />}
            <button
              onClick={() => { onSelectAgent(agent); setOpen(false) }}
              className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-all duration-200 hover:translate-x-1 active:scale-[0.99] ${
                i === 0 ? 'hover:bg-blue-500/[0.06]' : 'hover:bg-purple-500/[0.06]'
              }`}
            >
              <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${
                i === 0
                  ? 'border-blue-500/20 bg-blue-500/10'
                  : 'border-purple-500/20 bg-purple-500/10'
              }`}>
                {i === 0
                  ? <Terminal className="h-4 w-4 text-blue-400" />
                  : <Wrench className="h-4 w-4 text-purple-400" />
                }
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold text-gray-200">{agent.label}</div>
                <div className="text-xs text-gray-500">{agent.description} · {agent.cwd}</div>
              </div>
              <div className={`flex items-center gap-1 rounded px-1.5 py-0.5 text-[0.65rem] font-medium ${
                agent.ttyd === 'alive'
                  ? 'bg-green-500/10 text-green-400 border border-green-500/15'
                  : 'bg-red-500/10 text-red-400 border border-red-500/15'
              }`}>
                <span className={`h-1.5 w-1.5 rounded-full ${
                  agent.ttyd === 'alive' ? 'bg-green-400 animate-pulse' : 'bg-red-400'
                }`} />
                {agent.ttyd === 'alive' ? 'Live' : 'Down'}
              </div>
              <ChevronDown className="h-3.5 w-3.5 -rotate-90 text-gray-600 transition-all group-hover:translate-x-0.5 group-hover:text-gray-400" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Wire `AgentButtons` into `App.jsx`**

Add import:
```jsx
import AgentButtons from './components/AgentButtons'
```

Add state for selected agent:
```jsx
const [selectedAgent, setSelectedAgent] = useState(null)
```

In the header, between the hostname and the user section, add:
```jsx
<AgentButtons onSelectAgent={setSelectedAgent} />
```

Add the agent terminal overlay (alongside the existing env overlay):
```jsx
{selectedAgent && (
  <div className="fixed inset-0 z-50 flex flex-col bg-gray-950">
    <TerminalView
      agent={selectedAgent}
      host={host}
      onClose={() => setSelectedAgent(null)}
    />
  </div>
)}
```

- [ ] **Step 3: Test in browser**

Run: `cd dashboard && npm run dev`
Verify: Agents button appears in header, popover opens/closes, agent cards show status.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/AgentButtons.jsx dashboard/src/App.jsx
git commit -m "feat: add AgentButtons component with popover"
```

---

### Task 5: Modify `TerminalView` for agent support

**Files:**
- Modify: `dashboard/src/components/TerminalView.jsx`

- [ ] **Step 1: Add `agent` prop support**

Modify `TerminalView` to accept either `env` or `agent`. When `agent` is provided, render a simplified terminal-only view.

```jsx
import { useState } from 'react'
import { Code2, X, Terminal, ExternalLink } from 'lucide-react'
import ActionButtons from './ActionButtons'
import StatusBadge from './StatusBadge'
import LogsView from './LogsView'

export default function TerminalView({ env, agent, host, onClose, onAction, loadingAction }) {
  const [tab, setTab] = useState('terminal')
  const isAgent = !!agent
  const name = isAgent ? agent.label : env.name
  const ttydPort = isAgent ? agent.ttyd_port : env.ttyd_port
  const src = ttydPort ? `http://${host}:${ttydPort}` : null

  return (
    <div className="flex h-full w-full flex-col bg-gray-950">
      <div className="flex items-center gap-2 border-b border-gray-800 bg-gray-900 px-3 py-2 lg:gap-3 lg:px-4 lg:py-2.5 shrink-0">
        <Terminal className="hidden h-4 w-4 shrink-0 text-gray-500 lg:block" />
        <span className="font-mono text-sm font-medium text-gray-100 truncate">{name}</span>
        {!isAgent && <StatusBadge status={env.status.server} />}
        {!isAgent && (
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
        )}
        {!isAgent && (
          <div className="hidden lg:flex items-center gap-1">
            <ActionButtons env={env} onAction={onAction} loading={loadingAction} />
          </div>
        )}
        <div className="flex-1" />
        {!isAgent && (
          <>
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
            <a
              href={`vscode://vscode-remote/ssh-remote+${host}${env.worktree}`}
              title="Open in VSCode"
              className="flex items-center gap-1 rounded px-2 py-1 text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-200 transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              <Code2 className="h-3.5 w-3.5" />
              <span className="hidden lg:inline">VSCode</span>
            </a>
          </>
        )}
        <button
          onClick={onClose}
          className="rounded p-2 text-gray-500 hover:bg-gray-800 hover:text-gray-200 transition-colors"
          aria-label="Close terminal"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {!isAgent && tab === 'logs' ? (
        <LogsView envName={env.name} envUser={env.user} />
      ) : src ? (
        <iframe
          src={src}
          className="flex-1 w-full border-0"
          title={`Terminal: ${name}`}
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

- [ ] **Step 2: Test in browser**

Verify:
1. Environment terminal still works as before (with logs tab, action buttons, port link, VSCode link)
2. Agent terminal shows terminal only (no logs tab, no action buttons, no port/VSCode links)

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/TerminalView.jsx
git commit -m "feat: support agent prop in TerminalView for simplified rendering"
```

---

### Task 6: Dashboard visual refresh — CSS custom styles

**Files:**
- Create: `dashboard/src/styles/theme.css`
- Modify: `dashboard/src/main.jsx` (import theme.css)

- [ ] **Step 1: Create `theme.css` with shared visual refinements**

This file provides custom CSS for effects that Tailwind utility classes can't express (gradients, glassmorphism, complex shadows, animations). Components reference these classes via `className`.

```css
/* dashboard/src/styles/theme.css */

/* Smooth transitions for all interactive elements */
.theme-transition {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Header gradient */
.theme-header {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
}

/* Card hover lift */
.theme-card-hover:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* Subtle card gradient background */
.theme-card-bg {
  background: linear-gradient(160deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.4) 100%);
}

/* Gauge bar glow for high values */
.theme-gauge-glow-red {
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.3);
}

.theme-gauge-glow-yellow {
  box-shadow: 0 0 8px rgba(234, 179, 8, 0.2);
}

/* Button press effect */
.theme-btn-press:active {
  transform: scale(0.97);
}

/* Collapsible section refined */
.theme-section {
  background: linear-gradient(160deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.5) 100%);
  border-color: rgba(51, 65, 85, 0.6);
}

```

- [ ] **Step 2: Import in `main.jsx`**

Add after the existing tailwind import:
```jsx
import './styles/theme.css'
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/styles/theme.css dashboard/src/main.jsx
git commit -m "ui: add custom theme CSS for visual polish"
```

---

### Task 7: Dashboard visual refresh — apply to components

**Files:**
- Modify: `dashboard/src/App.jsx` (header)
- Modify: `dashboard/src/components/CollapsibleSection.jsx`
- Modify: `dashboard/src/components/EnvironmentCard.jsx`
- Modify: `dashboard/src/components/EnvironmentRow.jsx`
- Modify: `dashboard/src/components/HealthPanel.jsx`
- Modify: `dashboard/src/components/CreateEnvironment.jsx`
- Modify: `dashboard/src/components/UserPicker.jsx`
- Modify: `dashboard/src/components/ActionButtons.jsx`

- [ ] **Step 1: Update `App.jsx` header**

Change the header from:
```jsx
<header className="border-b border-gray-800 bg-gray-900">
```
To:
```jsx
<header className="border-b border-gray-800 theme-header">
```

- [ ] **Step 2: Update `CollapsibleSection.jsx`**

Change the outer div from:
```jsx
<div className="rounded-lg border border-gray-800 bg-gray-900 px-5 py-4">
```
To:
```jsx
<div className="rounded-lg border border-gray-700/60 theme-section px-5 py-4">
```

- [ ] **Step 3: Update `EnvironmentCard.jsx`**

Add `theme-card-hover theme-transition` to the card's outer div and change the background:
```jsx
<div
  onClick={() => onSelect(env)}
  className={`rounded-lg border p-4 theme-transition theme-card-hover ${
    isSelected
      ? 'border-blue-500 bg-gray-900'
      : 'border-gray-700/60 theme-card-bg active:bg-gray-900'
  }`}
>
```

- [ ] **Step 4: Update `EnvironmentRow.jsx`**

Replace `transition-colors` with `theme-transition` on the table row (don't use both — `theme-transition` sets `transition: all` which supersedes Tailwind's `transition-colors`):
```jsx
<tr
  className={`border-t border-gray-800 cursor-pointer theme-transition hover:bg-gray-900/60 ${
    isSelected
      ? 'bg-gray-900 border-l-2 border-l-blue-500'
      : 'border-l-2 border-l-transparent'
  }`}
  onClick={() => onSelect(env)}
>
```

- [ ] **Step 5: Update `HealthPanel.jsx` gauge bar**

Change the outer bar from:
```jsx
<div className="h-1.5 overflow-hidden rounded-full bg-gray-700">
```
To:
```jsx
<div className="h-2 overflow-hidden rounded-full bg-gray-800">
```

Add glow class to the fill bar based on color:
```jsx
const glowClass =
  pct > 85 ? 'theme-gauge-glow-red' :
  pct > 60 ? 'theme-gauge-glow-yellow' :
  ''
```
```jsx
<div
  className={`h-full rounded-full transition-all duration-700 ${color} ${glowClass}`}
  style={{ width: `${pct}%` }}
/>
```

- [ ] **Step 6: Update `ActionButtons.jsx`**

Add `theme-btn-press` to each button:
```jsx
className={`rounded-md p-2.5 lg:p-2 transition-colors disabled:opacity-50 theme-btn-press ${colorClass}`}
```

- [ ] **Step 7: Update `CreateEnvironment.jsx` submit buttons**

Add `theme-btn-press` to both submit buttons:
```jsx
className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors theme-btn-press"
```

- [ ] **Step 8: Update `UserPicker.jsx`**

Add `theme-transition theme-card-hover` to user buttons:
```jsx
className="rounded-lg bg-gray-800 px-8 py-3 text-lg font-medium text-gray-100 theme-transition theme-card-hover capitalize"
```

- [ ] **Step 9: Test in browser**

Run: `cd dashboard && npm run dev`
Verify:
- Header has gradient background
- Cards lift on hover with smooth transitions
- Gauges show subtle glow at high values
- Buttons have press feedback
- Overall look is cohesive and polished

- [ ] **Step 10: Commit**

```bash
git add dashboard/src/App.jsx dashboard/src/components/CollapsibleSection.jsx \
  dashboard/src/components/EnvironmentCard.jsx dashboard/src/components/EnvironmentRow.jsx \
  dashboard/src/components/HealthPanel.jsx dashboard/src/components/ActionButtons.jsx \
  dashboard/src/components/CreateEnvironment.jsx dashboard/src/components/UserPicker.jsx
git commit -m "ui: apply visual refresh across dashboard components"
```

---

### Task 8: Build and deploy

**Files:**
- Modify: `src/forsa_dev/dashboard/static/` (rebuilt assets)

- [ ] **Step 1: Build the React app**

Run: `cd dashboard && npm run build`

- [ ] **Step 2: Copy built assets to the static directory**

Run: `rm -rf src/forsa_dev/dashboard/static && cp -r dashboard/dist src/forsa_dev/dashboard/static`

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest -v`
Expected: all PASS

- [ ] **Step 4: Run linting**

Run: `uv run ruff check src/ tests/`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add src/forsa_dev/dashboard/static/
git commit -m "build: update dashboard production assets"
```

- [ ] **Step 6: Visual verification**

Start the dashboard and verify:
1. Agent buttons appear in header for Anders
2. Clicking agent → popover with two agent cards
3. Clicking agent card → terminal overlay opens with ttyd iframe
4. Close terminal overlay → back to dashboard
5. All existing environment features work unchanged
6. Visual polish applied across all components
