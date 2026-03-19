from __future__ import annotations

import os
import subprocess
from pathlib import Path


def create_session(session: str, cwd: Path, command: str | None = None) -> None:
    """Create a detached tmux session. Raises RuntimeError if it fails."""
    cmd = ["tmux", "new-session", "-d", "-s", session, "-c", str(cwd)]
    if command:
        cmd.append(command)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"tmux new-session failed: {result.stderr}")


def kill_session(session: str) -> None:
    """Kill a tmux session. Raises RuntimeError if it fails."""
    result = subprocess.run(
        ["tmux", "kill-session", "-t", session],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux kill-session failed: {result.stderr}")


def session_status(session: str) -> str:
    """Return "active", "detached", or "missing" for the given tmux session."""
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name} #{session_attached}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "missing"
    for line in result.stdout.splitlines():
        parts = line.split()
        if parts[0] == session:
            return "active" if int(parts[1]) > 0 else "detached"
    return "missing"


def session_exists(session: str) -> bool:
    """Return True if the tmux session exists."""
    return session_status(session) != "missing"


ALLOWED_KEYS = frozenset({
    "Escape", "Tab", "Up", "Down", "Left", "Right",
    "C-c", "PPage", "NPage",
})


def send_keys(session: str, key: str) -> None:
    """Send a key to the active pane of a tmux session.

    Only keys in ALLOWED_KEYS are accepted to prevent injection.
    Raises ValueError for disallowed keys, RuntimeError if the session is missing.
    """
    if key not in ALLOWED_KEYS:
        raise ValueError(f"Key not allowed: {key!r}")
    result = subprocess.run(
        ["tmux", "send-keys", "-t", session, key],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux send-keys failed: {result.stderr}")


def attach_session(session: str) -> None:
    """Attach to a tmux session. Replaces the current process.
    Uses switch-client if already inside tmux, attach-session otherwise."""
    if os.environ.get("TMUX"):
        os.execvp("tmux", ["tmux", "switch-client", "-t", session])
    else:
        os.execvp("tmux", ["tmux", "attach-session", "-t", session])
