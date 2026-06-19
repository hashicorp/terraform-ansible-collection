# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
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
        adapter.client.workspaces.list_tag_bindings.return_value = []
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

            mock_lock.assert_called_once_with(mock_adapter, workspace_response_unlocked["id"], reason=params["lock_reason"])
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
        adapter.client.workspaces.list_tag_bindings.return_value = []
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
        adapter.client.workspaces.list_tag_bindings.return_value = []
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

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id") as mock_get, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.update_workspace"
        ) as mock_update:

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
            assert result["id"] == "ws-123"
            assert result["name"] == "test-workspace"

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
        adapter.client.workspaces.list_tag_bindings.return_value = []
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
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace", return_value=None
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_create", return_value={"changed": True, "msg": "created"}):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert test_module.exit_args["msg"] == "created"

    def test_main_updates_workspace_if_exists(self, test_module):
        test_module.params["workspace_id"] = None
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace", return_value={"id": "ws-123"}
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_update", return_value={"changed": False, "msg": "no changes"}):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is False
            assert test_module.exit_args["msg"] == "no changes"

    def test_main_deletes_workspace(self, test_module):
        test_module.params.update({"state": "absent", "workspace_id": "ws-123"})
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id", return_value={"data": {}}
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_absent", return_value={"changed": True, "msg": "deleted"}):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert test_module.exit_args["msg"] == "deleted"

    def test_main_locks_workspace(self, test_module):
        test_module.params.update({"state": "locked", "workspace_id": "ws-123"})
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id", return_value={"id": "ws-123", "locked": False}
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_locked", return_value={"changed": True, "msg": "locked"}):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert test_module.exit_args["msg"] == "locked"

    def test_main_unlocks_workspace(self, test_module):
        test_module.params.update({"state": "unlocked", "workspace_id": "ws-123"})
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace_by_id", return_value={"id": "ws-123", "locked": True}
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_unlocked", return_value={"changed": True, "msg": "unlocked"}):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert test_module.exit_args["msg"] == "unlocked"

    def test_main_check_mode_creation(self, test_module):
        test_module.check_mode = True
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace", return_value=None
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.state_create", return_value={"changed": True, "msg": "would be created"}):

            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert "would be created" in test_module.exit_args["msg"]

    def test_main_fails_on_exception(self, test_module):
        test_module.client = lambda: (i for i in ()).throw(Exception("something broke"))
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace.AnsibleTerraformModule", return_value=test_module):

            with pytest.raises(AssertionError) as e:
                main()

            assert "something broke" in str(e.value)
