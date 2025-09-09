# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import sys

from unittest.mock import Mock, patch

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError


class TestWorkspaceInfoModule:
    """Test cases for the workspace_info module argument specification.

    Note: The core workspace functionality (get_workspace, get_workspace_by_id)
    is tested in test_workspace.py. This file only tests module-specific behavior.
    """

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    def test_module_argument_specification(self, mock_ansible_module):
        """Test that the module is created with correct argument specification."""
        # Import here to avoid import issues
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        mock_module = Mock()
        mock_module.params = {}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

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
        assert call_args["argument_spec"] == expected_argument_spec

        # Verify other module parameters
        assert call_args["supports_check_mode"] is True
        assert call_args["mutually_exclusive"] == [
            ["workspace_id", "workspace"],
            ["workspace_id", "organization"],
        ]
        assert call_args["required_one_of"] == [
            ["workspace_id", "workspace"],
        ]
        assert call_args["required_together"] == [
            ["workspace", "organization"],
        ]

    def test_status_field_removal_logic(self):
        """Test that status field removal logic works correctly."""
        # Test the simple logic of removing status field from workspace data
        workspace_data = {
            "id": "ws-123abc456def789",
            "type": "workspaces",
            "attributes": {"name": "test-workspace"},
            "status": 200,  # This should be removed
            "other_field": "should_remain",
        }

        # Simulate the logic from the main function
        workspace_data.pop("status", None)

        # Verify the status field was removed
        assert "status" not in workspace_data

        # Other fields should remain
        assert workspace_data["id"] == "ws-123abc456def789"
        assert workspace_data["type"] == "workspaces"
        assert workspace_data["attributes"]["name"] == "test-workspace"
        assert workspace_data["other_field"] == "should_remain"

    def test_status_field_removal_when_not_present(self):
        """Test that status field removal works when status is not present."""
        workspace_data = {
            "id": "ws-123abc456def789",
            "type": "workspaces",
            "attributes": {"name": "test-workspace"},
        }

        # Simulate the logic from the main function
        workspace_data.pop("status", None)

        # Should not raise an error and data should remain unchanged
        assert workspace_data == {
            "id": "ws-123abc456def789",
            "type": "workspaces",
            "attributes": {"name": "test-workspace"},
        }

    @pytest.mark.parametrize(
        "workspace_data,expected_result",
        [
            # Successful workspace retrieval
            (
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace"}, "status": 200},
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace"}},
            ),
            # Complex workspace data
            (
                {
                    "id": "ws-complex123",
                    "type": "workspaces",
                    "attributes": {"name": "complex-workspace", "auto-apply": True},
                    "relationships": {"organization": {"data": {"id": "org-456"}}},
                    "status": 200,
                },
                {
                    "id": "ws-complex123",
                    "type": "workspaces",
                    "attributes": {"name": "complex-workspace", "auto-apply": True},
                    "relationships": {"organization": {"data": {"id": "org-456"}}},
                },
            ),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id")
    def test_workspace_retrieval_by_id_success(self, mock_get_workspace_by_id, mock_terraform_client, mock_ansible_module, workspace_data, expected_result):
        """Test successful workspace retrieval by ID with proper result formatting."""
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        workspace_id = "ws-123abc456def789"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"workspace_id": workspace_id}
        mock_client = Mock()

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_workspace_by_id.return_value = workspace_data

        main()

        # Verify the correct function was called
        mock_get_workspace_by_id.assert_called_once_with(mock_client, workspace_id)

        # Verify exit_json was called with correct result
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["workspace"] == {"data": expected_result}
        assert call_args["changed"] is False

    @pytest.mark.parametrize(
        "workspace_data,expected_result",
        [
            # Successful workspace retrieval
            (
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace"}, "status": 200},
                {"id": "ws-123abc456def789", "type": "workspaces", "attributes": {"name": "test-workspace"}},
            ),
            # Minimal workspace data
            (
                {"id": "ws-minimal", "type": "workspaces", "status": 200},
                {"id": "ws-minimal", "type": "workspaces"},
            ),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace")
    def test_workspace_retrieval_by_name_success(self, mock_get_workspace, mock_terraform_client, mock_ansible_module, workspace_data, expected_result):
        """Test successful workspace retrieval by name and organization."""
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        organization = "test-org"
        workspace_name = "test-workspace"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"workspace": workspace_name, "organization": organization, "workspace_id": None}
        mock_client = Mock()

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_workspace.return_value = workspace_data

        main()

        # Verify the correct function was called
        mock_get_workspace.assert_called_once_with(mock_client, organization, workspace_name)

        # Verify exit_json was called with correct result
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["workspace"] == {"data": expected_result}
        assert call_args["changed"] is False

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id")
    def test_workspace_not_found_by_id(self, mock_get_workspace_by_id, mock_terraform_client, mock_ansible_module):
        """Test error handling when workspace is not found by ID."""
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        workspace_id = "ws-nonexistent"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"workspace_id": workspace_id}
        mock_client = Mock()

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_workspace_by_id.return_value = {}  # Empty dict indicates not found

        main()

        # Verify the correct function was called
        mock_get_workspace_by_id.assert_called_once_with(mock_client, workspace_id)

        # Verify fail_json was called with correct error message
        mock_module.fail_json.assert_called_once_with(msg=f"Workspace '{workspace_id}' was not found.")

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace")
    def test_workspace_not_found_by_name(self, mock_get_workspace, mock_terraform_client, mock_ansible_module):
        """Test error handling when workspace is not found by name and organization."""
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        organization = "test-org"
        workspace_name = "nonexistent-workspace"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"workspace": workspace_name, "organization": organization, "workspace_id": None}
        mock_client = Mock()

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_workspace.return_value = {}  # Empty dict indicates not found

        main()

        # Verify the correct function was called
        mock_get_workspace.assert_called_once_with(mock_client, organization, workspace_name)

        # Verify fail_json was called with correct error message
        mock_module.fail_json.assert_called_once_with(msg=f"The workspace {workspace_name} in {organization} organization was not found.")

    @pytest.mark.parametrize(
        "exception,expected_message",
        [
            (TerraformError("API Error: Unauthorized"), "API Error: Unauthorized"),
            (Exception("Generic error"), "Generic error"),
            (ValueError("Invalid workspace ID format"), "Invalid workspace ID format"),
            (ConnectionError("Network connection failed"), "Network connection failed"),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    def test_exception_handling(self, mock_terraform_client, mock_ansible_module, exception, expected_message):
        """Test exception handling during TerraformClient initialization or API calls."""
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        workspace_id = "ws-123abc456def789"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"workspace_id": workspace_id}

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.side_effect = exception  # Exception during client creation

        main()

        # Verify fail_json was called with the exception message
        mock_module.fail_json.assert_called_once_with(msg=expected_message)

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id")
    def test_check_mode_behavior(self, mock_get_workspace_by_id, mock_terraform_client, mock_ansible_module):
        """Test that check mode still retrieves workspace information."""
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        workspace_id = "ws-123abc456def789"
        mock_module = Mock()
        mock_module.check_mode = True  # Check mode enabled
        mock_module.params = {"workspace_id": workspace_id}
        mock_client = Mock()

        workspace_data = {"id": workspace_id, "type": "workspaces", "attributes": {"name": "test-workspace"}, "status": 200}
        expected_result = {"id": workspace_id, "type": "workspaces", "attributes": {"name": "test-workspace"}}

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_workspace_by_id.return_value = workspace_data

        main()

        # Even in check mode, workspace info should be retrieved
        mock_get_workspace_by_id.assert_called_once_with(mock_client, workspace_id)
        mock_module.exit_json.assert_called_once()

        call_args = mock_module.exit_json.call_args[1]
        assert call_args["workspace"] == {"data": expected_result}
        assert call_args["changed"] is False
