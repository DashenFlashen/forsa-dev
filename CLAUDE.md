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

The tool runs on a shared Linux machine exposed via Tailscale. Each environment
is reachable directly on its allocated port (`http://<base_url>:<port>/`). The
dashboard (`forsa-dev dashboard`) serves a React UI for managing environments
and exposes ttyd terminal sessions on a separate port range (7600–7699).

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

## Cross-user process management

The dashboard runs as anders's systemd user service but manages environments
for all `forsa-devs` group members. Cross-user operations use sudo:

- **tmux** commands accept `run_as` to prefix with `sudo -u <owner>`
- **ttyd** runs as the dashboard user but attaches to cross-user tmux via sudo
- **docker** works cross-user via the shared `docker` group
- **git/files** work via `forsa-devs` group ownership with setgid

Sudoers rule (`/etc/sudoers.d/forsa-devs`):
```
%forsa-devs ALL=(%forsa-devs) NOPASSWD: /usr/bin/tmux, /usr/bin/kill, /usr/bin/bash
```

## Dashboard service

The dashboard runs as a systemd user service (`forsa-dashboard.service`).

```bash
systemctl --user status forsa-dashboard   # check status
systemctl --user restart forsa-dashboard  # restart after code changes
journalctl --user -u forsa-dashboard -n 50 --no-pager  # view logs
```

The service unit lives at `~/.config/systemd/user/forsa-dashboard.service`
and auto-restarts on failure. It runs on port 8080 by default.

## Deploying changes

After editing Python code:
```bash
uv run pytest && uv run ruff check src/ tests/
uv tool install --force --reinstall .   # --reinstall is critical, --force alone can use cached builds
systemctl --user restart forsa-dashboard
```

For frontend changes, also build first:
```bash
cd dashboard && npm run build && cd ..
```

## Compose file location

`generate_compose()` writes `docker-compose.dev.yml` into the root of each git
worktree. This file should be listed in the main FORSA repo's `.gitignore` to
avoid accidental commits.
