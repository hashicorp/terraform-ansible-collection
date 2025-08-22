# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import sys

from unittest.mock import Mock

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace, get_workspace_by_id


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
                    "data": {"data": {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}}},
                    "status": 200,
                },
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}, "status": 200},
            ),
            # Empty data section
            ({"data": {"data": {}}, "status": 200}, {"status": 200}),
            # No data key
            ({"data": {}, "status": 200}, {"status": 200}),
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

        expected_response = {"data": {"data": {"id": workspace_id, "attributes": {"name": workspace_name}}}, "status": 200}
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
                }
            },
            "status": 200,
        }
        mock_tf_client.get.return_value = expected_response

        result = get_workspace(mock_tf_client, organization, workspace_name)

        expected_result = expected_response["data"]["data"].copy()
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
                    "data": {"data": {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}}},
                    "status": 200,
                },
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}, "status": 200},
            ),
            # Empty data section
            ({"data": {"data": {}}, "status": 200}, {"status": 200}),
            # No data key
            ({"data": {}, "status": 200}, {"status": 200}),
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

        expected_response = {"data": {"data": {"id": workspace_id, "type": "workspaces", "attributes": {"name": "test-workspace"}}}, "status": 200}
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
                }
            },
            "status": 200,
        }
        mock_tf_client.get.return_value = expected_response

        result = get_workspace_by_id(mock_tf_client, workspace_id)

        expected_result = expected_response["data"]["data"].copy()
        expected_result["status"] = 200
        assert result == expected_result
