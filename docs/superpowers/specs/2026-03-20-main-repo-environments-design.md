# Main Repo Environments

## Problem

The dashboard currently only manages worktree-based environments. The primary use
case for Hanna (and often Anders) is working in their main FORSA repo — editing
code, running the optimizer, checking results. These main repos should appear in
the dashboard as first-class environments with the same controls as worktrees.

## Prerequisites

**FORSA repo**: A `docker-compose.dev.yml` must be checked into the FORSA repo
root before forsa-dev can reference it. This file uses `${FORSA_DEV_*:-default}`
variable substitution for deployment-specific values (port, data dir, etc.) while
hardcoding container-internal paths in the `environment:` block.

Implementation order:
1. FORSA repo — create and check in `docker-compose.dev.yml`
2. forsa-dev — implement main repo environment support

## Use cases for the compose file

The checked-in `docker-compose.dev.yml` serves three use cases:

1. **forsa-dev** — passes `FORSA_DEV_PORT`, `FORSA_DEV_DATA`, etc. as shell
   environment variables when calling `docker compose`
2. **Local Docker development** — developers configure `FORSA_DEV_*` vars in
   `.env` or use the defaults
3. **Non-Docker development** (client) — unaffected, continues using `.env`
   with `FORSA_*` app variables directly

The `FORSA_DEV_*` namespace avoids collision with the app's `FORSA_*` variables.
Docker Compose resolves `${FORSA_DEV_PORT:-8000}` from host environment or `.env`,
while the `environment:` block passes container-internal paths (`/app/data`, etc.)
verbatim into the container.

## Design

### Data model

Add a `type` field to the `Environment` dataclass: `"worktree"` (default) or
`"repo"`. The `_deserialize` function must use `.get("type", "worktree")` so
existing state files without the field load correctly.

Main repo environments use the fixed name `"main"`, giving
`full_name = "{user}-main"`. This flows into tmux session names (`anders-main`),
docker compose project names, and state files (`anders-main.json`).

The name `"main"` is reserved — `up_env` must reject it to prevent worktree
state files from colliding with repo state files.

The `worktree` field points to the repo path from the user's config (the existing
`repo` field). The `compose_file` field points to `{repo}/docker-compose.dev.yml`
(the checked-in file, not generated).

The `branch` field reflects whatever branch is currently checked out in the repo.
It is refreshed on every `GET /api/environments` poll (a cheap
`git rev-parse --abbrev-ref HEAD` call) so the dashboard stays current when the
user switches branches. If the git command fails, the stale value from the state
file is used unchanged. Detached HEAD state displays as `HEAD`.

### Auto-discovery

On dashboard startup, for each discovered user:

1. Check if `{state_dir}/{user}-main.json` exists
2. If not, and the user's config has a valid `repo` path:
   - Verify `docker-compose.dev.yml` exists in the repo (if not, skip with a
     log warning — the state file is not created)
   - Allocate ports using `allocate_ports()` under the same `fcntl.flock`
     pattern as `up_env`, writing the state file before releasing the lock
   - Create state file with `type: "repo"`
3. Run ensure functions for repo environments (see below)

If a user's config file doesn't exist (e.g. Hanna's hasn't been created yet),
skip that user entirely. Do not auto-create config files.

### Ensure functions

Two targeted functions that check if a component exists and create it if missing:

- **ensure_tmux(env)** — if the tmux session doesn't exist, create it in the
  repo directory with Claude as the initial command (always, not configurable)
- **ensure_ttyd(env)** — if ttyd isn't alive on the allocated port, start it
  connected to the tmux session

These run on dashboard startup for repo environments. They are not called on
every poll (to avoid overhead). If tmux or ttyd crashes mid-session, recovery
requires a dashboard restart. This is a known limitation — a future improvement
could add on-demand recovery or periodic checks.

The ensure functions could later be reused for worktree environment recovery,
but that's out of scope.

No `ensure_compose` is needed — the compose file is checked into the FORSA repo.

### Docker compose invocation

For repo environments, `docker compose` is called with deployment-specific
values as shell environment variables:

```
FORSA_DEV_PORT=3005 \
FORSA_DEV_DATA=/data/dev \
FORSA_DEV_CONTAINER=forsa-anders-main \
FORSA_DEV_IMAGE=alvbyran/forsa:latest \
FORSA_DEV_GUROBI_LIC=/opt/gurobi/gurobi.lic \
docker compose -p anders-main -f /path/to/repo/docker-compose.dev.yml up -d
```

Variable mapping:

| Env var | Source |
|---------|--------|
| `FORSA_DEV_PORT` | `env.port` (from state file) |
| `FORSA_DEV_DATA` | `cfg.data_dir` (from user's forsa-dev config) |
| `FORSA_DEV_CONTAINER` | `forsa-{env.user}-{env.name}` |
| `FORSA_DEV_IMAGE` | `cfg.docker_image` (from user's forsa-dev config) |
| `FORSA_DEV_GUROBI_LIC` | `cfg.gurobi_lic` (from user's forsa-dev config) |

`serve_env`, `stop_env`, and `restart_env` must check `env.type` and, for repo
environments, pass the `FORSA_DEV_*` variables as the `env` parameter (merged
with `os.environ`) to `subprocess.run`. The existing `compose_cmd` function
remains unchanged — it only builds the command list.

`_serialize` needs no changes since `dataclasses.asdict` includes `type`
automatically.

For worktree environments, compose invocation is unchanged (uses the generated
compose file with baked-in values).

### API changes

**`GET /api/environments`**:
- Includes auto-discovered repo environments
- Each environment includes a `type` field in the response
- Repo environments are only included when the requesting user is the owner
  (filtered using the `forsa_user` cookie via existing `get_user` dependency)
- Worktree environments remain visible to all users (unchanged)
- For repo environments, refreshes `branch` from `git rev-parse`

**`DELETE /api/environments/{owner}/{name}`**:
- Returns 400 for `type="repo"` environments
- `down_env` itself also checks `type` and raises `ValueError` for repo
  environments (guards both API and CLI paths)

**Serve/stop/restart endpoints**:
- Same endpoints, same interface
- For repo environments, pass `FORSA_DEV_*` env vars when calling docker compose

### UI changes

The dashboard layout becomes two sections:

1. **Workspace** (top) — the current user's main repo environment
   - Single card, always present
   - Same controls: serve/stop/restart, terminal (ttyd), logs
   - Shows current branch, server status, uptime
   - No delete button
   - No create action (auto-discovered)

2. **Worktrees** (below) — create form and environment table, as today
   - All users' worktree environments visible
   - Unchanged behavior

### Visibility rules

| Environment type | Visible to owner | Visible to others |
|-----------------|-----------------|-------------------|
| repo            | Yes             | No                |
| worktree        | Yes             | Yes               |

### What main repo environments cannot do

- Cannot be deleted from the dashboard or via CLI (`down_env` must check
  `type` and refuse for repo environments, same as the API guard)
- No git worktree creation/removal
- No git branch creation/deletion
- Cannot be created manually (auto-discovered only)
