# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/policy_set.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.policy_set import (
    _plan_relationship_syncs,
    state_absent,
    state_present,
)

MOD = "ansible_collections.hashicorp.terraform.plugins.modules.policy_set"


class TestPlanRelationshipSyncs:
    def test_no_params_supplied_yields_no_plans(self):
        current = {"policies": [{"id": "pol-1"}]}
        assert _plan_relationship_syncs({}, current) == []

    def test_no_drift_yields_no_plans(self):
        current = {"policies": [{"id": "pol-1"}, {"id": "pol-2"}]}
        params = {"policy_ids": ["pol-2", "pol-1"]}  # order-independent
        assert _plan_relationship_syncs(params, current) == []

    def test_add_and_remove_detected(self):
        current = {"workspaces": [{"id": "ws-1"}, {"id": "ws-2"}]}
        params = {"workspace_ids": ["ws-2", "ws-3"]}
        plans = _plan_relationship_syncs(params, current)
        assert plans == [("workspaces", ["ws-3"], ["ws-1"])]

    def test_multiple_relationships(self):
        current = {"policies": [{"id": "pol-1"}], "projects": [{"id": "prj-1"}]}
        params = {"policy_ids": ["pol-1", "pol-2"], "project_ids": []}
        plans = _plan_relationship_syncs(params, current)
        assert ("policies", ["pol-2"], []) in plans
        assert ("projects", [], ["prj-1"]) in plans


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def _base_params(self, **overrides):
        params = {
            "policy_set_id": None,
            "organization": "my-org",
            "name": "baseline",
            "description": None,
            "kind": None,
            "global": None,
            "overridable": None,
            "agent_enabled": None,
            "policy_tool_version": None,
            "policies_path": None,
            "vcs_repo": None,
            "policy_ids": None,
            "workspace_ids": None,
            "workspace_exclusion_ids": None,
            "project_ids": None,
            "project_exclusion_ids": None,
            "state": "present",
            "check_mode": False,
        }
        params.update(overrides)
        return params

    def test_create_when_missing(self, adapter):
        # Regression: pytfe's PolicySets.create() cannot accept relationship
        # data (see create_policy_set()'s docstring) - create_data must never
        # carry a relationship key, even when the caller supplies policy_ids.
        params = self._base_params(policy_ids=["pol-1"])
        with patch(f"{MOD}._fetch_policy_set", return_value=None), patch(
            f"{MOD}.create_policy_set", return_value={"id": "polset-1", "name": "baseline"}
        ) as mock_create, patch(f"{MOD}.sync_relationship") as mock_sync, patch(
            f"{MOD}.get_policy_set", return_value={"id": "polset-1", "policies": [{"id": "pol-1"}]}
        ):
            result = state_present(adapter, params, check_mode=False)

        create_data = mock_create.call_args[0][2]
        assert create_data["kind"] == "sentinel"
        assert "policies" not in create_data
        mock_sync.assert_called_once_with(adapter, "polset-1", "policies", add_ids=["pol-1"], remove_ids=[])
        assert result["changed"] is True
        assert result["id"] == "polset-1"

    def test_create_with_project_exclusions_syncs_after_create(self, adapter):
        params = self._base_params(project_exclusion_ids=["prj-1"])
        with patch(f"{MOD}._fetch_policy_set", return_value=None), patch(
            f"{MOD}.create_policy_set", return_value={"id": "polset-1", "name": "baseline"}
        ), patch(f"{MOD}.sync_relationship") as mock_sync, patch(
            f"{MOD}.get_policy_set", return_value={"id": "polset-1", "project_exclusions": [{"id": "prj-1"}]}
        ):
            result = state_present(adapter, params, check_mode=False)

        mock_sync.assert_called_once_with(adapter, "polset-1", "project_exclusions", add_ids=["prj-1"], remove_ids=[])
        assert result["project_exclusions"] == [{"id": "prj-1"}]

    def test_create_check_mode(self, adapter):
        params = self._base_params(check_mode=True)
        with patch(f"{MOD}._fetch_policy_set", return_value=None), patch(f"{MOD}.create_policy_set") as mock_create:
            result = state_present(adapter, params, check_mode=True)

        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_kind_drift_raises(self, adapter):
        current = {"id": "polset-1", "kind": "opa"}
        params = self._base_params(kind="sentinel")
        with patch(f"{MOD}._fetch_policy_set", return_value=current):
            with pytest.raises(ValueError, match="immutable"):
                state_present(adapter, params, check_mode=False)

    def test_unset_kind_does_not_false_positive_drift(self, adapter):
        current = {"id": "polset-1", "kind": "opa", "name": "baseline"}
        params = self._base_params()  # kind left unset
        with patch(f"{MOD}._fetch_policy_set", return_value=current), patch(f"{MOD}.update_policy_set") as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False

    def test_idempotent_no_diff(self, adapter):
        current = {"id": "polset-1", "name": "baseline", "kind": "sentinel", "policies": [{"id": "pol-1"}]}
        params = self._base_params(policy_ids=["pol-1"])
        with patch(f"{MOD}._fetch_policy_set", return_value=current), patch(f"{MOD}.update_policy_set") as mock_update, patch(
            f"{MOD}.sync_relationship"
        ) as mock_sync:
            result = state_present(adapter, params, check_mode=False)

        mock_update.assert_not_called()
        mock_sync.assert_not_called()
        assert result["changed"] is False

    def test_attr_and_relationship_update(self, adapter):
        current = {"id": "polset-1", "name": "baseline", "description": "old", "kind": "sentinel", "policies": [{"id": "pol-1"}]}
        params = self._base_params(description="new", policy_ids=["pol-2"])
        with patch(f"{MOD}._fetch_policy_set", return_value=current), patch(f"{MOD}.update_policy_set") as mock_update, patch(
            f"{MOD}.sync_relationship"
        ) as mock_sync, patch(f"{MOD}.get_policy_set", return_value={"id": "polset-1", "description": "new", "policies": [{"id": "pol-2"}]}):
            result = state_present(adapter, params, check_mode=False)

        mock_update.assert_called_once_with(adapter, "polset-1", {"description": "new"})
        mock_sync.assert_called_once_with(adapter, "polset-1", "policies", ["pol-2"], ["pol-1"])
        assert result["changed"] is True
        assert result["description"] == "new"

    def test_update_check_mode(self, adapter):
        current = {"id": "polset-1", "name": "baseline", "description": "old", "kind": "sentinel"}
        params = self._base_params(description="new")
        with patch(f"{MOD}._fetch_policy_set", return_value=current), patch(f"{MOD}.update_policy_set") as mock_update:
            result = state_present(adapter, params, check_mode=True)

        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_existing(self, adapter):
        current = {"id": "polset-1"}
        params = {"policy_set_id": "polset-1", "organization": None, "name": None, "state": "absent", "check_mode": False}
        with patch(f"{MOD}._fetch_policy_set", return_value=current), patch(f"{MOD}.delete_policy_set") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)

        mock_delete.assert_called_once_with(adapter, "polset-1")
        assert result["changed"] is True

    def test_delete_absent_is_noop(self, adapter):
        params = {"policy_set_id": "polset-ghost", "organization": None, "name": None, "state": "absent", "check_mode": False}
        with patch(f"{MOD}._fetch_policy_set", return_value=None):
            result = state_absent(adapter, params, check_mode=False)
        assert result["changed"] is False
