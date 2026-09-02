# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/azure_oidc_configuration.py."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.azure_oidc_configuration import main

MOD = "ansible_collections.hashicorp.terraform.plugins.modules.azure_oidc_configuration"


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


@patch(f"{MOD}.AnsibleTerraformModule")
@patch(f"{MOD}.state_present")
def test_present_dispatches_with_provider_and_required_fields(mock_state_present, mock_module_class):
    params = {
        "oidc_configuration_id": None,
        "organization": "my-org",
        "client_id": "c",
        "subscription_id": "s",
        "tenant_id": "t",
        "state": "present",
    }
    mock_module, mock_adapter = _mock_module(params)
    mock_module_class.return_value = mock_module
    mock_state_present.return_value = {"changed": True, "id": "oidc-1"}

    main()

    args, _kwargs = mock_state_present.call_args
    assert args[0] is mock_adapter
    assert args[1] == "azure"
    assert args[2] == ("client_id", "subscription_id", "tenant_id")
    mock_module.exit_json.assert_called_once()


@patch(f"{MOD}.AnsibleTerraformModule")
@patch(f"{MOD}.state_absent")
def test_absent_dispatches_with_provider(mock_state_absent, mock_module_class):
    params = {"oidc_configuration_id": "oidc-1", "organization": None, "client_id": None, "subscription_id": None, "tenant_id": None, "state": "absent"}
    mock_module, mock_adapter = _mock_module(params)
    mock_module_class.return_value = mock_module
    mock_state_absent.return_value = {"changed": True, "msg": "deleted"}

    main()

    args, _kwargs = mock_state_absent.call_args
    assert args[0] is mock_adapter
    assert args[1] == "azure"
    mock_module.exit_json.assert_called_once()


@patch(f"{MOD}.AnsibleTerraformModule")
@patch(f"{MOD}.state_present")
def test_errors_propagate_to_fail_json(mock_state_present, mock_module_class):
    params = {"oidc_configuration_id": None, "organization": "my-org", "client_id": "c", "subscription_id": "s", "tenant_id": "t", "state": "present"}
    mock_module = _mock_module(params)[0]
    mock_module_class.return_value = mock_module
    mock_state_present.side_effect = ValueError("boom")

    main()

    mock_module.fail_json.assert_called_once()
    assert "boom" in mock_module.fail_json.call_args[1]["msg"]
