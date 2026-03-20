import subprocess

import pytest

from forsa_dev.git import (
    branch_is_pushed,
    create_branch_and_worktree,
    create_worktree_from_branch,
    current_branch,
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
    subprocess.run(
        ["git", "branch", "feature/cool-thing"], check=True, capture_output=True, cwd=git_repo
    )
    branches = list_branches(git_repo)
    assert "old-work" in branches
    assert "feature/cool-thing" in branches
    assert "main" not in branches


def test_list_branches_excludes_worktree_branches(git_repo, tmp_path):
    subprocess.run(["git", "branch", "in-use"], check=True, capture_output=True, cwd=git_repo)
    subprocess.run(["git", "branch", "available"], check=True, capture_output=True, cwd=git_repo)
    wt = tmp_path / "wt"
    subprocess.run(
        ["git", "worktree", "add", str(wt), "in-use"], check=True, capture_output=True, cwd=git_repo
    )
    branches = list_branches(git_repo)
    assert "in-use" not in branches
    assert "available" in branches


def test_create_worktree_from_branch(git_repo, tmp_path):
    subprocess.run(["git", "branch", "existing"], check=True, capture_output=True, cwd=git_repo)
    wt = tmp_path / "worktrees" / "existing"
    create_worktree_from_branch(repo=git_repo, branch="existing", worktree=wt)
    assert wt.exists()
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, cwd=wt,
    )
    assert result.stdout.strip() == "existing"


def test_create_worktree_from_branch_fails_for_missing_branch(git_repo, tmp_path):
    wt = tmp_path / "worktrees" / "no-such"
    with pytest.raises(RuntimeError, match="git worktree add failed"):
        create_worktree_from_branch(repo=git_repo, branch="no-such-branch", worktree=wt)
    assert not wt.exists()


def test_current_branch_returns_branch_name(git_repo):
    assert current_branch(git_repo) == "main"


def test_current_branch_after_checkout(git_repo):
    subprocess.run(["git", "checkout", "-b", "feature"], check=True, capture_output=True, cwd=git_repo)
    assert current_branch(git_repo) == "feature"


def test_current_branch_returns_head_when_detached(git_repo):
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=git_repo)
    sha = result.stdout.strip()
    subprocess.run(["git", "checkout", sha], check=True, capture_output=True, cwd=git_repo)
    assert current_branch(git_repo) == "HEAD"


def test_current_branch_returns_none_for_invalid_repo(tmp_path):
    assert current_branch(tmp_path) is None
