# forsa-dev Dashboard Design

**Date:** 2026-03-07

## Overview

Add a web dashboard to `forsa-dev` that shows all development environments and lets users start/stop/restart servers from a browser. Thin visual layer on top of existing CLI modules — no business logic duplication.

## Architecture

```
forsa-dev repo
├── src/forsa_dev/
│   ├── cli.py              # unchanged except: imports operations.py
│   ├── operations.py       # NEW: serve_env(), stop_env(), restart_env()
│   ├── state.py            # unchanged
│   ├── list_status.py      # unchanged
│   ├── tmux.py             # unchanged
│   ├── config.py           # add dashboard_port field (default 8080)
│   └── dashboard/
│       ├── __init__.py
│       ├── server.py       # FastAPI app
│       └── static/         # built React app (committed to repo)
└── dashboard/              # React source (Vite project)
    ├── src/
    ├── package.json
    └── vite.config.js
scripts/
└── build_dashboard.sh      # npm build + copy to static/
```

## Backend

### `operations.py`

Extracts serve/stop/restart logic from `cli.py` into reusable functions:

```python
def serve_env(cfg: Config, user: str, name: str) -> None: ...
def stop_env(cfg: Config, user: str, name: str) -> None: ...
def restart_env(cfg: Config, user: str, name: str) -> None: ...
```

`cli.py` becomes a thin wrapper calling these. No behavior changes to the CLI.

### `server.py` endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/environments` | List all envs with live status |
| GET | `/api/health` | CPU, RAM, disk via psutil |
| POST | `/api/environments/{name}/serve` | Start server |
| POST | `/api/environments/{name}/stop` | Stop server |
| POST | `/api/environments/{name}/restart` | Restart server |
| GET | `/*` | Serve built React app |

**`GET /api/environments` response:**
```json
[
  {
    "name": "ticket-42",
    "user": "anders",
    "branch": "ticket-42",
    "port": 3002,
    "url": "http://localhost:3002",
    "created_at": "2026-03-07T22:00:00Z",
    "served_at": "2026-03-07T22:05:00Z",
    "status": { "tmux": "active", "server": "running" },
    "uptime": "2h 15m"
  }
]
```

**`GET /api/health` response:**
```json
{
  "cpu_percent": 45.2,
  "cpu_count": 16,
  "ram_used_gb": 12.3,
  "ram_total_gb": 32.0,
  "disk_used_gb": 1200,
  "disk_total_gb": 4000
}
```

### `forsa-dev dashboard` CLI command

Loads config (respecting `--config` flag). Port resolved as: `--port` flag > `config.dashboard_port` > 8080. Starts uvicorn directly (same pattern as FORSA webserver).

### Config changes

- Add `dashboard_port: int` to `Config` dataclass
- `load_config` reads with fallback default (8080) so existing configs don't break
- `save_config` writes the field
- `init` prompts for it

### Dependencies added to `pyproject.toml`

- `fastapi`
- `uvicorn`
- `psutil`

## Frontend

Single-page React app, Vite build.

**Component structure:**
```
App
├── HealthBar        — CPU / RAM / disk progress bars
├── EnvironmentTable
│   └── EnvironmentRow
│       └── ActionButtons
└── ErrorBanner      — shown when API unreachable
```

**Polling:**
- `/api/environments` every 3 seconds
- `/api/health` every 10 seconds
- Re-fetch environments immediately after any action

**Styling:** Tailwind CSS, dark theme, mobile-friendly (horizontal scroll or card collapse on small screens).

**Status colors:**
- Server: green=running, red=crashed, gray=stopped
- Tmux: green=active, yellow=detached, red=missing

**Action buttons:** disabled + spinner while POST is in-flight. Show Serve when stopped/crashed, Stop + Restart when running.

**Build process:**
- `npm run build` in `dashboard/` outputs to `dashboard/dist/`
- `scripts/build_dashboard.sh` copies output to `src/forsa_dev/dashboard/static/`
- Static files committed to repo — no Node required after `uv tool install`
- FastAPI serves static files via `importlib.resources` path to package static dir

## Testing

**Backend:** pytest for `operations.py` (mock subprocess, verify state updates) and FastAPI endpoints (httpx.AsyncClient with test config + tmp state dir).

**Frontend:** Manual testing during development. Vitest added later if component tree grows.

## What's out of scope

- Authentication (Tailscale handles network access)
- `up` / `down` from dashboard (git + tmux operations — CLI only)
- Log viewer
- WebSocket (polling is sufficient)
