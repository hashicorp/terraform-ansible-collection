# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Unit tests for WorkspaceAdapter class.

These tests verify the WorkspaceAdapter's methods for interacting with
Terraform Cloud/Enterprise workspaces using the pytfe SDK.
"""

from unittest.mock import Mock

import pytest

from pytfe.errors import AuthError, NotFound
from pytfe.models import Workspace as PytfeWorkspace

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import (
    WorkspaceAdapter,
)


class TestWorkspaceAdapterInit:
    """Test WorkspaceAdapter initialization."""

    def test_adapter_initialization_with_token(self):
        """Test adapter can be initialized with token."""
        adapter = WorkspaceAdapter(tfe_token="test-token")
        
        assert adapter.token == "test-token"
        assert adapter.address == "https://app.terraform.io"

    def test_adapter_initialization_with_custom_address(self):
        """Test adapter can be initialized with custom address."""
        adapter = WorkspaceAdapter(
            tfe_token="test-token",
            tfe_address="https://custom.terraform.io"
        )
        
        assert adapter.token == "test-token"
        assert adapter.address == "https://custom.terraform.io"

    def test_adapter_initialization_without_token_raises_error(self):
        """Test adapter raises error when initialized without token."""
        with pytest.raises(Exception):  # TerraformTokenNotFoundError
            WorkspaceAdapter(tfe_token=None)


class TestWorkspaceAdapterGetWorkspaceById:
    """Test WorkspaceAdapter.get_workspace_by_id method."""

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock adapter with mocked client."""
        adapter = WorkspaceAdapter(tfe_token="test-token")
        adapter._client = Mock()
        return adapter

    @pytest.fixture
    def mock_workspace(self):
        """Create a mock pytfe Workspace object."""
        workspace = Mock(spec=PytfeWorkspace)
        workspace.id = "ws-123"
        workspace.name = "test-workspace"
        workspace.description = "Test description"
        workspace.auto_apply = True
        workspace.locked = False
        workspace.terraform_version = "1.5.0"
        workspace.execution_mode = "remote"
        return workspace

    def test_get_workspace_by_id_success(self, mock_adapter, mock_workspace):
        """Test successfully retrieving workspace by ID."""
        mock_workspace.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "description": "Test description",
            "auto_apply": True,
        }
        mock_adapter.client.workspaces.read_by_id.return_value = mock_workspace
        
        result = mock_adapter.get_workspace_by_id("ws-123")
        
        mock_adapter.client.workspaces.read_by_id.assert_called_once_with("ws-123")
        assert result is not None
        assert result["id"] == "ws-123"
        assert result["name"] == "test-workspace"

    def test_get_workspace_by_id_not_found(self, mock_adapter):
        """Test handling workspace not found."""
        mock_adapter.client.workspaces.read_by_id.side_effect = NotFound("Workspace not found")
        
        result = mock_adapter.get_workspace_by_id("ws-nonexistent")
        
        assert result is None

    def test_get_workspace_by_id_auth_error(self, mock_adapter):
        """Test handling authentication error."""
        mock_adapter.client.workspaces.read_by_id.side_effect = AuthError("Unauthorized")
        
        # AuthError propagates directly (not wrapped in TerraformError)
        with pytest.raises(AuthError):
            mock_adapter.get_workspace_by_id("ws-123")


