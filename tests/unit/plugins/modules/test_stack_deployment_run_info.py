# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/stack_deployment_run_info.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.stack_deployment_run_info import (
    main,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.stack_deployment_run_info"

_SDR_ID = "sdr-abc123"
_RUN = {
    "id": _SDR_ID,
    "status": "deploying",
    "created_at": "2026-07-02T09:40:37+00:00",
    "updated_at": "2026-07-02T09:40:38+00:00",
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
@patch(f"{MODULE_PATH}.get_stack_deployment_run")
def test_by_id_success(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module({"stack_deployment_run_id": _SDR_ID, "stack_deployment_group_id": None})
    mock_module_class.return_value = mock_module
    mock_get.return_value = _RUN

    main()

    mock_get.assert_called_once_with(mock_adapter, _SDR_ID)
    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_run"] == _RUN
    assert result["changed"] is False
    assert result["warnings"] == []


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_run")
def test_by_id_not_found_calls_fail_json(mock_get, mock_module_class):
    mock_module = _mock_module({"stack_deployment_run_id": "sdr-missing", "stack_deployment_group_id": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_run")
def test_unexpected_exception_calls_fail_json(mock_get, mock_module_class):
    mock_module = _mock_module({"stack_deployment_run_id": _SDR_ID, "stack_deployment_group_id": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.side_effect = RuntimeError("boom")

    main()

    mock_module.fail_json.assert_called_once()
    assert "boom" in mock_module.fail_json.call_args[1]["msg"]


def test_argument_spec_declares_required_one_of():
    """Verify required_one_of is declared for stack_deployment_run_id / stack_deployment_group_id."""
    with patch(f"{MODULE_PATH}.AnsibleTerraformModule", side_effect=SystemExit) as mock_cls:
        with pytest.raises(SystemExit):
            main()

    _args, kwargs = mock_cls.call_args
    assert ("stack_deployment_run_id", "stack_deployment_group_id") in kwargs["required_one_of"]
    assert ("stack_deployment_run_id", "stack_deployment_group_id") in kwargs["mutually_exclusive"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_run")
def test_check_mode_still_reads_and_returns_run(mock_get, mock_module_class):
    """check_mode does not skip the read; changed is always False for an info module."""
    mock_module, mock_adapter = _mock_module(
        {"stack_deployment_run_id": _SDR_ID, "stack_deployment_group_id": None},
        check_mode=True,
    )
    mock_module_class.return_value = mock_module
    mock_get.return_value = _RUN

    main()

    mock_get.assert_called_once_with(mock_adapter, _SDR_ID)
    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_run"] == _RUN
    assert result["changed"] is False
    assert result["warnings"] == []


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_stack_deployment_runs")
def test_list_by_group_id_success(mock_list, mock_module_class):
    """Providing stack_deployment_group_id returns stack_deployment_runs list."""
    _SDG_ID = "sdg-xyz789"
    runs = [_RUN, {**_RUN, "id": "sdr-def456"}]
    mock_module, mock_adapter = _mock_module({"stack_deployment_run_id": None, "stack_deployment_group_id": _SDG_ID})
    mock_module_class.return_value = mock_module
    mock_list.return_value = runs

    main()

    mock_list.assert_called_once_with(mock_adapter, _SDG_ID)
    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_runs"] == runs
    assert result["changed"] is False


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_stack_deployment_runs")
def test_list_by_group_id_empty(mock_list, mock_module_class):
    """An empty deployment group returns an empty list (no error)."""
    _SDG_ID = "sdg-empty"
    mock_module, mock_adapter = _mock_module({"stack_deployment_run_id": None, "stack_deployment_group_id": _SDG_ID})
    mock_module_class.return_value = mock_module
    mock_list.return_value = []

    main()

    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_runs"] == []
    assert result["changed"] is False
