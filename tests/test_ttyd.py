from __future__ import annotations

import signal
from unittest.mock import MagicMock, patch

from forsa_dev.ttyd import start_ttyd, stop_ttyd, ttyd_is_alive


def test_start_ttyd_launches_process_and_returns_pid():
    mock_proc = MagicMock()
    mock_proc.pid = 42
    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        pid = start_ttyd(7682, "anders-ticket-42")
    assert pid == 42
    mock_popen.assert_called_once()
    cmd = mock_popen.call_args[0][0]
    assert "ttyd" in cmd
    assert "-W" in cmd
    assert "-p" in cmd
    assert "7682" in cmd or 7682 in cmd
    assert "tmux" in cmd
    assert "anders-ticket-42" in cmd


def test_stop_ttyd_sends_sigterm():
    with patch("os.kill") as mock_kill:
        stop_ttyd(42)
    mock_kill.assert_called_once_with(42, signal.SIGTERM)


def test_stop_ttyd_ignores_process_not_found():
    with patch("os.kill", side_effect=ProcessLookupError):
        stop_ttyd(99999)  # should not raise


def test_ttyd_is_alive_returns_true_for_live_process():
    with patch("os.kill", return_value=None):
        assert ttyd_is_alive(42) is True


def test_ttyd_is_alive_returns_false_for_dead_process():
    with patch("os.kill", side_effect=ProcessLookupError):
        assert ttyd_is_alive(42) is False


def test_ttyd_is_alive_returns_true_for_unowned_process():
    """PermissionError means the process exists but we can't signal it — still alive."""
    with patch("os.kill", side_effect=PermissionError):
        assert ttyd_is_alive(42) is True
