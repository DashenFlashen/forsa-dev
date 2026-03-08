from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import replace
from datetime import datetime, timezone

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
) -> Environment:
    if not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid environment name '{name}': must start with a letter or digit "
            "and contain only lowercase letters, digits, hyphens, and underscores."
        )

    full_name = f"{user}-{name}"
    worktree = cfg.worktree_dir / name

    try:
        load_state(user, name, cfg.state_dir)
        raise ValueError(f"Environment '{full_name}' already exists.")
    except FileNotFoundError:
        pass

    git.create_branch_and_worktree(cfg.repo, name, worktree, from_branch)

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
                ttyd_port=ttyd_port,
            )
            save_state(env, cfg.state_dir)
    except Exception:
        git.remove_worktree(cfg.repo, worktree)
        git.delete_branch(cfg.repo, name, force=True)
        raise

    command = "zsh -i -c 'claude || exec zsh'" if with_claude else None
    try:
        tmux.create_session(full_name, worktree, command=command)
    except RuntimeError:
        delete_state(user, name, cfg.state_dir)
        git.remove_worktree(cfg.repo, worktree)
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
        git.delete_branch(cfg.repo, name, force=True)
        raise
    updated = replace(env, ttyd_pid=pid)
    save_state(updated, cfg.state_dir)
    return updated


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
