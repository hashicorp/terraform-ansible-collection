# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/public_registry_module_info.py."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.public_registry_module_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.public_registry_module_info"

_SAMPLE_MODULE = {
    "id": "hashicorp/consul/aws/0.1.0",
    "namespace": "hashicorp",
    "name": "consul",
    "provider": "aws",
    "version": "0.1.0",
    "verified": True,
}


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
@patch(f"{MODULE_PATH}.get_public_registry_module_latest")
def test_latest_success(mock_get_latest, mock_module_class):
    mock_module, mock_adapter = _mock_module(
        {
            "namespace": "hashicorp",
            "name": "consul",
            "provider": "aws",
            "version": None,
        }
    )
    mock_module_class.return_value = mock_module
    mock_get_latest.return_value = _SAMPLE_MODULE

    main()

    mock_get_latest.assert_called_once_with(mock_adapter, "hashicorp", "consul", "aws")
    result = mock_module.exit_json.call_args[1]
    assert result["public_registry_module"]["id"] == "hashicorp/consul/aws/0.1.0"
    assert result["public_registry_module"]["version"] == "0.1.0"
    assert result["changed"] is False


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_public_registry_module_latest")
def test_latest_not_found_fails(mock_get_latest, mock_module_class):
    mock_module, _adapter = _mock_module(
        {
            "namespace": "nonexistent",
            "name": "nomodule",
            "provider": "aws",
            "version": None,
        }
    )
    mock_module_class.return_value = mock_module
    mock_get_latest.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "was not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_public_registry_module")
def test_specific_version_success(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module(
        {
            "namespace": "hashicorp",
            "name": "consul",
            "provider": "aws",
            "version": "0.1.0",
        }
    )
    mock_module_class.return_value = mock_module
    mock_get.return_value = _SAMPLE_MODULE

    main()

    mock_get.assert_called_once_with(mock_adapter, "hashicorp", "consul", "aws", "0.1.0")
    result = mock_module.exit_json.call_args[1]
    assert result["public_registry_module"]["version"] == "0.1.0"
    assert result["changed"] is False


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_public_registry_module")
def test_specific_version_not_found_fails(mock_get, mock_module_class):
    mock_module, _adapter = _mock_module(
        {
            "namespace": "hashicorp",
            "name": "consul",
            "provider": "aws",
            "version": "99.99.99",
        }
    )
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    msg = mock_module.fail_json.call_args[1]["msg"]
    assert "was not found" in msg
    assert "99.99.99" in msg
