# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/team_workspace_access.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.team_workspace_access import (
    _build_desired,
    _has_diff,
    main,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.team_workspace_access"

TEST_TWA_ID = "tws-test123"
TEST_TEAM_ID = "team-abc123"
TEST_WORKSPACE_ID = "ws-xyz789"


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
        "id": TEST_TWA_ID,
        "access": "read",
        "team_id": TEST_TEAM_ID,
        "workspace_id": TEST_WORKSPACE_ID,
    }


@pytest.fixture
def existing_custom():
    """Existing grant with access=custom and permission fields set."""
    return {
        "id": TEST_TWA_ID,
        "access": "custom",
        "runs": "apply",
        "variables": "write",
        "state_versions": "read-outputs",
        "sentinel_mocks": "none",
        "workspace_locking": True,
        "run_tasks": False,
        "policy_overrides": False,
        "team_id": TEST_TEAM_ID,
        "workspace_id": TEST_WORKSPACE_ID,
    }


@pytest.fixture
def base_params():
    return {
        "team_id": TEST_TEAM_ID,
        "workspace_id": TEST_WORKSPACE_ID,
        "access": "read",
        "team_workspace_access_id": None,
        "runs": None,
        "variables": None,
        "state_versions": None,
        "sentinel_mocks": None,
        "workspace_locking": None,
        "run_tasks": None,
        "policy_overrides": None,
    }


# ---------------------------------------------------------------------------
# _build_desired / _has_diff helpers
# ---------------------------------------------------------------------------


class TestBuildDesired:
    def test_simple_access(self, base_params):
        desired = _build_desired(base_params)
        assert desired == {"access": "read"}

    def test_custom_fields_included(self):
        params = {
            "access": "custom",
            "runs": "apply",
            "variables": "write",
            "state_versions": None,
            "sentinel_mocks": None,
            "workspace_locking": True,
            "run_tasks": None,
            "policy_overrides": None,
        }
        desired = _build_desired(params)
        assert desired["access"] == "custom"
        assert desired["runs"] == "apply"
        assert desired["variables"] == "write"
        assert desired["workspace_locking"] is True
        assert "state_versions" not in desired
        assert "run_tasks" not in desired

    def test_none_fields_excluded(self, base_params):
        desired = _build_desired(base_params)
        for field in ["runs", "variables", "state_versions", "sentinel_mocks", "workspace_locking", "run_tasks", "policy_overrides"]:
            assert field not in desired


class TestHasDiff:
    def test_no_diff_same_access(self):
        existing = {"id": TEST_TWA_ID, "access": "read"}
        desired = {"access": "read"}
        assert _has_diff(existing, desired) is False

    def test_diff_access_changed(self):
        existing = {"id": TEST_TWA_ID, "access": "read"}
        desired = {"access": "write"}
        assert _has_diff(existing, desired) is True

    def test_diff_permission_field_changed(self):
        existing = {"id": TEST_TWA_ID, "access": "custom", "runs": "read"}
        desired = {"access": "custom", "runs": "apply"}
        assert _has_diff(existing, desired) is True

    def test_no_diff_custom_all_match(self):
        existing = {"access": "custom", "runs": "apply", "variables": "write"}
        desired = {"access": "custom", "runs": "apply", "variables": "write"}
        assert _has_diff(existing, desired) is False


# ---------------------------------------------------------------------------
# state_present
# ---------------------------------------------------------------------------


