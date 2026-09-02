# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the aws_oidc_configuration_info module."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.aws_oidc_configuration_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.aws_oidc_configuration_info"


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
@patch(f"{MODULE_PATH}.get_oidc_configuration")
def test_found(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module({"oidc_configuration_id": "oidc-1"})
    mock_module_class.return_value = mock_module
    mock_get.return_value = {"id": "oidc-1", "role_arn": "arn:aws:iam::123:role/tfc"}

    main()

    mock_get.assert_called_once_with(mock_adapter, "aws", "oidc-1")
    result = mock_module.exit_json.call_args[1]
    assert result["oidc_configuration"]["id"] == "oidc-1"
    assert result["changed"] is False


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_oidc_configuration")
def test_not_found_fails(mock_get, mock_module_class):
    mock_module = _mock_module({"oidc_configuration_id": "oidc-ghost"})[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]
