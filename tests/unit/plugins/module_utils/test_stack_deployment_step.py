# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/stack_deployment_step.py (pytfe adapter)."""

from unittest.mock import Mock

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_deployment_step import (
    get_stack_deployment_step,
)

_SDS_ID = "sds-abc123"
_STEP_PAYLOAD = {
    "id": _SDS_ID,
    "status": "running",
    "operation_type": "plan",
    "created_at": "2026-07-02T09:40:37+00:00",
    "updated_at": "2026-07-02T09:40:38+00:00",
}


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestGetStackDeploymentStep:
    def test_success(self):
        adapter = Mock()
        adapter.client.stack_deployment_steps.read.return_value = _make_model(_STEP_PAYLOAD)
        result = get_stack_deployment_step(adapter, _SDS_ID)
        adapter.client.stack_deployment_steps.read.assert_called_once_with(_SDS_ID)
        assert result == _STEP_PAYLOAD

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.stack_deployment_steps.read.side_effect = NotFound("missing")
        assert get_stack_deployment_step(adapter, "sds-missing") is None
