# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/stack_deployment_step_info.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.stack_deployment_step_info import (
    main,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.stack_deployment_step_info"

_SDS_ID = "sds-abc123"
_STEP = {
    "id": _SDS_ID,
    "status": "running",
    "operation_type": "plan",
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


_SDR_ID = "sdr-xyz789"


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_step")
def test_by_id_success(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module({"stack_deployment_step_id": _SDS_ID, "stack_deployment_run_id": None})
    mock_module_class.return_value = mock_module
    mock_get.return_value = _STEP

    main()

    mock_get.assert_called_once_with(mock_adapter, _SDS_ID)
    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_step"] == _STEP
    assert result["changed"] is False
    assert result["warnings"] == []


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_step")
def test_by_id_not_found_calls_fail_json(mock_get, mock_module_class):
    mock_module = _mock_module({"stack_deployment_step_id": "sds-missing", "stack_deployment_run_id": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_step")
def test_unexpected_exception_calls_fail_json(mock_get, mock_module_class):
    mock_module = _mock_module({"stack_deployment_step_id": _SDS_ID, "stack_deployment_run_id": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.side_effect = RuntimeError("boom")

    main()

    mock_module.fail_json.assert_called_once()
    assert "boom" in mock_module.fail_json.call_args[1]["msg"]


def test_argument_spec_declares_required_one_of():
    """Verify required_one_of is declared for step_id / run_id."""
    with patch(f"{MODULE_PATH}.AnsibleTerraformModule", side_effect=SystemExit) as mock_cls:
        with pytest.raises(SystemExit):
            main()

    _args, kwargs = mock_cls.call_args
    assert ("stack_deployment_step_id", "stack_deployment_run_id") in kwargs["required_one_of"]
    assert ("stack_deployment_step_id", "stack_deployment_run_id") in kwargs["mutually_exclusive"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_step")
def test_check_mode_still_reads_and_returns_step(mock_get, mock_module_class):
    """check_mode does not skip the read; changed is always False for an info module."""
    mock_module, mock_adapter = _mock_module(
        {"stack_deployment_step_id": _SDS_ID, "stack_deployment_run_id": None},
        check_mode=True,
    )
    mock_module_class.return_value = mock_module
    mock_get.return_value = _STEP

    main()

    mock_get.assert_called_once_with(mock_adapter, _SDS_ID)
    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_step"] == _STEP
    assert result["changed"] is False
    assert result["warnings"] == []


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_stack_deployment_steps")
def test_list_by_run_id_success(mock_list, mock_module_class):
    """Providing stack_deployment_run_id returns stack_deployment_steps list."""
    steps = [_STEP, {**_STEP, "id": "sds-def456"}]
    mock_module, mock_adapter = _mock_module({"stack_deployment_step_id": None, "stack_deployment_run_id": _SDR_ID})
    mock_module_class.return_value = mock_module
    mock_list.return_value = steps

    main()

    mock_list.assert_called_once_with(mock_adapter, _SDR_ID)
    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_steps"] == steps
    assert result["changed"] is False


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_stack_deployment_steps")
def test_list_by_run_id_empty(mock_list, mock_module_class):
    """An empty run returns an empty list (no error)."""
    mock_module, mock_adapter = _mock_module({"stack_deployment_step_id": None, "stack_deployment_run_id": _SDR_ID})
    mock_module_class.return_value = mock_module
    mock_list.return_value = []

    main()

    result = mock_module.exit_json.call_args[1]
    assert result["stack_deployment_steps"] == []
    assert result["changed"] is False


_DIAG = {"id": "std-abc001", "severity": "error", "summary": "bad input"}


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_stack_diagnostics")
def test_list_diagnostics_success(mock_list_diag, mock_module_class):
    """list_diagnostics=true returns stack_diagnostics list for the given step."""
    diags = [_DIAG, {**_DIAG, "id": "std-abc002"}]
    mock_module, mock_adapter = _mock_module({"stack_deployment_step_id": _SDS_ID, "stack_deployment_run_id": None, "list_diagnostics": True})
    mock_module_class.return_value = mock_module
    mock_list_diag.return_value = diags

    main()

    mock_list_diag.assert_called_once_with(mock_adapter, _SDS_ID)
    result = mock_module.exit_json.call_args[1]
    assert result["stack_diagnostics"] == diags
    assert result["changed"] is False


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_stack_diagnostics")
def test_list_diagnostics_empty(mock_list_diag, mock_module_class):
    """list_diagnostics=true with no diagnostics returns an empty list (no error)."""
    mock_module, mock_adapter = _mock_module({"stack_deployment_step_id": _SDS_ID, "stack_deployment_run_id": None, "list_diagnostics": True})
    mock_module_class.return_value = mock_module
    mock_list_diag.return_value = []

    main()

    result = mock_module.exit_json.call_args[1]
    assert result["stack_diagnostics"] == []
    assert result["changed"] is False


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_deployment_step")
def test_list_diagnostics_false_reads_step(mock_get, mock_module_class):
    """list_diagnostics=false (default) still reads the step, not diagnostics."""
    mock_module, mock_adapter = _mock_module({"stack_deployment_step_id": _SDS_ID, "stack_deployment_run_id": None, "list_diagnostics": False})
    mock_module_class.return_value = mock_module
    mock_get.return_value = _STEP

    main()

    mock_get.assert_called_once_with(mock_adapter, _SDS_ID)
    result = mock_module.exit_json.call_args[1]
    assert "stack_deployment_step" in result
    assert "stack_diagnostics" not in result


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
def test_list_diagnostics_without_step_id_fails(mock_module_class):
    """list_diagnostics=true without stack_deployment_step_id must call fail_json."""
    mock_module = _mock_module({"stack_deployment_step_id": None, "stack_deployment_run_id": _SDR_ID, "list_diagnostics": True})[0]
    mock_module_class.return_value = mock_module

    main()

    mock_module.fail_json.assert_called_once()
    assert "list_diagnostics requires stack_deployment_step_id" in mock_module.fail_json.call_args[1]["msg"]
