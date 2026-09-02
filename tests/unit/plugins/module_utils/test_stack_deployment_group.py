# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/stack_deployment_group.py (pytfe adapter)."""

from unittest.mock import Mock

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_deployment_group import (
    get_stack_deployment_group,
    get_stack_deployment_group_by_name,
)


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


_SDG_ID = "sdg-xyz789"
_STC_ID = "stc-abc123"
_GROUP_PAYLOAD = {
    "id": _SDG_ID,
    "name": "dev",
    "status": "deploying",
    "created_at": "2026-07-02T09:40:00+00:00",
    "updated_at": "2026-07-02T09:41:00+00:00",
}


class TestGetStackDeploymentGroup:
    def test_success(self):
        adapter = Mock()
        adapter.client.stack_deployment_groups.read.return_value = _make_model(_GROUP_PAYLOAD)
        result = get_stack_deployment_group(adapter, _SDG_ID)
        adapter.client.stack_deployment_groups.read.assert_called_once_with(_SDG_ID)
        assert result == _GROUP_PAYLOAD

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.stack_deployment_groups.read.side_effect = NotFound("missing")
        assert get_stack_deployment_group(adapter, "sdg-missing") is None


class TestGetStackDeploymentGroupByName:
    def test_success(self):
        adapter = Mock()
        adapter.client.stack_deployment_groups.read_by_name.return_value = _make_model(_GROUP_PAYLOAD)
        result = get_stack_deployment_group_by_name(adapter, _STC_ID, "dev")
        adapter.client.stack_deployment_groups.read_by_name.assert_called_once_with(_STC_ID, "dev")
        assert result["name"] == "dev"
        assert result["id"] == _SDG_ID

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.stack_deployment_groups.read_by_name.side_effect = NotFound("missing")
        assert get_stack_deployment_group_by_name(adapter, _STC_ID, "ghost") is None
