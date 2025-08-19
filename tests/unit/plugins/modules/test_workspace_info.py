# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import unittest

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)
from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main


class TestWorkspaceInfoModule(unittest.TestCase):
    """Unit tests for the workspace_info module."""

    def setUp(self):
        """Set up common test variables and mocks."""
        self.mock_module = Mock()
        self.mock_module.check_mode = False
        self.mock_module.params = {}
        self.mock_client = Mock()
        self.workspace_id = "ws-123abc456def789"
        self.organization = "test-org"
        self.workspace_name = "test-workspace"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id")
    def test_main_workspace_by_id_success(self, mock_get_workspace_by_id, mock_terraform_client, mock_ansible_module):
        """Test main function with successful workspace retrieval by ID."""
        test_cases = [
            # Successful workspace retrieval
            (
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}, "status": 200},
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}},
            ),
            # Complex workspace data
            (
                {
                    "id": "ws-123abc456def789",
                    "type": "workspaces",
                    "attributes": {
                        "name": "complex-workspace",
                        "auto-apply": True,
                        "terraform-version": "1.5.0",
                        "permissions": {"can-update": True, "can-destroy": False},
                    },
                    "relationships": {"organization": {"data": {"id": "org-456", "type": "organizations"}}},
                    "links": {"self": "/api/v2/workspaces/ws-123abc456def789"},
                    "status": 200,
                },
                {
                    "id": "ws-123abc456def789",
                    "type": "workspaces",
                    "attributes": {
                        "name": "complex-workspace",
                        "auto-apply": True,
                        "terraform-version": "1.5.0",
                        "permissions": {"can-update": True, "can-destroy": False},
                    },
                    "relationships": {"organization": {"data": {"id": "org-456", "type": "organizations"}}},
                    "links": {"self": "/api/v2/workspaces/ws-123abc456def789"},
                },
            ),
        ]

        # Setup mocks once
        mock_ansible_module.return_value = self.mock_module
        mock_terraform_client.return_value = self.mock_client

        for workspace_data, expected_result in test_cases:
            with self.subTest(workspace_data=workspace_data):
                # Setup test-specific mock return value
                mock_get_workspace_by_id.return_value = workspace_data
                self.mock_module.params = {"workspace_id": self.workspace_id}

                # Call main function
                main()

                # Verify calls
                mock_get_workspace_by_id.assert_called_with(self.mock_client, self.workspace_id)
                self.mock_module.exit_json.assert_called()

                # Check the result
                call_args = self.mock_module.exit_json.call_args[1]
                self.assertEqual(call_args["workspace"], expected_result)
                self.assertFalse(call_args["changed"])

                # Reset call records for next iteration
                mock_get_workspace_by_id.reset_mock()
                self.mock_module.exit_json.reset_mock()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace")
    def test_main_workspace_by_name_success(self, mock_get_workspace, mock_terraform_client, mock_ansible_module):
        """Test main function with successful workspace retrieval by name and organization."""
        test_cases = [
            # Successful workspace retrieval
            (
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}, "status": 200},
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace", "environment": "production"}},
            ),
            # Minimal workspace data
            ({"id": "ws-minimal", "type": "workspaces", "status": 200}, {"id": "ws-minimal", "type": "workspaces"}),
        ]

        # Setup mocks once
        mock_ansible_module.return_value = self.mock_module
        mock_terraform_client.return_value = self.mock_client

        for workspace_data, expected_result in test_cases:
            with self.subTest(workspace_data=workspace_data):
                # Setup test-specific mock return value
                mock_get_workspace.return_value = workspace_data
                self.mock_module.params = {"workspace": self.workspace_name, "organization": self.organization, "workspace_id": None}

                # Call main function
                main()

                # Verify calls
                mock_get_workspace.assert_called_with(self.mock_client, self.organization, self.workspace_name)
                self.mock_module.exit_json.assert_called()

                # Check the result
                call_args = self.mock_module.exit_json.call_args[1]
                self.assertEqual(call_args["workspace"], expected_result)
                self.assertFalse(call_args["changed"])

                # Reset call records for next iteration
                mock_get_workspace.reset_mock()
                self.mock_module.exit_json.reset_mock()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id")
    def test_main_workspace_by_id_not_found(self, mock_get_workspace_by_id, mock_terraform_client, mock_ansible_module):
        """Test main function when workspace is not found by ID."""
        # Setup mocks
        mock_ansible_module.return_value = self.mock_module
        mock_terraform_client.return_value = self.mock_client
        mock_get_workspace_by_id.return_value = {}  # Empty dict indicates not found

        self.mock_module.params = {"workspace_id": self.workspace_id}

        # Call main function
        main()

        # Verify calls
        mock_get_workspace_by_id.assert_called_once_with(self.mock_client, self.workspace_id)
        self.mock_module.fail_json.assert_called_once_with(msg=f"Workspace with ID '{self.workspace_id}' not found")

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace")
    def test_main_workspace_by_name_not_found(self, mock_get_workspace, mock_terraform_client, mock_ansible_module):
        """Test main function when workspace is not found by name and organization."""
        # Setup mocks
        mock_ansible_module.return_value = self.mock_module
        mock_terraform_client.return_value = self.mock_client
        mock_get_workspace.return_value = {}  # Empty dict indicates not found

        self.mock_module.params = {"workspace": self.workspace_name, "organization": self.organization, "workspace_id": None}

        # Call main function
        main()

        # Verify calls
        mock_get_workspace.assert_called_once_with(self.mock_client, self.organization, self.workspace_name)
        self.mock_module.fail_json.assert_called_once_with(msg=f"Workspace '{self.workspace_name}' not found in organization '{self.organization}'")

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    def test_main_exception_handling(self, mock_terraform_client, mock_ansible_module):
        """Test main function exception handling."""
        test_cases = [
            (TerraformError("API Error"), "API Error"),
            (Exception("Generic error"), "Generic error"),
            (ValueError("Invalid value"), "Invalid value"),
            (ConnectionError("Connection failed"), "Connection failed"),
        ]

        # Setup mocks once
        mock_ansible_module.return_value = self.mock_module

        for exception, expected_message in test_cases:
            with self.subTest(exception=exception):
                # Setup test-specific side effect
                mock_terraform_client.side_effect = exception
                self.mock_module.params = {"workspace_id": self.workspace_id}

                # Call main function
                main()

                # Verify exception handling
                self.mock_module.fail_json.assert_called_with(msg=expected_message)

                # Reset call records for next iteration
                self.mock_module.fail_json.reset_mock()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    def test_module_argument_spec(self, mock_ansible_module):
        """Test that the module is created with correct argument specification."""
        mock_ansible_module.return_value = self.mock_module

        # Mock TerraformClient to raise an exception so we can check argument spec
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient", side_effect=Exception("test")):
            main()

        # Check that AnsibleTerraformModule was called with correct arguments
        mock_ansible_module.assert_called_once()
        call_args = mock_ansible_module.call_args[1]

        # Verify argument spec
        expected_argument_spec = {
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
        }
        self.assertEqual(call_args["argument_spec"], expected_argument_spec)

        # Verify other module parameters
        self.assertTrue(call_args["supports_check_mode"])
        self.assertEqual(
            call_args["mutually_exclusive"],
            [
                ["workspace_id", "workspace"],
                ["workspace_id", "organization"],
            ],
        )
        self.assertEqual(
            call_args["required_one_of"],
            [
                ["workspace_id", "workspace"],
            ],
        )
        self.assertEqual(
            call_args["required_together"],
            [
                ["workspace", "organization"],
            ],
        )

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id")
    def test_main_various_workspace_ids(self, mock_get_workspace_by_id, mock_terraform_client, mock_ansible_module):
        """Test main function with various workspace ID formats."""
        workspace_ids = [
            "ws-123abc456def789",
            "ws-abcdef1234567890",
            "ws-prod-workspace",
            "ws-dev-test_123",
            "ws-special-chars@domain",
        ]

        # Setup mocks once
        mock_ansible_module.return_value = self.mock_module
        mock_terraform_client.return_value = self.mock_client

        for workspace_id in workspace_ids:
            with self.subTest(workspace_id=workspace_id):
                # Setup test-specific mock return value
                workspace_data = {"id": workspace_id, "type": "workspaces", "attributes": {"name": f"workspace-{workspace_id}"}, "status": 200}
                mock_get_workspace_by_id.return_value = workspace_data
                self.mock_module.params = {"workspace_id": workspace_id}

                # Call main function
                main()

                # Verify calls
                mock_get_workspace_by_id.assert_called_with(self.mock_client, workspace_id)
                self.mock_module.exit_json.assert_called()

                # Reset call records for next iteration
                mock_get_workspace_by_id.reset_mock()
                self.mock_module.exit_json.reset_mock()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace")
    def test_main_various_org_workspace_names(self, mock_get_workspace, mock_terraform_client, mock_ansible_module):
        """Test main function with various organization and workspace name formats."""
        test_cases = [
            ("test-org", "test-workspace"),
            ("org-with-dashes", "workspace_with_underscores"),
            ("org.with.dots", "workspace-with-dashes"),
            ("special$org", "workspace@123"),
            ("unicode-тест", "workspace-测试"),
        ]

        # Setup mocks once
        mock_ansible_module.return_value = self.mock_module
        mock_terraform_client.return_value = self.mock_client

        for org, workspace in test_cases:
            with self.subTest(org=org, workspace=workspace):
                # Setup test-specific mock return value
                workspace_data = {"id": "ws-test123", "type": "workspaces", "attributes": {"name": workspace}, "status": 200}
                mock_get_workspace.return_value = workspace_data
                self.mock_module.params = {"workspace": workspace, "organization": org, "workspace_id": None}

                # Call main function
                main()

                # Verify calls
                mock_get_workspace.assert_called_with(self.mock_client, org, workspace)
                self.mock_module.exit_json.assert_called()

                # Reset call records for next iteration
                mock_get_workspace.reset_mock()
                self.mock_module.exit_json.reset_mock()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id")
    def test_main_check_mode(self, mock_get_workspace_by_id, mock_terraform_client, mock_ansible_module):
        """Test main function in check mode."""
        # Setup mocks
        mock_ansible_module.return_value = self.mock_module
        mock_terraform_client.return_value = self.mock_client
        self.mock_module.check_mode = True
        workspace_data = {"id": self.workspace_id, "type": "workspaces", "attributes": {"name": "test-workspace"}, "status": 200}
        mock_get_workspace_by_id.return_value = workspace_data

        self.mock_module.params = {"workspace_id": self.workspace_id, "check_mode": True}

        # Call main function
        main()

        # Verify that it still works in check mode (info modules don't change state)
        mock_get_workspace_by_id.assert_called_once_with(self.mock_client, self.workspace_id)
        self.mock_module.exit_json.assert_called_once()

        # Check the result
        call_args = self.mock_module.exit_json.call_args[1]
        self.assertFalse(call_args["changed"])

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id")
    def test_main_status_field_removal(self, mock_get_workspace_by_id, mock_terraform_client, mock_ansible_module):
        """Test that the status field is properly removed from the response."""
        # Setup mocks
        mock_ansible_module.return_value = self.mock_module
        mock_terraform_client.return_value = self.mock_client
        workspace_data = {
            "id": self.workspace_id,
            "type": "workspaces",
            "attributes": {"name": "test-workspace"},
            "status": 200,  # This should be removed
            "other_field": "should_remain",
        }
        mock_get_workspace_by_id.return_value = workspace_data

        self.mock_module.params = {"workspace_id": self.workspace_id}

        # Call main function
        main()

        # Verify the status field was removed
        call_args = self.mock_module.exit_json.call_args[1]
        workspace_result = call_args["workspace"]

        # Status should be removed
        self.assertNotIn("status", workspace_result)

        # Other fields should remain
        self.assertEqual(workspace_result["id"], self.workspace_id)
        self.assertEqual(workspace_result["type"], "workspaces")
        self.assertEqual(workspace_result["attributes"]["name"], "test-workspace")
        self.assertEqual(workspace_result["other_field"], "should_remain")


if __name__ == "__main__":
    unittest.main()
