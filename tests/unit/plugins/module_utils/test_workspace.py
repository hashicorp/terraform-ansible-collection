# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import sys

from unittest.mock import Mock

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import (
    create_workspace,
    force_delete_workspace,
    force_unlock_workspace,
    get_tag_bindings,
    get_workspace,
    get_workspace_by_id,
    lock_workspace,
    safe_delete_workspace,
    unlock_workspace,
    update_workspace,
)


class TestGetWorkspace:
    """Test cases for get_workspace function."""

    @pytest.mark.parametrize("status_code", [401, 403, 500, 502])
    def test_get_workspace_raises_terraform_error_on_error_status(self, status_code):
        """Test get_workspace raises TerraformError for error status codes."""
        mock_tf_client = Mock()
        organization = "test-org"
        workspace_name = "test-workspace"

        response = {"status": status_code}
        mock_tf_client.get.return_value = response

        with pytest.raises(TerraformError):
            get_workspace(mock_tf_client, organization, workspace_name)

    @pytest.mark.parametrize(
        "response_data,expected_result",
        [
            # Successful response with full data
            (
                {
                    "data": {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}},
                    "status": 200,
                },
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}, "status": 200},
            ),
            # Empty data section
            ({"data": {}, "status": 200}, {"status": 200}),
            # No data key
            ({"status": 200}, {"status": 200}),
            # Workspace not found
            ({"status": 404}, {}),
        ],
    )
    def test_get_workspace_responses(self, response_data, expected_result):
        """Test get_workspace with various response formats."""
        mock_tf_client = Mock()
        organization = "test-org"
        workspace_name = "test-workspace"

        mock_tf_client.get.return_value = response_data
        result = get_workspace(mock_tf_client, organization, workspace_name)
        assert result == expected_result

    @pytest.mark.parametrize(
        "organization,workspace_name",
        [
            ("test-org", "test-workspace"),
            ("my-company", "production-app"),
            ("dev-team", "staging-environment"),
        ],
    )
    def test_get_workspace_with_valid_names(self, organization, workspace_name):
        """Test get_workspace with realistic organization and workspace names."""
        mock_tf_client = Mock()
        workspace_id = "ws-123abc456def789"

        expected_response = {"data": {"id": workspace_id, "attributes": {"name": workspace_name}}, "status": 200}
        mock_tf_client.get.return_value = expected_response

        result = get_workspace(mock_tf_client, organization, workspace_name)

        expected_result = {"id": workspace_id, "attributes": {"name": workspace_name}, "status": 200}
        assert result == expected_result
        mock_tf_client.get.assert_called_with(f"/organizations/{organization}/workspaces/{workspace_name}")

    def test_get_workspace_with_complex_data_structure(self):
        """Test get_workspace with complex nested data structure."""
        mock_tf_client = Mock()
        organization = "test-org"
        workspace_name = "test-workspace"
        workspace_id = "ws-123abc456def789"

        expected_response = {
            "data": {
                "id": workspace_id,
                "type": "workspaces",
                "attributes": {
                    "name": workspace_name,
                    "environment": "production",
                    "auto-apply": False,
                    "terraform-version": "1.0.0",
                    "working-directory": "/terraform",
                    "vcs-repo": {"identifier": "org/repo", "branch": "main", "oauth-token-id": "ot-123"},
                    "tags": ["production", "webapp"],
                },
                "relationships": {"organization": {"data": {"id": "org-123", "type": "organizations"}}},
            },
            "status": 200,
        }
        mock_tf_client.get.return_value = expected_response

        result = get_workspace(mock_tf_client, organization, workspace_name)

        expected_result = expected_response["data"].copy()
        expected_result["status"] = 200
        assert result == expected_result


