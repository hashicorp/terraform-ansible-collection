# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Unit tests for refactored workspace module_utils functions.
These tests mock the pytfe SDK calls instead of HTTP responses.
"""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import (
    create_workspace,
    force_delete_workspace,
    force_unlock_workspace,
    get_workspace,
    get_workspace_by_id,
    lock_workspace,
    safe_delete_workspace,
    unlock_workspace,
    update_workspace,
)


class TestGetWorkspace:
    """Test cases for get_workspace function with pytfe SDK."""

    def test_get_workspace_success(self):
        """Test get_workspace returns formatted workspace data."""
        mock_adapter = Mock()
        mock_workspace = Mock()
        mock_workspace.id = "ws-123"
        mock_workspace.name = "test-workspace"
        mock_workspace.model_dump.return_value = {"id": "ws-123", "name": "test-workspace", "description": "Test workspace"}

        mock_adapter.client.workspaces.read.return_value = mock_workspace

        result = get_workspace(mock_adapter, "test-org", "test-workspace")

        assert result is not None
        assert result["id"] == "ws-123"
        assert result["name"] == "test-workspace"
        mock_adapter.client.workspaces.read.assert_called_once_with("test-workspace", organization="test-org")

    def test_get_workspace_not_found(self):
        """Test get_workspace returns None when workspace not found."""
        mock_adapter = Mock()
        mock_adapter.client.workspaces.read.side_effect = NotFound("Workspace not found")

        result = get_workspace(mock_adapter, "test-org", "nonexistent")

        assert result is None
        mock_adapter.client.workspaces.read.assert_called_once_with("nonexistent", organization="test-org")


class TestGetWorkspaceById:
    """Test cases for get_workspace_by_id function with pytfe SDK."""

    def test_get_workspace_by_id_success(self):
        """Test get_workspace_by_id returns formatted workspace data."""
        mock_adapter = Mock()
        mock_workspace = Mock()
        mock_workspace.id = "ws-456"
        mock_workspace.name = "prod-workspace"
        mock_workspace.model_dump.return_value = {"id": "ws-456", "name": "prod-workspace", "auto_apply": True}

        mock_adapter.client.workspaces.read_by_id.return_value = mock_workspace

        result = get_workspace_by_id(mock_adapter, "ws-456")

        assert result is not None
        assert result["id"] == "ws-456"
        assert result["name"] == "prod-workspace"
        mock_adapter.client.workspaces.read_by_id.assert_called_once_with("ws-456")

    def test_get_workspace_by_id_not_found(self):
        """Test get_workspace_by_id returns None when workspace not found."""
        mock_adapter = Mock()
        mock_adapter.client.workspaces.read_by_id.side_effect = NotFound("Workspace not found")

        result = get_workspace_by_id(mock_adapter, "ws-nonexistent")

        assert result is None
        mock_adapter.client.workspaces.read_by_id.assert_called_once_with("ws-nonexistent")


class TestCreateWorkspace:
    """Test cases for create_workspace function with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.format_response")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace._build_workspace_payload")
    def test_create_workspace_success(self, mock_build_payload, mock_format, mock_safe_call):
        """Test create_workspace with successful creation."""
        mock_adapter = Mock()
        mock_workspace = Mock()
        mock_workspace.id = "ws-new"

        mock_build_payload.return_value = {"name": "new-workspace"}
        mock_safe_call.return_value = mock_workspace
        mock_format.return_value = {"id": "ws-new", "name": "new-workspace"}

        result = create_workspace(mock_adapter, "test-org", name="new-workspace")

        assert result["id"] == "ws-new"
        mock_build_payload.assert_called_once()
        mock_safe_call.assert_called_once()
        mock_format.assert_called_once_with(mock_workspace)


class TestUpdateWorkspace:
    """Test cases for update_workspace function with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.format_response")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace._build_workspace_payload")
    def test_update_workspace_success(self, mock_build_payload, mock_format, mock_safe_call):
        """Test update_workspace with successful update."""
        mock_adapter = Mock()
        mock_workspace = Mock()
        mock_workspace.id = "ws-123"

        # Include name in the payload since WorkspaceUpdateOptions requires it
        mock_build_payload.return_value = {"name": "test-workspace", "description": "Updated description"}
        mock_safe_call.return_value = mock_workspace
        mock_format.return_value = {"id": "ws-123", "name": "test-workspace", "description": "Updated description"}

        result = update_workspace(mock_adapter, "ws-123", name="test-workspace", description="Updated description")

        assert result["id"] == "ws-123"
        mock_build_payload.assert_called_once()
        mock_safe_call.assert_called_once()
        mock_format.assert_called_once_with(mock_workspace)


class TestLockWorkspace:
    """Test cases for lock_workspace function with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.format_response")
    def test_lock_workspace_success(self, mock_format, mock_safe_call):
        """Test lock_workspace with successful lock."""
        mock_adapter = Mock()
        mock_workspace = Mock()
        mock_workspace.id = "ws-123"
        mock_workspace.locked = True

        mock_safe_call.return_value = mock_workspace
        mock_format.return_value = {"id": "ws-123", "locked": True}

        result = lock_workspace(mock_adapter, "ws-123", "Maintenance")

        assert result["locked"] is True
        mock_safe_call.assert_called_once()
        mock_format.assert_called_once_with(mock_workspace)


class TestUnlockWorkspace:
    """Test cases for unlock_workspace function with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.format_response")
    def test_unlock_workspace_success(self, mock_format, mock_safe_call):
        """Test unlock_workspace with successful unlock."""
        mock_adapter = Mock()
        mock_workspace = Mock()
        mock_workspace.id = "ws-123"
        mock_workspace.locked = False

        mock_safe_call.return_value = mock_workspace
        mock_format.return_value = {"id": "ws-123", "locked": False}

        result = unlock_workspace(mock_adapter, "ws-123")

        assert result["locked"] is False
        mock_safe_call.assert_called_once()
        mock_format.assert_called_once_with(mock_workspace)


class TestForceUnlockWorkspace:
    """Test cases for force_unlock_workspace function with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.format_response")
    def test_force_unlock_workspace_success(self, mock_format, mock_safe_call):
        """Test force_unlock_workspace with successful force unlock."""
        mock_adapter = Mock()
        mock_workspace = Mock()
        mock_workspace.id = "ws-123"
        mock_workspace.locked = False

        mock_safe_call.return_value = mock_workspace
        mock_format.return_value = {"id": "ws-123", "locked": False}

        result = force_unlock_workspace(mock_adapter, "ws-123")

        assert result["locked"] is False
        mock_safe_call.assert_called_once()
        mock_format.assert_called_once_with(mock_workspace)


class TestDeleteWorkspace:
    """Test cases for delete workspace functions with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.safe_api_call")
    def test_safe_delete_workspace(self, mock_safe_call):
        """Test safe_delete_workspace calls safe_api_call correctly."""
        mock_adapter = Mock()
        mock_safe_call.return_value = None

        safe_delete_workspace(mock_adapter, "ws-123")

        mock_safe_call.assert_called_once()

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.safe_api_call")
    def test_force_delete_workspace(self, mock_safe_call):
        """Test force_delete_workspace calls safe_api_call correctly."""
        mock_adapter = Mock()
        mock_safe_call.return_value = None

        force_delete_workspace(mock_adapter, "ws-123")

        mock_safe_call.assert_called_once()
