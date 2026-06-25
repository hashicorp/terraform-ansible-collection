# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the agent_pool_info module."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.agent_pool_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.agent_pool_info"


def _mock_module(params, check_mode=False):
    mock_module = Mock()
    mock_module.params = params
    mock_module.check_mode = check_mode

    mock_adapter = Mock()
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_adapter)
    mock_context.__exit__ = Mock(return_value=False)
    mock_module.client.return_value = mock_context
    return mock_module, mock_adapter


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_agent_pool")
def test_by_id_success(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module({"agent_pool_id": "apool-1", "organization": None, "name": None})
    mock_module_class.return_value = mock_module
    mock_get.return_value = {"id": "apool-1", "name": "builders"}

    main()

    mock_get.assert_called_once_with(mock_adapter, "apool-1")
    result = mock_module.exit_json.call_args[1]
    assert result["agent_pool"]["id"] == "apool-1"
    assert "agent_pools" not in result


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_agent_pool")
def test_by_id_not_found_fails(mock_get, mock_module_class):
    mock_module = _mock_module({"agent_pool_id": "apool-x", "organization": None, "name": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_agent_pool_by_name")
def test_by_name_success(mock_get_by_name, mock_module_class):
    mock_module, mock_adapter = _mock_module({"agent_pool_id": None, "organization": "org", "name": "builders"})
    mock_module_class.return_value = mock_module
    mock_get_by_name.return_value = {"id": "apool-1", "name": "builders"}

    main()

    mock_get_by_name.assert_called_once_with(mock_adapter, "org", "builders")
    result = mock_module.exit_json.call_args[1]
    assert result["agent_pool"]["id"] == "apool-1"
    assert result["agent_pools"] == [{"id": "apool-1", "name": "builders"}]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_agent_pool_by_name")
def test_by_name_not_found_fails(mock_get_by_name, mock_module_class):
    mock_module = _mock_module({"agent_pool_id": None, "organization": "org", "name": "ghost"})[0]
    mock_module_class.return_value = mock_module
    mock_get_by_name.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_agent_pools")
def test_list_by_organization(mock_list, mock_module_class):
    mock_module, mock_adapter = _mock_module({"agent_pool_id": None, "organization": "org", "name": None})
    mock_module_class.return_value = mock_module
    mock_list.return_value = [{"id": "apool-1", "name": "a"}, {"id": "apool-2", "name": "b"}]

    main()

    mock_list.assert_called_once_with(mock_adapter, "org")
    result = mock_module.exit_json.call_args[1]
    assert len(result["agent_pools"]) == 2
    assert "agent_pool" not in result
