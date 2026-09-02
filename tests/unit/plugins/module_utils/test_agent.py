# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/agent.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.agent import (
    delete_agent,
    get_agent,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.agent"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestGetAgent:
    def test_success(self):
        adapter = Mock()
        adapter.client.agents.read.return_value = _make_model({"id": "agent-1", "name": "my-agent", "status": "idle"})
        result = get_agent(adapter, "agent-1")
        assert result == {"id": "agent-1", "name": "my-agent", "status": "idle"}
        adapter.client.agents.read.assert_called_once_with("agent-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.agents.read.side_effect = NotFound("missing")
        assert get_agent(adapter, "agent-missing") is None


class TestDeleteAgent:
    @patch(f"{MU_PATH}.safe_api_call")
    def test_delete(self, mock_safe_call):
        adapter = Mock()
        delete_agent(adapter, "agent-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.agents.delete
        assert args[1] == "agent-1"
        assert "error_context" in kwargs
