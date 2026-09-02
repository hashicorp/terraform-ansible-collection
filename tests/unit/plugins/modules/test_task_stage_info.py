# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the task_stage_info module."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.task_stage_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.task_stage_info"


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


def _base_params(**overrides):
    params = {"task_stage_id": None, "run_id": None, "include": None}
    params.update(overrides)
    return params


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_task_stage")
def test_by_id_success(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module(_base_params(task_stage_id="ts-1", include=["task_results"]))
    mock_module_class.return_value = mock_module
    mock_get.return_value = {"id": "ts-1", "status": "passed"}

    main()

    mock_get.assert_called_once_with(mock_adapter, "ts-1", ["task_results"])
    result = mock_module.exit_json.call_args[1]
    assert result["task_stage"]["id"] == "ts-1"
    assert "task_stages" not in result


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_task_stage")
def test_by_id_not_found_fails(mock_get, mock_module_class):
    mock_module = _mock_module(_base_params(task_stage_id="ts-x"))[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_task_stages")
def test_list_by_run(mock_list, mock_module_class):
    mock_module, mock_adapter = _mock_module(_base_params(run_id="run-1"))
    mock_module_class.return_value = mock_module
    mock_list.return_value = [{"id": "ts-1"}, {"id": "ts-2"}]

    main()

    mock_list.assert_called_once_with(mock_adapter, "run-1")
    result = mock_module.exit_json.call_args[1]
    assert result["task_stages"] == [{"id": "ts-1"}, {"id": "ts-2"}]
    assert "task_stage" not in result