class TestGetWorkspaceById:
    """Test cases for get_workspace_by_id function."""

    @pytest.mark.parametrize("status_code", [401, 403, 500, 502])
    def test_get_workspace_by_id_raises_terraform_error_on_error_status(self, status_code):
        """Test get_workspace_by_id raises TerraformError for error status codes."""
        mock_tf_client = Mock()
        workspace_id = "ws-123abc456def789"

        response = {"status": status_code}
        mock_tf_client.get.return_value = response

        with pytest.raises(TerraformError):
            get_workspace_by_id(mock_tf_client, workspace_id)

    @pytest.mark.parametrize(
        "response_data,expected_result",
        [
            # Successful response with full data
            (
                {
                    "data": {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}},
                    "status": 200,
                },
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}, "status": 200},
            ),
            # Empty data section
            ({"data": {}, "status": 200}, {"status": 200}),
            # No data key
            ({"status": 200}, {"status": 200}),
            # Workspace not found
            ({"status": 404}, {}),
        ],
    )
    def test_get_workspace_by_id_responses(self, response_data, expected_result):
        """Test get_workspace_by_id with various response formats."""
        mock_tf_client = Mock()
        workspace_id = "ws-123abc456def789"

        mock_tf_client.get.return_value = response_data
        result = get_workspace_by_id(mock_tf_client, workspace_id)
        assert result == expected_result

    def test_get_workspace_by_id_with_valid_id(self):
        """Test get_workspace_by_id with a valid workspace ID."""
        mock_tf_client = Mock()
        workspace_id = "ws-123abc456def789"

        expected_response = {"data": {"id": workspace_id, "type": "workspaces", "attributes": {"name": "test-workspace"}}, "status": 200}
        mock_tf_client.get.return_value = expected_response

        result = get_workspace_by_id(mock_tf_client, workspace_id)

        expected_result = {"id": workspace_id, "type": "workspaces", "attributes": {"name": "test-workspace"}, "status": 200}
        assert result == expected_result
        mock_tf_client.get.assert_called_with(f"/workspaces/{workspace_id}")

    def test_get_workspace_by_id_with_complex_data_structure(self):
        """Test get_workspace_by_id with complex nested data structure."""
        mock_tf_client = Mock()
        workspace_id = "ws-123abc456def789"

        expected_response = {
            "data": {
                "id": workspace_id,
                "type": "workspaces",
                "attributes": {
                    "name": "complex-workspace",
                    "environment": "staging",
                    "auto-apply": True,
                    "terraform-version": "1.5.0",
                    "working-directory": "/terraform/modules",
                    "vcs-repo": {"identifier": "company/infrastructure", "branch": "develop", "oauth-token-id": "ot-987654321"},
                    "tags": ["staging", "infrastructure", "automated"],
                    "permissions": {"can-update": True, "can-destroy": False, "can-queue-run": True},
                },
                "relationships": {
                    "organization": {"data": {"id": "org-456", "type": "organizations"}},
                    "current-run": {"data": {"id": "run-789", "type": "runs"}},
                },
                "links": {"self": "/api/v2/workspaces/ws-123abc456def789", "self-html": "/app/org-456/workspaces/complex-workspace"},
            },
            "status": 200,
        }
        mock_tf_client.get.return_value = expected_response

        result = get_workspace_by_id(mock_tf_client, workspace_id)

        expected_result = expected_response["data"].copy()
        expected_result["status"] = 200
        assert result == expected_result


