# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/policy_evaluation.py (pytfe adapter)."""

from unittest.mock import Mock

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_evaluation import list_policy_evaluations


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestListPolicyEvaluations:
    def test_success(self):
        adapter = Mock()
        adapter.client.policy_evaluations.list.return_value = iter([_make_model({"id": "poleval-1", "status": "passed"})])
        assert list_policy_evaluations(adapter, "ts-1") == [{"id": "poleval-1", "status": "passed"}]
        adapter.client.policy_evaluations.list.assert_called_once_with("ts-1")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.policy_evaluations.list.side_effect = NotFound("nope")
        assert list_policy_evaluations(adapter, "ts-1") == []
