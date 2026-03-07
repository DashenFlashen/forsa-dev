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
    # Check branch doesn't already exist
    result = _git(["branch", "--list", branch], repo)
    if result.stdout.strip():
        raise RuntimeError(f"Branch '{branch}' already exists.")

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
    return bool(result.stdout.strip())
