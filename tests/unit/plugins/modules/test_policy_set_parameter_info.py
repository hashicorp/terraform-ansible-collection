# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the policy_set_parameter_info module."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.policy_set_parameter_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.policy_set_parameter_info"


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
@patch(f"{MODULE_PATH}.get_policy_set_parameter")
def test_by_id_success(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module({"policy_set_id": "polset-1", "parameter_id": "var-1", "key": None})
    mock_module_class.return_value = mock_module
    mock_get.return_value = {"id": "var-1", "key": "environment"}

    main()

    mock_get.assert_called_once_with(mock_adapter, "polset-1", "var-1")
    result = mock_module.exit_json.call_args[1]
    assert result["parameter"]["id"] == "var-1"


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_policy_set_parameter")
def test_by_id_not_found_fails(mock_get, mock_module_class):
    mock_module = _mock_module({"policy_set_id": "polset-1", "parameter_id": "var-x", "key": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_policy_set_parameter_by_key")
def test_by_key_success(mock_get_by_key, mock_module_class):
    mock_module, mock_adapter = _mock_module({"policy_set_id": "polset-1", "parameter_id": None, "key": "environment"})
    mock_module_class.return_value = mock_module
    mock_get_by_key.return_value = {"id": "var-1", "key": "environment"}

    main()

    mock_get_by_key.assert_called_once_with(mock_adapter, "polset-1", "environment")
    result = mock_module.exit_json.call_args[1]
    assert result["parameter"]["id"] == "var-1"


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_policy_set_parameters")
def test_list_all(mock_list, mock_module_class):
    mock_module, mock_adapter = _mock_module({"policy_set_id": "polset-1", "parameter_id": None, "key": None})
    mock_module_class.return_value = mock_module
    mock_list.return_value = [{"id": "var-1"}, {"id": "var-2"}]

    main()

    mock_list.assert_called_once_with(mock_adapter, "polset-1")
    result = mock_module.exit_json.call_args[1]
    assert len(result["parameters"]) == 2
