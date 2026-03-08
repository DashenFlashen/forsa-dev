from __future__ import annotations

import fcntl
from contextlib import contextmanager
from pathlib import Path

from forsa_dev.state import list_states


def _used_ports(state_dir: Path) -> set[int]:
    used = set()
    for env in list_states(state_dir):
        used.add(env.port)
        if env.ttyd_port is not None:
            used.add(env.ttyd_port)
    return used


@contextmanager
def allocate_ports(state_dir: Path, *ranges: tuple[int, int]):
    """Atomically allocate one port from each range under a single lock.

    Yields a list of allocated ports in the same order as the input ranges.
    The lock is held until the with-block exits so callers can write state
    before any concurrent allocation sees the new ports as free.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / ".port.lock"
    with lock_path.open("a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            used = _used_ports(state_dir)
            allocated = []
            for start, end in ranges:
                port = next(
                    (p for p in range(start, end + 1) if p not in used), None
                )
                if port is None:
                    raise RuntimeError(f"No free ports in range {start}-{end}.")
                used.add(port)
                allocated.append(port)
            yield allocated
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


@contextmanager
def allocate_port(state_dir: Path, start: int, end: int):
    """Convenience wrapper: allocate a single port from [start, end]."""
    with allocate_ports(state_dir, (start, end)) as ports:
        yield ports[0]
