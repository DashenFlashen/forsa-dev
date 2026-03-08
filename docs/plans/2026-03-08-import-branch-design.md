# Import Existing Branch Design

## Goal

Allow users to create a forsa-dev environment from a branch that already exists, rather than always creating a new one from main.

## Data Model

No changes. `Environment` already has separate `name` and `branch` fields. Today they are always equal; after this feature they can differ (e.g. `name: ticket-42`, `branch: feature/ticket-42`).

## Backend

### `git.list_branches(repo) -> list[str]`

Returns deduplicated branch names available to import:
- Runs `git fetch` first so remote-only branches appear
- Includes local branches and remote-tracking branches (strips `origin/` prefix, deduplicates)
- Excludes branches already checked out in a worktree (already have an environment)
- Excludes `HEAD` and `main`

### `git.create_worktree_from_branch(repo, branch, worktree)`

Creates a worktree for an existing branch without creating a new branch:
```
git worktree add <worktree> <branch>
```
If the branch only exists on remote, git auto-creates a local tracking branch.

### `GET /api/branches`

Thin endpoint wrapping `git.list_branches`. Returns `{"branches": [...]}`.

### `up_env` extension

Add `existing_branch: str | None = None` parameter:
- If `None` (default): current behaviour — creates new branch named `name` from `from_branch`
- If set: calls `create_worktree_from_branch` instead; `env.branch = existing_branch`, `env.name = name`

`CreateEnvRequest` gets a matching `existing_branch: str | None = None` field.

Teardown is unchanged — same `branch_is_pushed` check then local delete.

## Frontend

### `ImportBranch.jsx` (new card, below CreateEnvironment)

- Fetches `/api/branches` on mount
- Branch dropdown populated from the response
- Name input: auto-filled with last segment after `/` from selected branch, user-editable
- Data dir field: same pattern as create form, pre-filled from `/api/config`
- Import button (disabled until branch selected and name valid)

On submit, calls `POST /api/environments` with `existing_branch` set.

### `App.jsx`

Pass `defaultDataDir` to `ImportBranch` (already fetched for `CreateEnvironment`).
