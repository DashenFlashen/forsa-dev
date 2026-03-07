from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass
class Status:
    tmux: str   # "active" | "detached" | "missing"
    server: str  # "running" | "crashed" | "stopped"


def check_status(tmux_status: str, served: bool, port_open: bool) -> Status:
    if served and port_open:
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
