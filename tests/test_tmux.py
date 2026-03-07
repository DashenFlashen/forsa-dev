import subprocess
import pytest
from forsa_dev.tmux import create_session, kill_session, session_exists


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
