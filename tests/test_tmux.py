import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forsa_dev.tmux import (
    create_session,
    kill_session,
    send_text,
    session_exists,
    session_status,
)

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


def test_send_text_delivers_to_session(tmp_path):
    """send_text sends literal text followed by Enter to a real tmux session."""
    create_session(session=SESSION, cwd=tmp_path, command="cat")
    time.sleep(0.3)
    send_text(SESSION, "hello world")
    time.sleep(0.3)
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", SESSION, "-p"],
        capture_output=True, text=True,
    )
    assert "hello world" in result.stdout


def test_send_text_constructs_correct_commands():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        send_text("my-session", "test prompt")
    assert mock_run.call_count == 2
    first_cmd = mock_run.call_args_list[0][0][0]
    assert "-l" in first_cmd
    assert "test prompt" in first_cmd
    second_cmd = mock_run.call_args_list[1][0][0]
    assert "Enter" in second_cmd


def test_send_text_raises_on_missing_session():
    with pytest.raises(RuntimeError):
        send_text("forsa-dev-nonexistent-xyz", "hello")
