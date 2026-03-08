from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from forsa_dev.cli import app

runner = CliRunner()


def _make_config(tmp_path, dashboard_port=8080):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f'repo = "{tmp_path}"\n'
        f'worktree_dir = "{tmp_path}"\n'
        'data_dir = "/data/dev"\n'
        f'state_dir = "{tmp_path}"\n'
        'base_url = "localhost"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\n"
        "port_range_end = 3099\n"
        f"dashboard_port = {dashboard_port}\n"
    )
    return cfg_file


def test_dashboard_starts_uvicorn_on_config_port(tmp_path):
    cfg_file = _make_config(tmp_path, dashboard_port=8080)
    mock_app = MagicMock()
    with patch("forsa_dev.dashboard.server.create_app", return_value=mock_app), \
         patch("uvicorn.run") as mock_run:
        result = runner.invoke(app, ["dashboard", "--config", str(cfg_file)])
    assert result.exit_code == 0, result.output
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert kwargs["port"] == 8080


def test_dashboard_port_flag_overrides_config(tmp_path):
    cfg_file = _make_config(tmp_path, dashboard_port=8080)
    mock_app = MagicMock()
    with patch("forsa_dev.dashboard.server.create_app", return_value=mock_app), \
         patch("uvicorn.run") as mock_run:
        result = runner.invoke(app, ["dashboard", "--config", str(cfg_file), "--port", "9090"])
    assert result.exit_code == 0, result.output
    args, kwargs = mock_run.call_args
    assert kwargs["port"] == 9090
