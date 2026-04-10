from __future__ import annotations

import getpass
import os
import subprocess
from pathlib import Path


def _sudo_prefix(run_as: str | None) -> list[str]:
    """Return a sudo prefix if run_as differs from the current user."""
    if run_as and run_as != getpass.getuser():
        return ["sudo", "-u", run_as]
    return []


def create_session(
    session: str, cwd: Path, command: str | None = None, run_as: str | None = None,
) -> None:
    """Create a detached tmux session. Raises RuntimeError if it fails."""
    prefix = _sudo_prefix(run_as)
    cmd = [*prefix, "tmux", "new-session", "-d", "-s", session, "-c", str(cwd)]
    if command:
        cmd.append(command)
    elif prefix:
        # No command given — start a login shell as the target user.
        cmd.append(f"sudo -u {run_as} -i bash")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"tmux new-session failed: {result.stderr}")


def kill_session(session: str, run_as: str | None = None) -> None:
    """Kill a tmux session. Raises RuntimeError if it fails."""
    result = subprocess.run(
        [*_sudo_prefix(run_as), "tmux", "kill-session", "-t", session],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux kill-session failed: {result.stderr}")


def session_status(session: str, run_as: str | None = None) -> str:
    """Return "active", "detached", or "missing" for the given tmux session."""
    cmd = [
        *_sudo_prefix(run_as), "tmux", "list-sessions",
        "-F", "#{session_name} #{session_attached}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return "missing"
    for line in result.stdout.splitlines():
        parts = line.split()
        if parts[0] == session:
            return "active" if int(parts[1]) > 0 else "detached"
    return "missing"


def session_exists(session: str, run_as: str | None = None) -> bool:
    """Return True if the tmux session exists."""
    return session_status(session, run_as=run_as) != "missing"


ALLOWED_KEYS = frozenset({
    "Escape", "Tab", "Up", "Down", "Left", "Right",
    "C-c", "PPage", "NPage",
})


def send_keys(session: str, key: str, run_as: str | None = None) -> None:
    """Send a key to the active pane of a tmux session.

    Only keys in ALLOWED_KEYS are accepted to prevent injection.
    Raises ValueError for disallowed keys, RuntimeError if the session is missing.
    """
    if key not in ALLOWED_KEYS:
        raise ValueError(f"Key not allowed: {key!r}")
    result = subprocess.run(
        [*_sudo_prefix(run_as), "tmux", "send-keys", "-t", session, key],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux send-keys failed: {result.stderr}")


def send_text(session: str, text: str, run_as: str | None = None) -> None:
    """Send literal text to a tmux session and press Enter to submit.

    Raises RuntimeError if the session is missing or the command fails.
    """
    prefix = _sudo_prefix(run_as)
    result = subprocess.run(
        [*prefix, "tmux", "send-keys", "-t", session, "-l", text],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux send-keys failed: {result.stderr}")
    result = subprocess.run(
        [*prefix, "tmux", "send-keys", "-t", session, "Enter"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux send-keys Enter failed: {result.stderr}")


def attach_session(session: str) -> None:
    """Attach to a tmux session. Replaces the current process.
    Uses switch-client if already inside tmux, attach-session otherwise."""
    if os.environ.get("TMUX"):
        os.execvp("tmux", ["tmux", "switch-client", "-t", session])
    else:
        os.execvp("tmux", ["tmux", "attach-session", "-t", session])