class TestWorkspaceAdapterGetWorkspaceByName:
    """Test WorkspaceAdapter.get_workspace_by_name method."""

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock adapter with mocked client."""
        adapter = WorkspaceAdapter(tfe_token="test-token")
        adapter._client = Mock()
        return adapter

    @pytest.fixture
    def mock_workspace(self):
        """Create a mock pytfe Workspace object."""
        workspace = Mock(spec=PytfeWorkspace)
        workspace.id = "ws-123"
        workspace.name = "test-workspace"
        workspace.description = "Test description"
        workspace.organization_name = "test-org"
        return workspace

    def test_get_workspace_by_name_success(self, mock_adapter, mock_workspace):
        """Test successfully retrieving workspace by name."""
        mock_workspace.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "description": "Test description",
            "organization_name": "test-org",
        }
        mock_adapter.client.workspaces.read.return_value = mock_workspace
        
        result = mock_adapter.get_workspace_by_name("test-org", "test-workspace")
        
        mock_adapter.client.workspaces.read.assert_called_once_with(
            "test-workspace",
            organization="test-org"
        )
        assert result is not None
        assert result["id"] == "ws-123"
        assert result["name"] == "test-workspace"

    def test_get_workspace_by_name_not_found(self, mock_adapter):
        """Test handling workspace not found by name."""
        mock_adapter.client.workspaces.read.side_effect = NotFound("Workspace not found")
        
        result = mock_adapter.get_workspace_by_name("test-org", "nonexistent-workspace")
        
        assert result is None

    def test_get_workspace_by_name_auth_error(self, mock_adapter):
        """Test handling authentication error."""
        mock_adapter.client.workspaces.read.side_effect = AuthError("Unauthorized")
        
        # AuthError propagates directly (not wrapped in TerraformError)
        with pytest.raises(AuthError):
            mock_adapter.get_workspace_by_name("test-org", "test-workspace")


class TestWorkspaceAdapterCreateWorkspace:
    """Test WorkspaceAdapter.create_workspace method."""

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock adapter with mocked client."""
        adapter = WorkspaceAdapter(tfe_token="test-token")
        adapter._client = Mock()
        return adapter

    @pytest.fixture
    def mock_workspace(self):
        """Create a mock pytfe Workspace object."""
        workspace = Mock(spec=PytfeWorkspace)
        workspace.id = "ws-new-123"
        workspace.name = "new-workspace"
        workspace.description = "New workspace"
        workspace.auto_apply = True
        return workspace

    def test_create_workspace_success(self, mock_adapter, mock_workspace):
        """Test successfully creating a workspace."""
        mock_workspace.model_dump.return_value = {
            "id": "ws-new-123",
            "name": "new-workspace",
            "description": "New workspace",
            "auto_apply": True,
        }
        mock_adapter.client.workspaces.create.return_value = mock_workspace
        
        result = mock_adapter.create_workspace(
            "test-org",
            name="new-workspace",
            description="New workspace",
            auto_apply=True
        )
        
        assert result is not None
        assert result["id"] == "ws-new-123"
        assert result["name"] == "new-workspace"
        assert result["description"] == "New workspace"

    def test_create_workspace_minimal_attributes(self, mock_adapter, mock_workspace):
        """Test creating workspace with minimal attributes."""
        mock_workspace.description = None
        mock_workspace.model_dump.return_value = {
            "id": "ws-new-123",
            "name": "new-workspace",
        }
        mock_adapter.client.workspaces.create.return_value = mock_workspace
        
        result = mock_adapter.create_workspace("test-org", name="new-workspace")
        
        assert result is not None
        assert result["id"] == "ws-new-123"


class TestWorkspaceAdapterUpdateWorkspace:
    """Test WorkspaceAdapter.update_workspace method."""

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock adapter with mocked client."""
        adapter = WorkspaceAdapter(tfe_token="test-token")
        adapter._client = Mock()
        return adapter

    @pytest.fixture
    def mock_workspace(self):
        """Create a mock pytfe Workspace object."""
        workspace = Mock(spec=PytfeWorkspace)
        workspace.id = "ws-123"
        workspace.name = "test-workspace"
        workspace.description = "Updated description"
        workspace.auto_apply = False
        return workspace

    def test_update_workspace_success(self, mock_adapter, mock_workspace):
        """Test successfully updating a workspace."""
        mock_workspace.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "description": "Updated description",
            "auto_apply": False,
        }
        mock_adapter.client.workspaces.update_by_id.return_value = mock_workspace
        
        result = mock_adapter.update_workspace(
            "ws-123",
            name="test-workspace",
            description="Updated description",
            auto_apply=False
        )
        
        assert result is not None
        assert result["id"] == "ws-123"
        assert result["description"] == "Updated description"
        assert result["auto_apply"] is False

    def test_update_workspace_not_found(self, mock_adapter):
        """Test updating a workspace that doesn't exist."""
        mock_adapter.client.workspaces.update_by_id.side_effect = NotFound("Workspace not found")
        
        with pytest.raises(TerraformError):
            mock_adapter.update_workspace("ws-nonexistent", name="test", description="New")


class TestWorkspaceAdapterDeleteWorkspace:
    """Test WorkspaceAdapter delete methods."""

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock adapter with mocked client."""
        adapter = WorkspaceAdapter(tfe_token="test-token")
        adapter._client = Mock()
        return adapter

    def test_safe_delete_workspace_success(self, mock_adapter):
        """Test successfully performing safe delete."""
        mock_adapter.client.workspaces.safe_delete_by_id.return_value = None
        
        # Should not raise error
        mock_adapter.safe_delete_workspace("ws-123")
        
        mock_adapter.client.workspaces.safe_delete_by_id.assert_called_once_with("ws-123")

    def test_force_delete_workspace_success(self, mock_adapter):
        """Test successfully performing force delete."""
        mock_adapter.client.workspaces.delete_by_id.return_value = None
        
        # Should not raise error
        mock_adapter.force_delete_workspace("ws-123")
        
        mock_adapter.client.workspaces.delete_by_id.assert_called_once_with("ws-123")

    def test_delete_workspace_not_found(self, mock_adapter):
        """Test deleting a workspace that doesn't exist."""
        mock_adapter.client.workspaces.safe_delete_by_id.side_effect = NotFound("Workspace not found")
        
        with pytest.raises(TerraformError):
            mock_adapter.safe_delete_workspace("ws-nonexistent")


