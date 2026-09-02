# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/stack.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.stack import (
    _desired_payload,
    _fetch_stack,
    _has_drift,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.stack"


class TestFetchStack:
    def test_by_id(self):
        with patch(f"{MODULE_PATH}.get_stack", return_value={"id": "st-1"}) as mock_get:
            assert _fetch_stack(Mock(), {"stack_id": "st-1"}) == {"id": "st-1"}
            mock_get.assert_called_once()

    def test_by_name_and_organization(self):
        adapter = Mock()
        with patch(
            f"{MODULE_PATH}.get_stack_by_name",
            return_value={"id": "st-1", "name": "stack-a"},
        ) as mock_get_by_name:
            assert _fetch_stack(adapter, {"organization": "org", "name": "stack-a"}) == {
                "id": "st-1",
                "name": "stack-a",
            }
            mock_get_by_name.assert_called_once_with(adapter, "org", "stack-a")

    def test_nothing_given(self):
        assert _fetch_stack(Mock(), {}) is None


class TestDesiredPayload:
    def test_includes_name_and_description(self):
        params = {"name": "a", "description": "desc", "project_id": "prj-1"}
        payload = _desired_payload(params)
        assert payload["name"] == "a"
        assert payload["description"] == "desc"
        assert payload["project"] == {"id": "prj-1"}

    def test_excludes_none_values(self):
        params = {
            "name": "a",
            "description": None,
            "vcs_repo": None,
        }
        payload = _desired_payload(params)
        assert "description" not in payload
        assert "vcs_repo" not in payload

    def test_includes_vcs_repo(self):
        params = {"vcs_repo": {"identifier": "org/repo", "branch": "main"}}
        payload = _desired_payload(params)
        assert payload["vcs_repo"] == {"identifier": "org/repo", "branch": "main"}

    def test_includes_agent_pool_id(self):
        params = {"agent_pool_id": "apool-1"}
        payload = _desired_payload(params)
        assert payload["agent_pool"] == {"id": "apool-1"}

    def test_empty(self):
        assert _desired_payload({}) == {}


