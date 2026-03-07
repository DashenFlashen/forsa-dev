from __future__ import annotations
import logging

import requests

logger = logging.getLogger(__name__)


def _route_id(name: str) -> str:
    return f"forsa-{name}"


def register_route(caddy_admin: str, name: str, port: int) -> None:
    """Add a path-based reverse proxy route to Caddy. Warns if Caddy is unreachable."""
    route = {
        "@id": _route_id(name),
        "match": [{"path": [f"/{name}/*"]}],
        "handle": [
            {"handler": "rewrite", "strip_path_prefix": f"/{name}"},
            {
                "handler": "reverse_proxy",
                "upstreams": [{"dial": f"localhost:{port}"}],
            },
        ],
    }
    try:
        admin_url = caddy_admin.rstrip("/")
        resp = requests.post(
            f"{admin_url}/config/apps/http/servers/srv0/routes/",
            json=route,
            timeout=5,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Caddy registration failed (continuing without it): %s", exc)


def deregister_route(caddy_admin: str, name: str) -> None:
    """Remove a route from Caddy by ID. Warns if Caddy is unreachable."""
    try:
        admin_url = caddy_admin.rstrip("/")
        resp = requests.delete(
            f"{admin_url}/id/{_route_id(name)}",
            timeout=5,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Caddy deregistration failed (continuing without it): %s", exc)
