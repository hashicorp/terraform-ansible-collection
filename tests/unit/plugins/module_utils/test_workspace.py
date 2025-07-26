# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import unittest

from unittest.mock import Mock, patch


# Mock HTTPError class for testing
class MockHTTPError(Exception):
    def __init__(self, response=None):
        self.response = response
        super().__init__()


# Import the module under test
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import (
    get_workspace,
)


@patch("ansible_collections.hashicorp.terraform.plugins.module_utils.workspace.requests")
class TestWorkspaceFunctions(unittest.TestCase):
    """Unit tests for Terraform workspace helper functions."""

    def setUp(self):
        """Set up common test variables and mocks."""
        self.mock_tf_client = Mock()
        self.organization = "test-org"
        self.workspace_name = "test-workspace"
        self.workspace_id = "ws-123abc456def789"

    def test_get_workspace_success(self, mock_requests):
        """Test successful retrieval of a workspace."""
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

    def test_get_workspace_empty_data_section(self, mock_requests):
        """Test get_workspace with empty data section."""
        expected_response = {"data": {}, "status": 200}
        self.mock_tf_client.get.return_value = expected_response

        result = get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

        expected_result = {"status": 200}
        self.assertEqual(result, expected_result)

    def test_get_workspace_no_data_key(self, mock_requests):
        """Test get_workspace with no data key."""
        expected_response = {"status": 200}
        self.mock_tf_client.get.return_value = expected_response

        result = get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

        expected_result = {"status": 200}
        self.assertEqual(result, expected_result)

    def test_get_workspace_404(self, mock_requests):
        """Test get_workspace returns empty dict on 404 (workspace not found)."""
        response = {"status": 404}
        self.mock_tf_client.get.return_value = response

        result = get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

        self.assertEqual(result, {})

    def test_get_workspace_failure_raises_error(self, mock_requests):
        """Test get_workspace raises HTTPError on non-200/non-404 status."""
        response = {"status": 500}
        mock_requests.HTTPError = MockHTTPError
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(MockHTTPError):
            get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

    def test_get_workspace_various_failure_statuses(self, mock_requests):
        """Test get_workspace with various non-success status codes."""
        mock_requests.HTTPError = MockHTTPError

        for status_code in [400, 401, 403, 422, 500, 502, 503]:
            with self.subTest(status_code=status_code):
                response = {"status": status_code}
                self.mock_tf_client.get.return_value = response

                with self.assertRaises(MockHTTPError):
                    get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

    def test_get_workspace_with_special_characters_in_names(self, mock_requests):
        """Test get_workspace with special characters in organization and workspace names."""
        special_org = "test-org-123"
        special_workspace = "test-workspace_prod.v2"

        expected_response = {"data": {"id": self.workspace_id, "attributes": {"name": special_workspace}}, "status": 200}
        self.mock_tf_client.get.return_value = expected_response

        result = get_workspace(self.mock_tf_client, special_org, special_workspace)

        expected_result = {"id": self.workspace_id, "attributes": {"name": special_workspace}, "status": 200}
        self.assertEqual(result, expected_result)
        self.mock_tf_client.get.assert_called_once_with(f"/organizations/{special_org}/workspaces/{special_workspace}")

    def test_get_workspace_unauthorized(self, mock_requests):
        """Test get_workspace with 401 unauthorized."""
        response = {"status": 401}
        mock_requests.HTTPError = MockHTTPError
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(MockHTTPError):
            get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

    def test_get_workspace_forbidden(self, mock_requests):
        """Test get_workspace with 403 forbidden."""
        response = {"status": 403}
        mock_requests.HTTPError = MockHTTPError
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(MockHTTPError):
            get_workspace(self.mock_tf_client, self.organization, self.workspace_name)

    def test_get_workspace_with_complex_data_structure(self, mock_requests):
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


# Test import error scenarios for workspace module
class TestWorkspaceImportErrorHandling(unittest.TestCase):
    """Test handling when imports are not available in workspace module."""

    def test_import_error_handling(self):
        """Test that the workspace module handles import errors gracefully."""
        import ansible_collections.hashicorp.terraform.plugins.module_utils.workspace as workspace_module

        # Verify that HAS_REQUESTS variable exists
        self.assertTrue(hasattr(workspace_module, "HAS_REQUESTS"))

        # In normal circumstances, it should be True since requests is available
        self.assertTrue(workspace_module.HAS_REQUESTS)

    def test_workspace_module_structure(self):
        """Test that workspace module has expected structure."""
        import ansible_collections.hashicorp.terraform.plugins.module_utils.workspace as workspace_module

        # Verify the get_workspace function exists
        self.assertTrue(hasattr(workspace_module, "get_workspace"))
        self.assertTrue(callable(workspace_module.get_workspace))


if __name__ == "__main__":
    unittest.main()
