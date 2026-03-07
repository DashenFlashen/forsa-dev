from __future__ import annotations
import fcntl
from pathlib import Path

from forsa_dev.state import list_states


def allocate_port(state_dir: Path, start: int, end: int) -> int:
    """Atomically allocate the lowest free port in [start, end] inclusive."""
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / ".port.lock"
    with lock_path.open("a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            used = {env.port for env in list_states(state_dir)}
            for port in range(start, end + 1):
                if port not in used:
                    return port
            raise RuntimeError(f"No free ports in range {start}-{end}.")
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
