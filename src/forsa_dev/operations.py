from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from forsa_dev import git, tmux, ttyd
from forsa_dev.compose import generate_compose
from forsa_dev.config import Config
from forsa_dev.ports import allocate_ports
from forsa_dev.state import Environment, delete_state, load_state, save_state

logger = logging.getLogger(__name__)

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def compose_cmd(env: Environment, *args: str) -> list[str]:
    return [
        "docker", "compose",
        "-p", f"{env.user}-{env.name}",
        "-f", str(env.compose_file),
        *args,
    ]


def serve_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    result = subprocess.run(compose_cmd(env, "up", "-d"), check=False)
    if result.returncode != 0:
        raise RuntimeError("docker compose up failed")
    url = f"http://{cfg.base_url}:{env.port}"
    updated = replace(env, url=url, served_at=datetime.now(tz=timezone.utc))
    save_state(updated, cfg.state_dir)


def stop_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    subprocess.run(compose_cmd(env, "down"), check=False)
    updated = replace(env, url=None, served_at=None)
    save_state(updated, cfg.state_dir)


def restart_env(cfg: Config, user: str, name: str) -> None:
    env = load_state(user, name, cfg.state_dir)
    subprocess.run(compose_cmd(env, "restart"), check=False)


def up_env(
    cfg: Config,
    user: str,
    name: str,
    from_branch: str = "main",
    with_claude: bool = False,
    data_dir: Path | None = None,
    existing_branch: str | None = None,
) -> Environment:
    if not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid environment name '{name}': must start with a letter or digit "
            "and contain only lowercase letters, digits, hyphens, and underscores."
        )

    if name == "main":
        raise ValueError(
            "The name 'main' is reserved for main repo environments."
        )

    full_name = f"{user}-{name}"
    worktree = cfg.worktree_dir / name

    try:
        load_state(user, name, cfg.state_dir)
        raise ValueError(f"Environment '{full_name}' already exists.")
    except FileNotFoundError:
        pass

    if existing_branch:
        git.create_worktree_from_branch(cfg.repo, existing_branch, worktree)
        branch = existing_branch
    else:
        git.create_branch_and_worktree(cfg.repo, name, worktree, from_branch)
        branch = name

    ranges = (
        (cfg.port_range_start, cfg.port_range_end),
        (cfg.ttyd_port_range_start, cfg.ttyd_port_range_end),
    )
    try:
        with allocate_ports(cfg.state_dir, *ranges) as (port, ttyd_port):
            compose_file = generate_compose(
                worktree=worktree,
                user=user,
                name=name,
                port=port,
                data_dir=data_dir or cfg.data_dir,
                docker_image=cfg.docker_image,
                gurobi_lic=cfg.gurobi_lic,
            )
            env = Environment(
                name=name,
                user=user,
                branch=branch,
                worktree=worktree,
                tmux_session=full_name,
                compose_file=compose_file,
                port=port,
                url=None,
                created_at=datetime.now(tz=timezone.utc),
                served_at=None,
                ttyd_port=ttyd_port,
            )
            save_state(env, cfg.state_dir)
    except Exception:
        git.remove_worktree(cfg.repo, worktree)
        if not existing_branch:
            git.delete_branch(cfg.repo, name, force=True)
        raise

    shell = os.environ.get("SHELL", "/bin/bash")
    command = (
        f"{shell} -i -c 'claude --dangerously-skip-permissions --effort max; exec {shell}'"
        if with_claude else None
    )
    try:
        tmux.create_session(full_name, worktree, command=command)
    except RuntimeError:
        delete_state(user, name, cfg.state_dir)
        git.remove_worktree(cfg.repo, worktree)
        if not existing_branch:
            git.delete_branch(cfg.repo, name, force=True)
        raise

    try:
        pid = ttyd.start_ttyd(ttyd_port, full_name)
    except Exception:
        try:
            tmux.kill_session(full_name)
        except RuntimeError:
            pass
        delete_state(user, name, cfg.state_dir)
        git.remove_worktree(cfg.repo, worktree)
        if not existing_branch:
            git.delete_branch(cfg.repo, name, force=True)
        raise
    updated = replace(env, ttyd_pid=pid)
    save_state(updated, cfg.state_dir)
    return updated


def run_local(cfg: Config, work_dir: Path, data_dir: Path | None = None) -> None:
    """Run a FORSA server from an arbitrary directory. Foreground, no state file."""
    # Allocate port under lock, write a temporary state file so concurrent
    # allocations see this port as taken, then release the lock before
    # running compose (which blocks indefinitely).
    with allocate_ports(cfg.state_dir, (cfg.port_range_start, cfg.port_range_end)) as (port,):
        compose_file = generate_compose(
            worktree=work_dir,
            user="local",
            name="run",
            port=port,
            data_dir=data_dir or cfg.data_dir,
            docker_image=cfg.docker_image,
            gurobi_lic=cfg.gurobi_lic,
        )
        # Write temporary state so the port stays reserved after lock release
        env = Environment(
            name="run",
            user="local",
            branch="",
            worktree=work_dir,
            tmux_session="",
            compose_file=compose_file,
            port=port,
            url=f"http://{cfg.base_url}:{port}",
            created_at=datetime.now(tz=timezone.utc),
            served_at=datetime.now(tz=timezone.utc),
        )
        save_state(env, cfg.state_dir)
    # Lock is released — other allocations can proceed
    try:
        print(f"Serving at http://{cfg.base_url}:{port}")
        print("Press Ctrl+C to stop.")
        subprocess.run(
            ["docker", "compose", "-p", "forsa-run", "-f", str(compose_file), "up"],
            check=False,
        )
    finally:
        subprocess.run(
            ["docker", "compose", "-p", "forsa-run", "-f", str(compose_file), "down"],
            check=False,
        )
        delete_state("local", "run", cfg.state_dir)


def down_env(cfg: Config, user: str, name: str, force: bool = False) -> None:
    env = load_state(user, name, cfg.state_dir)

    if not force and not git.branch_is_pushed(cfg.repo, env.branch):
        raise RuntimeError(
            f"Branch '{env.branch}' has not been pushed or merged. Use force=True to delete anyway."
        )

    subprocess.run(compose_cmd(env, "down"), check=False)

    try:
        tmux.kill_session(env.tmux_session)
    except RuntimeError:
        pass

    if env.ttyd_pid is not None:
        ttyd.stop_ttyd(env.ttyd_pid)

    try:
        git.remove_worktree(cfg.repo, env.worktree)
    except RuntimeError as e:
        logger.warning("Could not remove worktree: %s", e)

    try:
        git.delete_branch(cfg.repo, env.branch, force=force)
    except RuntimeError as e:
        logger.warning("Could not delete branch: %s", e)

    delete_state(user, name, cfg.state_dir)
