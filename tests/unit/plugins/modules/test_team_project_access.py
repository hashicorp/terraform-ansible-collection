# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/team_project_access.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.team_project_access import (
    _build_desired,
    _has_diff,
    main,
    state_absent,
    state_present,
)
from tests.unit.conftest import DummyModule

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.team_project_access"

TEST_TPA_ID = "tpa-test123"
TEST_TEAM_ID = "team-abc123"
TEST_PROJECT_ID = "prj-xyz789"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter():
    return Mock()


@pytest.fixture
def existing_read():
    """Existing grant with access=read."""
    return {
        "id": TEST_TPA_ID,
        "access": "read",
        "team_id": TEST_TEAM_ID,
        "project_id": TEST_PROJECT_ID,
    }


@pytest.fixture
def existing_custom():
    """Existing grant with access=custom and permission fields set."""
    return {
        "id": TEST_TPA_ID,
        "access": "custom",
        "project_settings": "read",
        "project_teams": "none",
        "project_variable_sets": "read",
        "workspace_runs": "apply",
        "workspace_variables": "write",
        "workspace_locking": True,
        "workspace_create": False,
        "workspace_delete": False,
        "workspace_move": False,
        "workspace_run_tasks": False,
        "team_id": TEST_TEAM_ID,
        "project_id": TEST_PROJECT_ID,
    }


# ---------------------------------------------------------------------------
# TestBuildDesired
# ---------------------------------------------------------------------------


class TestBuildDesired:
    def test_simple_access(self):
        params = {"access": "read", "project_settings": None, "workspace_runs": None}
        result = _build_desired(params)
        assert result == {"access": "read"}

    def test_custom_with_project_fields(self):
        params = {
            "access": "custom",
            "project_settings": "update",
            "project_teams": "manage",
            "project_variable_sets": None,
            "workspace_runs": None,
            "workspace_variables": None,
            "workspace_locking": None,
            "workspace_create": None,
            "workspace_delete": None,
            "workspace_move": None,
            "workspace_run_tasks": None,
            "workspace_sentinel_mocks": None,
            "workspace_state_versions": None,
        }
        result = _build_desired(params)
        assert result["access"] == "custom"
        assert result["project_settings"] == "update"
        assert result["project_teams"] == "manage"
        assert "project_variable_sets" not in result

    def test_none_fields_excluded(self):
        params = {"access": "maintain", "project_settings": None, "workspace_runs": None, "workspace_locking": None}
        result = _build_desired(params)
        assert list(result.keys()) == ["access"]


# ---------------------------------------------------------------------------
# TestHasDiff
# ---------------------------------------------------------------------------


class TestHasDiff:
    def test_no_diff_same_access(self):
        existing = {"id": TEST_TPA_ID, "access": "read", "team_id": TEST_TEAM_ID}
        desired = {"access": "read"}
        assert not _has_diff(existing, desired)

    def test_diff_access_changed(self):
        existing = {"id": TEST_TPA_ID, "access": "read", "team_id": TEST_TEAM_ID}
        desired = {"access": "maintain"}
        assert _has_diff(existing, desired)

    def test_diff_project_permission_changed(self):
        existing = {"id": TEST_TPA_ID, "access": "custom", "project_settings": "read"}
        desired = {"access": "custom", "project_settings": "update"}
        assert _has_diff(existing, desired)

    def test_no_diff_custom_all_match(self):
        existing = {"id": TEST_TPA_ID, "access": "custom", "workspace_runs": "apply", "project_settings": "read"}
        desired = {"access": "custom", "workspace_runs": "apply", "project_settings": "read"}
        assert not _has_diff(existing, desired)


# ---------------------------------------------------------------------------
# TestStatePresent
# ---------------------------------------------------------------------------


