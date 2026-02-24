# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.workspace import (
    main,
    state_absent,
    state_create,
    state_locked,
    state_unlocked,
    state_update,
)


class TestWorkspaceLockAndUnlock:
    """Test locking and unlocking workspace operations."""

    @pytest.fixture
    def params(self):
        return {
            "workspace_id": "ws-123",
            "lock_reason": "Locking for maintenance",
            "force": False,
        }

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock WorkspaceAdapter."""
        adapter = Mock()
        adapter.token = "test-token"
        adapter.address = "https://app.terraform.io"
        return adapter

    @pytest.fixture
    def workspace_response_locked(self):
        """Workspace response indicating locked state."""
        return {
            "id": "ws-123",
            "type": "workspaces",
            "name": "test-workspace",
            "locked": True,
            "lock_reason": "Manual lock",
        }

    @pytest.fixture
    def workspace_response_unlocked(self):
        """Workspace response indicating unlocked state."""
        return {
            "id": "ws-123",
            "type": "workspaces",
            "name": "test-workspace",
            "locked": False,
            "lock_reason": None,
        }

    def test_workspace_already_locked(self, mock_adapter, params, workspace_response_locked):
        """Test attempting to lock an already locked workspace."""
        result = state_locked(mock_adapter, params, workspace_response_locked, check_mode=False)
        
        assert result["changed"] is False
        assert "already locked" in result["msg"]

    def test_workspace_lock_success(self, mock_adapter, params, workspace_response_unlocked):
        """Test successfully locking an unlocked workspace."""
        mock_response = {
            "id": params["workspace_id"],
            "type": "workspaces",
            "locked": True,
            "lock_reason": params["lock_reason"],
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.lock_workspace") as mock_lock:
            mock_lock.return_value = mock_response

            result = state_locked(mock_adapter, params, workspace_response_unlocked, check_mode=False)

            mock_lock.assert_called_once_with(
                mock_adapter,
                workspace_response_unlocked["id"], 
                reason=params["lock_reason"]
            )
            assert result["changed"] is True
            assert result["locked"] is True
            assert result["id"] == params["workspace_id"]

    def test_workspace_lock_check_mode(self, mock_adapter, params, workspace_response_unlocked):
        """Test locking workspace in check mode."""
        result = state_locked(mock_adapter, params, workspace_response_unlocked, check_mode=True)
        
        assert result["changed"] is True
        assert "Skipped locking due to check mode" in result["msg"]

    def test_workspace_already_unlocked(self, mock_adapter, params, workspace_response_unlocked):
        """Test attempting to unlock an already unlocked workspace."""
        result = state_unlocked(mock_adapter, params, workspace_response_unlocked, check_mode=False)
        
        assert result["changed"] is False
        assert "already unlocked" in result["msg"]

    def test_workspace_unlock_success(self, mock_adapter, params, workspace_response_locked):
        """Test successfully unlocking a locked workspace."""
        mock_response = {
            "id": params["workspace_id"],
            "type": "workspaces",
            "locked": False,
            "lock_reason": None,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.unlock_workspace") as mock_unlock:
            mock_unlock.return_value = mock_response

            result = state_unlocked(mock_adapter, params, workspace_response_locked, check_mode=False)

            mock_unlock.assert_called_once_with(mock_adapter, workspace_response_locked["id"])
            assert result["changed"] is True
            assert result["locked"] is False
            assert result["id"] == params["workspace_id"]

    def test_workspace_force_unlock_success(self, mock_adapter, params, workspace_response_locked):
        """Test force unlocking a locked workspace."""
        params["force"] = True
        mock_response = {
            "id": params["workspace_id"],
            "type": "workspaces",
            "locked": False,
            "lock_reason": None,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.force_unlock_workspace") as mock_force_unlock:
            mock_force_unlock.return_value = mock_response

            result = state_unlocked(mock_adapter, params, workspace_response_locked, check_mode=False)

            mock_force_unlock.assert_called_once_with(mock_adapter, workspace_response_locked["id"])
            assert result["changed"] is True
            assert result["locked"] is False
            assert result["id"] == params["workspace_id"]

    def test_workspace_unlock_check_mode(self, mock_adapter, params, workspace_response_locked):
        """Test unlocking workspace in check mode."""
        result = state_unlocked(mock_adapter, params, workspace_response_locked, check_mode=True)
        
        assert result["changed"] is True
        assert "Skipped unlocking due to check mode" in result["msg"]


class TestWorkspaceDelete:
    """Test workspace deletion operations."""

    @pytest.fixture
    def params(self):
        return {
            "workspace_id": "ws-123",
            "force": False,
        }

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock WorkspaceAdapter."""
        adapter = Mock()
        adapter.token = "test-token"
        adapter.address = "https://app.terraform.io"
        return adapter

    @pytest.fixture
    def mock_workspace_response(self):
        return {
            "id": "ws-123",
            "type": "workspaces",
            "name": "test-workspace",
        }

    def test_safe_delete_success(self, mock_adapter, params, mock_workspace_response):
        """Test successfully performing a safe delete."""
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.safe_delete_workspace") as mock_safe_delete:
            mock_safe_delete.return_value = None

            result = state_absent(mock_adapter, params, mock_workspace_response, check_mode=False)

            mock_safe_delete.assert_called_once_with(mock_adapter, params["workspace_id"])
            assert result["changed"] is True
            assert "safe-deleted successfully" in result["msg"]

    def test_force_delete_success(self, mock_adapter, params, mock_workspace_response):
        """Test successfully performing a force delete."""
        params["force"] = True

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.force_delete_workspace") as mock_force_delete:
            mock_force_delete.return_value = None

            result = state_absent(mock_adapter, params, mock_workspace_response, check_mode=False)

            mock_force_delete.assert_called_once_with(mock_adapter, params["workspace_id"])
            assert result["changed"] is True
            assert "force-deleted successfully" in result["msg"]

    def test_delete_check_mode(self, mock_adapter, params, mock_workspace_response):
        """Test deleting workspace in check mode."""
        result = state_absent(mock_adapter, params, mock_workspace_response, check_mode=True)
        
        assert result["changed"] is True
        assert "Skipped delete due to check mode" in result["msg"]

    def test_delete_workspace_not_found(self, mock_adapter, params):
        """Test attempting to delete a workspace that doesn't exist."""
        result = state_absent(mock_adapter, params, None, check_mode=False)
        
        assert result["changed"] is False
        assert "was not found" in result["msg"]


