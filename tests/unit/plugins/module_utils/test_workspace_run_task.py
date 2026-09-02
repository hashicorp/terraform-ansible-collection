# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/workspace_run_task.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace_run_task import (
    create_workspace_run_task,
    delete_workspace_run_task,
    get_workspace_run_task,
    get_workspace_run_task_by_run_task,
    list_workspace_run_tasks,
    update_workspace_run_task,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.workspace_run_task"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestListWorkspaceRunTasks:
    def test_success(self):
        adapter = Mock()
        adapter.client.workspace_run_tasks.list.return_value = iter(
            [
                _make_model({"id": "wstask-1", "enforcement_level": "advisory"}),
                _make_model({"id": "wstask-2", "enforcement_level": "mandatory"}),
            ]
        )
        assert list_workspace_run_tasks(adapter, "ws-1") == [
            {"id": "wstask-1", "enforcement_level": "advisory"},
            {"id": "wstask-2", "enforcement_level": "mandatory"},
        ]
        adapter.client.workspace_run_tasks.list.assert_called_once_with("ws-1")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.workspace_run_tasks.list.side_effect = NotFound("nope")
        assert list_workspace_run_tasks(adapter, "ws-1") == []


class TestGetWorkspaceRunTask:
    def test_success(self):
        adapter = Mock()
        adapter.client.workspace_run_tasks.read.return_value = _make_model({"id": "wstask-1"})
        assert get_workspace_run_task(adapter, "ws-1", "wstask-1") == {"id": "wstask-1"}
        adapter.client.workspace_run_tasks.read.assert_called_once_with("ws-1", "wstask-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.workspace_run_tasks.read.side_effect = NotFound("missing")
        assert get_workspace_run_task(adapter, "ws-1", "wstask-missing") is None


class TestGetWorkspaceRunTaskByRunTask:
    def test_match(self):
        adapter = Mock()
        adapter.client.workspace_run_tasks.list.return_value = iter(
            [
                _make_model({"id": "wstask-1", "run_task": {"id": "task-1"}}),
                _make_model({"id": "wstask-2", "run_task": {"id": "task-2"}}),
            ]
        )
        assert get_workspace_run_task_by_run_task(adapter, "ws-1", "task-2") == {
            "id": "wstask-2",
            "run_task": {"id": "task-2"},
        }

    def test_no_match(self):
        adapter = Mock()
        adapter.client.workspace_run_tasks.list.return_value = iter([])
        assert get_workspace_run_task_by_run_task(adapter, "ws-1", "task-ghost") is None


class TestCreateWorkspaceRunTask:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.WorkspaceRunTaskCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "wstask-1", "enforcement_level": "advisory"})

        data = {"enforcement_level": "advisory", "run_task": {"id": "task-1"}}
        result = create_workspace_run_task(adapter, "ws-1", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.workspace_run_tasks.create
        assert args[1] == "ws-1"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "wstask-1", "enforcement_level": "advisory"}


class TestUpdateWorkspaceRunTask:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.WorkspaceRunTaskUpdateOptions")
    def test_update_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "wstask-1", "enforcement_level": "mandatory"})

        data = {"enforcement_level": "mandatory"}
        result = update_workspace_run_task(adapter, "ws-1", "wstask-1", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.workspace_run_tasks.update
        assert args[1] == "ws-1"
        assert args[2] == "wstask-1"
        assert args[3] is opts
        assert result == {"id": "wstask-1", "enforcement_level": "mandatory"}


class TestDeleteWorkspaceRunTask:
    @patch(f"{MU_PATH}.safe_api_call")
    def test_delete(self, mock_safe_call):
        adapter = Mock()
        delete_workspace_run_task(adapter, "ws-1", "wstask-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.workspace_run_tasks.delete
        assert args[1] == "ws-1"
        assert args[2] == "wstask-1"
        assert "error_context" in kwargs
