# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/tf_policy_evaluation.py (pytfe adapter)."""

from unittest.mock import Mock

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.tf_policy_evaluation import (
    get_evaluation,
    get_set_outcome,
    list_evaluations,
    list_set_outcomes,
    override_evaluation,
)


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestListEvaluations:
    def test_success(self):
        adapter = Mock()
        adapter.client.tf_policy_evaluations.list.return_value = iter([_make_model({"id": "tfpeval-1", "status": "passed"})])
        assert list_evaluations(adapter, "run-1") == [{"id": "tfpeval-1", "status": "passed"}]
        adapter.client.tf_policy_evaluations.list.assert_called_once_with("run-1")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.tf_policy_evaluations.list.side_effect = NotFound("nope")
        assert list_evaluations(adapter, "run-1") == []


class TestGetEvaluation:
    def test_success(self):
        adapter = Mock()
        adapter.client.tf_policy_evaluations.read.return_value = _make_model({"id": "tfpeval-1", "status": "awaiting_override"})
        result = get_evaluation(adapter, "tfpeval-1")
        assert result == {"id": "tfpeval-1", "status": "awaiting_override"}
        args, kwargs = adapter.client.tf_policy_evaluations.read.call_args
        assert args == ("tfpeval-1",)
        assert kwargs["options"].include is None

    def test_include_outcomes_sets_include_param(self):
        adapter = Mock()
        adapter.client.tf_policy_evaluations.read.return_value = _make_model({"id": "tfpeval-1"})
        get_evaluation(adapter, "tfpeval-1", include_outcomes=True)
        _args, kwargs = adapter.client.tf_policy_evaluations.read.call_args
        assert kwargs["options"].include == "tf_policy_set_outcomes"

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.tf_policy_evaluations.read.side_effect = NotFound("nope")
        assert get_evaluation(adapter, "tfpeval-missing") is None


class TestListSetOutcomes:
    def test_success(self):
        adapter = Mock()
        adapter.client.tf_policy_evaluations.list_set_outcomes.return_value = iter([_make_model({"id": "tfpsout-1", "policy_set_name": "baseline"})])
        result = list_set_outcomes(adapter, "tfpeval-1")
        assert result == [{"id": "tfpsout-1", "policy_set_name": "baseline"}]

    def test_filters_forwarded(self):
        adapter = Mock()
        adapter.client.tf_policy_evaluations.list_set_outcomes.return_value = iter([])
        list_set_outcomes(adapter, "tfpeval-1", filter_status="failed", filter_enforcement_level="mandatory_overridable")
        _args, kwargs = adapter.client.tf_policy_evaluations.list_set_outcomes.call_args
        assert kwargs["options"].filter_status == "failed"
        assert kwargs["options"].filter_enforcement_level == "mandatory_overridable"

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.tf_policy_evaluations.list_set_outcomes.side_effect = NotFound("nope")
        assert list_set_outcomes(adapter, "tfpeval-1") == []


class TestGetSetOutcome:
    def test_success(self):
        adapter = Mock()
        adapter.client.tf_policy_set_outcomes.read.return_value = _make_model({"id": "tfpsout-1"})
        assert get_set_outcome(adapter, "tfpsout-1") == {"id": "tfpsout-1"}

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.tf_policy_set_outcomes.read.side_effect = NotFound("nope")
        assert get_set_outcome(adapter, "tfpsout-missing") is None


class TestOverrideEvaluation:
    def test_with_comment(self):
        adapter = Mock()
        adapter.client.tf_policy_evaluations.override.return_value = _make_model({"id": "tfpeval-1", "status": "overridden"})
        result = override_evaluation(adapter, "tfpeval-1", comment="approved")
        assert result == {"id": "tfpeval-1", "status": "overridden"}
        args, _kwargs = adapter.client.tf_policy_evaluations.override.call_args
        assert args[0] == "tfpeval-1"
        assert args[1].comment == "approved"

    def test_without_comment(self):
        adapter = Mock()
        adapter.client.tf_policy_evaluations.override.return_value = _make_model({"id": "tfpeval-1", "status": "overridden"})
        override_evaluation(adapter, "tfpeval-1")
        args, _kwargs = adapter.client.tf_policy_evaluations.override.call_args
        assert args[1].comment is None
