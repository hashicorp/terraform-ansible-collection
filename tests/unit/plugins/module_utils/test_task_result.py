# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/task_result.py (pytfe adapter)."""

from unittest.mock import Mock

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.task_result import get_task_result


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestGetTaskResult:
    def test_success(self):
        adapter = Mock()
        adapter.client.task_results.read.return_value = _make_model({"id": "taskrs-1", "status": "passed"})
        assert get_task_result(adapter, "taskrs-1") == {"id": "taskrs-1", "status": "passed"}
        adapter.client.task_results.read.assert_called_once_with("taskrs-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.task_results.read.side_effect = NotFound("missing")
        assert get_task_result(adapter, "taskrs-missing") is None