class TestGetTagBindings:
    """Test cases for get_tag_bindings function."""

    @pytest.mark.parametrize("status_code", [401, 403])
    def test_get_tag_bindings_raises_terraform_error_on_error_status(self, status_code):
        """Test get_tag_bindings raises TerraformError for error status codes."""
        mock_tf_client = Mock()
        workspace_id = "ws-123abc456def789"

        response = {"status": status_code}
        mock_tf_client.get.return_value = response

        with pytest.raises(TerraformError):
            get_tag_bindings(mock_tf_client, workspace_id)

    @pytest.mark.parametrize(
        "response_data,expected_result",
        [
            # Successful response with full data
            (
                {
                    "data": {
                        "id": "tag-bindings-123",
                        "type": "tag-bindings",
                        "attributes": {"key": "environment", "value": "uat"},
                    },
                    "status": 200,
                },
                {
                    "id": "tag-bindings-123",
                    "type": "tag-bindings",
                    "attributes": {"key": "environment", "value": "uat"},
                    "status": 200,
                },
            ),
            # Empty data section
            ({"data": {}, "status": 200}, {"status": 200}),
            # No data key
            ({"status": 200}, {"status": 200}),
            # Workspace not found
            ({"status": 404}, {}),
        ],
    )
    def test_get_tag_bindings_responses(self, response_data, expected_result):
        """Test get_tag_bindings with various response formats."""
        mock_tf_client = Mock()
        workspace_id = "ws-123abc456def789"

        mock_tf_client.get.return_value = response_data
        result = get_tag_bindings(mock_tf_client, workspace_id)
        assert result == expected_result

    def test_get_tag_bindings_with_valid_workspace_id(self):
        """Test get_tag_bindings returns correct structure with known response."""
        mock_tf_client = Mock()
        workspace_id = "ws-abc123"

        response_data = {
            "data": {
                "id": "tag-bindings-999",
                "type": "tag-bindings",
                "attributes": {"key": "region", "value": "us-east"},
            },
            "status": 200,
        }

        mock_tf_client.get.return_value = response_data
        result = get_tag_bindings(mock_tf_client, workspace_id)

        expected_result = response_data["data"].copy()
        expected_result["status"] = 200
        assert result == expected_result
        mock_tf_client.get.assert_called_once_with(f"/workspaces/{workspace_id}/tag-bindings")


class TestCreateWorkspace:
    """Test cases for create_workspace function."""

    def test_create_workspace_success(self):
        """Test that create_workspace returns data correctly on successful creation (201)."""
        mock_tf_client = Mock()
        organization = "test-org"
        workspace_payload = {"name": "my-workspace", "description": "Test workspace"}

        mock_response = {
            "data": {
                "id": "ws-123456",
                "type": "workspaces",
                "attributes": workspace_payload,
            },
            "status": 201,
        }
        mock_tf_client.post.return_value = mock_response

        result = create_workspace(mock_tf_client, organization, workspace_payload)

        expected_result = mock_response["data"].copy()
        expected_result["status"] = 201
        assert result == expected_result
        mock_tf_client.post.assert_called_once_with(f"/organizations/{organization}/workspaces", data=workspace_payload)

    @pytest.mark.parametrize("status_code", [400, 401, 500])
    def test_create_workspace_failure_raises_terraform_error(self, status_code):
        """Test that create_workspace raises TerraformError on failure (non-201 status)."""
        mock_tf_client = Mock()
        organization = "test-org"
        workspace_payload = {"name": "invalid-workspace"}

        mock_response = {"status": status_code}
        mock_tf_client.post.return_value = mock_response

        with pytest.raises(TerraformError):
            create_workspace(mock_tf_client, organization, workspace_payload)


class TestUpdateWorkspace:
    """Test cases for update_workspace function."""

    def test_update_workspace_success(self):
        """Test that update_workspace returns updated data correctly on success (200)."""
        mock_tf_client = Mock()
        workspace_id = "ws-789xyz"
        update_payload = {"description": "Updated description"}

        mock_response = {
            "data": {
                "id": workspace_id,
                "type": "workspaces",
                "attributes": update_payload,
            },
            "status": 200,
        }
        mock_tf_client.patch.return_value = mock_response

        result = update_workspace(mock_tf_client, workspace_id, update_payload)

        expected_result = mock_response["data"].copy()
        expected_result["status"] = 200

        assert result == expected_result
        mock_tf_client.patch.assert_called_once_with(f"/workspaces/{workspace_id}", data=update_payload)

    @pytest.mark.parametrize("status_code", [400, 401, 404])
    def test_update_workspace_failure_raises_terraform_error(self, status_code):
        """Test that update_workspace raises TerraformError on failure (non-200 status)."""
        mock_tf_client = Mock()
        workspace_id = "ws-invalid"
        update_payload = {"name": "bad-workspace"}

        mock_response = {"status": status_code}
        mock_tf_client.patch.return_value = mock_response

        with pytest.raises(TerraformError):
            update_workspace(mock_tf_client, workspace_id, update_payload)


