# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/policy_set_outcome.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set_outcome import get_policy_set_outcome, list_policy_set_outcomes

MOD = "ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set_outcome"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestListPolicySetOutcomes:
    def test_success_no_filter(self):
        adapter = Mock()
        adapter.client.policy_set_outcomes.list.return_value = iter([_make_model({"id": "pso-1"})])
        assert list_policy_set_outcomes(adapter, "poleval-1") == [{"id": "pso-1"}]
        adapter.client.policy_set_outcomes.list.assert_called_once_with("poleval-1")

    def test_status_filter_is_client_side(self):
        # Regression: the server rejects filter[0][status]=... with HTTP 400
        # for this endpoint (confirmed live) - list() must be called with no
        # options at all, and filtering must happen locally.
        adapter = Mock()
        adapter.client.policy_set_outcomes.list.return_value = iter(
            [
                _make_model({"id": "pso-1", "outcomes": [{"status": "passed", "enforcement_level": "advisory"}]}),
                _make_model({"id": "pso-2", "outcomes": [{"status": "failed", "enforcement_level": "mandatory"}]}),
            ]
        )
        result = list_policy_set_outcomes(adapter, "poleval-1", status="failed")
        adapter.client.policy_set_outcomes.list.assert_called_once_with("poleval-1")
        assert [o["id"] for o in result] == ["pso-2"]

    def test_enforcement_level_filter_requires_matching_result(self):
        adapter = Mock()
        adapter.client.policy_set_outcomes.list.return_value = iter(
            [
                _make_model({"id": "pso-1", "outcomes": [{"status": "failed", "enforcement_level": "advisory"}]}),
                _make_model({"id": "pso-2", "outcomes": [{"status": "failed", "enforcement_level": "mandatory"}]}),
            ]
        )
        result = list_policy_set_outcomes(adapter, "poleval-1", status="failed", enforcement_level="mandatory")
        assert [o["id"] for o in result] == ["pso-2"]

    def test_no_matching_outcomes_returns_empty(self):
        adapter = Mock()
        adapter.client.policy_set_outcomes.list.return_value = iter([_make_model({"id": "pso-1", "outcomes": [{"status": "passed"}]})])
        assert list_policy_set_outcomes(adapter, "poleval-1", status="errored") == []

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.policy_set_outcomes.list.side_effect = NotFound("nope")
        assert list_policy_set_outcomes(adapter, "poleval-1") == []


class TestGetPolicySetOutcome:
    @patch(f"{MOD}.PolicySetOutcome")
    def test_reparses_from_leaked_attributes(self, mock_outcome_cls):
        # Regression: pytfe's read() returns a PolicySetOutcome whose real
        # fields are empty and whose raw JSON:API envelope leaks through as
        # `.attributes`/`.relationships` extras (confirmed live). The adapter
        # must re-parse from `.attributes`, not trust the object as returned.
        adapter = Mock()
        raw = Mock()
        raw.id = "pso-1"
        raw.attributes = {"outcomes": [], "policy-set-name": "my-set"}
        adapter.client.policy_set_outcomes.read.return_value = raw

        fixed = _make_model({"id": "pso-1", "policy_set_name": "my-set"})
        mock_outcome_cls.model_validate.return_value = fixed

        result = get_policy_set_outcome(adapter, "pso-1")

        mock_outcome_cls.model_validate.assert_called_once_with({"id": "pso-1", "outcomes": [], "policy-set-name": "my-set"})
        assert result == {"id": "pso-1", "policy_set_name": "my-set"}

    def test_no_leaked_attributes_falls_back_to_raw(self):
        adapter = Mock()
        raw = _make_model({"id": "pso-1"})
        del raw.attributes  # Mock() auto-creates attrs; simulate a real object with none
        raw.attributes = None
        adapter.client.policy_set_outcomes.read.return_value = raw

        assert get_policy_set_outcome(adapter, "pso-1") == {"id": "pso-1"}

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.policy_set_outcomes.read.side_effect = NotFound("missing")
        assert get_policy_set_outcome(adapter, "pso-missing") is None
