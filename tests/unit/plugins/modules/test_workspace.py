# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.workspace import (
    fetch_workspace_tag_bindings,
    get_workspace_id,
    normalize_workspace_response,
    workspace_create,
    workspace_delete,
    workspace_lock,
    workspace_unlock,
    workspace_update,
)


class EnhancedDummyModule:
    """A mock Ansible module for better inspection in tests."""

    def __init__(self, params=None):
        self.params = params or {}
        self.failed = False
        self.exit_args = None
        self.fail_args = None

    def fail_json(self, **kwargs):
        self.failed = True
        self.fail_args = kwargs
        raise AssertionError(kwargs.get("msg", "fail_json called with no message"))

    def exit_json(self, **kwargs):
        self.exit_args = kwargs
        raise SystemExit(kwargs)


class TestWorkspaceLockAndUnlock:
    @pytest.fixture
    def params(self):
        return {
            "workspace_id": "ws-123",
            "lock_reason": "Locking for maintenance",
            "force": False,
        }

    @pytest.fixture
    def mock_workspace_response_locked(self):
        return {"data": {"attributes": {"locked": True}}}

    @pytest.fixture
    def mock_workspace_response_unlocked(self):
        return {"data": {"attributes": {"locked": False}}}

    def test_workspace_already_locked(self, params, mock_workspace_response_locked):
        result = workspace_lock(Mock(), params, mock_workspace_response_locked, check_mode=False)
        assert result["changed"] is False
        assert "already locked" in result["msg"]

    def test_workspace_lock_success(self, params, mock_workspace_response_unlocked):
        mock_client = Mock()
        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.lock_workspace",
            return_value={"data": {"id": params["workspace_id"], "attributes": {"locked": True}}},
        ):

            result = workspace_lock(mock_client, params, mock_workspace_response_unlocked, check_mode=False)

            assert result["changed"] is True
            assert result["msg"] == f"Workspace {params['workspace_id']} locked successfully."
            assert result["id"] == params["workspace_id"]
            assert result["attributes"]["locked"] is True

    def test_workspace_lock_check_mode(self, params, mock_workspace_response_unlocked):
        result = workspace_lock(Mock(), params, mock_workspace_response_unlocked, check_mode=True)
        assert result["changed"] is True
        assert "Skipped locking due to check-mode" in result["msg"]

    def test_workspace_already_unlocked(self, params, mock_workspace_response_unlocked):
        result = workspace_unlock(Mock(), params, mock_workspace_response_unlocked, check_mode=False)
        assert result["changed"] is False
        assert "already unlocked" in result["msg"]

    def test_workspace_unlock_success(self, params, mock_workspace_response_locked):
        mock_client = Mock()
        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.unlock_workspace",
            return_value={"data": {"id": params["workspace_id"], "attributes": {"locked": False}}},
        ):
            result = workspace_unlock(mock_client, params, mock_workspace_response_locked, check_mode=False)

            assert result["changed"] is True
            assert result["msg"] == f"Workspace {params['workspace_id']} unlocked successfully."
            assert result["id"] == params["workspace_id"]

    def test_workspace_force_unlock_success(self, params, mock_workspace_response_locked):
        params["force"] = True
        mock_client = Mock()
        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.force_unlock_workspace",
            return_value={"data": {"id": params["workspace_id"], "attributes": {"locked": False}}},
        ):
            result = workspace_unlock(mock_client, params, mock_workspace_response_locked, check_mode=False)
            assert result["changed"] is True
            assert result["msg"] == f"Workspace {params['workspace_id']} unlocked successfully."
            assert result["id"] == params["workspace_id"]

    def test_workspace_unlock_check_mode(self, params, mock_workspace_response_locked):
        result = workspace_unlock(Mock(), params, mock_workspace_response_locked, check_mode=True)
        assert result["changed"] is True
        assert "Skipped unlock due to check-mode" in result["msg"]


