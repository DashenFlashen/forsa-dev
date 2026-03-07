from __future__ import annotations
import getpass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import typer

from forsa_dev import caddy, git, tmux
from forsa_dev.compose import generate_compose
from forsa_dev.config import DEFAULT_CONFIG_PATH, Config, load_config, save_config
from forsa_dev.list_status import check_status, port_is_open
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


def _compose_cmd(env: Environment, *args: str) -> list[str]:
    return [
        "docker", "compose",
        "-p", env.tmux_session,
        "-f", str(env.compose_file),
        *args,
    ]


@app.command()
def serve(
    name: str,
    config: ConfigOption = None,
):
    """Start the Docker server for an environment."""
    import subprocess
    cfg = _load(config)
    user = getpass.getuser()
    env = load_state(user, name, cfg.state_dir)

    typer.echo(f"Starting server on port {env.port}...")
    result = subprocess.run(_compose_cmd(env, "up", "-d"), check=False)
    if result.returncode != 0:
        typer.echo("Error: docker compose up failed.", err=True)
        raise typer.Exit(1)

    url = f"{cfg.base_url}/{name}/"
    caddy.register_route(cfg.caddy_admin, name, env.port)

    updated = Environment(
        **{**env.__dict__,
           "url": url,
           "served_at": datetime.now(tz=timezone.utc)}
    )
    save_state(updated, cfg.state_dir)
    typer.echo(f"Serving at {url}")


@app.command()
def stop(
    name: str,
    config: ConfigOption = None,
):
    """Stop the Docker server. Tmux session is preserved."""
    import subprocess
    cfg = _load(config)
    user = getpass.getuser()
    env = load_state(user, name, cfg.state_dir)

    typer.echo("Stopping server...")
    subprocess.run(_compose_cmd(env, "down"), check=False)
    caddy.deregister_route(cfg.caddy_admin, name)

    updated = Environment(
        **{**env.__dict__, "url": None, "served_at": None}
    )
    save_state(updated, cfg.state_dir)
    typer.echo("Server stopped. Tmux session preserved.")


@app.command()
def restart(
    name: str,
    config: ConfigOption = None,
):
    """Restart the Docker containers without changing port or Caddy registration."""
    import subprocess
    cfg = _load(config)
    user = getpass.getuser()
    env = load_state(user, name, cfg.state_dir)
    typer.echo("Restarting...")
    subprocess.run(_compose_cmd(env, "restart"), check=False)
    typer.echo("Done.")


@app.command()
def down(
    name: str,
    force: Annotated[bool, typer.Option("--force", help="Skip branch-push check.")] = False,
    config: ConfigOption = None,
):
    """Stop server, kill tmux, remove worktree. Checks branch is pushed first."""
    import subprocess
    cfg = _load(config)
    user = getpass.getuser()
    env = load_state(user, name, cfg.state_dir)

    if not force and not git.branch_is_pushed(cfg.repo, env.branch):
        typer.echo(
            f"Error: branch '{env.branch}' has not been pushed or merged.\n"
            "Use --force to delete anyway.",
            err=True,
        )
        raise typer.Exit(1)

    # Stop server if running
    if env.url:
        typer.echo("Stopping server...")
        subprocess.run(_compose_cmd(env, "down"), check=False)
        caddy.deregister_route(cfg.caddy_admin, name)

    # Kill tmux
    typer.echo("Killing tmux session...")
    try:
        tmux.kill_session(env.tmux_session)
    except RuntimeError:
        pass  # session may already be gone

    # Remove worktree
    typer.echo("Removing worktree...")
    git.remove_worktree(cfg.repo, env.worktree)

    # Delete state
    delete_state(user, name, cfg.state_dir)
    typer.echo(f"Environment '{_full_name(user, name)}' removed.")


@app.command(name="list")
def list_envs(
    config: ConfigOption = None,
):
    """List all environments with live status."""
    from rich.console import Console
    from rich.table import Table

    cfg = _load(config)
    envs = list_states(cfg.state_dir)

    console = Console()

    if not envs:
        console.print("No environments found.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("NAME")
    table.add_column("USER")
    table.add_column("TMUX")
    table.add_column("SERVER")
    table.add_column("PORT")
    table.add_column("URL")

    for env in envs:
        tmux_alive = tmux.session_exists(env.tmux_session)
        port_open = port_is_open(env.port)
        status = check_status(tmux_exists=tmux_alive, port_open=port_open)

        table.add_row(
            env.name,
            env.user,
            status.tmux,
            status.server,
            str(env.port),
            env.url or "-",
        )

    console.print(table)
