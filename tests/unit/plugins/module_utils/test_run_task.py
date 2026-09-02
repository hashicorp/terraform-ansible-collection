# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/run_task.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.run_task import (
    create_run_task,
    delete_run_task,
    get_run_task,
    get_run_task_by_name,
    list_run_tasks,
    update_run_task,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.run_task"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestListRunTasks:
    def test_success(self):
        adapter = Mock()
        adapter.client.run_tasks.list.return_value = iter([_make_model({"id": "task-1", "name": "a"}), _make_model({"id": "task-2", "name": "b"})])
        assert list_run_tasks(adapter, "my-org") == [
            {"id": "task-1", "name": "a"},
            {"id": "task-2", "name": "b"},
        ]
        adapter.client.run_tasks.list.assert_called_once_with("my-org")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.run_tasks.list.side_effect = NotFound("nope")
        assert list_run_tasks(adapter, "my-org") == []


class TestGetRunTask:
    def test_success(self):
        adapter = Mock()
        adapter.client.run_tasks.read.return_value = _make_model({"id": "task-1", "name": "a"})
        assert get_run_task(adapter, "task-1") == {"id": "task-1", "name": "a"}
        adapter.client.run_tasks.read.assert_called_once_with("task-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.run_tasks.read.side_effect = NotFound("missing")
        assert get_run_task(adapter, "task-missing") is None


class TestGetRunTaskByName:
    def test_match(self):
        adapter = Mock()
        adapter.client.run_tasks.list.return_value = iter([_make_model({"id": "task-1", "name": "a"}), _make_model({"id": "task-2", "name": "b"})])
        assert get_run_task_by_name(adapter, "org", "b") == {"id": "task-2", "name": "b"}

    def test_no_match(self):
        adapter = Mock()
        adapter.client.run_tasks.list.return_value = iter([])
        assert get_run_task_by_name(adapter, "org", "ghost") is None


class TestCreateRunTask:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RunTaskCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "task-1", "name": "scan"})

        data = {"name": "scan", "url": "https://x", "category": "task"}
        result = create_run_task(adapter, "my-org", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.run_tasks.create
        assert args[1] == "my-org"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "task-1", "name": "scan"}


class TestUpdateRunTask:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RunTaskUpdateOptions")
    def test_update_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "task-1", "name": "renamed"})

        data = {"name": "renamed"}
        result = update_run_task(adapter, "task-1", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.run_tasks.update
        assert args[1] == "task-1"
        assert args[2] is opts
        assert result == {"id": "task-1", "name": "renamed"}


class TestDeleteRunTask:
    @patch(f"{MU_PATH}.safe_api_call")
    def test_delete(self, mock_safe_call):
        adapter = Mock()
        delete_run_task(adapter, "task-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.run_tasks.delete
        assert args[1] == "task-1"
        assert "error_context" in kwargs
