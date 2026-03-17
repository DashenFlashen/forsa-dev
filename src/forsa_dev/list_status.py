from __future__ import annotations

import socket
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Status:
    tmux: str   # "active" | "detached" | "missing"
    server: str  # "running" | "crashed" | "stopped"


def check_status(tmux_status: str, served: bool, port_open: bool) -> Status:
    if port_open:
        server = "running"
    elif served and not port_open:
        server = "crashed"
    else:
        server = "stopped"
    return Status(tmux=tmux_status, server=server)


def port_is_open(port: int, host: str = "localhost") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def format_uptime(served_at: datetime | None) -> str:
    if served_at is None:
        return "-"
    delta = datetime.now(tz=timezone.utc) - served_at
    seconds = int(delta.total_seconds())
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    return f"{seconds // 86400}d {(seconds % 86400) // 3600}h"