class TestSafeDeleteWorkspace:
    """Test cases for safe_delete_workspace function."""

    def test_safe_delete_successful(self):
        """Should return status=204 when deletion is successful."""
        mock_tf_client = Mock()
        workspace_id = "ws-123abc"

        mock_tf_client.post.return_value = {"status": 204}

        result = safe_delete_workspace(mock_tf_client, workspace_id)
        assert result == {"status": 204}
        mock_tf_client.post.assert_called_once_with(f"/workspaces/{workspace_id}/actions/safe-delete")

    def test_safe_delete_workspace_not_found(self):
        """Should return empty dict when workspace is not found (404)."""
        mock_tf_client = Mock()
        workspace_id = "ws-notfound"

        mock_tf_client.post.return_value = {"status": 404}

        result = safe_delete_workspace(mock_tf_client, workspace_id)
        assert result == {}
        mock_tf_client.post.assert_called_once_with(f"/workspaces/{workspace_id}/actions/safe-delete")

    @pytest.mark.parametrize("status_code", [400, 401, 403])
    def test_safe_delete_raises_terraform_error_on_failure(self, status_code):
        """Should raise TerraformError for any status code not 204 or 404."""
        mock_tf_client = Mock()
        workspace_id = "ws-error"

        mock_tf_client.post.return_value = {"status": status_code}

        with pytest.raises(TerraformError) as exc_info:
            safe_delete_workspace(mock_tf_client, workspace_id)

        assert exc_info.type is TerraformError
        assert exc_info.value.args[0]["status"] == status_code
        mock_tf_client.post.assert_called_once_with(f"/workspaces/{workspace_id}/actions/safe-delete")


class TestForceDeleteWorkspace:
    """Test cases for force_delete_workspace function."""

    def test_force_delete_successful(self):
        """Should return status=204 when deletion is successful."""
        mock_tf_client = Mock()
        workspace_id = "ws-123"

        mock_tf_client.delete.return_value = {"status": 204}

        result = force_delete_workspace(mock_tf_client, workspace_id)
        assert result == {"status": 204}
        mock_tf_client.delete.assert_called_once_with(f"/workspaces/{workspace_id}")

    def test_force_delete_workspace_not_found(self):
        """Should return empty dict when workspace is not found (404)."""
        mock_tf_client = Mock()
        workspace_id = "ws-404"

        mock_tf_client.delete.return_value = {"status": 404}

        result = force_delete_workspace(mock_tf_client, workspace_id)
        assert result == {}
        mock_tf_client.delete.assert_called_once_with(f"/workspaces/{workspace_id}")

    @pytest.mark.parametrize("status_code", [400, 401, 403])
    def test_force_delete_raises_terraform_error(self, status_code):
        """Should raise TerraformError for any non-204/404 status."""
        mock_tf_client = Mock()
        workspace_id = "ws-failure"

        mock_tf_client.delete.return_value = {"status": status_code}

        with pytest.raises(TerraformError) as exc_info:
            force_delete_workspace(mock_tf_client, workspace_id)

        assert exc_info.type is TerraformError
        assert exc_info.value.args[0]["status"] == status_code
        mock_tf_client.delete.assert_called_once_with(f"/workspaces/{workspace_id}")


