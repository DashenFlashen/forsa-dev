from pathlib import Path

import pytest

from forsa_dev.config import Config, load_config, save_config


def test_load_config_from_file(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'repo = "/home/anders/forsa"\n'
        'worktree_dir = "/home/anders/worktrees"\n'
        'data_dir = "/data/dev"\n'
        'state_dir = "/var/lib/forsa-dev"\n'
        'base_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\ngurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\n"
        "port_range_end = 3099\n"
    )
    config = load_config(config_file)
    assert config.repo == Path("/home/anders/forsa")
    assert config.worktree_dir == Path("/home/anders/worktrees")
    assert config.port_range_start == 3000
    assert config.port_range_end == 3099
    assert config.dashboard_port == 8080


def test_load_config_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.toml")


def test_save_config_roundtrip(tmp_path):
    config_file = tmp_path / "config.toml"
    config = Config(
        repo=Path("/home/anders/forsa"),
        worktree_dir=Path("/home/anders/worktrees"),
        data_dir=Path("/data/dev"),
        state_dir=Path("/tmp/forsa-dev"),
        base_url="optbox.example.ts.net",
        docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000,
        port_range_end=3099,
    )
    save_config(config, config_file)
    loaded = load_config(config_file)
    assert loaded == config
    assert loaded.dashboard_port == 8080


def test_load_config_without_dashboard_port_defaults_to_8080(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'repo = "/home/anders/forsa"\n'
        'worktree_dir = "/home/anders/worktrees"\n'
        'data_dir = "/data/dev"\n'
        'state_dir = "/var/lib/forsa-dev"\n'
        'base_url = "optbox.example.ts.net"\n'
        'docker_image = "forsa:latest"\n'
        'gurobi_lic = "/opt/gurobi/gurobi.lic"\n'
        "port_range_start = 3000\n"
        "port_range_end = 3099\n"
    )
    config = load_config(config_file)
    assert config.dashboard_port == 8080


def test_save_config_roundtrip_nondefault_dashboard_port(tmp_path):
    config_file = tmp_path / "config.toml"
    config = Config(
        repo=Path("/home/anders/forsa"),
        worktree_dir=Path("/home/anders/worktrees"),
        data_dir=Path("/data/dev"),
        state_dir=Path("/tmp/forsa-dev"),
        base_url="optbox.example.ts.net",
        docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000,
        port_range_end=3099,
        dashboard_port=9090,
    )
    save_config(config, config_file)
    loaded = load_config(config_file)
    assert loaded.dashboard_port == 9090


def test_load_config_without_ttyd_range_uses_defaults(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        'repo = "/r"\nworktree_dir = "/w"\ndata_dir = "/d"\n'
        'state_dir = "/s"\nbase_url = "localhost"\n'
        'docker_image = "img"\ngurobi_lic = "/g"\n'
        'port_range_start = 3000\nport_range_end = 3099\n'
    )
    cfg = load_config(cfg_file)
    assert cfg.ttyd_port_range_start == 7600
    assert cfg.ttyd_port_range_end == 7699


def test_config_ttyd_range_roundtrip(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg = Config(
        repo=Path("/r"), worktree_dir=Path("/w"), data_dir=Path("/d"),
        state_dir=Path("/s"), base_url="localhost",
        docker_image="img", gurobi_lic=Path("/g"),
        port_range_start=3000, port_range_end=3099,
        ttyd_port_range_start=7600, ttyd_port_range_end=7699,
    )
    save_config(cfg, cfg_file)
    loaded = load_config(cfg_file)
    assert loaded.ttyd_port_range_start == 7600
    assert loaded.ttyd_port_range_end == 7699