class TestWorkspaceAdapterLockUnlock:
    """Test WorkspaceAdapter lock and unlock methods."""

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock adapter with mocked client."""
        adapter = WorkspaceAdapter(tfe_token="test-token")
        adapter._client = Mock()
        return adapter

    @pytest.fixture
    def mock_locked_workspace(self):
        """Create a mock locked workspace."""
        workspace = Mock(spec=PytfeWorkspace)
        workspace.id = "ws-123"
        workspace.name = "test-workspace"
        workspace.locked = True
        workspace.lock_reason = "Maintenance"
        return workspace

    @pytest.fixture
    def mock_unlocked_workspace(self):
        """Create a mock unlocked workspace."""
        workspace = Mock(spec=PytfeWorkspace)
        workspace.id = "ws-123"
        workspace.name = "test-workspace"
        workspace.locked = False
        workspace.lock_reason = None
        return workspace

    def test_lock_workspace_success(self, mock_adapter, mock_locked_workspace):
        """Test successfully locking a workspace."""
        mock_locked_workspace.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "locked": True,
            "lock_reason": "Maintenance",
        }
        mock_adapter.client.workspaces.lock.return_value = mock_locked_workspace
        
        result = mock_adapter.lock_workspace("ws-123", "Maintenance")
        
        assert result is not None
        assert result["id"] == "ws-123"
        assert result["locked"] is True
        assert result["lock_reason"] == "Maintenance"

    def test_unlock_workspace_success(self, mock_adapter, mock_unlocked_workspace):
        """Test successfully unlocking a workspace."""
        mock_unlocked_workspace.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "locked": False,
        }
        mock_adapter.client.workspaces.unlock.return_value = mock_unlocked_workspace
        
        result = mock_adapter.unlock_workspace("ws-123")
        
        assert result is not None
        assert result["id"] == "ws-123"
        assert result["locked"] is False

    def test_force_unlock_workspace_success(self, mock_adapter, mock_unlocked_workspace):
        """Test successfully force unlocking a workspace."""
        mock_unlocked_workspace.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "locked": False,
        }
        mock_adapter.client.workspaces.force_unlock.return_value = mock_unlocked_workspace
        
        result = mock_adapter.force_unlock_workspace("ws-123")
        
        assert result is not None
        assert result["id"] == "ws-123"
        assert result["locked"] is False

    def test_lock_workspace_not_found(self, mock_adapter):
        """Test locking a workspace that doesn't exist."""
        mock_adapter.client.workspaces.lock.side_effect = NotFound("Workspace not found")
        
        with pytest.raises(TerraformError):
            mock_adapter.lock_workspace("ws-nonexistent", "Test")

    def test_unlock_workspace_auth_error(self, mock_adapter):
        """Test unlocking without proper permissions."""
        mock_adapter.client.workspaces.unlock.side_effect = AuthError("Unauthorized")
        
        with pytest.raises(TerraformError):
            mock_adapter.unlock_workspace("ws-123")


class TestWorkspaceAdapterFormatResponse:
    """Test WorkspaceAdapter.format_response method."""

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock adapter."""
        return WorkspaceAdapter(tfe_token="test-token")

    def test_format_response_with_pytfe_workspace(self, mock_adapter):
        """Test formatting a pytfe Workspace object."""
        workspace = Mock(spec=PytfeWorkspace)
        workspace.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "type": "workspaces",
            "description": "Test",
            "auto_apply": True,
            "locked": False,
            "terraform_version": "1.5.0",
            "execution_mode": "remote",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
        }
        
        result = mock_adapter.format_response(workspace)
        
        assert isinstance(result, dict)
        assert result["id"] == "ws-123"
        assert result["name"] == "test-workspace"
        assert result["type"] == "workspaces"

    def test_format_response_handles_nested_objects(self, mock_adapter):
        """Test formatting workspace with nested objects."""
        workspace = Mock(spec=PytfeWorkspace)
        workspace.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "project": {
                "id": "prj-123",
                "name": "test-project",
            }
        }
        
        result = mock_adapter.format_response(workspace)
        
        assert result["id"] == "ws-123"
        assert result["project"]["id"] == "prj-123"


class TestWorkspaceAdapterCleanup:
    """Test WorkspaceAdapter cleanup functionality."""

    def test_adapter_cleanup(self):
        """Test adapter cleanup is called."""
        adapter = WorkspaceAdapter(tfe_token="test-token")
        mock_client = Mock()
        adapter._client = mock_client
        
        adapter.cleanup()
        
        mock_client.close.assert_called_once()
        assert adapter._client is None
