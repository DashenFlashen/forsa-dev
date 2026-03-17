# Agent Sessions & Dashboard Visual Refresh

## Summary

Add two always-on Claude agent sessions (Root Claude and forsa-dev Claude) accessible from the dashboard header via a popover menu. Simultaneously refresh the dashboard's visual design to match the polished aesthetic of the new agent UI.

## Context

Anders uses the shared Linux machine for both FORSA development and general maintenance. Having persistent Claude sessions accessible from the phone via the dashboard enables continuous development and system administration without needing SSH.

## Agent Sessions

### Agents

| Name | tmux session | Working directory | Command |
|------|-------------|-------------------|---------|
| Root Claude | `claude-root` | `/home/anders` | `claude --effort max` |
| forsa-dev Claude | `claude-forsa-dev` | `/home/anders/repos/forsa-dev` | `claude --effort max` |

### Lifecycle

- **Always-on**: Sessions start when the dashboard starts and run indefinitely
- **Survive restarts**: tmux sessions persist independently; the dashboard reconnects on restart
- **No restart UI**: If a session gets stuck, Anders uses `/clear` directly in the Claude terminal
- **Anders only**: Hardcoded to only appear when logged in as `anders`

### Backend: `src/forsa_dev/agents.py`

Defines the two agents as configuration and provides lifecycle functions:

- `AGENTS` list with session name, working directory, and command for each agent
- `ensure_agents(ttyd_ports)`: For each agent, creates the tmux session if missing, starts ttyd if not already listening on its port. Called once at dashboard startup.
- `agent_status(ttyd_ports)`: Returns current tmux status and ttyd health for each agent. Called by the API endpoint.

No state files — tmux sessions are the source of truth. ttyd PIDs are tracked in memory only.

### Fixed ttyd ports

Agents use fixed ports from the top of the existing ttyd range:
- Root Claude: **7698**
- forsa-dev Claude: **7699**

These are singletons, so dynamic allocation adds complexity with no benefit. The ttyd range (7600–7699) still has 98 ports for environments.

### API: `GET /api/agents`

Returns agent data with live status. Returns empty list for non-Anders users.

```json
[
  {
    "name": "root-claude",
    "label": "Root Claude",
    "description": "General purpose",
    "cwd": "~/",
    "ttyd_port": 7698,
    "tmux": "detached",
    "ttyd": "alive"
  },
  {
    "name": "forsa-dev-claude",
    "label": "forsa-dev Claude",
    "description": "Dashboard & CLI",
    "cwd": "~/repos/forsa-dev",
    "ttyd_port": 7699,
    "tmux": "detached",
    "ttyd": "alive"
  }
]
```

### Dashboard startup flow

In `create_app()`:
1. Check if `anders` exists in `user_configs`
2. If yes, call `ensure_agents()` with the fixed port mapping
3. Register the `/api/agents` endpoint

### Frontend: `AgentButtons` component

Single "Agents" button in the header bar (between hostname and user avatar) that opens a popover with two agent cards.

**Trigger button:**
- Indigo/purple gradient background with subtle glow
- Sparkle icon + "Agents" label + chevron
- Chevron rotates on open, button gets active state highlight

**Popover:**
- Glassmorphism panel with gradient background and shadow
- Slides in with scale+fade animation (cubic-bezier easing)
- "Active Agents" header
- Two agent cards, each with:
  - Colored icon (blue for Root, purple for forsa-dev)
  - Name and description
  - Live status badge with pulsing dot
  - Arrow indicator with hover slide
  - Ripple effect on click
- Closes on outside click

**Terminal:**
- Clicking an agent card opens the existing `TerminalView` fullscreen overlay
- Terminal tab only (no Logs tab — agents don't have docker compose)
- TerminalView accepts a simplified agent object (name, ttyd_port, ttyd status)

**Data fetching:**
- Fetch `/api/agents` once on mount and on the health polling interval (10s)
- Empty response = render nothing (handles non-Anders users gracefully)

**Responsive:**
- Desktop: Inline in header bar with divider separator
- Mobile: Same button, popover anchored to right edge

### Reference mockup

Interactive mockup at `.superpowers/brainstorm/session/fancy-agents-v2.html` — demonstrates the popover animation, card interactions, ripple effects, and terminal overlay transition.

## Dashboard Visual Refresh

Update the existing dashboard to match the polished aesthetic established by the agent popover. Applied across all existing components.

### Changes

- **Header**: Gradient background, refined spacing, consistent with agent button style
- **Environment cards/rows**: Subtle gradient backgrounds, improved borders, hover transitions with translate effects
- **Status badges**: Consistent color language — green (running/alive), yellow (detached/warning), red (crashed/dead), gray (stopped/missing)
- **Action buttons**: Refined hover/active states, smoother transitions
- **Health panel gauges**: Polished styling consistent with the new palette
- **Create environment form**: Updated input and button styles
- **TerminalView overlay**: Already close to the target aesthetic; minor polish for consistency
- **Typography**: Consistent use of Inter font weights, improved spacing and hierarchy
- **Color palette**: Indigo/purple for interactive elements, slate grays for backgrounds, green/yellow/red for status
- **Animations**: Consistent cubic-bezier easing, subtle hover lifts, smooth transitions throughout

### Constraints

- No structural changes to components — this is a visual-only pass
- Must remain responsive and mobile-friendly
- Must not break existing functionality
- Build on existing Tailwind classes where possible, add custom CSS only where needed
