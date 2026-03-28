# Branch Selector Improvements

## Problem

The branch selector has two issues:

1. **Missing branches in base selector:** The "New" tab's base branch dropdown reuses the import-filtered branch list, which excludes `main` and worktree-checked-out branches. Users can't branch from `next` or `main` when those are already in use as worktrees.

2. **Too many stale branches:** Both dropdowns show every branch regardless of age, making it hard to find relevant branches among dozens of stale ones.

## Design

### Backend: `git.py`

Replace `list_branches()` with a function that returns branch metadata instead of plain names.

Use `git for-each-ref --format='%(refname:short) %(committerdate:iso)' refs/heads/ refs/remotes/origin/` to get branch names and last commit dates in a single command (after the existing `git fetch --all`).

Return a list of objects with:
- `name` (str): branch name, with `origin/` prefix stripped for remote branches
- `last_commit` (str): ISO datetime of the tip commit
- `in_worktree` (bool): whether the branch is currently checked out as a worktree

When a branch exists both locally and on the remote, deduplicate by name, keeping the more recent `last_commit` date.

`main` and worktree-checked-out branches are included and tagged, not excluded.

### Backend: API endpoint

`/api/branches` returns the richer structure:

```json
{
  "branches": [
    {"name": "main", "last_commit": "2026-03-27T14:30:00+02:00", "in_worktree": true},
    {"name": "next", "last_commit": "2026-03-25T09:00:00+02:00", "in_worktree": true},
    {"name": "feature/old", "last_commit": "2025-11-01T12:00:00+02:00", "in_worktree": false}
  ]
}
```

### Frontend: `CreateEnvironment.jsx`

**Date filtering:** Compare each branch's `last_commit` against a 90-day cutoff from today. Branches older than 90 days are hidden by default.

**"Show all" toggle:** A small button/link below each dropdown that toggles stale branch visibility. Each dropdown manages its own toggle state independently.

**"From branch" tab (import):**
- Exclude `in_worktree` branches (can't check out the same branch twice)
- Apply 90-day date filter by default

**"New" tab base branch selector:**
- Include all branches (including `main` and worktree-checked-out ones)
- Apply 90-day date filter by default
- `main` is always shown regardless of age (it's the default base)

**Sort order:** Alphabetical, same as today.

### Testing

Update `test_git.py` to cover the new return format:
- Branch objects contain `name`, `last_commit`, and `in_worktree` fields
- `main` and worktree-checked-out branches are present (tagged, not excluded)
- Deduplication of local/remote branches prefers the more recent date
- `HEAD` entries are still excluded

Date filtering is frontend-only and doesn't need backend test coverage.