class TestStatePresent:
    def test_create_when_not_exists(self, adapter):
        params = {"access": "read", "team_id": TEST_TEAM_ID, "project_id": TEST_PROJECT_ID}
        created = {"id": TEST_TPA_ID, "access": "read", "team_id": TEST_TEAM_ID, "project_id": TEST_PROJECT_ID}
        with patch(f"{MODULE_PATH}.add_team_project_access", return_value=created) as mock_add:
            result = state_present(adapter, params, existing=None)
        assert result["changed"] is True
        assert result["id"] == TEST_TPA_ID
        mock_add.assert_called_once()

    def test_create_passes_team_and_project_ids(self, adapter):
        params = {"access": "write", "team_id": TEST_TEAM_ID, "project_id": TEST_PROJECT_ID}
        created = {"id": TEST_TPA_ID, "access": "write", "team_id": TEST_TEAM_ID, "project_id": TEST_PROJECT_ID}
        with patch(f"{MODULE_PATH}.add_team_project_access", return_value=created) as mock_add:
            state_present(adapter, params, existing=None)
        call_options = mock_add.call_args[0][1]
        assert call_options["team_id"] == TEST_TEAM_ID
        assert call_options["project_id"] == TEST_PROJECT_ID

    def test_create_check_mode_skips_api(self, adapter):
        params = {"access": "read", "team_id": TEST_TEAM_ID, "project_id": TEST_PROJECT_ID}
        with patch(f"{MODULE_PATH}.add_team_project_access") as mock_add:
            result = state_present(adapter, params, existing=None, check_mode=True)
        assert result["changed"] is True
        assert "check mode" in result["msg"]
        mock_add.assert_not_called()

    def test_idempotent_no_diff_returns_existing(self, adapter, existing_read):
        params = {"access": "read", "team_id": TEST_TEAM_ID, "project_id": TEST_PROJECT_ID}
        with patch(f"{MODULE_PATH}.update_team_project_access") as mock_update:
            result = state_present(adapter, params, existing=existing_read)
        assert result["changed"] is False
        assert result["id"] == TEST_TPA_ID
        assert result["access"] == "read"
        assert result["team_id"] == TEST_TEAM_ID
        assert result["project_id"] == TEST_PROJECT_ID
        mock_update.assert_not_called()

    def test_update_when_diff(self, adapter, existing_read):
        params = {"access": "maintain", "team_id": TEST_TEAM_ID, "project_id": TEST_PROJECT_ID}
        updated = {"id": TEST_TPA_ID, "access": "maintain", "team_id": TEST_TEAM_ID, "project_id": TEST_PROJECT_ID}
        with patch(f"{MODULE_PATH}.update_team_project_access", return_value=updated) as mock_update:
            result = state_present(adapter, params, existing=existing_read)
        assert result["changed"] is True
        assert result["access"] == "maintain"
        mock_update.assert_called_once_with(adapter, TEST_TPA_ID, {"access": "maintain"})

    def test_update_check_mode_skips_api(self, adapter, existing_read):
        params = {"access": "admin", "team_id": TEST_TEAM_ID, "project_id": TEST_PROJECT_ID}
        with patch(f"{MODULE_PATH}.update_team_project_access") as mock_update:
            result = state_present(adapter, params, existing=existing_read, check_mode=True)
        assert result["changed"] is True
        assert "check mode" in result["msg"]
        mock_update.assert_not_called()

    def test_custom_access_create(self, adapter):
        params = {
            "access": "custom",
            "team_id": TEST_TEAM_ID,
            "project_id": TEST_PROJECT_ID,
            "project_settings": "read",
            "workspace_runs": "apply",
            "workspace_locking": True,
            "project_teams": None,
            "project_variable_sets": None,
            "workspace_sentinel_mocks": None,
            "workspace_state_versions": None,
            "workspace_variables": None,
            "workspace_create": None,
            "workspace_delete": None,
            "workspace_move": None,
            "workspace_run_tasks": None,
        }
        created = {
            "id": TEST_TPA_ID,
            "access": "custom",
            "project_settings": "read",
            "workspace_runs": "apply",
            "workspace_locking": True,
            "team_id": TEST_TEAM_ID,
            "project_id": TEST_PROJECT_ID,
        }
        with patch(f"{MODULE_PATH}.add_team_project_access", return_value=created):
            result = state_present(adapter, params, existing=None)
        assert result["changed"] is True
        assert result["access"] == "custom"

    def test_custom_access_idempotent(self, adapter, existing_custom):
        params = {
            "access": "custom",
            "project_settings": "read",
            "project_teams": "none",
            "project_variable_sets": "read",
            "workspace_runs": "apply",
            "workspace_variables": "write",
            "workspace_locking": True,
            "workspace_create": False,
            "workspace_delete": False,
            "workspace_move": False,
            "workspace_run_tasks": False,
            "workspace_sentinel_mocks": None,
            "workspace_state_versions": None,
            "team_id": TEST_TEAM_ID,
            "project_id": TEST_PROJECT_ID,
        }
        with patch(f"{MODULE_PATH}.update_team_project_access") as mock_update:
            result = state_present(adapter, params, existing=existing_custom)
        assert result["changed"] is False
        assert result["id"] == TEST_TPA_ID
        mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# TestStateAbsent
# ---------------------------------------------------------------------------


class TestStateAbsent:
    def test_remove_existing(self, adapter, existing_read):
        with patch(f"{MODULE_PATH}.remove_team_project_access") as mock_remove:
            result = state_absent(adapter, {}, existing=existing_read)
        assert result["changed"] is True
        assert TEST_TPA_ID in result["msg"]
        mock_remove.assert_called_once_with(adapter, TEST_TPA_ID)

    def test_already_absent_no_change(self, adapter):
        params = {"team_project_access_id": TEST_TPA_ID}
        result = state_absent(adapter, params, existing=None)
        assert result["changed"] is False
        assert "not found" in result["msg"]

    def test_remove_check_mode(self, adapter, existing_read):
        with patch(f"{MODULE_PATH}.remove_team_project_access") as mock_remove:
            result = state_absent(adapter, {}, existing=existing_read, check_mode=True)
        assert result["changed"] is True
        assert "check mode" in result["msg"]
        mock_remove.assert_not_called()


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------


class TestMain:
    def test_invalid_custom_field_with_non_custom_access(self):
        module = DummyModule(
            params={
                "state": "present",
                "team_id": TEST_TEAM_ID,
                "project_id": TEST_PROJECT_ID,
                "access": "read",
                "workspace_runs": "apply",
                "project_settings": None,
                "project_teams": None,
                "project_variable_sets": None,
                "workspace_sentinel_mocks": None,
                "workspace_state_versions": None,
                "workspace_variables": None,
                "workspace_create": None,
                "workspace_delete": None,
                "workspace_locking": None,
                "workspace_move": None,
                "workspace_run_tasks": None,
                "team_project_access_id": None,
                "tfe_token": "test-token",
                "tfe_address": None,
                "tfe_hostname": None,
                "validate_certs": True,
                "connection_timeout": 30,
                "retry_count": 3,
            }
        )
        with patch(f"{MODULE_PATH}.AnsibleTerraformModule", return_value=module):
            with pytest.raises(AssertionError) as exc_info:
                main()
        assert "workspace_runs" in str(exc_info.value)
        assert "custom" in str(exc_info.value)
