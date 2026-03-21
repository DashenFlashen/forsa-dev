from __future__ import annotations

import getpass
import os
import signal
import subprocess


def _sudo_prefix(run_as: str | None) -> list[str]:
    """Return a sudo prefix if run_as differs from the current user."""
    if run_as and run_as != getpass.getuser():
        return ["sudo", "-u", run_as]
    return []


def start_ttyd(port: int, session: str, run_as: str | None = None) -> int:
    """Start a ttyd process for the given tmux session. Returns the PID."""
    # ttyd always runs as the current user, but attaches to tmux via sudo
    # when the session belongs to a different user.
    tmux_cmd = [*_sudo_prefix(run_as), "tmux", "attach", "-t", session]
    cmd = ["ttyd", "-W", "-p", str(port), *tmux_cmd]
    proc = subprocess.Popen(
        cmd,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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
