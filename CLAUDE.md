# forsa-dev

CLI tool for managing personal FORSA development environments on a shared Linux machine.

## Running tests

```
uv run pytest
uv run ruff check src/ tests/
```

## Non-Python dependencies

The tool assumes these are installed on the host machine:

- **tmux** — each environment gets a named session
- **docker** (with compose plugin) — containers run via `docker compose`
- **git** — worktrees require Git ≥ 2.5

## Deployment context

The tool runs on a shared Linux machine exposed via Tailscale. Caddy acts as a
path-based reverse proxy, routing `https://<base_url>/<name>/` to each
environment's container port. The Caddy admin API (`http://localhost:2019`) must
be reachable for `serve` and `stop` to register/deregister routes.

State files live in a shared directory (default `/var/lib/forsa-dev`) so
multiple users on the same machine can see each other's environments. Port
allocation uses `fcntl.flock` on a shared lock file to prevent races.

## Naming: `name` vs `full_name`

Every environment is scoped by both user and name:

- `name` — the short name the user provides (e.g. `ticket-42`)
- `full_name` — `{user}-{name}` (e.g. `anders-ticket-42`)

`full_name` is used for tmux session names, docker compose project names, and
state file names (`anders-ticket-42.json`). This lets two users independently
create an environment called `ticket-42` without colliding on state or containers,
though the underlying git branch will still collide (intentional — see git.py).

## Compose file location

`generate_compose()` writes `docker-compose.dev.yml` into the root of each git
worktree. This file should be listed in the main FORSA repo's `.gitignore` to
avoid accidental commits.
