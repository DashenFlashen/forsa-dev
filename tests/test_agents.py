from __future__ import annotations

from unittest.mock import call, patch

from forsa_dev.agents import AGENTS, agent_status, ensure_agents


TTYD_PORTS = {"claude-root": 7698, "claude-forsa-dev": 7699}


def test_agents_config_has_two_entries():
    assert len(AGENTS) == 2
    names = [a["session"] for a in AGENTS]
    assert "claude-root" in names
    assert "claude-forsa-dev" in names


def test_ensure_agents_creates_missing_sessions():
    with patch("forsa_dev.agents.tmux") as mock_tmux, \
         patch("forsa_dev.agents.ttyd") as mock_ttyd:
        mock_tmux.session_exists.return_value = False
        mock_ttyd.ttyd_port_is_open.return_value = False
        mock_ttyd.start_ttyd.return_value = 12345

        pids = ensure_agents(TTYD_PORTS)

        assert mock_tmux.create_session.call_count == 2
        assert mock_ttyd.start_ttyd.call_count == 2
        assert len(pids) == 2


def test_ensure_agents_skips_existing_sessions():
    with patch("forsa_dev.agents.tmux") as mock_tmux, \
         patch("forsa_dev.agents.ttyd") as mock_ttyd:
        mock_tmux.session_exists.return_value = True
        mock_ttyd.ttyd_port_is_open.return_value = True

        pids = ensure_agents(TTYD_PORTS)

        mock_tmux.create_session.assert_not_called()
        mock_ttyd.start_ttyd.assert_not_called()
        assert len(pids) == 2


def test_ensure_agents_starts_ttyd_if_port_not_open():
    with patch("forsa_dev.agents.tmux") as mock_tmux, \
         patch("forsa_dev.agents.ttyd") as mock_ttyd:
        mock_tmux.session_exists.return_value = True
        mock_ttyd.ttyd_port_is_open.return_value = False
        mock_ttyd.start_ttyd.return_value = 99999

        pids = ensure_agents(TTYD_PORTS)

        mock_tmux.create_session.assert_not_called()
        assert mock_ttyd.start_ttyd.call_count == 2


def test_agent_status_returns_live_status():
    with patch("forsa_dev.agents.tmux") as mock_tmux, \
         patch("forsa_dev.agents.ttyd") as mock_ttyd:
        mock_tmux.session_status.return_value = "detached"
        mock_ttyd.ttyd_port_is_open.return_value = True

        result = agent_status(TTYD_PORTS)

        assert len(result) == 2
        assert result[0]["tmux"] == "detached"
        assert result[0]["ttyd"] == "alive"
        assert result[0]["ttyd_port"] == 7698


def test_agent_status_reports_dead_ttyd():
    with patch("forsa_dev.agents.tmux") as mock_tmux, \
         patch("forsa_dev.agents.ttyd") as mock_ttyd:
        mock_tmux.session_status.return_value = "missing"
        mock_ttyd.ttyd_port_is_open.return_value = False

        result = agent_status(TTYD_PORTS)

        assert result[0]["tmux"] == "missing"
        assert result[0]["ttyd"] == "dead"
