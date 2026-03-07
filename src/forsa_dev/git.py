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
