from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forsa_dev.config import Config
from forsa_dev.operations import run_local


@pytest.fixture()
def run_cfg(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    return Config(
        repo=tmp_path / "repo",
        worktree_dir=tmp_path / "worktrees",
        data_dir=Path("/data/dev"),
        state_dir=state_dir,
        base_url="optbox.example.ts.net",
        docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
        port_range_start=3000,
        port_range_end=3099,
        ttyd_port_range_start=7600,
        ttyd_port_range_end=7699,
    )


def test_run_local_generates_compose_and_runs(run_cfg, tmp_path):
    work_dir = tmp_path / "my-repo"
    work_dir.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        run_local(run_cfg, work_dir)
    compose_file = work_dir / "docker-compose.dev.yml"
    assert compose_file.exists()
    # Called twice: docker compose up, then docker compose down
    assert mock_run.call_count == 2
    up_cmd = mock_run.call_args_list[0][0][0]
    assert "docker" in up_cmd[0]
    assert "up" in up_cmd
    down_cmd = mock_run.call_args_list[1][0][0]
    assert "down" in down_cmd


def test_run_local_allocates_port_in_range(run_cfg, tmp_path):
    work_dir = tmp_path / "my-repo"
    work_dir.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        run_local(run_cfg, work_dir)
    compose_content = (work_dir / "docker-compose.dev.yml").read_text()
    assert "3000" in compose_content
