from __future__ import annotations
import getpass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import typer

from forsa_dev import caddy, git, tmux
from forsa_dev.compose import generate_compose
from forsa_dev.config import DEFAULT_CONFIG_PATH, Config, load_config, save_config
from forsa_dev.ports import allocate_port
from forsa_dev.state import Environment, delete_state, list_states, load_state, save_state

app = typer.Typer(help="Manage FORSA development environments.")

ConfigOption = Annotated[
    Optional[Path],
    typer.Option("--config", help="Path to config file.", show_default=False),
]


def _load(config_path: Optional[Path]) -> Config:
    return load_config(config_path or DEFAULT_CONFIG_PATH)


def _full_name(user: str, name: str) -> str:
    return f"{user}-{name}"


@app.command()
def init(
    config: ConfigOption = None,
):
    """Interactive setup — creates ~/.config/forsa/config.toml."""
    config_path = config or DEFAULT_CONFIG_PATH
    typer.echo("Setting up forsa-dev configuration.")
    repo = typer.prompt("Path to your FORSA git repo", default=str(Path.home() / "forsa"))
    worktree_dir = typer.prompt("Directory for git worktrees", default=str(Path.home() / "worktrees"))
    data_dir = typer.prompt("Default data directory", default="/data/dev")
    state_dir = typer.prompt("Shared state directory", default="/var/lib/forsa-dev")
    caddy_admin = typer.prompt("Caddy admin API URL", default="http://localhost:2019")
    base_url = typer.prompt("Base URL (e.g. optbox.tailnet.ts.net)")
    docker_image = typer.prompt("Docker image name", default="forsa:latest")
    gurobi_lic = typer.prompt("Path to gurobi.lic on this machine", default="/opt/gurobi/gurobi.lic")
    port_start = typer.prompt("Port range start", default=3000)
    port_end = typer.prompt("Port range end", default=3099)

    cfg = Config(
        repo=Path(repo),
        worktree_dir=Path(worktree_dir),
        data_dir=Path(data_dir),
        state_dir=Path(state_dir),
        caddy_admin=caddy_admin,
        base_url=base_url,
        docker_image=docker_image,
        gurobi_lic=Path(gurobi_lic),
        port_range_start=int(port_start),
        port_range_end=int(port_end),
    )
    save_config(cfg, config_path)
    typer.echo(f"Config written to {config_path}")


@app.command()
def up(
    name: str,
    from_branch: Annotated[str, typer.Option("--from", help="Branch to create from.")] = "main",
    config: ConfigOption = None,
):
    """Create a git worktree, compose file, and tmux session."""
    cfg = _load(config)
    user = getpass.getuser()
    full_name = _full_name(user, name)
    worktree = cfg.worktree_dir / name

    # Guard: already exists
    try:
        load_state(user, name, cfg.state_dir)
        typer.echo(f"Error: environment '{full_name}' already exists. Use `forsa-dev down {name}` first.", err=True)
        raise typer.Exit(1)
    except FileNotFoundError:
        pass

    typer.echo(f"Creating branch '{name}' from '{from_branch}'...")
    git.create_branch_and_worktree(cfg.repo, name, worktree, from_branch)

    typer.echo("Allocating port...")
    port = allocate_port(cfg.state_dir, cfg.port_range_start, cfg.port_range_end)

    typer.echo(f"Generating docker-compose.dev.yml (port {port})...")
    compose_file = generate_compose(
        worktree=worktree,
        user=user,
        name=name,
        port=port,
        data_dir=cfg.data_dir,
        docker_image=cfg.docker_image,
        gurobi_lic=cfg.gurobi_lic,
    )

    env = Environment(
        name=name,
        user=user,
        branch=name,
        worktree=worktree,
        tmux_session=full_name,
        compose_file=compose_file,
        port=port,
        url=None,
        created_at=datetime.now(tz=timezone.utc),
        served_at=None,
    )
    save_state(env, cfg.state_dir)

    typer.echo(f"Starting tmux session '{full_name}'...")
    tmux.create_session(full_name, worktree)

    typer.echo(f"Ready. Attaching to '{full_name}'...")
    tmux.attach_session(full_name)
