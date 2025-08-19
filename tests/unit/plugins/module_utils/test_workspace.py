# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import unittest

from unittest.mock import Mock

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)

# Import the module under test
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import (
    get_workspace,
    get_workspace_by_id,
)


class TestWorkspaceFunctions(unittest.TestCase):
    """Unit tests for Terraform workspace helper functions."""

    def setUp(self):
        """Set up common test variables and mocks."""
        self.mock_tf_client = Mock()
        self.organization = "test-org"
        self.workspace_name = "test-workspace"
        self.workspace_id = "ws-123abc456def789"

    def test_get_workspace_error_status_codes(self):
        """Test get_workspace raises TerraformError for various error status codes."""
        error_codes = [400, 401, 403, 422, 500, 502, 503]

        for status_code in error_codes:
            with self.subTest(status_code=status_code):
                response = {"status": status_code}
                self.mock_tf_client.get.return_value = response

                with self.assertRaises(TerraformError):
                    get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

    def test_get_workspace_responses(self):
        """Test get_workspace with various response formats."""
        test_cases = [
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
        ]

        for response_data, expected_result in test_cases:
            with self.subTest(response_data=response_data):
                self.mock_tf_client.get.return_value = response_data
                result = get_workspace(self.mock_tf_client, self.organization, self.workspace_name)
                self.assertEqual(result, expected_result)

    def test_get_workspace_with_various_names(self):
        """Test get_workspace with various organization and workspace names."""
        test_cases = [
            ("test-org", "test-workspace"),
            ("test-org-123", "test-workspace_prod.v2"),
            ("org.with.dots", "workspace-with-dashes"),
            ("special$org", "workspace@123"),
            ("unicode-тест", "workspace-测试"),
        ]

        for org, workspace in test_cases:
            with self.subTest(org=org, workspace=workspace):
                expected_response = {"data": {"id": self.workspace_id, "attributes": {"name": workspace}}, "status": 200}
                self.mock_tf_client.get.return_value = expected_response

                result = get_workspace(self.mock_tf_client, org, workspace)

                expected_result = {"id": self.workspace_id, "attributes": {"name": workspace}, "status": 200}
                self.assertEqual(result, expected_result)
                self.mock_tf_client.get.assert_called_with(f"/organizations/{org}/workspaces/{workspace}")

    def test_get_workspace_with_complex_data_structure(self):
        """Test get_workspace with complex nested data structure."""
        expected_response = {
            "data": {
                "id": self.workspace_id,
                "type": "workspaces",
                "attributes": {
                    "name": self.workspace_name,
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
        self.mock_tf_client.get.return_value = expected_response

        result = get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

        expected_result = expected_response["data"].copy()
        expected_result["status"] = 200
        self.assertEqual(result, expected_result)


class TestGetWorkspaceById(unittest.TestCase):
    """Unit tests for get_workspace_by_id function."""

    def setUp(self):
        """Set up common test variables and mocks."""
        self.mock_tf_client = Mock()
        self.workspace_id = "ws-123abc456def789"

    def test_get_workspace_by_id_error_status_codes(self):
        """Test get_workspace_by_id raises TerraformError for various error status codes."""
        error_codes = [400, 401, 403, 422, 500, 502, 503]

        for status_code in error_codes:
            with self.subTest(status_code=status_code):
                response = {"status": status_code}
                self.mock_tf_client.get.return_value = response

                with self.assertRaises(TerraformError):
                    get_workspace_by_id(self.mock_tf_client, self.workspace_id)

    def test_get_workspace_by_id_responses(self):
        """Test get_workspace_by_id with various response formats."""
        test_cases = [
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
        ]

        for response_data, expected_result in test_cases:
            with self.subTest(response_data=response_data):
                self.mock_tf_client.get.return_value = response_data
                result = get_workspace_by_id(self.mock_tf_client, self.workspace_id)
                self.assertEqual(result, expected_result)

    def test_get_workspace_by_id_with_various_ids(self):
        """Test get_workspace_by_id with various workspace IDs."""
        workspace_ids = [
            "ws-123abc456def789",
            "ws-abcdef1234567890",
            "ws-prod-12345",
            "ws-dev-67890",
            "ws-test_workspace_id",
        ]

        for workspace_id in workspace_ids:
            with self.subTest(workspace_id=workspace_id):
                expected_response = {"data": {"id": workspace_id, "type": "workspaces", "attributes": {"name": "test-workspace"}}, "status": 200}
                self.mock_tf_client.get.return_value = expected_response

                result = get_workspace_by_id(self.mock_tf_client, workspace_id)

                expected_result = {"id": workspace_id, "type": "workspaces", "attributes": {"name": "test-workspace"}, "status": 200}
                self.assertEqual(result, expected_result)
                self.mock_tf_client.get.assert_called_with(f"/workspaces/{workspace_id}")

    def test_get_workspace_by_id_with_complex_data_structure(self):
        """Test get_workspace_by_id with complex nested data structure."""
        expected_response = {
            "data": {
                "id": self.workspace_id,
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
        self.mock_tf_client.get.return_value = expected_response

        result = get_workspace_by_id(self.mock_tf_client, self.workspace_id)

        expected_result = expected_response["data"].copy()
        expected_result["status"] = 200
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
