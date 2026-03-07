from datetime import datetime, timezone
from pathlib import Path

import pytest

from forsa_dev.state import Environment, delete_state, list_states, load_state, save_state


def make_env(state_dir: Path) -> Environment:
    return Environment(
        name="ticket-42",
        user="anders",
        branch="ticket-42",
        worktree=Path("/home/anders/worktrees/ticket-42"),
        tmux_session="anders-ticket-42",
        compose_file=Path("/home/anders/worktrees/ticket-42/docker-compose.dev.yml"),
        port=3002,
        url=None,
        created_at=datetime(2026, 3, 7, 22, 0, 0, tzinfo=timezone.utc),
        served_at=None,
    )


def test_save_and_load_state(tmp_path):
    env = make_env(tmp_path)
    save_state(env, tmp_path)
    loaded = load_state("anders", "ticket-42", tmp_path)
    assert loaded == env


def test_load_state_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_state("anders", "ticket-42", tmp_path)


def test_delete_state(tmp_path):
    env = make_env(tmp_path)
    save_state(env, tmp_path)
    delete_state("anders", "ticket-42", tmp_path)
    assert not (tmp_path / "anders-ticket-42.json").exists()


def test_list_states_empty(tmp_path):
    assert list_states(tmp_path) == []


def test_list_states_multiple(tmp_path):
    env1 = make_env(tmp_path)
    env2 = Environment(
        name="experiment",
        user="hanna",
        branch="experiment",
        worktree=Path("/home/hanna/worktrees/experiment"),
        tmux_session="hanna-experiment",
        compose_file=Path("/home/hanna/worktrees/experiment/docker-compose.dev.yml"),
        port=3003,
        url="optbox.example.ts.net/experiment/",
        created_at=datetime(2026, 3, 7, 23, 0, 0, tzinfo=timezone.utc),
        served_at=datetime(2026, 3, 7, 23, 5, 0, tzinfo=timezone.utc),
    )
    save_state(env1, tmp_path)
    save_state(env2, tmp_path)
    states = list_states(tmp_path)
    assert len(states) == 2
    names = {s.name for s in states}
    assert names == {"ticket-42", "experiment"}


def test_state_with_url_roundtrips(tmp_path):
    env = make_env(tmp_path)
    env_with_url = Environment(
        **{
            **env.__dict__,
            "url": "optbox.example.ts.net/ticket-42/",
            "served_at": datetime(2026, 3, 7, 22, 5, 0, tzinfo=timezone.utc),
        }
    )
    save_state(env_with_url, tmp_path)
    loaded = load_state("anders", "ticket-42", tmp_path)
    assert loaded.url == "optbox.example.ts.net/ticket-42/"
    assert loaded.served_at is not None
