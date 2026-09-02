# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/agent_token.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.agent_token import (
    create_agent_token,
    delete_agent_token,
    get_agent_token,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.agent_token"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestGetAgentToken:
    def test_success(self):
        adapter = Mock()
        adapter.client.agent_tokens.read.return_value = _make_model({"id": "at-1", "description": "ci-runner"})

        result = get_agent_token(adapter, "at-1")

        assert result == {"id": "at-1", "description": "ci-runner"}
        adapter.client.agent_tokens.read.assert_called_once_with("at-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.agent_tokens.read.side_effect = NotFound("missing")

        assert get_agent_token(adapter, "at-missing") is None


class TestCreateAgentToken:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.AgentTokenCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "at-1", "description": "ci-runner", "token": "t.secret"})

        data = {"description": "ci-runner"}
        result = create_agent_token(adapter, "apool-1", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.agent_tokens.create
        assert args[1] == "apool-1"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "at-1", "description": "ci-runner", "token": "t.secret"}


class TestDeleteAgentToken:
    @patch(f"{MU_PATH}.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        mock_safe_call.return_value = None

        delete_agent_token(adapter, "at-1")

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.agent_tokens.delete
        assert args[1] == "at-1"
        assert "error_context" in kwargs
