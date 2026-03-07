from pathlib import Path

from typer.testing import CliRunner

from forsa_dev.cli import app
from forsa_dev.config import load_config

runner = CliRunner()


def test_init_writes_config(tmp_path):
    config_path = tmp_path / "config.toml"
    repo = tmp_path / "forsa"
    worktree_dir = tmp_path / "worktrees"
    inputs = "\n".join([
        str(repo),
        str(worktree_dir),
        "/data/dev",
        "/var/lib/forsa-dev",
        "optbox.example.ts.net",
        "alvbyran/forsa:latest",
        "/opt/gurobi/gurobi.lic",
        "3000",
        "3099",
        "8080",
    ]) + "\n"

    result = runner.invoke(app, ["init", "--config", str(config_path)], input=inputs)

    assert result.exit_code == 0, result.output
    cfg = load_config(config_path)
    assert cfg.repo == repo
    assert cfg.worktree_dir == worktree_dir
    assert cfg.data_dir == Path("/data/dev")
    assert cfg.state_dir == Path("/var/lib/forsa-dev")
    assert cfg.base_url == "optbox.example.ts.net"
    assert cfg.docker_image == "alvbyran/forsa:latest"
    assert cfg.gurobi_lic == Path("/opt/gurobi/gurobi.lic")
    assert cfg.port_range_start == 3000
    assert cfg.port_range_end == 3099
    assert cfg.dashboard_port == 8080
