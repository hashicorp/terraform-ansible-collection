# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/agent_pool.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.agent_pool import (
    _desired_payload,
    _fetch_agent_pool,
    _has_drift,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.agent_pool"


class TestFetch:
    def test_by_id(self):
        with patch(f"{MODULE_PATH}.get_agent_pool", return_value={"id": "apool-1"}) as mock_get:
            assert _fetch_agent_pool(Mock(), {"agent_pool_id": "apool-1"}) == {"id": "apool-1"}
            mock_get.assert_called_once()

    def test_by_name(self):
        with patch(f"{MODULE_PATH}.get_agent_pool_by_name", return_value={"id": "apool-1", "name": "a"}) as mock_get:
            result = _fetch_agent_pool(Mock(), {"organization": "org", "name": "a"})
        assert result["id"] == "apool-1"
        mock_get.assert_called_once()

    def test_nothing_given(self):
        assert _fetch_agent_pool(Mock(), {}) is None


class TestDesiredPayload:
    def test_includes_only_supplied(self):
        params = {"name": "a", "organization_scoped": True, "allowed_workspace_ids": ["ws-1"], "excluded_workspace_ids": None}
        assert _desired_payload(params) == {"name": "a", "organization_scoped": True, "allowed_workspace_ids": ["ws-1"]}

    def test_empty(self):
        assert _desired_payload({}) == {}


class TestHasDrift:
    def test_name_drift(self):
        assert _has_drift({"name": "b"}, {"name": "a"}) is True

    def test_organization_scoped_drift(self):
        assert _has_drift({"organization_scoped": False}, {"organization_scoped": True}) is True

    def test_allowed_workspace_ids_drift(self):
        current = {"allowed_workspaces": [{"id": "ws-1"}]}
        assert _has_drift({"allowed_workspace_ids": ["ws-1", "ws-2"]}, current) is True

    def test_allowed_workspace_ids_no_drift_order_independent(self):
        current = {"allowed_workspaces": [{"id": "ws-2"}, {"id": "ws-1"}]}
        assert _has_drift({"allowed_workspace_ids": ["ws-1", "ws-2"]}, current) is False

    def test_allowed_project_ids_drift(self):
        current = {"allowed_projects": []}
        assert _has_drift({"allowed_project_ids": ["prj-1"]}, current) is True

    def test_no_drift_when_unspecified(self):
        current = {"name": "a", "organization_scoped": True, "allowed_workspaces": [{"id": "ws-1"}]}
        assert _has_drift({"name": "a"}, current) is False


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_when_missing(self, adapter):
        params = {"organization": "org", "name": "a", "organization_scoped": True, "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_agent_pool", return_value=None), patch(
            f"{MODULE_PATH}.create_agent_pool", return_value={"id": "apool-1", "name": "a"}
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once_with(adapter, "org", {"name": "a", "organization_scoped": True})
        assert result["changed"] is True
        assert result["id"] == "apool-1"

    def test_create_check_mode(self, adapter):
        params = {"organization": "org", "name": "a", "check_mode": True}
        with patch(f"{MODULE_PATH}._fetch_agent_pool", return_value=None), patch(f"{MODULE_PATH}.create_agent_pool") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_create_without_organization_raises(self, adapter):
        params = {"name": "a", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_agent_pool", return_value=None):
            with pytest.raises(ValueError, match="organization"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_name_raises(self, adapter):
        params = {"organization": "org", "agent_pool_id": "apool-x", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_agent_pool", return_value=None):
            with pytest.raises(ValueError, match="name"):
                state_present(adapter, params, check_mode=False)

    def test_idempotent_no_drift(self, adapter):
        current = {"id": "apool-1", "name": "a", "organization_scoped": True}
        params = {"organization": "org", "name": "a", "organization_scoped": True, "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_agent_pool", return_value=current), patch(f"{MODULE_PATH}.update_agent_pool") as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "apool-1"

    def test_update_on_name_drift(self, adapter):
        current = {"id": "apool-1", "name": "a"}
        params = {"organization": "org", "name": "renamed", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_agent_pool", return_value=current), patch(
            f"{MODULE_PATH}.update_agent_pool", return_value={"id": "apool-1", "name": "renamed"}
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_called_once_with(adapter, "apool-1", {"name": "renamed"})
        assert result["changed"] is True
        assert result["name"] == "renamed"

    def test_update_check_mode(self, adapter):
        current = {"id": "apool-1", "name": "a"}
        params = {"organization": "org", "name": "renamed", "check_mode": True}
        with patch(f"{MODULE_PATH}._fetch_agent_pool", return_value=current), patch(f"{MODULE_PATH}.update_agent_pool") as mock_update:
            result = state_present(adapter, params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_present(self, adapter):
        current = {"id": "apool-1", "name": "a"}
        params = {"agent_pool_id": "apool-1", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_agent_pool", return_value=current), patch(f"{MODULE_PATH}.delete_agent_pool") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "apool-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_noop_when_absent(self, adapter):
        params = {"agent_pool_id": "apool-missing", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_agent_pool", return_value=None), patch(f"{MODULE_PATH}.delete_agent_pool") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        current = {"id": "apool-1", "name": "a"}
        params = {"agent_pool_id": "apool-1", "check_mode": True}
        with patch(f"{MODULE_PATH}._fetch_agent_pool", return_value=current), patch(f"{MODULE_PATH}.delete_agent_pool") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]