class TestStatePresent:
    def test_create_when_not_exists(self, adapter, base_params):
        created = {"id": TEST_TWA_ID, "access": "read", "team_id": TEST_TEAM_ID, "workspace_id": TEST_WORKSPACE_ID}
        with patch(f"{MODULE_PATH}.add_team_workspace_access", return_value=created) as mock_add:
            result = state_present(adapter, base_params, existing=None, check_mode=False)

        mock_add.assert_called_once()
        assert result["changed"] is True
        assert result["id"] == TEST_TWA_ID
        assert result["access"] == "read"

    def test_create_passes_team_and_workspace_ids(self, adapter, base_params):
        """add_team_workspace_access must receive team_id and workspace_id."""
        with patch(f"{MODULE_PATH}.add_team_workspace_access", return_value={"id": TEST_TWA_ID, "access": "read"}) as mock_add:
            state_present(adapter, base_params, existing=None, check_mode=False)

        call_options = mock_add.call_args[0][1]
        assert call_options["team_id"] == TEST_TEAM_ID
        assert call_options["workspace_id"] == TEST_WORKSPACE_ID

    def test_create_check_mode_skips_api(self, adapter, base_params):
        with patch(f"{MODULE_PATH}.add_team_workspace_access") as mock_add:
            result = state_present(adapter, base_params, existing=None, check_mode=True)

        mock_add.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_present_missing_ids_raises_clear_error(self, adapter):
        # Regression: present with only a (nonexistent) grant id must fail with a
        # clear message instead of creating with team_id/workspace_id = None.
        params = {"access": "read", "team_workspace_access_id": "tws-missing", "team_id": None, "workspace_id": None}
        with patch(f"{MODULE_PATH}.add_team_workspace_access") as mock_add:
            with pytest.raises(ValueError, match="was not found"):
                state_present(adapter, params, existing=None, check_mode=False)
        mock_add.assert_not_called()

    def test_idempotent_no_diff_returns_existing(self, adapter, base_params, existing_read):
        """No diff → changed=False AND full existing data returned (issue #142 pattern)."""
        with patch(f"{MODULE_PATH}.update_team_workspace_access") as mock_update:
            result = state_present(adapter, base_params, existing=existing_read, check_mode=False)

        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == TEST_TWA_ID
        assert result["access"] == "read"
        assert result["team_id"] == TEST_TEAM_ID
        assert result["workspace_id"] == TEST_WORKSPACE_ID

    def test_update_when_diff(self, adapter, base_params, existing_read):
        updated_params = dict(base_params, access="write")
        updated_grant = {"id": TEST_TWA_ID, "access": "write", "team_id": TEST_TEAM_ID, "workspace_id": TEST_WORKSPACE_ID}

        with patch(f"{MODULE_PATH}.update_team_workspace_access", return_value=updated_grant) as mock_update:
            result = state_present(adapter, updated_params, existing=existing_read, check_mode=False)

        mock_update.assert_called_once_with(adapter, TEST_TWA_ID, {"access": "write"})
        assert result["changed"] is True
        assert result["access"] == "write"

    def test_update_check_mode_skips_api(self, adapter, base_params, existing_read):
        updated_params = dict(base_params, access="write")
        with patch(f"{MODULE_PATH}.update_team_workspace_access") as mock_update:
            result = state_present(adapter, updated_params, existing=existing_read, check_mode=True)

        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_custom_access_create(self, adapter):
        params = {
            "team_id": TEST_TEAM_ID,
            "workspace_id": TEST_WORKSPACE_ID,
            "access": "custom",
            "runs": "apply",
            "variables": "write",
            "state_versions": "read-outputs",
            "sentinel_mocks": "none",
            "workspace_locking": True,
            "run_tasks": False,
            "policy_overrides": False,
            "team_workspace_access_id": None,
        }
        created = {"id": TEST_TWA_ID, "access": "custom", "runs": "apply", "variables": "write", "team_id": TEST_TEAM_ID, "workspace_id": TEST_WORKSPACE_ID}
        with patch(f"{MODULE_PATH}.add_team_workspace_access", return_value=created) as mock_add:
            result = state_present(adapter, params, existing=None, check_mode=False)

        call_options = mock_add.call_args[0][1]
        assert call_options["access"] == "custom"
        assert call_options["runs"] == "apply"
        assert call_options["variables"] == "write"
        assert call_options["workspace_locking"] is True
        assert result["changed"] is True

    def test_custom_access_idempotent(self, adapter, existing_custom):
        """Custom access with same permissions → no-op, existing data returned."""
        params = {
            "team_id": TEST_TEAM_ID,
            "workspace_id": TEST_WORKSPACE_ID,
            "access": "custom",
            "runs": "apply",
            "variables": "write",
            "state_versions": "read-outputs",
            "sentinel_mocks": "none",
            "workspace_locking": True,
            "run_tasks": False,
            "policy_overrides": False,
            "team_workspace_access_id": None,
        }
        with patch(f"{MODULE_PATH}.update_team_workspace_access") as mock_update:
            result = state_present(adapter, params, existing=existing_custom, check_mode=False)

        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == TEST_TWA_ID
        assert result["runs"] == "apply"


# ---------------------------------------------------------------------------
# state_absent
# ---------------------------------------------------------------------------


class TestStateAbsent:
    def test_remove_existing(self, adapter, existing_read):
        with patch(f"{MODULE_PATH}.remove_team_workspace_access") as mock_remove:
            result = state_absent(adapter, {}, existing=existing_read, check_mode=False)

        mock_remove.assert_called_once_with(adapter, TEST_TWA_ID)
        assert result["changed"] is True
        assert TEST_TWA_ID in result["msg"]

    def test_already_absent_no_change(self, adapter):
        result = state_absent(adapter, {"team_workspace_access_id": TEST_TWA_ID}, existing=None, check_mode=False)
        assert result["changed"] is False
        assert "not found" in result["msg"]

    def test_remove_check_mode(self, adapter, existing_read):
        with patch(f"{MODULE_PATH}.remove_team_workspace_access") as mock_remove:
            result = state_absent(adapter, {}, existing=existing_read, check_mode=True)

        mock_remove.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


# ---------------------------------------------------------------------------
# main() integration via DummyModule
# ---------------------------------------------------------------------------


class TestMain:
    def _run_main(self, params, existing, check_mode=False):
        from tests.unit.conftest import DummyModule

        dummy = DummyModule(params=params, check_mode=check_mode)

        with patch(f"{MODULE_PATH}.AnsibleTerraformModule", return_value=dummy), patch(f"{MODULE_PATH}._resolve_existing", return_value=existing):
            try:
                main()
            except SystemExit as e:
                return e.args[0]
        return dummy.exit_args

    def test_invalid_custom_field_with_non_custom_access(self):
        from tests.unit.conftest import DummyModule

        params = {
            "state": "present",
            "team_id": TEST_TEAM_ID,
            "workspace_id": TEST_WORKSPACE_ID,
            "access": "read",
            "runs": "apply",  # invalid when access != custom
            "variables": None,
            "state_versions": None,
            "sentinel_mocks": None,
            "workspace_locking": None,
            "run_tasks": None,
            "policy_overrides": None,
            "team_workspace_access_id": None,
        }
        dummy = DummyModule(params=params)

        with patch(f"{MODULE_PATH}.AnsibleTerraformModule", return_value=dummy):
            with pytest.raises(AssertionError, match="only valid when access='custom'"):
                main()

        assert dummy.failed is True
