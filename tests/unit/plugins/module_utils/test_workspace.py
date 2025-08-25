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
)


class TestWorkspaceFunctions(unittest.TestCase):
    """Test suite for Terraform workspace management functions.

    Tests the workspace-related functionality including workspace retrieval,
    error handling for various HTTP status codes, and proper handling of
    different response formats from the Terraform API.
    """

    def setUp(self):
        """Set up common test variables and mocks for workspace tests.

        Initializes mock Terraform client and standard test data including
        organization name, workspace name, and workspace ID for consistent
        testing across all workspace-related test methods.
        """
        self.mock_tf_client = Mock()
        self.organization = "test-org"
        self.workspace_name = "test-workspace"
        self.workspace_id = "ws-123abc456def789"

    def test_get_workspace_success(self):
        """Test successful workspace retrieval with complete response data.

        Verifies that get_workspace correctly processes a successful API response
        containing full workspace data including ID, type, and attributes, and
        properly merges the status code into the returned data structure.
        """
        expected_response = {
            "data": {
                "id": self.workspace_id,
                "type": "workspaces",
                "attributes": {"name": self.workspace_name, "environment": "production", "auto-apply": False, "terraform-version": "1.0.0"},
            },
            "status": 200,
        }
        self.mock_tf_client.get.return_value = expected_response

        result = get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

        # Should return the data part with status added
        expected_result = {
            "id": self.workspace_id,
            "type": "workspaces",
            "attributes": {"name": self.workspace_name, "environment": "production", "auto-apply": False, "terraform-version": "1.0.0"},
            "status": 200,
        }
        self.assertEqual(result, expected_result)
        self.mock_tf_client.get.assert_called_once_with(f"/organizations/{self.organization}/workspaces/{self.workspace_name}")

    def test_get_workspace_empty_data_section(self):
        """Test get_workspace with empty data section."""
        expected_response = {"data": {}, "status": 200}
        self.mock_tf_client.get.return_value = expected_response

        result = get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

        expected_result = {"status": 200}
        self.assertEqual(result, expected_result)

    def test_get_workspace_no_data_key(self):
        """Test get_workspace with no data key."""
        expected_response = {"status": 200}
        self.mock_tf_client.get.return_value = expected_response

        result = get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

        expected_result = {"status": 200}
        self.assertEqual(result, expected_result)

    def test_get_workspace_404(self):
        """Test get_workspace returns empty dict on 404 (workspace not found)."""
        response = {"status": 404}
        self.mock_tf_client.get.return_value = response

        result = get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

        self.assertEqual(result, {})

    def test_get_workspace_failure_raises_error(self):
        """Test get_workspace raises HTTPError on non-200/non-404 status."""
        response = {"status": 500}
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(TerraformError):
            get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

    def test_get_workspace_various_failure_statuses(self):
        """Test get_workspace error handling across multiple HTTP error status codes.

        Uses subTest to verify that get_workspace properly raises TerraformError
        exceptions for various HTTP error conditions (400, 401, 403, 422, 500, etc.)
        ensuring consistent error handling across different failure scenarios.
        """
        for status_code in [400, 401, 403, 422, 500, 502, 503]:
            with self.subTest(status_code=status_code):
                response = {"status": status_code}
                self.mock_tf_client.get.return_value = response

                with self.assertRaises(TerraformError):
                    get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

    def test_get_workspace_with_special_characters_in_names(self):
        """Test get_workspace with special characters in organization and workspace names."""
        special_org = "test-org-123"
        special_workspace = "test-workspace_prod.v2"

        expected_response = {"data": {"id": self.workspace_id, "attributes": {"name": special_workspace}}, "status": 200}
        self.mock_tf_client.get.return_value = expected_response

        result = get_workspace(self.mock_tf_client, special_org, special_workspace)

        expected_result = {"id": self.workspace_id, "attributes": {"name": special_workspace}, "status": 200}
        self.assertEqual(result, expected_result)
        self.mock_tf_client.get.assert_called_once_with(f"/organizations/{special_org}/workspaces/{special_workspace}")

    def test_get_workspace_unauthorized(self):
        """Test get_workspace with 401 unauthorized."""
        response = {"status": 401}
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(TerraformError):
            get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

    def test_get_workspace_forbidden(self):
        """Test get_workspace with 403 forbidden."""
        response = {"status": 403}
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(TerraformError):
            get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

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

        # Should return the data part with status added
        expected_result = expected_response["data"].copy()
        expected_result["status"] = 200
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
