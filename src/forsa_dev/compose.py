from __future__ import annotations
from pathlib import Path


_TEMPLATE = """\
services:
  forsa:
    image: {docker_image}
    container_name: forsa-{user}-{name}
    ports:
      - "{port}:8000"
    volumes:
      - ./src:/app/src
      - {data_dir}:/app/data
      - ./logs:/app/src/python/webserver/.local/webserver_logs
      - {gurobi_lic}:/opt/gurobi/gurobi.lic
    environment:
      FORSA_DATA_PATH: /app/data
      FORSA_WEBSERVER_PATH: /app/src/python/webserver
      FORSA_OPTIMIZER_PATH: /app/src/julia
      JULIA_PROJECT: /app/src/julia/forsa-env
      FORSA_WEBSERVER_PORT: 8000
      FORSA_JULIA_BACKEND: juliacall
      FORSA_BIDDING_ZONE_PATH: /app/data/elomraden.xlsx
      FORSA_SPOT_PRICE_PATH: /app/data/elspot_prices.xlsx
      PYTHON: /usr/bin/python3
      GRB_LICENSE_FILE: /opt/gurobi/gurobi.lic
    command: ["bash", "-c", "cd /app/src/python/webserver && pip install --no-deps --break-system-packages -e . && python3 -m forsa.main"]
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/ready')"]
      interval: 10s
      timeout: 5s
      start_period: 120s
      retries: 3
    restart: "no"
"""


def generate_compose(
    worktree: Path,
    user: str,
    name: str,
    port: int,
    data_dir: Path,
    docker_image: str,
    gurobi_lic: Path,
) -> Path:
    """Write docker-compose.dev.yml into the worktree. Returns the file path."""
    content = _TEMPLATE.format(
        docker_image=docker_image,
        user=user,
        name=name,
        port=port,
        data_dir=data_dir,
        gurobi_lic=gurobi_lic,
    )
    compose_file = worktree / "docker-compose.dev.yml"
    compose_file.write_text(content)
    return compose_file