class TestWorkspaceDelete:
    @pytest.fixture
    def params(self):
        return {
            "workspace_id": "ws-123",
            "force": False,
        }

    @pytest.fixture
    def mock_workspace_response(self):
        return {
            "data": {
                "id": "ws-123",
                "attributes": {
                    "locked": False,
                },
            }
        }

    @pytest.fixture
    def mock_empty_workspace_response(self):
        return None

    def test_safe_delete_success(self, params, mock_workspace_response):
        mock_client = Mock()
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.safe_delete_workspace") as mock_safe_delete:
            mock_safe_delete.return_value = None
            result = workspace_delete(mock_client, params, mock_workspace_response, check_mode=False)
            mock_safe_delete.assert_called_once_with(mock_client, params["workspace_id"])
            assert result["changed"] is True
            assert "safe-deleted successfully" in result["msg"]

    def test_force_delete_success(self, params, mock_workspace_response):
        params["force"] = True
        mock_client = Mock()
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.force_delete_workspace") as mock_force_delete:
            mock_force_delete.return_value = None
            result = workspace_delete(mock_client, params, mock_workspace_response, check_mode=False)
            mock_force_delete.assert_called_once_with(mock_client, params["workspace_id"])
            assert result["changed"] is True
            assert "force-deleted successfully" in result["msg"]

    def test_delete_check_mode(self, params, mock_workspace_response):
        mock_client = Mock()
        result = workspace_delete(mock_client, params, mock_workspace_response, check_mode=True)
        assert result["changed"] is True
        assert "Skipped delete due to check-mode" in result["msg"]

    def test_delete_workspace_not_found(self, params, mock_empty_workspace_response):
        mock_client = Mock()
        result = workspace_delete(mock_client, params, mock_empty_workspace_response, check_mode=False)
        assert result["changed"] is False
        assert "was not found" in result["msg"]


class TestWorkspaceUpdate:
    @pytest.fixture
    def params(self):
        return {
            "workspace_id": "ws-123",
            "workspace": "workspace-name",
            "description": "Updated description",
            "organization": "org-1",
            "auto_destroy_at": "2025-08-10T15:00:00Z",
            "assessments_enabled": True,
            "auto_destroy_activity_duration": "14d",
        }

    @pytest.fixture
    def existing_workspace_response(self):
        return {
            "data": {
                "id": "ws-123",
                "attributes": {
                    "description": "Old description",
                },
            }
        }

    def test_workspace_update_success(self, params, existing_workspace_response):
        mock_client = Mock()

        # Patch the internal calls inside workspace_update
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id", return_value=existing_workspace_response), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.normalize_workspace_response",
            return_value={
                "description": "Old description",
            },
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.dict_diff",
            return_value={
                "description": params["description"],
                "auto_destroy_at": params["auto_destroy_at"],
                "assessments_enabled": params["assessments_enabled"],
                "auto_destroy_activity_duration": params["auto_destroy_activity_duration"],
            },
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.update_workspace",
            return_value={
                "data": {
                    "id": params["workspace_id"],
                    "attributes": {
                        "description": params["description"],
                        "auto_destroy_at": params["auto_destroy_at"],
                        "assessments_enabled": params["assessments_enabled"],
                        "auto_destroy_activity_duration": params["auto_destroy_activity_duration"],
                    },
                    "relationships": {},
                    "type": "workspaces",
                }
            },
        ):
            result = workspace_update(mock_client, params, check_mode=False)
            assert result["changed"] is True
            assert params["workspace_id"] in result["msg"]
            assert result["id"] == params["workspace_id"]
            assert result["attributes"]["description"] == params["description"]
            assert result["attributes"]["auto_destroy_at"] == params["auto_destroy_at"]
            assert result["attributes"]["assessments_enabled"] == params["assessments_enabled"]
            assert result["attributes"]["auto_destroy_activity_duration"] == params["auto_destroy_activity_duration"]

    def test_workspace_update_check_mode(self, params, existing_workspace_response):
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id", return_value=existing_workspace_response), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.normalize_workspace_response",
            return_value={
                "description": "Old description",
            },
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.dict_diff",
            return_value={
                "description": params["description"],
            },
        ):

            result = workspace_update(mock_client, params, check_mode=True)
            assert "attributes" in result
            assert "description" in result["attributes"]

    def test_workspace_update_no_changes(self, params, existing_workspace_response):
        mock_client = Mock()

        # dict_diff returns empty dict indicating no changes
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id", return_value=existing_workspace_response), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.normalize_workspace_response",
            return_value={
                "name": params["workspace"],
                "description": params["description"],
            },
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.dict_diff", return_value={}):

            result = workspace_update(mock_client, params, check_mode=False)
            assert result["changed"] is False
            assert "No changes" in result["msg"]

    def test_workspace_update_workspace_not_found(self, params):
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id", return_value=None):
            with pytest.raises(ValueError) as excinfo:
                workspace_update(mock_client, params, check_mode=False)
            assert f"The workspace {params['workspace_id']} was not found." in str(excinfo.value)

    def test_workspace_update_raises_on_update_failure(self, params, existing_workspace_response):
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id", return_value=existing_workspace_response), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.normalize_workspace_response",
            return_value={
                "description": "Old description",
            },
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.dict_diff",
            return_value={
                "description": params["description"],
            },
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.update_workspace", side_effect=Exception("Update failed")
        ):

            with pytest.raises(Exception) as excinfo:
                workspace_update(mock_client, params, check_mode=False)
            assert "Update failed" in str(excinfo.value)


