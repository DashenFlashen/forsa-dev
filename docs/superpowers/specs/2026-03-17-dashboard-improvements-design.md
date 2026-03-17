# Dashboard Improvements

Consolidated improvements to the forsa-dev dashboard covering UX, workflow, and configuration changes.

## 1. Terminal: near-fullscreen overlay

**Current:** Desktop shows the terminal in a side panel (`h-[600px]`, 1/3 + 2/3 split). Too small to work in.

**Change:** Replace the side panel with a fullscreen overlay on desktop, matching the existing mobile behavior. The overlay covers the entire viewport (`fixed inset-0`, same as the current mobile implementation) including the header. The close button is the escape hatch back to the dashboard.

The terminal overlay header includes:
- Environment name and status badge
- Tab switcher (terminal / logs)
- Environment URL link (`:port`, opens in new tab)
- Quick action buttons (start/stop/restart) so the user doesn't have to leave the terminal to control the server
- "Open in VSCode" link (see section 4)
- Close button to return to the dashboard

**Files affected:**
- `App.jsx` — remove the desktop split layout (`lg:flex-row`, `lg:w-1/3`, `h-[600px]`), unify both mobile and desktop to use the same fullscreen overlay. Pass `onAction` and `loadingActions` props through to `TerminalView`.
- `TerminalView.jsx` — accept new `onAction`/`loadingActions` props, add action buttons and VSCode link to the header bar

## 2. Unified create environment form

**Current:** Two separate collapsible sections: "New Environment" (`CreateEnvironment.jsx`) and "Import Branch" (`ImportBranch.jsx`).

**Change:** Merge into a single collapsible section with two tabs: **New** and **From branch**.

- **New tab:** Name input + Create button (creates branch from `main`). Same as current `CreateEnvironment`.
- **From branch tab:** Branch dropdown + auto-derived name input + Import button. Same as current `ImportBranch`.
- Both tabs share the "Options..." data dir toggle.
- Branch list is fetched once when the component mounts (same as current `ImportBranch`).

**Files affected:**
- Create new `CreateEnvironment.jsx` replacing both current components (branch list fetched internally, same as current `ImportBranch`)
- Delete `ImportBranch.jsx`
- `App.jsx` — remove `ImportBranch` import and usage

## 3. Button sizing

**Current:** Desktop action buttons use `p-1.5` padding with `h-3.5 w-3.5` icons. Hard to click and distinguish.

**Change:** Increase desktop button sizes:
- `ActionButtons.jsx` `ActionBtn`: change `lg:p-1.5` → `lg:p-2`, change `lg:h-3.5 lg:w-3.5` → `lg:h-4 lg:w-4`
- `EnvironmentRow.jsx` terminal and delete buttons: change `p-1.5` → `p-2`, change `h-3.5 w-3.5` → `h-4 w-4`
- `ActionButtons.jsx` line 27 and `EnvironmentRow.jsx` line 56: increase `gap-1` → `gap-1.5`

Mobile sizes stay the same — `EnvironmentCard.jsx` already uses `p-2.5` and `h-4 w-4`, no changes needed there.

## 4. VSCode "Open in editor" link

**Change:** Add a link/button to each environment that opens the worktree in VSCode via the Remote SSH extension.

URI format: `vscode://vscode-remote/ssh-remote+{ssh_host}{worktree_path}`

- `ssh_host` is derived from the dashboard's `base_url` config (or the browser's `window.location.hostname`)
- `worktree_path` is already available in the environment state

**Backend:** The `Environment` dataclass stores `worktree` as a `Path`, but `server.py` doesn't include it in the API response. Add it as `worktree` (matching the dataclass field name) to the environment JSON returned by `/api/environments`.

**Frontend:** Render a VSCode icon link in:
- `EnvironmentRow.jsx` actions column
- `TerminalView.jsx` header bar

Use `lucide-react`'s `Code2` or `ExternalLink` icon with a "VSCode" label/tooltip.

**Note:** The `vscode://` URI scheme requires the Remote SSH extension and a matching SSH config entry on the user's local machine. This should be tested manually before relying on it.

## 5. Lightweight CLI run command

**Note:** `forsa-dev serve` already exists (starts the Docker server for an existing environment). This new command is named `forsa-dev run` to avoid collision.

**Change:** Add a `forsa-dev run` command that starts a FORSA server from the current directory (or a specified path) without creating a worktree.

Behavior:
- Allocates a port from the shared port range (same locking mechanism)
- Generates `docker-compose.dev.yml` in the target directory
- Runs `docker compose up` in the **foreground** — a temporary state file (`local-run.json`) reserves the port so concurrent allocations see it as taken; the state file is cleaned up on exit
- Prints the URL before attaching to compose output

This is for users (like Hanna) who work directly in the main repo checkout and just want to run the server. No tmux session, no ttyd, no dashboard integration. A temporary state file reserves the port during the run. Ctrl+C stops everything cleanly and removes the state file.

**Files affected:**
- `cli.py` — add `run` subcommand
- `operations.py` — extract compose generation and port allocation into a reusable function that can be used by both `up_env()` and the new `run` command
- `compose.py` — no changes needed (already generates from a directory path)

## 6. User visibility and access

**Problem:** Only `anders` appears in the user picker because `discover_users()` requires membership in the `forsa-devs` UNIX group AND a valid config at `~{user}/.config/forsa/config.toml`.

**Fix (operational):** Add Hanna to the `forsa-devs` group and create her config file. This is a sysadmin task, not a code change.

**UI improvement:** Make the current user more visually prominent in the header. Currently it says "logged in as **anders**" in small text. Consider:
- Larger user display with the `UserInitials` avatar component in the header
- Color-code environments in the table by owner (already shows `UserInitials`, but could be more prominent)

This is a minor styling change — no architectural work needed.

## 7. `--effort max` for Claude sessions

**Current:** Claude launches with only `--dangerously-skip-permissions`.

**Change:** Add `--effort max` flag. One-line change in `operations.py`:

```python
# Before
f"{shell} -i -c 'claude --dangerously-skip-permissions || exec {shell}'"
# After
f"{shell} -i -c 'claude --dangerously-skip-permissions --effort max || exec {shell}'"
```

Hardcoded, not configurable.

**Note:** This only affects environments created with `with_claude=True`. The dashboard always sets this, but CLI users need `--with-claude` to get a Claude session.

**Files affected:**
- `operations.py` line 121

## Implementation order

Suggested order by dependency and risk:

1. **Button sizing** (#3) — trivial CSS change, immediate visual improvement
2. **`--effort max`** (#7) — one-line change
3. **User access fix** (#6) — sysadmin task + minor header styling
4. **Unified create form** (#2) — self-contained frontend refactor
5. **Terminal overlay** (#1) — frontend layout change, touches `App.jsx` and `TerminalView.jsx`
6. **VSCode link** (#4) — requires backend change (expose `worktree_path`) + frontend
7. **CLI run command** (#5) — new feature, requires backend refactoring