class TestLockWorkspace:
    """Test cases for lock_workspace function."""

    def test_lock_workspace_successful(self):
        """Should return data with status when lock is successful (200)."""
        mock_tf_client = Mock()
        workspace_id = "ws-123"
        lock_reason = "Prevent changes during release"

        mock_tf_client.post.return_value = {"data": {"id": workspace_id, "type": "workspaces", "attributes": {"locked": True}}, "status": 200}

        result = lock_workspace(mock_tf_client, workspace_id, lock_reason)
        assert result == {"id": workspace_id, "type": "workspaces", "attributes": {"locked": True}, "status": 200}
        mock_tf_client.post.assert_called_once_with(f"/workspaces/{workspace_id}/actions/lock", data={"reason": lock_reason})

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404])
    def test_lock_workspace_raises_terraform_error(self, status_code):
        """Should raise TerraformError on any non-200 response status."""
        mock_tf_client = Mock()
        workspace_id = "ws-error"
        lock_reason = "Testing failure"

        mock_tf_client.post.return_value = {"status": status_code, "error": f"Failed with {status_code}"}

        with pytest.raises(TerraformError) as exc_info:
            lock_workspace(mock_tf_client, workspace_id, lock_reason)

        assert exc_info.type is TerraformError
        assert exc_info.value.args[0]["status"] == status_code
        mock_tf_client.post.assert_called_once_with(f"/workspaces/{workspace_id}/actions/lock", data={"reason": lock_reason})


class TestUnlockWorkspace:
    """Test cases for unlock_workspace function."""

    def test_unlock_workspace_successful(self):
        """Should return data with status when unlock is successful (200)."""
        mock_tf_client = Mock()
        workspace_id = "ws-123"

        mock_tf_client.post.return_value = {"data": {"id": workspace_id, "type": "workspaces", "attributes": {"locked": False}}, "status": 200}

        result = unlock_workspace(mock_tf_client, workspace_id)
        assert result == {"id": workspace_id, "type": "workspaces", "attributes": {"locked": False}, "status": 200}
        mock_tf_client.post.assert_called_once_with(f"/workspaces/{workspace_id}/actions/unlock")

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404])
    def test_unlock_workspace_raises_terraform_error(self, status_code):
        """Should raise TerraformError on any non-200 response status."""
        mock_tf_client = Mock()
        workspace_id = "ws-error"

        mock_tf_client.post.return_value = {"status": status_code, "error": f"Failed with status {status_code}"}

        with pytest.raises(TerraformError) as exc_info:
            unlock_workspace(mock_tf_client, workspace_id)

        assert exc_info.type is TerraformError
        assert exc_info.value.args[0]["status"] == status_code
        mock_tf_client.post.assert_called_once_with(f"/workspaces/{workspace_id}/actions/unlock")


class TestForceUnlockWorkspace:
    """Test cases for force_unlock_workspace function."""

    def test_force_unlock_workspace_successful(self):
        """Should return response data when force unlock succeeds (status 200)."""
        mock_tf_client = Mock()
        workspace_id = "ws-123"

        mock_tf_client.post.return_value = {"data": {"id": workspace_id, "type": "workspaces", "attributes": {"locked": False}}, "status": 200}

        result = force_unlock_workspace(mock_tf_client, workspace_id)

        assert result == {"id": workspace_id, "type": "workspaces", "attributes": {"locked": False}, "status": 200}
        mock_tf_client.post.assert_called_once_with(f"/workspaces/{workspace_id}/actions/force-unlock")

    @pytest.mark.parametrize(
        "status_code",
        [
            400,
            401,
            403,
            404,
        ],
    )
    def test_force_unlock_workspace_raises_terraform_error(self, status_code):
        """Should raise TerraformError when force unlock fails with non-200 status."""
        mock_tf_client = Mock()
        workspace_id = "ws-error"

        mock_tf_client.post.return_value = {"status": status_code, "error": f"Force unlock failed with status {status_code}"}

        with pytest.raises(TerraformError) as exc_info:
            force_unlock_workspace(mock_tf_client, workspace_id)

        assert exc_info.type is TerraformError
        assert exc_info.value.args[0]["status"] == status_code
        mock_tf_client.post.assert_called_once_with(f"/workspaces/{workspace_id}/actions/force-unlock")
