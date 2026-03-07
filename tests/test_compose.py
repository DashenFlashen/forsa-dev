from pathlib import Path
import yaml
import pytest
from forsa_dev.compose import generate_compose


@pytest.fixture()
def compose_content(tmp_path):
    worktree = tmp_path / "ticket-42"
    worktree.mkdir()
    generate_compose(
        worktree=worktree,
        user="anders",
        name="ticket-42",
        port=3002,
        data_dir=Path("/data/dev"),
        docker_image="forsa:latest",
        gurobi_lic=Path("/opt/gurobi/gurobi.lic"),
    )
    compose_file = worktree / "docker-compose.dev.yml"
    assert compose_file.exists()
    with compose_file.open() as f:
        return yaml.safe_load(f)


def test_compose_port(compose_content):
    ports = compose_content["services"]["forsa"]["ports"]
    assert "3002:8000" in ports


def test_compose_image(compose_content):
    assert compose_content["services"]["forsa"]["image"] == "forsa:latest"


def test_compose_container_name(compose_content):
    assert compose_content["services"]["forsa"]["container_name"] == "forsa-anders-ticket-42"


def test_compose_source_volume(compose_content):
    volumes = compose_content["services"]["forsa"]["volumes"]
    assert "./src:/app/src" in volumes


def test_compose_data_volume(compose_content):
    volumes = compose_content["services"]["forsa"]["volumes"]
    assert "/data/dev:/app/data" in volumes


def test_compose_gurobi_volume(compose_content):
    volumes = compose_content["services"]["forsa"]["volumes"]
    assert "/opt/gurobi/gurobi.lic:/opt/gurobi/gurobi.lic" in volumes


def test_compose_required_env_vars(compose_content):
    env = compose_content["services"]["forsa"]["environment"]
    assert env["FORSA_DATA_PATH"] == "/app/data"
    assert env["FORSA_WEBSERVER_PORT"] == 8000
    assert env["JULIA_PROJECT"] == "/app/src/julia/forsa-env"
    assert env["GRB_LICENSE_FILE"] == "/opt/gurobi/gurobi.lic"


def test_compose_command(compose_content):
    command = compose_content["services"]["forsa"]["command"]
    full_cmd = " ".join(command)
    assert "pip install" in full_cmd
    assert "forsa.main" in full_cmd