class TestWorkspaceUpdate:
    """Test workspace update operations."""

    @pytest.fixture
    def params(self):
        return {
            "workspace_id": "ws-123",
            "workspace": "test-workspace",
            "description": "Updated description",
            "organization": "test-org",
            "auto_apply": True,
            "terraform_version": "1.5.0",
        }

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock WorkspaceAdapter."""
        adapter = Mock()
        adapter.token = "test-token"
        adapter.address = "https://app.terraform.io"
        return adapter

    @pytest.fixture
    def existing_workspace_response(self):
        return {
            "id": "ws-123",
            "type": "workspaces",
            "name": "test-workspace",
            "description": "Old description",
            "auto_apply": False,
            "terraform_version": "1.4.0",
        }

    def test_workspace_update_with_changes(self, mock_adapter, params):
        """Test updating workspace when changes are detected."""
        existing_response = {
            "id": "ws-123",
            "type": "workspaces",
            "name": "test-workspace",
            "description": "Old description",
            "auto_apply": False,
        }
        
        updated_response = {
            "id": "ws-123",
            "type": "workspaces",
            "name": "test-workspace",
            "description": "Updated description",
            "auto_apply": True,
        }
        
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id") as mock_get, \
             patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.update_workspace") as mock_update:
            
            mock_get.return_value = existing_response
            mock_update.return_value = updated_response

            result = state_update(mock_adapter, params, check_mode=False)

            mock_get.assert_called_once_with(mock_adapter, params["workspace_id"])
            assert result["changed"] is True
            assert result["description"] == "Updated description"

    def test_workspace_update_check_mode(self, mock_adapter, params):
        """Test updating workspace in check mode."""
        existing_response = {
            "id": "ws-123",
            "type": "workspaces",
            "name": "test-workspace",
            "description": "Old description",
        }
        
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id") as mock_get:
            mock_get.return_value = existing_response

            result = state_update(mock_adapter, params, check_mode=True)

            mock_get.assert_called_once()
            assert result["changed"] is True
            assert "Skipped update due to check mode" in result["msg"]

    def test_workspace_update_no_changes(self, mock_adapter, params):
        """Test updating workspace when no changes are detected."""
        # Set params to match existing workspace
        params["description"] = "Same description"
        params["auto_apply"] = False
        
        existing_response = {
            "id": "ws-123",
            "type": "workspaces",
            "name": "test-workspace",
            "description": "Same description",
            "auto_apply": False,
            "terraform_version": "1.5.0",
        }
        
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id") as mock_get:
            mock_get.return_value = existing_response

            result = state_update(mock_adapter, params, check_mode=False)

            mock_get.assert_called_once()
            assert result["changed"] is False

    def test_workspace_update_not_found(self, mock_adapter, params):
        """Test updating a workspace that doesn't exist."""
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id") as mock_get:
            mock_get.return_value = None

            with pytest.raises(ValueError) as excinfo:
                state_update(mock_adapter, params, check_mode=False)
            
            assert "was not found" in str(excinfo.value)


