# forsa-dev CLI — Design

## Overview

A Python CLI tool that manages FORSA development environments on a shared remote machine. Orchestrates git worktrees, Docker containers, tmux sessions, and Caddy reverse proxy so developers can run multiple branches simultaneously.

---

## Project Structure

```
forsa-dev/
├── pyproject.toml
└── src/
    └── forsa_dev/
        ├── __init__.py
        ├── cli.py        # Typer app, all commands
        ├── config.py     # ~/.config/forsa/config.toml load/save
        ├── state.py      # {state_dir}/{user}-{name}.json CRUD
        ├── ports.py      # Atomic port allocation via flock
        ├── compose.py    # docker-compose.dev.yml generation
        ├── caddy.py      # Caddy admin API (graceful failure)
        ├── git.py        # git branch + worktree operations
        └── tmux.py       # tmux session create/kill/attach
```

**Dependencies:** `typer`, `rich` (list table), `requests` (Caddy API), `tomli-w` (writing config in init — reading uses stdlib `tomllib`)

---

## Config

Location: `~/.config/forsa/config.toml`

```toml
repo = "/home/anders/forsa"
worktree_dir = "/home/anders/worktrees"
data_dir = "/data/dev"
state_dir = "/var/lib/forsa-dev"
caddy_admin = "http://localhost:2019"
base_url = "optbox.example.ts.net"
docker_image = "forsa:latest"
gurobi_lic = "/opt/gurobi/gurobi.lic"
port_range_start = 3000
port_range_end = 3099
```

`forsa-dev init` creates this file interactively.

---

## State File

Location: `{state_dir}/{user}-{name}.json`

Port is allocated at `up` time and stays for the environment's lifetime. `url` is null when not serving.

```json
{
  "name": "ticket-42",
  "user": "anders",
  "branch": "ticket-42",
  "worktree": "/home/anders/worktrees/ticket-42",
  "tmux_session": "anders-ticket-42",
  "compose_file": "/home/anders/worktrees/ticket-42/docker-compose.dev.yml",
  "port": 3002,
  "url": null,
  "created_at": "2026-03-07T22:00:00Z",
  "served_at": null
}
```

Port pool is implicit: used ports = ports in all state files. Freeing a port = deleting the state file (`down`).

---

## Commands

### `forsa-dev init`
Interactive prompts with sensible defaults. Writes `~/.config/forsa/config.toml`.

### `forsa-dev up <name> [--from <branch>]`
1. Compute `full_name = {user}-{name}`
2. Fail if state file already exists
3. Create git branch `{name}` from main (or `--from`). Fail if branch already exists.
4. `git worktree add {worktree_dir}/{name} {name}`
5. Atomically allocate port via flock on `{state_dir}/.port.lock`
6. Generate `{worktree_dir}/{name}/docker-compose.dev.yml`
7. Write state file
8. `tmux new-session -d -s {full_name} -c {worktree_dir}/{name}`
9. Attach: `tmux attach-session -t {full_name}` (or `tmux switch-client` if already inside tmux)

### `forsa-dev serve <name>`
1. Load state
2. `docker compose -p {full_name} -f {compose_file} up -d`
3. Register path→port route with Caddy (warn + continue if unreachable)
4. Update state: set `url`, `served_at`

### `forsa-dev stop <name>`
1. `docker compose -p {full_name} -f {compose_file} down`
2. Deregister from Caddy (warn + continue if unreachable)
3. Update state: clear `url`, `served_at`

### `forsa-dev down <name> [--force]`
1. If serving: stop first
2. Check branch pushed/merged via `git branch -r --contains {branch}`. Fail without `--force` if not.
3. Kill tmux: `tmux kill-session -t {full_name}`
4. `git worktree remove {worktree_dir}/{name}`
5. Delete state file (port freed implicitly)

### `forsa-dev list`
Read all state files. For each environment, live-check:
- tmux: `tmux has-session -t {full_name}`
- server: attempt socket connect on port

Print Rich table:
```
NAME         USER     TMUX       SERVER    PORT   URL
ticket-42    anders   active     running   3002   .../ticket-42/
experiment   anders   active     stopped   3005   -
ticket-38    hanna    detached   running   3001   .../ticket-38/
```

### `forsa-dev logs <name>`
`docker compose -p {full_name} -f {compose_file} logs -f`

### `forsa-dev attach <name>`
`tmux attach-session -t {full_name}` (or `tmux switch-client` if already in tmux)

### `forsa-dev restart <name>`
`docker compose -p {full_name} -f {compose_file} restart`

---

## Docker Compose Template

Generated at `{worktree_dir}/{name}/docker-compose.dev.yml` during `up`.
Variables substituted: `port`, `data_dir`, `gurobi_lic`, `docker_image`, `user`, `name`.
Source code and logs use relative paths (compose file lives in worktree root).

```yaml
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
```

---

## Port Allocation

Port allocation is atomic using `fcntl.flock` on `{state_dir}/.port.lock`:
1. Acquire exclusive flock
2. Read all state files to find used ports
3. Pick lowest port in range not in used set
4. Return port (caller writes state file while lock is held, or immediately after)
5. Release flock

---

## Caddy Integration

Caddy admin API at `{caddy_admin}` (default `http://localhost:2019`).
On `serve`: add a route matching `/{name}/*` → reverse proxy to `localhost:{port}`.
On `stop`: remove that route.
If Caddy is unreachable: log a warning, continue. CLI works without Caddy.

---

## Naming Convention

| Thing | Format | Example |
|---|---|---|
| Full name | `{user}-{name}` | `anders-ticket-42` |
| Git branch | `{name}` (no prefix) | `ticket-42` |
| Worktree path | `{worktree_dir}/{name}` | `/home/anders/worktrees/ticket-42` |
| tmux session | `{user}-{name}` | `anders-ticket-42` |
| Docker container | `forsa-{user}-{name}` | `forsa-anders-ticket-42` |
| State file | `{state_dir}/{user}-{name}.json` | `/var/lib/forsa-dev/anders-ticket-42.json` |
| Caddy path | `/{name}/` | `/ticket-42/` |

---

## Out of Scope (Phase 2)

- GitHub integration (auto-comment on issues)
- Auto-timeout / TTL for servers
- `forsa-dev deploy production`
