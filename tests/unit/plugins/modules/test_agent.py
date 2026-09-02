# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/agent.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.modules.agent import (
    _fetch_agent,
    state_absent,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.agent"


class TestFetchAgent:
    def test_by_id(self):
        with patch(f"{MODULE_PATH}.get_agent", return_value={"id": "agent-1"}) as mock_get:
            result = _fetch_agent(Mock(), {"agent_id": "agent-1"})
        assert result == {"id": "agent-1"}
        mock_get.assert_called_once()

    def test_missing_agent_id(self):
        assert _fetch_agent(Mock(), {}) is None


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_present(self, adapter):
        current = {"id": "agent-1", "name": "my-agent"}
        params = {"agent_id": "agent-1"}
        with patch(f"{MODULE_PATH}._fetch_agent", return_value=current), patch(f"{MODULE_PATH}.delete_agent") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "agent-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_noop_when_absent(self, adapter):
        params = {"agent_id": "agent-missing"}
        with patch(f"{MODULE_PATH}._fetch_agent", return_value=None), patch(f"{MODULE_PATH}.delete_agent") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        current = {"id": "agent-1", "name": "my-agent"}
        params = {"agent_id": "agent-1"}
        with patch(f"{MODULE_PATH}._fetch_agent", return_value=current), patch(f"{MODULE_PATH}.delete_agent") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_api_rejection_propagates(self, adapter):
        """TFC API rejects deletion of idle/busy agents; the error must propagate."""
        current = {"id": "agent-1", "name": "my-agent", "status": "idle"}
        params = {"agent_id": "agent-1"}
        error = TerraformError("Agent with status 'idle' may not be deleted")
        with patch(f"{MODULE_PATH}._fetch_agent", return_value=current), patch(f"{MODULE_PATH}.delete_agent", side_effect=error):
            with pytest.raises(TerraformError, match="may not be deleted"):
                state_absent(adapter, params, check_mode=False)
