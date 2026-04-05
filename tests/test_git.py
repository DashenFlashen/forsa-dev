import getpass
import subprocess
from unittest.mock import MagicMock, patch

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


def test_list_branches_returns_branch_metadata(git_repo, tmp_path):
    subprocess.run(["git", "branch", "old-work"], check=True, capture_output=True, cwd=git_repo)
    subprocess.run(
        ["git", "branch", "feature/cool-thing"], check=True, capture_output=True, cwd=git_repo
    )
    branches = list_branches(git_repo)
    names = [b["name"] for b in branches]
    assert "old-work" in names
    assert "feature/cool-thing" in names
    assert "main" in names  # main is no longer excluded
    for b in branches:
        assert "name" in b
        assert "last_commit" in b
        assert "in_worktree" in b
        assert isinstance(b["in_worktree"], bool)


def test_list_branches_tags_worktree_branches(git_repo, tmp_path):
    subprocess.run(["git", "branch", "in-use"], check=True, capture_output=True, cwd=git_repo)
    subprocess.run(["git", "branch", "available"], check=True, capture_output=True, cwd=git_repo)
    wt = tmp_path / "wt"
    subprocess.run(
        ["git", "worktree", "add", str(wt), "in-use"], check=True, capture_output=True, cwd=git_repo
    )
    branches = list_branches(git_repo)
    by_name = {b["name"]: b for b in branches}
    assert by_name["in-use"]["in_worktree"] is True
    assert by_name["available"]["in_worktree"] is False


def test_list_branches_deduplicates_local_and_remote(git_repo, tmp_path):
    """When a branch exists locally and on a remote, keep the more recent date."""
    # Create a "remote" repo with a branch
    remote = tmp_path / "remote"
    remote.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(remote)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t.com"], check=True, capture_output=True, cwd=remote
    )
    subprocess.run(
        ["git", "config", "user.name", "T"], check=True, capture_output=True, cwd=remote
    )
    (remote / "f.txt").write_text("v1")
    subprocess.run(["git", "add", "."], check=True, capture_output=True, cwd=remote)
    subprocess.run(["git", "commit", "-m", "init"], check=True, capture_output=True, cwd=remote)
    subprocess.run(["git", "checkout", "-b", "shared"], check=True, capture_output=True, cwd=remote)
    (remote / "f.txt").write_text("v2")
    subprocess.run(["git", "add", "."], check=True, capture_output=True, cwd=remote)
    subprocess.run(
        ["git", "commit", "-m", "remote-update"], check=True, capture_output=True, cwd=remote
    )

    # Add as remote and fetch
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote)],
        check=True, capture_output=True, cwd=git_repo,
    )
    subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True, cwd=git_repo)

    # Create a local branch "shared" from an older point (main)
    subprocess.run(["git", "branch", "shared"], check=True, capture_output=True, cwd=git_repo)

    # Get the remote's commit date for comparison
    remote_date_result = subprocess.run(
        ["git", "log", "-1", "--format=%ci", "origin/shared"],
        capture_output=True, text=True, cwd=git_repo,
    )
    remote_commit_date = remote_date_result.stdout.strip()

    branches = list_branches(git_repo)
    names = [b["name"] for b in branches]
    assert names.count("shared") == 1  # deduplicated, not listed twice
    shared = next(b for b in branches if b["name"] == "shared")
    assert shared["last_commit"] == remote_commit_date  # kept the newer remote date


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
    subprocess.run(
        ["git", "checkout", "-b", "feature"],
        check=True, capture_output=True, cwd=git_repo,
    )
    assert current_branch(git_repo) == "feature"


def test_current_branch_returns_head_when_detached(git_repo):
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=git_repo,
    )
    sha = result.stdout.strip()
    subprocess.run(["git", "checkout", sha], check=True, capture_output=True, cwd=git_repo)
    assert current_branch(git_repo) == "HEAD"


def test_current_branch_returns_none_for_invalid_repo(tmp_path):
    assert current_branch(tmp_path) is None


# --- run_as (sudo) tests ---


def test_create_branch_and_worktree_uses_sudo_for_different_user(tmp_path):
    """git commands are prefixed with sudo -u when run_as differs from current user."""
    worktree_path = tmp_path / "worktrees" / "feature-x"
    with patch("forsa_dev.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        create_branch_and_worktree(
            repo=tmp_path / "repo",
            branch="feature-x",
            worktree=worktree_path,
            run_as="otheruser",
        )
    assert mock_run.call_count == 2
    for call in mock_run.call_args_list:
        cmd = call[0][0]
        assert cmd[:3] == ["sudo", "-u", "otheruser"]
        assert "git" in cmd


def test_create_branch_and_worktree_no_sudo_for_same_user(tmp_path):
    """No sudo prefix when run_as matches current user."""
    me = getpass.getuser()
    worktree_path = tmp_path / "worktrees" / "feature-x"
    with patch("forsa_dev.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        create_branch_and_worktree(
            repo=tmp_path / "repo",
            branch="feature-x",
            worktree=worktree_path,
            run_as=me,
        )
    for call in mock_run.call_args_list:
        cmd = call[0][0]
        assert cmd[0] == "git"


def test_create_branch_and_worktree_no_sudo_for_none(git_repo, tmp_path):
    """No sudo prefix when run_as is None (default)."""
    worktree_path = tmp_path / "worktrees" / "feature-nosudo"
    create_branch_and_worktree(
        repo=git_repo,
        branch="feature-nosudo",
        worktree=worktree_path,
    )
    assert worktree_path.exists()


def test_remove_worktree_uses_sudo_for_different_user(tmp_path):
    with patch("forsa_dev.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        remove_worktree(repo=tmp_path, worktree=tmp_path / "wt", run_as="otheruser")
    cmd = mock_run.call_args[0][0]
    assert cmd[:3] == ["sudo", "-u", "otheruser"]


def test_delete_branch_uses_sudo_for_different_user(tmp_path):
    with patch("forsa_dev.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        delete_branch(repo=tmp_path, branch="feature-x", run_as="otheruser")
    cmd = mock_run.call_args[0][0]
    assert cmd[:3] == ["sudo", "-u", "otheruser"]


def test_create_worktree_from_branch_uses_sudo_for_different_user(tmp_path):
    worktree_path = tmp_path / "worktrees" / "existing"
    with patch("forsa_dev.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        create_worktree_from_branch(
            repo=tmp_path / "repo",
            branch="existing",
            worktree=worktree_path,
            run_as="otheruser",
        )
    cmd = mock_run.call_args[0][0]
    assert cmd[:3] == ["sudo", "-u", "otheruser"]
