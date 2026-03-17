from __future__ import annotations

import os
import signal
import subprocess


def start_ttyd(port: int, session: str) -> int:
    """Start a ttyd process for the given tmux session. Returns the PID."""
    proc = subprocess.Popen(
        ["ttyd", "-W", "-p", str(port), "tmux", "attach", "-t", session]
    )
    return proc.pid


def stop_ttyd(pid: int) -> None:
    """Send SIGTERM to a ttyd process. Ignores errors if already gone."""
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def ttyd_is_alive(pid: int) -> bool:
    """Return True if the process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True  # process exists but we can't signal it
    except ProcessLookupError:
        return False


def ttyd_port_is_open(port: int) -> bool:
    """Return True if something is listening on the given port."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0
