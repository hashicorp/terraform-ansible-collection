# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the policy_set_version_info module."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.policy_set_version_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.policy_set_version_info"


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
@patch(f"{MODULE_PATH}.get_policy_set_version")
def test_found(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module({"policy_set_version_id": "polsetver-1"})
    mock_module_class.return_value = mock_module
    mock_get.return_value = {"id": "polsetver-1", "status": "ready"}

    main()

    mock_get.assert_called_once_with(mock_adapter, "polsetver-1")
    result = mock_module.exit_json.call_args[1]
    assert result["policy_set_version"]["id"] == "polsetver-1"


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_policy_set_version")
def test_not_found_fails(mock_get, mock_module_class):
    mock_module = _mock_module({"policy_set_version_id": "polsetver-x"})[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]
