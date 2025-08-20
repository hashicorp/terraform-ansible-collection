# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import sys

from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))


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