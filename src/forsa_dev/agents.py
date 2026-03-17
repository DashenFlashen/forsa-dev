from __future__ import annotations

from pathlib import Path

from forsa_dev import tmux, ttyd

AGENTS = [
    {
        "name": "root-claude",
        "label": "Root Claude",
        "description": "General purpose",
        "session": "claude-root",
        "cwd": Path.home(),
        "command": "claude --effort max",
    },
    {
        "name": "forsa-dev-claude",
        "label": "forsa-dev Claude",
        "description": "Dashboard & CLI",
        "session": "claude-forsa-dev",
        "cwd": Path.home() / "repos" / "forsa-dev",
        "command": "claude --effort max",
    },
]


def ensure_agents(ttyd_ports: dict[str, int]) -> dict[str, int | None]:
    """Ensure agent tmux sessions and ttyd processes are running.

    Returns a dict mapping session name to ttyd PID (None if already running).
    """
    pids: dict[str, int | None] = {}
    for agent in AGENTS:
        session = agent["session"]
        if not tmux.session_exists(session):
            tmux.create_session(session, agent["cwd"], agent["command"])

        port = ttyd_ports[session]
        if ttyd.ttyd_port_is_open(port):
            pids[session] = None
        else:
            pids[session] = ttyd.start_ttyd(port, session)
    return pids


def agent_status(ttyd_ports: dict[str, int]) -> list[dict]:
    """Return current status for each agent."""
    result = []
    for agent in AGENTS:
        session = agent["session"]
        port = ttyd_ports[session]
        result.append({
            "name": agent["name"],
            "label": agent["label"],
            "description": agent["description"],
            "cwd": str(agent["cwd"]),
            "ttyd_port": port,
            "tmux": tmux.session_status(session),
            "ttyd": "alive" if ttyd.ttyd_port_is_open(port) else "dead",
        })
    return result