class TestWorkspaceCreate:
    """Test workspace creation operations."""

    @pytest.fixture
    def params(self):
        return {
            "workspace": "new-workspace",
            "organization": "test-org",
            "description": "Test workspace",
            "auto_apply": True,
            "terraform_version": "1.5.0",
        }

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock WorkspaceAdapter."""
        adapter = Mock()
        adapter.token = "test-token"
        adapter.address = "https://app.terraform.io"
        return adapter

    def test_workspace_create_success(self, mock_adapter, params):
        """Test successfully creating a new workspace."""
        mock_response = {
            "id": "ws-new-123",
            "type": "workspaces",
            "name": "new-workspace",
            "description": "Test workspace",
            "auto_apply": True,
            "terraform_version": "1.5.0",
        }
        
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.create_workspace") as mock_create:
            mock_create.return_value = mock_response

            result = state_create(mock_adapter, params, check_mode=False)

            mock_create.assert_called_once()
            assert result["changed"] is True
            assert result["id"] == "ws-new-123"
            assert result["name"] == "new-workspace"
            assert result["description"] == "Test workspace"

    def test_workspace_create_check_mode(self, mock_adapter, params):
        """Test creating workspace in check mode."""
        result = state_create(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "Skipped creation due to check mode" in result["msg"]

    def test_workspace_create_minimal_params(self, mock_adapter):
        """Test creating workspace with minimal parameters."""
        params = {
            "workspace": "minimal-workspace",
            "organization": "test-org",
        }
        
        mock_response = {
            "id": "ws-minimal-123",
            "type": "workspaces",
            "name": "minimal-workspace",
        }
        
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.create_workspace") as mock_create:
            mock_create.return_value = mock_response

            result = state_create(mock_adapter, params, check_mode=False)

            assert result["changed"] is True
            assert result["id"] == "ws-minimal-123"
            assert result["name"] == "minimal-workspace"


@pytest.mark.skip(reason="get_workspace_id function removed during pytfe refactoring")
class TestGetWorkspaceID:
    @pytest.fixture
    def params(self):
        return {
            "workspace": "my-workspace",
            "organization": "my-org",
        }

    def test_get_workspace_id_success(self, params):
        mock_response = create_workspace_response(workspace_id="ws-123", name="my-workspace")

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


@pytest.mark.skip(reason="fetch_workspace_tag_bindings function removed during pytfe refactoring")
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


@pytest.mark.skip(reason="normalize_workspace_response function removed during pytfe refactoring")
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


class TestMainFunctionBehavior:
    @pytest.fixture
    def test_module(self, enhanced_dummy_module):
        enhanced_dummy_module.params = {
            "workspace": "test-ws",
            "organization": "test-org",
            "state": "present",
            "description": "test",
        }
        return enhanced_dummy_module

    def test_main_creates_workspace_if_not_exists(self, test_module):
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace", return_value=None), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_create", return_value={"changed": True, "msg": "created"}
        ):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert test_module.exit_args["msg"] == "created"

    def test_main_updates_workspace_if_exists(self, test_module):
        test_module.params["workspace_id"] = None
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.TerraformClient"
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace", return_value={"id": "ws-123"}
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_update", return_value={"changed": False, "msg": "no changes"}
        ):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is False
            assert test_module.exit_args["msg"] == "no changes"

    def test_main_deletes_workspace(self, test_module):
        test_module.params.update({"state": "absent", "workspace_id": "ws-123"})
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id", return_value={"data": {}}), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_absent", return_value={"changed": True, "msg": "deleted"}
        ):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert test_module.exit_args["msg"] == "deleted"

    def test_main_locks_workspace(self, test_module):
        test_module.params.update({"state": "locked", "workspace_id": "ws-123"})
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.TerraformClient"
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id", return_value={"id": "ws-123", "locked": False}
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_locked", return_value={"changed": True, "msg": "locked"}
        ):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert test_module.exit_args["msg"] == "locked"

    def test_main_unlocks_workspace(self, test_module):
        test_module.params.update({"state": "unlocked", "workspace_id": "ws-123"})
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.TerraformClient"
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id", return_value={"id": "ws-123", "locked": True}
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_unlocked", return_value={"changed": True, "msg": "unlocked"}
        ):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert test_module.exit_args["msg"] == "unlocked"

    def test_main_check_mode_creation(self, test_module):
        test_module.check_mode = True
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace", return_value=None), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_create", return_value={"changed": True, "msg": "would be created"}
        ):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert "would be created" in test_module.exit_args["msg"]

    def test_main_fails_on_exception(self, test_module):
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.TerraformClient", side_effect=Exception("something broke")
        ):

            with pytest.raises(AssertionError) as e:
                main()

            assert "something broke" in str(e.value)