class TestHasDrift:
    def test_name_drift(self):
        assert _has_drift({"name": "b"}, {"name": "a"}) is True

    def test_description_drift(self):
        assert _has_drift({"description": "new"}, {"description": "old"}) is True

    def test_vcs_repo_identifier_drift(self):
        current = {"vcs_repo": {"identifier": "old/repo", "branch": "main"}}
        assert _has_drift({"vcs_repo": {"identifier": "new/repo"}}, current) is True

    def test_vcs_repo_branch_drift(self):
        current = {"vcs_repo": {"identifier": "org/repo", "branch": "main"}}
        assert _has_drift({"vcs_repo": {"identifier": "org/repo", "branch": "dev"}}, current) is True

    def test_vcs_repo_no_drift(self):
        current = {"vcs_repo": {"identifier": "org/repo", "branch": "main"}}
        assert _has_drift({"vcs_repo": {"identifier": "org/repo", "branch": "main"}}, current) is False

    def test_project_id_drift(self):
        current = {"project": {"id": "prj-old"}}
        assert _has_drift({"project_id": "prj-new"}, current) is True

    def test_project_id_no_drift(self):
        current = {"project": {"id": "prj-1"}}
        assert _has_drift({"project_id": "prj-1"}, current) is False

    def test_agent_pool_id_drift(self):
        current = {"agent_pool": {"id": "apool-old"}}
        assert _has_drift({"agent_pool_id": "apool-new"}, current) is True

    def test_agent_pool_id_no_drift(self):
        current = {"agent_pool": {"id": "apool-1"}}
        assert _has_drift({"agent_pool_id": "apool-1"}, current) is False

    def test_no_drift_when_unspecified(self):
        current = {"id": "st-1", "name": "stack-a"}
        assert _has_drift({"name": "stack-a"}, current) is False

    def test_no_drift_all_none(self):
        current = {"name": "stack-a"}
        assert _has_drift({"name": None, "description": None}, current) is False


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_when_missing(self, adapter):
        params = {
            "organization": "org",
            "name": "stack-a",
            "project_id": "prj-1",
            "description": None,
            "vcs_repo": None,
            "agent_pool_id": None,
        }
        with (
            patch(f"{MODULE_PATH}._fetch_stack", return_value=None),
            patch(
                f"{MODULE_PATH}.create_stack",
                return_value={"id": "st-1", "name": "stack-a"},
            ) as mock_create,
        ):
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once_with(adapter, {"name": "stack-a", "project": {"id": "prj-1"}})
        assert result["changed"] is True
        assert result["id"] == "st-1"

    def test_create_check_mode(self, adapter):
        params = {"organization": "org", "name": "stack-a", "project_id": "prj-1"}
        with (
            patch(f"{MODULE_PATH}._fetch_stack", return_value=None),
            patch(f"{MODULE_PATH}.create_stack") as mock_create,
        ):
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_create_without_organization_raises(self, adapter):
        params = {"name": "stack-a", "project_id": "prj-1"}
        with patch(f"{MODULE_PATH}._fetch_stack", return_value=None):
            with pytest.raises(ValueError, match="organization"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_name_raises(self, adapter):
        params = {"organization": "org", "project_id": "prj-1"}
        with patch(f"{MODULE_PATH}._fetch_stack", return_value=None):
            with pytest.raises(ValueError, match="name"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_project_id_raises(self, adapter):
        params = {"organization": "org", "name": "stack-a"}
        with patch(f"{MODULE_PATH}._fetch_stack", return_value=None):
            with pytest.raises(ValueError, match="project_id"):
                state_present(adapter, params, check_mode=False)

    def test_idempotent_no_drift(self, adapter):
        current = {"id": "st-1", "name": "stack-a", "description": "desc"}
        params = {
            "organization": "org",
            "name": "stack-a",
            "description": "desc",
            "project_id": None,
        }
        with (
            patch(f"{MODULE_PATH}._fetch_stack", return_value=current),
            patch(f"{MODULE_PATH}.update_stack") as mock_update,
        ):
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "st-1"

    def test_update_on_description_drift(self, adapter):
        current = {"id": "st-1", "name": "stack-a", "description": "old"}
        params = {
            "organization": "org",
            "name": "stack-a",
            "description": "new",
            "project_id": None,
        }
        with (
            patch(f"{MODULE_PATH}._fetch_stack", return_value=current),
            patch(
                f"{MODULE_PATH}.update_stack",
                return_value={"id": "st-1", "name": "stack-a", "description": "new"},
            ) as mock_update,
        ):
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_called_once_with(adapter, "st-1", {"name": "stack-a", "description": "new"})
        assert result["changed"] is True
        assert result["description"] == "new"

    def test_update_check_mode(self, adapter):
        current = {"id": "st-1", "name": "stack-a", "description": "old"}
        params = {"organization": "org", "name": "stack-a", "description": "new"}
        with (
            patch(f"{MODULE_PATH}._fetch_stack", return_value=current),
            patch(f"{MODULE_PATH}.update_stack") as mock_update,
        ):
            result = state_present(adapter, params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_present(self, adapter):
        current = {"id": "st-1", "name": "stack-a"}
        params = {"stack_id": "st-1"}
        with (
            patch(f"{MODULE_PATH}._fetch_stack", return_value=current),
            patch(f"{MODULE_PATH}.delete_stack") as mock_delete,
        ):
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "st-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_noop_when_absent(self, adapter):
        params = {"stack_id": "st-missing"}
        with (
            patch(f"{MODULE_PATH}._fetch_stack", return_value=None),
            patch(f"{MODULE_PATH}.delete_stack") as mock_delete,
        ):
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_by_name_and_organization(self, adapter):
        current = {"id": "st-1", "name": "stack-a"}
        params = {"organization": "org", "name": "stack-a"}
        with (
            patch(f"{MODULE_PATH}._fetch_stack", return_value=current),
            patch(f"{MODULE_PATH}.delete_stack") as mock_delete,
        ):
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "st-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_delete_check_mode(self, adapter):
        current = {"id": "st-1", "name": "stack-a"}
        params = {"stack_id": "st-1"}
        with (
            patch(f"{MODULE_PATH}._fetch_stack", return_value=current),
            patch(f"{MODULE_PATH}.delete_stack") as mock_delete,
        ):
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]
