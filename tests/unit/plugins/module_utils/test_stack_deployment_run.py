# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/stack_deployment_run.py (pytfe adapter)."""

from unittest.mock import Mock

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_deployment_run import (
    get_stack_deployment_run,
    list_stack_deployment_runs,
)

_SDR_ID = "sdr-abc123"
_RUN_PAYLOAD = {
    "id": _SDR_ID,
    "status": "pre-deploying-pending-operator",
    "created_at": "2026-07-02T09:40:37+00:00",
    "updated_at": "2026-07-02T09:40:38+00:00",
}


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


_SDG_ID = "sdg-xyz789"


class TestGetStackDeploymentRun:
    def test_success(self):
        adapter = Mock()
        adapter.client.stack_deployment_runs.read.return_value = _make_model(_RUN_PAYLOAD)
        result = get_stack_deployment_run(adapter, _SDR_ID)
        adapter.client.stack_deployment_runs.read.assert_called_once_with(_SDR_ID)
        assert result == _RUN_PAYLOAD

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.stack_deployment_runs.read.side_effect = NotFound("missing")
        assert get_stack_deployment_run(adapter, "sdr-missing") is None


class TestListStackDeploymentRuns:
    def test_returns_list_of_runs(self):
        adapter = Mock()
        adapter.client.stack_deployment_runs.list.return_value = [_make_model(_RUN_PAYLOAD)]
        result = list_stack_deployment_runs(adapter, _SDG_ID)
        adapter.client.stack_deployment_runs.list.assert_called_once_with(_SDG_ID)
        assert result == [_RUN_PAYLOAD]

    def test_empty_iterator_returns_empty_list(self):
        adapter = Mock()
        adapter.client.stack_deployment_runs.list.return_value = []
        result = list_stack_deployment_runs(adapter, _SDG_ID)
        assert result == []

    def test_not_found_returns_empty_list(self):
        adapter = Mock()
        adapter.client.stack_deployment_runs.list.side_effect = NotFound("missing")
        assert list_stack_deployment_runs(adapter, _SDG_ID) == []
