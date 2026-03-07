import subprocess

import pytest


@pytest.fixture()
def git_repo(tmp_path):
    """A real git repo with one commit on main, ready for worktrees."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], check=True, capture_output=True, cwd=repo
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], check=True, capture_output=True, cwd=repo
    )
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], check=True, capture_output=True, cwd=repo)
    subprocess.run(["git", "commit", "-m", "init"], check=True, capture_output=True, cwd=repo)
    return repo
