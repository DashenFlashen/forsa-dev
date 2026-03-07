import pytest
from pytest_httpserver import HTTPServer
from forsa_dev.caddy import register_route, deregister_route


def test_register_route_success(httpserver: HTTPServer):
    httpserver.expect_request(
        "/config/apps/http/servers/srv0/routes/",
        method="POST",
    ).respond_with_data("", status=200)

    register_route(
        caddy_admin=httpserver.url_for(""),
        name="ticket-42",
        port=3002,
    )
    # No exception raised — success


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
