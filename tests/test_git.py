import subprocess

import pytest

from forsa_dev.git import (
    branch_is_pushed,
    create_branch_and_worktree,
    delete_branch,
    list_branches,
    remove_worktree,
)


def test_create_branch_and_worktree(git_repo, tmp_path):
    worktree_path = tmp_path / "worktrees" / "feature-x"
    create_branch_and_worktree(
        repo=git_repo,
        branch="feature-x",
        worktree=worktree_path,
        from_branch="main",
    )
    assert worktree_path.exists()
    result = subprocess.run(
        ["git", "branch", "--list", "feature-x"],
        capture_output=True, text=True, cwd=git_repo
    )
    assert "feature-x" in result.stdout


def test_create_branch_fails_if_branch_exists(git_repo, tmp_path):
    worktree_path = tmp_path / "worktrees" / "main-copy"
    with pytest.raises(RuntimeError, match="already exists"):
        create_branch_and_worktree(
            repo=git_repo,
            branch="main",
            worktree=worktree_path,
            from_branch="main",
        )


def test_remove_worktree(git_repo, tmp_path):
    worktree_path = tmp_path / "worktrees" / "feature-y"
    create_branch_and_worktree(git_repo, "feature-y", worktree_path, "main")
    assert worktree_path.exists()
    remove_worktree(repo=git_repo, worktree=worktree_path)
    assert not worktree_path.exists()


def test_branch_is_pushed_false_for_local_branch(git_repo, tmp_path):
    worktree_path = tmp_path / "worktrees" / "feature-z"
    create_branch_and_worktree(git_repo, "feature-z", worktree_path, "main")
    assert not branch_is_pushed(repo=git_repo, branch="feature-z")


def test_delete_branch(git_repo, tmp_path):
    worktree_path = tmp_path / "worktrees" / "feature-del"
    create_branch_and_worktree(git_repo, "feature-del", worktree_path, "main")
    remove_worktree(git_repo, worktree_path)
    delete_branch(git_repo, "feature-del")
    result = subprocess.run(
        ["git", "branch", "--list", "feature-del"],
        capture_output=True, text=True, cwd=git_repo
    )
    assert result.stdout.strip() == ""


def test_delete_branch_force(git_repo, tmp_path):
    worktree_path = tmp_path / "worktrees" / "feature-force"
    create_branch_and_worktree(git_repo, "feature-force", worktree_path, "main")
    remove_worktree(git_repo, worktree_path)
    delete_branch(git_repo, "feature-force", force=True)
    result = subprocess.run(
        ["git", "branch", "--list", "feature-force"],
        capture_output=True, text=True, cwd=git_repo
    )
    assert result.stdout.strip() == ""


def test_list_branches_returns_available_branches(git_repo, tmp_path):
    subprocess.run(["git", "branch", "old-work"], check=True, capture_output=True, cwd=git_repo)
    subprocess.run(["git", "branch", "feature/cool-thing"], check=True, capture_output=True, cwd=git_repo)
    branches = list_branches(git_repo)
    assert "old-work" in branches
    assert "feature/cool-thing" in branches
    assert "main" not in branches


def test_list_branches_excludes_worktree_branches(git_repo, tmp_path):
    subprocess.run(["git", "branch", "in-use"], check=True, capture_output=True, cwd=git_repo)
    subprocess.run(["git", "branch", "available"], check=True, capture_output=True, cwd=git_repo)
    wt = tmp_path / "wt"
    subprocess.run(["git", "worktree", "add", str(wt), "in-use"], check=True, capture_output=True, cwd=git_repo)
    branches = list_branches(git_repo)
    assert "in-use" not in branches
    assert "available" in branches
