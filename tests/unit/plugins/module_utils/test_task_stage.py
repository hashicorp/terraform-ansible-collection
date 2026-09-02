# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/task_stage.py (pytfe adapter)."""

from unittest.mock import Mock

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.task_stage import (
    get_task_stage,
    list_task_stages,
)


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestGetTaskStage:
    def test_success(self):
        adapter = Mock()
        adapter.client.task_stages.read.return_value = _make_model({"id": "ts-1", "status": "passed"})
        assert get_task_stage(adapter, "ts-1") == {"id": "ts-1", "status": "passed"}
        adapter.client.task_stages.read.assert_called_once_with("ts-1", None)

    def test_with_include_builds_options(self):
        adapter = Mock()
        adapter.client.task_stages.read.return_value = _make_model({"id": "ts-1"})
        get_task_stage(adapter, "ts-1", ["task_results", "run"])
        args, _kwargs = adapter.client.task_stages.read.call_args
        assert args[0] == "ts-1"
        options = args[1]
        assert options is not None
        # Underscore choices map to the API's hyphenated include values.
        assert [opt.value for opt in options.include] == ["task-results", "run"]

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.task_stages.read.side_effect = NotFound("missing")
        assert get_task_stage(adapter, "ts-missing") is None


class TestListTaskStages:
    def test_success(self):
        adapter = Mock()
        adapter.client.task_stages.list.return_value = iter([_make_model({"id": "ts-1"}), _make_model({"id": "ts-2"})])
        assert list_task_stages(adapter, "run-1") == [{"id": "ts-1"}, {"id": "ts-2"}]
        adapter.client.task_stages.list.assert_called_once_with("run-1")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.task_stages.list.side_effect = NotFound("nope")
        assert list_task_stages(adapter, "run-1") == []
