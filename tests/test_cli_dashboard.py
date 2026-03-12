from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from forsa_dev.cli import app

runner = CliRunner()


def test_dashboard_calls_discover_users():
    with patch("forsa_dev.dashboard.server.discover_users") as mock_discover, \
         patch("forsa_dev.dashboard.server.create_app") as mock_create_app, \
         patch("uvicorn.run"):
        mock_discover.return_value = {"alice": MagicMock()}
        mock_create_app.return_value = MagicMock()
        result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 0, result.output
    mock_discover.assert_called_once()
    mock_create_app.assert_called_once_with(mock_discover.return_value)


def test_dashboard_exits_when_no_users_found():
    with patch("forsa_dev.dashboard.server.discover_users", return_value={}):
        result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 1
    assert "no users found" in result.output


def test_dashboard_port_flag_overrides_default():
    with patch("forsa_dev.dashboard.server.discover_users") as mock_discover, \
         patch("forsa_dev.dashboard.server.create_app") as mock_create_app, \
         patch("uvicorn.run") as mock_run:
        mock_discover.return_value = {"alice": MagicMock()}
        mock_create_app.return_value = MagicMock()
        result = runner.invoke(app, ["dashboard", "--port", "9090"])
    assert result.exit_code == 0, result.output
    _, kwargs = mock_run.call_args
    assert kwargs["port"] == 9090


def test_dashboard_default_port_from_config():
    mock_cfg = MagicMock()
    mock_cfg.dashboard_port = 80
    with patch("forsa_dev.dashboard.server.discover_users") as mock_discover, \
         patch("forsa_dev.dashboard.server.create_app") as mock_create_app, \
         patch("uvicorn.run") as mock_run:
        mock_discover.return_value = {"alice": mock_cfg}
        mock_create_app.return_value = MagicMock()
        result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 0, result.output
    _, kwargs = mock_run.call_args
    assert kwargs["port"] == 80
