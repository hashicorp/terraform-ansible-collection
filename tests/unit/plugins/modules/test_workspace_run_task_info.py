# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the workspace_run_task_info module."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.workspace_run_task_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.workspace_run_task_info"


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
    params = {
        "workspace_id": "ws-1",
        "organization": None,
        "workspace": None,
        "workspace_run_task_id": None,
        "run_task_id": None,
        "run_task_name": None,
    }
    params.update(overrides)
    return params


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_workspace_run_task")
def test_by_id_success(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module(_base_params(workspace_run_task_id="wstask-1"))
    mock_module_class.return_value = mock_module
    mock_get.return_value = {"id": "wstask-1", "enforcement_level": "advisory"}

    main()

    mock_get.assert_called_once_with(mock_adapter, "ws-1", "wstask-1")
    result = mock_module.exit_json.call_args[1]
    assert result["workspace_run_task"]["id"] == "wstask-1"
    assert "workspace_run_tasks" not in result


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_workspace_run_task")
def test_by_id_not_found_fails(mock_get, mock_module_class):
    mock_module = _mock_module(_base_params(workspace_run_task_id="wstask-x"))[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_workspace_run_task_by_run_task")
def test_by_run_task_success(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module(_base_params(run_task_id="task-1"))
    mock_module_class.return_value = mock_module
    mock_get.return_value = {"id": "wstask-1", "run_task": {"id": "task-1"}}

    main()

    mock_get.assert_called_once_with(mock_adapter, "ws-1", "task-1")
    result = mock_module.exit_json.call_args[1]
    assert result["workspace_run_task"]["id"] == "wstask-1"
    assert result["workspace_run_tasks"] == [{"id": "wstask-1", "run_task": {"id": "task-1"}}]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_workspace_run_task_by_run_task")
def test_by_run_task_not_found_fails(mock_get, mock_module_class):
    mock_module = _mock_module(_base_params(run_task_id="task-x"))[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not associated" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_workspace_run_tasks")
def test_list_for_workspace(mock_list, mock_module_class):
    mock_module, mock_adapter = _mock_module(_base_params())
    mock_module_class.return_value = mock_module
    mock_list.return_value = [{"id": "wstask-1"}, {"id": "wstask-2"}]

    main()

    mock_list.assert_called_once_with(mock_adapter, "ws-1")
    result = mock_module.exit_json.call_args[1]
    assert result["workspace_run_tasks"] == [{"id": "wstask-1"}, {"id": "wstask-2"}]
    assert "workspace_run_task" not in result
