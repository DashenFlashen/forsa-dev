import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forsa_dev.tmux import create_session, kill_session, session_exists, session_status

pytestmark = pytest.mark.skipif(
    subprocess.run(["which", "tmux"], capture_output=True).returncode != 0,
    reason="tmux not installed",
)

SESSION = "forsa-dev-test-session"


@pytest.fixture(autouse=True)
def cleanup_session():
    yield
    subprocess.run(["tmux", "kill-session", "-t", SESSION], capture_output=True)


def test_create_and_detect_session(tmp_path):
    create_session(session=SESSION, cwd=tmp_path)
    assert session_exists(SESSION)


def test_kill_session(tmp_path):
    create_session(session=SESSION, cwd=tmp_path)
    kill_session(SESSION)
    assert not session_exists(SESSION)


def test_session_exists_false_when_missing():
    assert not session_exists("forsa-dev-nonexistent-xyz")


def test_session_status_detached(tmp_path):
    create_session(session=SESSION, cwd=tmp_path)
    # Session created with -d (detached), so status should be "detached"
    assert session_status(SESSION) == "detached"


def test_session_status_missing():
    assert session_status("forsa-dev-nonexistent-xyz") == "missing"


def test_create_session_with_command():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        create_session("my-session", Path("/workdir"), command="claude --resume foo || bash")
    cmd = mock_run.call_args[0][0]
    assert "claude --resume foo || bash" in cmd


def test_create_session_without_command_has_no_trailing_command():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        create_session("my-session", Path("/workdir"))
    cmd = mock_run.call_args[0][0]
    assert "claude" not in " ".join(str(c) for c in cmd)
    assert "bash" not in " ".join(str(c) for c in cmd)
