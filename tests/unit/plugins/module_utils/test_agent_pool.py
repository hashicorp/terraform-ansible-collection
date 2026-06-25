# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/agent_pool.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.agent_pool import (
    create_agent_pool,
    delete_agent_pool,
    get_agent_pool,
    get_agent_pool_by_name,
    list_agent_pools,
    update_agent_pool,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.agent_pool"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestListAgentPools:
    def test_success(self):
        adapter = Mock()
        adapter.client.agent_pools.list.return_value = iter([_make_model({"id": "apool-1", "name": "a"}), _make_model({"id": "apool-2", "name": "b"})])
        assert list_agent_pools(adapter, "my-org") == [
            {"id": "apool-1", "name": "a"},
            {"id": "apool-2", "name": "b"},
        ]
        adapter.client.agent_pools.list.assert_called_once_with("my-org")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.agent_pools.list.side_effect = NotFound("nope")
        assert list_agent_pools(adapter, "my-org") == []


class TestGetAgentPool:
    def test_success(self):
        adapter = Mock()
        adapter.client.agent_pools.read.return_value = _make_model({"id": "apool-1", "name": "a"})
        assert get_agent_pool(adapter, "apool-1") == {"id": "apool-1", "name": "a"}
        adapter.client.agent_pools.read.assert_called_once_with("apool-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.agent_pools.read.side_effect = NotFound("missing")
        assert get_agent_pool(adapter, "apool-missing") is None


class TestGetAgentPoolByName:
    def test_match(self):
        adapter = Mock()
        adapter.client.agent_pools.list.return_value = iter([_make_model({"id": "apool-1", "name": "a"}), _make_model({"id": "apool-2", "name": "b"})])
        assert get_agent_pool_by_name(adapter, "org", "b") == {"id": "apool-2", "name": "b"}

    def test_no_match(self):
        adapter = Mock()
        adapter.client.agent_pools.list.return_value = iter([])
        assert get_agent_pool_by_name(adapter, "org", "ghost") is None


class TestCreateAgentPool:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.AgentPoolCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "apool-1", "name": "a"})

        data = {"name": "a", "organization_scoped": True}
        result = create_agent_pool(adapter, "my-org", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.agent_pools.create
        assert args[1] == "my-org"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "apool-1", "name": "a"}


class TestUpdateAgentPool:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.AgentPoolUpdateOptions")
    def test_update_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "apool-1", "name": "renamed"})

        data = {"name": "renamed"}
        result = update_agent_pool(adapter, "apool-1", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.agent_pools.update
        assert args[1] == "apool-1"
        assert args[2] is opts
        assert result == {"id": "apool-1", "name": "renamed"}


class TestDeleteAgentPool:
    @patch(f"{MU_PATH}.safe_api_call")
    def test_delete(self, mock_safe_call):
        adapter = Mock()
        delete_agent_pool(adapter, "apool-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.agent_pools.delete
        assert args[1] == "apool-1"
        assert "error_context" in kwargs
