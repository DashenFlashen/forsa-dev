import json

from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Request

from forsa_dev.caddy import deregister_route, register_route


def test_register_route_success(httpserver: HTTPServer):
    received: list[dict] = []

    def handler(req: Request):
        received.append(json.loads(req.data))
        from werkzeug.wrappers import Response
        return Response("", status=200)

    # Stub the _ensure_server GET — return a valid server so bootstrap is skipped
    httpserver.expect_request(
        "/config/apps/http/servers/srv0",
        method="GET",
    ).respond_with_data('{"listen":[":80"],"routes":[]}', status=200, content_type="application/json")

    httpserver.expect_request(
        "/config/apps/http/servers/srv0/routes/",
        method="POST",
    ).respond_with_handler(handler)

    register_route(
        caddy_admin=httpserver.url_for(""),
        name="ticket-42",
        port=3002,
    )

    assert len(received) == 1
    handlers = received[0]["handle"]
    handler_types = [h["handler"] for h in handlers]
    assert "rewrite" in handler_types
    assert "reverse_proxy" in handler_types
    rewrite = next(h for h in handlers if h["handler"] == "rewrite")
    assert rewrite["strip_path_prefix"] == "/ticket-42"


def test_register_route_bootstraps_server(httpserver: HTTPServer):
    """When srv0 is missing, a minimal server config is created before adding the route."""
    put_called = []
    received: list[dict] = []

    httpserver.expect_request(
        "/config/apps/http/servers/srv0",
        method="GET",
    ).respond_with_data("null", status=200, content_type="application/json")

    def put_handler(req: Request):
        put_called.append(json.loads(req.data))
        from werkzeug.wrappers import Response
        return Response("", status=200)

    httpserver.expect_request(
        "/config/apps/http/servers/srv0",
        method="PUT",
    ).respond_with_handler(put_handler)

    def post_handler(req: Request):
        received.append(json.loads(req.data))
        from werkzeug.wrappers import Response
        return Response("", status=200)

    httpserver.expect_request(
        "/config/apps/http/servers/srv0/routes/",
        method="POST",
    ).respond_with_handler(post_handler)

    register_route(caddy_admin=httpserver.url_for(""), name="ticket-42", port=3002)

    assert len(put_called) == 1
    assert put_called[0] == {"listen": [":80"], "routes": []}
    assert len(received) == 1


def test_deregister_route_success(httpserver: HTTPServer):
    httpserver.expect_request(
        "/id/forsa-ticket-42",
        method="DELETE",
    ).respond_with_data("", status=200)

    deregister_route(
        caddy_admin=httpserver.url_for(""),
        name="ticket-42",
    )
    # No exception raised — success


def test_register_route_unreachable_warns(caplog):
    import logging
    with caplog.at_level(logging.WARNING):
        register_route(
            caddy_admin="http://localhost:19999",  # nothing listening here
            name="ticket-42",
            port=3002,
        )
    assert "Caddy" in caplog.text


def test_deregister_route_unreachable_warns(caplog):
    import logging
    with caplog.at_level(logging.WARNING):
        deregister_route(
            caddy_admin="http://localhost:19999",
            name="ticket-42",
        )
    assert "Caddy" in caplog.text
