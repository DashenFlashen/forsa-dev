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
