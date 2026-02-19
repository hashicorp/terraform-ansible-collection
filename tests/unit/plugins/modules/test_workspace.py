# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Unit tests for workspace module using WorkspaceAdapter.

These tests verify the workspace module's state handlers (create, update, 
delete, lock, unlock) work correctly with the new WorkspaceAdapter architecture.
"""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.workspace import (
    extract_comparable_attributes,
    main,
    normalize_workspace_attributes,
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
        # Should not call adapter methods
        mock_adapter.lock_workspace.assert_not_called()

    def test_workspace_lock_success(self, mock_adapter, params, workspace_response_unlocked):
        """Test successfully locking an unlocked workspace."""
        mock_response = {
            "id": params["workspace_id"],
            "type": "workspaces",
            "locked": True,
            "lock_reason": params["lock_reason"],
        }
        mock_adapter.lock_workspace.return_value = mock_response

        result = state_locked(mock_adapter, params, workspace_response_unlocked, check_mode=False)

        mock_adapter.lock_workspace.assert_called_once_with(
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
        # Should not call adapter methods in check mode
        mock_adapter.lock_workspace.assert_not_called()

    def test_workspace_already_unlocked(self, mock_adapter, params, workspace_response_unlocked):
        """Test attempting to unlock an already unlocked workspace."""
        result = state_unlocked(mock_adapter, params, workspace_response_unlocked, check_mode=False)
        
        assert result["changed"] is False
        assert "already unlocked" in result["msg"]
        # Should not call adapter methods
        mock_adapter.unlock_workspace.assert_not_called()
        mock_adapter.force_unlock_workspace.assert_not_called()

    def test_workspace_unlock_success(self, mock_adapter, params, workspace_response_locked):
        """Test successfully unlocking a locked workspace."""
        mock_response = {
            "id": params["workspace_id"],
            "type": "workspaces",
            "locked": False,
            "lock_reason": None,
        }
        mock_adapter.unlock_workspace.return_value = mock_response

        result = state_unlocked(mock_adapter, params, workspace_response_locked, check_mode=False)

        mock_adapter.unlock_workspace.assert_called_once_with(workspace_response_locked["id"])
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
        mock_adapter.force_unlock_workspace.return_value = mock_response

        result = state_unlocked(mock_adapter, params, workspace_response_locked, check_mode=False)

        mock_adapter.force_unlock_workspace.assert_called_once_with(workspace_response_locked["id"])
        assert result["changed"] is True
        assert result["locked"] is False
        assert result["id"] == params["workspace_id"]

    def test_workspace_unlock_check_mode(self, mock_adapter, params, workspace_response_locked):
        """Test unlocking workspace in check mode."""
        result = state_unlocked(mock_adapter, params, workspace_response_locked, check_mode=True)
        
        assert result["changed"] is True
        assert "Skipped unlocking due to check mode" in result["msg"]
        # Should not call adapter methods in check mode
        mock_adapter.unlock_workspace.assert_not_called()
        mock_adapter.force_unlock_workspace.assert_not_called()


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
        mock_adapter.safe_delete_workspace.return_value = None

        result = state_absent(mock_adapter, params, mock_workspace_response, check_mode=False)

        mock_adapter.safe_delete_workspace.assert_called_once_with(params["workspace_id"])
        assert result["changed"] is True
        assert "safe-deleted successfully" in result["msg"]

    def test_force_delete_success(self, mock_adapter, params, mock_workspace_response):
        """Test successfully performing a force delete."""
        params["force"] = True
        mock_adapter.force_delete_workspace.return_value = None

        result = state_absent(mock_adapter, params, mock_workspace_response, check_mode=False)

        mock_adapter.force_delete_workspace.assert_called_once_with(params["workspace_id"])
        assert result["changed"] is True
        assert "force-deleted successfully" in result["msg"]

    def test_delete_check_mode(self, mock_adapter, params, mock_workspace_response):
        """Test deleting workspace in check mode."""
        result = state_absent(mock_adapter, params, mock_workspace_response, check_mode=True)
        
        assert result["changed"] is True
        assert "Skipped delete due to check mode" in result["msg"]
        # Should not call adapter methods in check mode
        mock_adapter.safe_delete_workspace.assert_not_called()
        mock_adapter.force_delete_workspace.assert_not_called()

    def test_delete_workspace_not_found(self, mock_adapter, params):
        """Test attempting to delete a workspace that doesn't exist."""
        result = state_absent(mock_adapter, params, None, check_mode=False)
        
        assert result["changed"] is False
        assert "was not found" in result["msg"]
        # Should not call adapter methods
        mock_adapter.safe_delete_workspace.assert_not_called()
        mock_adapter.force_delete_workspace.assert_not_called()


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
        
        mock_adapter.get_workspace_by_id.return_value = existing_response
        mock_adapter.update_workspace.return_value = updated_response

        result = state_update(mock_adapter, params, check_mode=False)

        mock_adapter.get_workspace_by_id.assert_called_once_with(params["workspace_id"])
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
        
        mock_adapter.get_workspace_by_id.return_value = existing_response

        result = state_update(mock_adapter, params, check_mode=True)

        mock_adapter.get_workspace_by_id.assert_called_once()
        # Should not call update in check mode
        mock_adapter.update_workspace.assert_not_called()
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
        
        mock_adapter.get_workspace_by_id.return_value = existing_response

        result = state_update(mock_adapter, params, check_mode=False)

        mock_adapter.get_workspace_by_id.assert_called_once()
        # Should not call update if no changes
        mock_adapter.update_workspace.assert_not_called()
        assert result["changed"] is False

    def test_workspace_update_not_found(self, mock_adapter, params):
        """Test updating a workspace that doesn't exist."""
        mock_adapter.get_workspace_by_id.return_value = None

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
        
        mock_adapter.create_workspace.return_value = mock_response

        result = state_create(mock_adapter, params, check_mode=False)

        mock_adapter.create_workspace.assert_called_once()
        assert result["changed"] is True
        assert result["id"] == "ws-new-123"
        assert result["name"] == "new-workspace"
        assert result["description"] == "Test workspace"

    def test_workspace_create_check_mode(self, mock_adapter, params):
        """Test creating workspace in check mode."""
        result = state_create(mock_adapter, params, check_mode=True)

        # Should not call adapter methods in check mode
        mock_adapter.create_workspace.assert_not_called()
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
        
        mock_adapter.create_workspace.return_value = mock_response

        result = state_create(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        assert result["id"] == "ws-minimal-123"
        assert result["name"] == "minimal-workspace"


class TestNormalizeWorkspaceAttributes:
    """Test workspace attribute normalization."""

    def test_normalize_basic_attributes(self):
        """Test normalizing basic workspace attributes."""
        params = {
            "name": "test-ws",  # normalize_workspace_attributes expects 'name' not 'workspace'
            "organization": "test-org",
            "description": "Test description",
            "auto_apply": True,
            "terraform_version": "1.5.0",
        }
        
        result = normalize_workspace_attributes(params)
        
        assert result["name"] == "test-ws"
        assert result["description"] == "Test description"
        assert result["auto_apply"] is True
        assert result["terraform_version"] == "1.5.0"

    def test_normalize_filters_none_values(self):
        """Test that None values are not included in normalized output."""
        params = {
            "name": "test-ws",
            "description": None,
            "auto_apply": True,
            "project_id": None,
        }
        
        result = normalize_workspace_attributes(params)
        
        assert "description" not in result
        assert "project_id" not in result
        assert result["auto_apply"] is True

    def test_normalize_includes_false_values(self):
        """Test that False/0 values are included (not filtered as None)."""
        params = {
            "name": "test-ws",
            "auto_apply": False,
            "assessments_enabled": False,
        }
        
        result = normalize_workspace_attributes(params)
        
        assert result["auto_apply"] is False
        assert result["assessments_enabled"] is False


class TestExtractComparableAttributes:
    """Test extraction of comparable attributes from workspace response."""

    def test_extract_basic_attributes(self):
        """Test extracting basic attributes from workspace data."""
        workspace_data = {
            "id": "ws-123",
            "type": "workspaces",
            "name": "test-workspace",
            "description": "Test description",
            "auto_apply": True,
            "terraform_version": "1.5.0",
        }
        
        result = extract_comparable_attributes(workspace_data)
        
        assert result["name"] == "test-workspace"
        assert result["description"] == "Test description"
        assert result["auto_apply"] is True
        assert result["terraform_version"] == "1.5.0"

    def test_extract_handles_missing_attributes(self):
        """Test extracting attributes when some are missing."""
        workspace_data = {
            "id": "ws-123",
            "type": "workspaces",
            "name": "minimal-workspace",
        }
        
        result = extract_comparable_attributes(workspace_data)
        
        assert result["name"] == "minimal-workspace"
        # Missing attributes should not be in result
        assert "description" not in result or result.get("description") is None


class TestMainFunctionBehavior:
    @pytest.fixture
    def test_module(self, enhanced_dummy_module):
        enhanced_dummy_module.params = {
            "workspace": "test-ws",
            "organization": "test-org",
            "state": "present",
            "description": "test",
            "tfe_token": "test-token",
            "tfe_address": "https://app.terraform.io",
        }
        return enhanced_dummy_module

    def test_main_creates_workspace_if_not_exists(self, test_module):
        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule",
            return_value=test_module
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.WorkspaceAdapter"
        ) as mock_adapter_class:
            # Setup mock adapter instance
            mock_adapter = Mock()
            mock_adapter.get_workspace_by_name.return_value = None  # Workspace doesn't exist
            mock_adapter.create_workspace.return_value = {
                "id": "ws-123",
                "name": "test-ws",
                "type": "workspaces",
                "description": "test",
            }
            mock_adapter.cleanup.return_value = None
            mock_adapter_class.return_value = mock_adapter

            with pytest.raises(SystemExit):
                main()

            # Verify workspace creation was called
            mock_adapter.get_workspace_by_name.assert_called_once_with("test-org", "test-ws")
            assert test_module.exit_args["changed"] is True
            assert test_module.exit_args["msg"] == "Workspace 'test-ws' created successfully."

    def test_main_updates_workspace_if_exists(self, test_module):
        """Test main function updates workspace when it exists."""
        
        test_module.params["description"] = "updated description"
        test_module.params["auto_apply"] = True
        
        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule",
            return_value=test_module
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.WorkspaceAdapter"
        ) as mock_adapter_class:
            # Setup mock adapter instance
            mock_adapter = Mock()
            # Workspace exists
            mock_adapter.get_workspace_by_name.return_value = {
                "id": "ws-123",
                "name": "test-ws",
                "description": "old description",
                "auto_apply": False,
            }
            # Return existing workspace for comparison
            mock_adapter.get_workspace_by_id.return_value = {
                "id": "ws-123",
                "name": "test-ws",
                "description": "old description",
                "auto_apply": False,
            }
            # Return updated workspace
            mock_adapter.update_workspace.return_value = {
                "id": "ws-123",
                "name": "test-ws",
                "description": "updated description",
                "auto_apply": True,
            }
            mock_adapter.cleanup.return_value = None
            mock_adapter_class.return_value = mock_adapter

            with pytest.raises(SystemExit):
                main()

            # Verify update was called
            mock_adapter.get_workspace_by_name.assert_called_once_with("test-org", "test-ws")
            mock_adapter.get_workspace_by_id.assert_called_once_with("ws-123")
            assert test_module.exit_args["changed"] is True

    def test_main_deletes_workspace(self, test_module):
        test_module.params.update({"state": "absent", "workspace_id": "ws-123", "force": False})
        
        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule",
            return_value=test_module
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.WorkspaceAdapter"
        ) as mock_adapter_class:
            # Setup mock adapter instance
            mock_adapter = Mock()
            mock_adapter.get_workspace_by_id.return_value = {
                "id": "ws-123",
                "name": "test-ws",
                "locked": False,
            }
            mock_adapter.safe_delete_workspace.return_value = None
            mock_adapter.cleanup.return_value = None
            mock_adapter_class.return_value = mock_adapter

            with pytest.raises(SystemExit):
                main()

            # Verify deletion was called
            mock_adapter.get_workspace_by_id.assert_called_once_with("ws-123")
            mock_adapter.safe_delete_workspace.assert_called_once_with("ws-123")
            assert test_module.exit_args["changed"] is True
            assert "safe-deleted successfully" in test_module.exit_args["msg"]

    def test_main_locks_workspace(self, test_module):
        """Test main function locks workspace."""        
        test_module.params.update({
            "state": "locked",
            "workspace_id": "ws-123",
            "lock_reason": "Maintenance",
        })
        
        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule",
            return_value=test_module
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.WorkspaceAdapter"
        ) as mock_adapter_class:
            # Setup mock adapter instance
            mock_adapter = Mock()
            mock_adapter.get_workspace_by_id.return_value = {
                "id": "ws-123",
                "name": "test-ws",
                "locked": False,
            }
            mock_adapter.lock_workspace.return_value = {
                "id": "ws-123",
                "name": "test-ws",
                "locked": True,
                "lock_reason": "Maintenance",
            }
            mock_adapter.cleanup.return_value = None
            mock_adapter_class.return_value = mock_adapter

            with pytest.raises(SystemExit):
                main()

            # Verify lock was called
            mock_adapter.get_workspace_by_id.assert_called_once_with("ws-123")
            mock_adapter.lock_workspace.assert_called_once()
            assert test_module.exit_args["changed"] is True

    def test_main_unlocks_workspace(self, test_module):
        """Test main function unlocks workspace."""        
        test_module.params.update({
            "state": "unlocked",
            "workspace_id": "ws-123",
            "force": False,
        })
        
        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule",
            return_value=test_module
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.WorkspaceAdapter"
        ) as mock_adapter_class:
            # Setup mock adapter instance
            mock_adapter = Mock()
            mock_adapter.get_workspace_by_id.return_value = {
                "id": "ws-123",
                "name": "test-ws",
                "locked": True,
            }
            mock_adapter.unlock_workspace.return_value = {
                "id": "ws-123",
                "name": "test-ws",
                "locked": False,
            }
            mock_adapter.cleanup.return_value = None
            mock_adapter_class.return_value = mock_adapter

            with pytest.raises(SystemExit):
                main()

            # Verify unlock was called
            mock_adapter.get_workspace_by_id.assert_called_once_with("ws-123")
            mock_adapter.unlock_workspace.assert_called_once()
            assert test_module.exit_args["changed"] is True

    def test_main_check_mode_creation(self, test_module):
        """Test main function in check mode for creation."""
        
        test_module.check_mode = True
        
        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule",
            return_value=test_module
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.WorkspaceAdapter"
        ) as mock_adapter_class:
            # Setup mock adapter instance
            mock_adapter = Mock()
            mock_adapter.get_workspace_by_name.return_value = None  # Workspace doesn't exist
            mock_adapter.cleanup.return_value = None
            mock_adapter_class.return_value = mock_adapter

            with pytest.raises(SystemExit):
                main()

            # In check mode, create should not be called
            mock_adapter.create_workspace.assert_not_called()
            assert test_module.exit_args["changed"] is True
            assert "Skipped creation due to check mode" in test_module.exit_args["msg"]
