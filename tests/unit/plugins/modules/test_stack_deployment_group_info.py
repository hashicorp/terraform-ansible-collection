# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/stack_deployment_group_info.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.stack_deployment_group_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.stack_deployment_group_info"

_SDG_ID = "sdg-xyz789"
_STC_ID = "stc-abc123"
_GROUP = {
    "id": _SDG_ID,
    "name": "dev",
    "status": "deploying",
    "created_at": "2026-07-02T09:40:00+00:00",
    "updated_at": "2026-07-02T09:41:00+00:00",
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
@patch(f"{MODULE_PATH}.get_stack_deployment_group")
def test_by_id_success(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module({"stack_deployment_group_id": _SDG_ID, "stack_configuration_id": None, "name": None})
    mock_module_class.return_value = mock_module
    mock_get.return_value = _GROUP

    main()

    mock_get.assert_called_once_with(mock_adapter, _SDG_ID)
    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_group"] == _GROUP
    assert result["changed"] is False
    assert result["warnings"] == []


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_group")
def test_by_id_not_found_calls_fail_json(mock_get, mock_module_class):
    mock_module = _mock_module({"stack_deployment_group_id": "sdg-missing", "stack_configuration_id": None, "name": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_group_by_name")
def test_by_name_success(mock_get_by_name, mock_module_class):
    mock_module, mock_adapter = _mock_module({"stack_deployment_group_id": None, "stack_configuration_id": _STC_ID, "name": "dev"})
    mock_module_class.return_value = mock_module
    mock_get_by_name.return_value = _GROUP

    main()

    mock_get_by_name.assert_called_once_with(mock_adapter, _STC_ID, "dev")
    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_group"] == _GROUP
    assert result["changed"] is False
    assert result["warnings"] == []


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_group_by_name")
def test_by_name_not_found_calls_fail_json(mock_get_by_name, mock_module_class):
    mock_module = _mock_module({"stack_deployment_group_id": None, "stack_configuration_id": _STC_ID, "name": "ghost"})[0]
    mock_module_class.return_value = mock_module
    mock_get_by_name.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_group")
def test_unexpected_exception_calls_fail_json(mock_get, mock_module_class):
    mock_module = _mock_module({"stack_deployment_group_id": _SDG_ID, "stack_configuration_id": None, "name": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.side_effect = RuntimeError("boom")

    main()

    mock_module.fail_json.assert_called_once()
    assert "boom" in mock_module.fail_json.call_args[1]["msg"]


def test_argument_spec_requires_stack_configuration_id_with_name():
    """Verify required_by: name requires stack_configuration_id is declared on the module."""
    with patch(f"{MODULE_PATH}.AnsibleTerraformModule", side_effect=SystemExit) as mock_cls:
        with pytest.raises(SystemExit):
            main()

    _args, kwargs = mock_cls.call_args
    assert kwargs.get("required_by", {}).get("name") == ("stack_configuration_id",)


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_group")
def test_check_mode_by_id_still_reads_and_returns_group(mock_get, mock_module_class):
    """check_mode does not skip the read; changed is always False for an info module."""
    mock_module, mock_adapter = _mock_module(
        {"stack_deployment_group_id": _SDG_ID, "stack_configuration_id": None, "name": None},
        check_mode=True,
    )
    mock_module_class.return_value = mock_module
    mock_get.return_value = _GROUP

    main()

    mock_get.assert_called_once_with(mock_adapter, _SDG_ID)
    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_group"] == _GROUP
    assert result["changed"] is False
    assert result["warnings"] == []


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_group_by_name")
def test_check_mode_by_name_still_reads_and_returns_group(mock_get_by_name, mock_module_class):
    """check_mode does not skip the read; changed is always False for an info module."""
    mock_module, mock_adapter = _mock_module(
        {"stack_deployment_group_id": None, "stack_configuration_id": _STC_ID, "name": "dev"},
        check_mode=True,
    )
    mock_module_class.return_value = mock_module
    mock_get_by_name.return_value = _GROUP

    main()

    mock_get_by_name.assert_called_once_with(mock_adapter, _STC_ID, "dev")
    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_group"] == _GROUP
    assert result["changed"] is False
    assert result["warnings"] == []
