from __future__ import annotations
import socket
from dataclasses import dataclass


@dataclass
class Status:
    tmux: str   # "active" | "missing"
    server: str  # "running" | "stopped"


def check_status(tmux_exists: bool, port_open: bool) -> Status:
    return Status(
        tmux="active" if tmux_exists else "missing",
        server="running" if port_open else "stopped",
    )


def port_is_open(port: int, host: str = "localhost") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0