class TestWorkspaceCreate:
    @pytest.fixture
    def params(self):
        return {
            "workspace": "my-workspace",
            "organization": "my-org",
            "description": "Test workspace",
            "auto_apply": True,
            "force": True,
            "project_id": "proj-123",
            "tag_bindings": {"env": "dev"},
        }

    def test_workspace_create_success(self, params):
        workspace_payload = {
            "data": {
                "type": "workspaces",
                "attributes": {
                    "name": "my-workspace",
                    "description": "Test workspace",
                    "auto_apply": True,
                },
                "relationships": {"project": {"data": {"id": "proj-123", "type": "projects"}}, "tags": {"data": [{"key": "env", "value": "dev"}]}},
            }
        }

        mock_response = {
            "data": {
                "id": "ws-123",
                "type": "workspaces",
                "attributes": workspace_payload["data"]["attributes"],
                "relationships": workspace_payload["data"]["relationships"],
            }
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.WorkspaceRequest.create") as mock_create, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.create_workspace"
        ) as mock_api_call:

            mock_create.return_value.model_dump.return_value = workspace_payload
            mock_api_call.return_value = mock_response

            mock_client = Mock()
            result = workspace_create(mock_client, params, check_mode=False)

            assert result["changed"] is True
            assert result["msg"] == "Workspace ws-123 created successfully."
            assert result["id"] == "ws-123"
            assert result["attributes"]["description"] == "Test workspace"

    def test_workspace_create_check_mode(self, params):
        workspace_payload = {
            "data": {
                "type": "workspaces",
                "attributes": {
                    "name": "my-workspace",
                    "description": "Test workspace",
                    "auto_apply": True,
                },
                "relationships": {"project": {"data": {"id": "proj-123", "type": "projects"}}, "tags": {"data": [{"key": "env", "value": "dev"}]}},
            }
        }

        params["workspace_id"] = "ws-checkmode"

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.WorkspaceRequest.create") as mock_create:
            mock_create.return_value.model_dump.return_value = workspace_payload

            mock_client = Mock()
            result = workspace_create(mock_client, params, check_mode=True)

            assert result["changed"] is True
            assert "would be created with the given payload" in result["msg"]
            assert result["type"] == "workspaces"
            assert result["attributes"]["auto_apply"] is True

    def test_workspace_create_api_failure(self, params):
        workspace_payload = {"data": {"attributes": {}, "type": "workspaces", "relationships": {}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.WorkspaceRequest.create") as mock_create, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.create_workspace"
        ) as mock_api_call:

            mock_create.return_value.model_dump.return_value = workspace_payload
            mock_api_call.side_effect = Exception("API error")

            mock_client = Mock()

            with pytest.raises(Exception) as excinfo:
                workspace_create(mock_client, params, check_mode=False)
            assert "API error" in str(excinfo.value)


class TestGetWorkspaceID:
    @pytest.fixture
    def params(self):
        return {
            "workspace": "my-workspace",
            "organization": "my-org",
        }

    def test_get_workspace_id_success(self, params):
        mock_response = {"data": {"id": "ws-123", "attributes": {"name": "my-workspace"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace") as mock_get_workspace:
            mock_get_workspace.return_value = mock_response

            mock_client = Mock()
            workspace_id = get_workspace_id(mock_client, params)

            assert workspace_id == "ws-123"
            mock_get_workspace.assert_called_once_with(mock_client, "my-org", "my-workspace")

    def test_get_workspace_id_not_found(self, params):
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace") as mock_get_workspace:
            mock_get_workspace.return_value = None

            mock_client = Mock()

            with pytest.raises(ValueError) as excinfo:
                get_workspace_id(mock_client, params)

            assert "The workspace my-workspace in my-org organization was not found." in str(excinfo.value)
            mock_get_workspace.assert_called_once_with(mock_client, "my-org", "my-workspace")


class TestFetchWorkspaceTagBindings:
    def test_fetch_workspace_tag_bindings_success(self):
        workspace_id = "ws-123"
        mock_response = {
            "data": [
                {"type": "tag-bindings", "attributes": {"key": "env", "value": "production"}},
                {"type": "tag-bindings", "attributes": {"key": "team", "value": "devops"}},
                {"type": "irrelevant-type", "attributes": {"key": "ignored", "value": "ignored"}},
            ]
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_tag_bindings") as mock_get_tag_bindings:
            mock_get_tag_bindings.return_value = mock_response

            mock_client = Mock()
            result = fetch_workspace_tag_bindings(mock_client, workspace_id)

            assert result == {"env": "production", "team": "devops"}

            mock_get_tag_bindings.assert_called_once_with(mock_client, workspace_id)

    def test_fetch_workspace_tag_bindings_empty_response(self):
        workspace_id = "ws-456"

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_tag_bindings") as mock_get_tag_bindings:
            mock_get_tag_bindings.return_value = None

            mock_client = Mock()
            result = fetch_workspace_tag_bindings(mock_client, workspace_id)

            assert result == {}
            mock_get_tag_bindings.assert_called_once_with(mock_client, workspace_id)


class TestNormalizeWorkspaceResponse:
    @pytest.fixture
    def base_response_data(self):
        return {
            "attributes": {
                "name": "my-workspace",
                "description": "Sample workspace",
                "allow-destroy-plan": True,
                "assessments-enabled": False,
                "auto-apply": True,
                "auto-apply-run-trigger": True,
                "auto-destroy-at": "2025-08-25T14:30:00.000Z",
                "auto-destroy-activity-duration": "7d",
                "terraform-version": "1.5.0",
                "execution-mode": "agent",
                "setting-overwrites": {"execution_mode": True, "agent_pool": True},
            },
            "relationships": {"project": {"data": {"id": "proj-123"}}},
        }

    def test_normalize_workspace_response_basic(self, base_response_data):
        workspace_id = "ws-123"
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.fetch_workspace_tag_bindings") as mock_fetch_tags:
            mock_fetch_tags.return_value = {"env": "dev"}

            mock_client = Mock()
            result = normalize_workspace_response(base_response_data, mock_client, workspace_id)

            assert result["name"] == "my-workspace"
            assert result["description"] == "Sample workspace"
            assert result["allow_destroy_plan"] is True
            assert result["auto_apply"] is True
            assert result["execution_mode"] == "agent"
            assert result["terraform_version"] == "1.5.0"
            assert result["project_id"] == "proj-123"
            assert result["auto_destroy_at"] == "2025-08-25T14:30:00Z"
            assert result["tag_bindings"] == {"env": "dev"}
            assert result["setting_overwrites"] == {"execution_mode": True, "agent_pool": True}

    def test_normalize_workspace_response_with_agent_mode(self, base_response_data):
        base_response_data["attributes"]["execution-mode"] = "agent"
        base_response_data["relationships"]["agent-pool"] = {"data": {"id": "agent-999"}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.fetch_workspace_tag_bindings") as mock_fetch_tags:
            mock_fetch_tags.return_value = {}

            mock_client = Mock()
            result = normalize_workspace_response(base_response_data, mock_client, "ws-123")

            assert result["execution_mode"] == "agent"
            assert result["agent_pool_id"] == "agent-999"

    def test_normalize_workspace_response_timestamp(self, base_response_data):
        base_response_data["attributes"]["auto-destroy-at"] = "2026-08-20T15:00:00.000Z"

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.fetch_workspace_tag_bindings") as mock_fetch_tags:
            mock_fetch_tags.return_value = {}

            mock_client = Mock()
            result = normalize_workspace_response(base_response_data, mock_client, "ws-123")

            # Should keep original invalid timestamp
            assert result["auto_destroy_at"] == "2026-08-20T15:00:00Z"

    def test_normalize_workspace_response_missing_fields(self):
        response_data = {"attributes": {"name": "partial-workspace", "execution-mode": "remote", "setting-overwrites": {}}, "relationships": {}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.fetch_workspace_tag_bindings") as mock_fetch_tags:
            mock_fetch_tags.return_value = {}

            mock_client = Mock()
            result = normalize_workspace_response(response_data, mock_client, "ws-456")

            assert result["name"] == "partial-workspace"
            assert "description" not in result
            assert "project_id" not in result
            assert "agent_pool_id" not in result
