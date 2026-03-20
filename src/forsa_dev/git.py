from __future__ import annotations

import subprocess
from pathlib import Path


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def create_branch_and_worktree(
    repo: Path,
    branch: str,
    worktree: Path,
    from_branch: str = "main",
) -> None:
    """Create a new git branch and check it out as a worktree."""
    # Check branch doesn't already exist.
    # Note: there's a TOCTOU window between this check and `worktree add -b` below —
    # two concurrent `up` calls for the same branch will both pass, and the second
    # `worktree add` will fail with a raw git error rather than this friendly message.
    result = _git(["branch", "--list", branch], repo)
    if result.stdout.strip():
        raise RuntimeError(f"Branch '{branch}' already exists — it may belong to another user.")

    worktree.parent.mkdir(parents=True, exist_ok=True)
    result = _git(
        ["worktree", "add", "-b", branch, str(worktree), from_branch],
        repo,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {result.stderr}")


def remove_worktree(repo: Path, worktree: Path) -> None:
    """Remove a git worktree and prune the worktree list."""
    result = _git(["worktree", "remove", "--force", str(worktree)], repo)
    if result.returncode != 0:
        raise RuntimeError(f"git worktree remove failed: {result.stderr}")


def branch_is_pushed(repo: Path, branch: str) -> bool:
    """Return True if the branch has a remote tracking ref."""
    result = _git(["branch", "-r", "--contains", branch], repo)
    if result.returncode != 0:
        raise RuntimeError(f"git branch -r failed: {result.stderr}")
    return bool(result.stdout.strip())


def delete_branch(repo: Path, branch: str, force: bool = False) -> None:
    """Delete a git branch. Use force=True to delete unmerged branches."""
    flag = "-D" if force else "-d"
    result = _git(["branch", flag, branch], repo)
    if result.returncode != 0:
        raise RuntimeError(f"git branch {flag} failed: {result.stderr}")


def create_worktree_from_branch(repo: Path, branch: str, worktree: Path) -> None:
    """Check out an existing branch as a worktree (does not create a new branch)."""
    worktree.parent.mkdir(parents=True, exist_ok=True)
    result = _git(["worktree", "add", str(worktree), branch], repo)
    if result.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {result.stderr}")


def current_branch(repo: Path) -> str | None:
    """Return the current branch name, 'HEAD' if detached, or None if not a repo."""
    result = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def list_branches(repo: Path) -> list[str]:
    """List branches available to import (excludes main and worktree-checked-out branches)."""
    _git(["fetch", "--all", "--quiet"], repo)  # ignore failure — no remote in tests

    local = _git(["branch", "--format=%(refname:short)"], repo)
    local_branches = {b.strip() for b in local.stdout.splitlines() if b.strip()}

    remote = _git(["branch", "-r", "--format=%(refname:short)"], repo)
    remote_branches = set()
    for b in remote.stdout.splitlines():
        b = b.strip()
        if not b or "HEAD" in b:
            continue
        if b.startswith("origin/"):
            remote_branches.add(b[len("origin/"):])

    all_branches = local_branches | remote_branches

    worktree_result = _git(["worktree", "list", "--porcelain"], repo)
    in_use = set()
    for line in worktree_result.stdout.splitlines():
        if line.startswith("branch "):
            in_use.add(line.split("refs/heads/", 1)[-1])

    return sorted(all_branches - in_use - {"main"})
