# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError


class TestProjectInfoModule:
    """Test cases for the project_info module argument specification.

    Note: The core project functionality (get_project_by_id) is tested in
    test_project.py. This file only tests module-specific behavior.
    """

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    def test_module_argument_specification(self, mock_ansible_module):
        """Test that the module is created with correct argument specification."""
        # Import here to avoid import issues
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        mock_module = Mock()
        mock_module.params = {}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        # Mock TerraformClient to raise an exception so we can check argument spec
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient", side_effect=Exception("test")):
            main()

        # Check that AnsibleTerraformModule was called with correct arguments
        mock_ansible_module.assert_called_once()
        call_args = mock_ansible_module.call_args[1]

        # Verify argument spec
        expected_argument_spec = {
            "project_id": {"type": "str", "required": True},
        }
        assert call_args["argument_spec"] == expected_argument_spec

        # Verify other module parameters
        assert call_args["supports_check_mode"] is True


    @pytest.mark.parametrize(
        "project_data,expected_result",
        [
            # Successful project retrieval
            (
                {"id": "prj-123abc456def789", "type": "projects", "attributes": {"name": "test-project"}, "status": 200},
                {"id": "prj-123abc456def789", "type": "projects", "attributes": {"name": "test-project"}},
            ),
            # Complex project data
            (
                {
                    "id": "prj-complex123",
                    "type": "projects",
                    "attributes": {
                        "name": "complex-project",
                        "description": "A complex project",
                        "created-at": "2025-01-01T00:00:00.000Z",
                        "permissions": {
                            "can-read": True,
                            "can-update": True,
                            "can-destroy": False,
                        },
                        "workspace-count": 5,
                        "team-count": 2,
                        "stack-count": 1,
                        "auto-destroy-activity-duration": None,
                        "default-execution-mode": "remote",
                        "setting-overwrites": {
                            "default-execution-mode": False,
                            "default-agent-pool": False,
                        },
                    },
                    "relationships": {
                        "organization": {
                            "data": {"id": "test-org", "type": "organizations"},
                            "links": {"related": "/api/v2/organizations/test-org"},
                        },
                        "default-agent-pool": {"data": None},
                    },
                    "links": {"self": "/api/v2/projects/prj-complex123"},
                    "status": 200,
                },
                {
                    "id": "prj-complex123",
                    "type": "projects",
                    "attributes": {
                        "name": "complex-project",
                        "description": "A complex project",
                        "created-at": "2025-01-01T00:00:00.000Z",
                        "permissions": {
                            "can-read": True,
                            "can-update": True,
                            "can-destroy": False,
                        },
                        "workspace-count": 5,
                        "team-count": 2,
                        "stack-count": 1,
                        "auto-destroy-activity-duration": None,
                        "default-execution-mode": "remote",
                        "setting-overwrites": {
                            "default-execution-mode": False,
                            "default-agent-pool": False,
                        },
                    },
                    "relationships": {
                        "organization": {
                            "data": {"id": "test-org", "type": "organizations"},
                            "links": {"related": "/api/v2/organizations/test-org"},
                        },
                        "default-agent-pool": {"data": None},
                    },
                    "links": {"self": "/api/v2/projects/prj-complex123"},
                },
            ),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_project_retrieval_success(self, mock_get_project_by_id, mock_terraform_client, mock_ansible_module, project_data, expected_result):
        """Test successful project retrieval with proper result formatting."""
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-123abc456def789"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"project_id": project_id}
        mock_client = Mock()

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_project_by_id.return_value = project_data

        main()

        # Verify the correct function was called
        mock_get_project_by_id.assert_called_once_with(mock_client, project_id)

        # Verify exit_json was called with correct result
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["project"] == expected_result
        assert call_args["changed"] is False

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_project_not_found(self, mock_get_project_by_id, mock_terraform_client, mock_ansible_module):
        """Test error handling when project is not found."""
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-nonexistent"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"project_id": project_id}
        mock_client = Mock()

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_project_by_id.return_value = {}  # Empty dict indicates not found

        main()

        # Verify the correct function was called
        mock_get_project_by_id.assert_called_once_with(mock_client, project_id)

        # Verify fail_json was called with correct error message
        mock_module.fail_json.assert_called_once_with(msg=f"Project '{project_id}' was not found.")

    @pytest.mark.parametrize(
        "exception,expected_message",
        [
            (TerraformError("API Error: Unauthorized"), "API Error: Unauthorized"),
            (Exception("Generic error"), "Generic error"),
            (ValueError("Invalid project ID format"), "Invalid project ID format"),
            (ConnectionError("Network connection failed"), "Network connection failed"),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    def test_exception_handling(self, mock_terraform_client, mock_ansible_module, exception, expected_message):
        """Test exception handling during TerraformClient initialization or API calls."""
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-123abc456def789"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"project_id": project_id}

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.side_effect = exception  # Exception during client creation

        main()

        # Verify fail_json was called with the exception message
        mock_module.fail_json.assert_called_once_with(msg=expected_message)

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_check_mode_behavior(self, mock_get_project_by_id, mock_terraform_client, mock_ansible_module):
        """Test that check mode still retrieves project information."""
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-123abc456def789"
        mock_module = Mock()
        mock_module.check_mode = True  # Check mode enabled
        mock_module.params = {"project_id": project_id}
        mock_client = Mock()

        project_data = {"id": project_id, "type": "projects", "attributes": {"name": "test-project"}, "status": 200}
        expected_result = {"id": project_id, "type": "projects", "attributes": {"name": "test-project"}}

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_project_by_id.return_value = project_data

        main()

        # Even in check mode, project info should be retrieved
        mock_get_project_by_id.assert_called_once_with(mock_client, project_id)
        mock_module.exit_json.assert_called_once()

        call_args = mock_module.exit_json.call_args[1]
        assert call_args["project"] == expected_result
        assert call_args["changed"] is False

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_project_data_with_nested_data_key(self, mock_get_project_by_id, mock_terraform_client, mock_ansible_module):
        """Test handling of project data with nested 'data' key."""
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-nested123"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"project_id": project_id}
        mock_client = Mock()

        # Simulate response where project_data has a nested 'data' key
        project_data_with_nested_data = {
            "data": {
                "id": project_id,
                "type": "projects",
                "attributes": {"name": "nested-test-project"},
            },
            "status": 200,
        }

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_project_by_id.return_value = project_data_with_nested_data

        main()

        # Verify the correct function was called
        mock_get_project_by_id.assert_called_once_with(mock_client, project_id)

        # Verify exit_json was called with the nested data
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]

        # Should use the nested 'data' content
        expected_result = {
            "id": project_id,
            "type": "projects",
            "attributes": {"name": "nested-test-project"},
        }
        assert call_args["project"] == expected_result
        assert call_args["changed"] is False

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_project_data_without_nested_data_key(self, mock_get_project_by_id, mock_terraform_client, mock_ansible_module):
        """Test handling of project data without nested 'data' key."""
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-direct123"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"project_id": project_id}
        mock_client = Mock()

        # Simulate response where project_data doesn't have a nested 'data' key
        project_data_direct = {
            "id": project_id,
            "type": "projects",
            "attributes": {"name": "direct-test-project"},
            "status": 200,
        }

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_project_by_id.return_value = project_data_direct

        main()

        # Verify the correct function was called
        mock_get_project_by_id.assert_called_once_with(mock_client, project_id)

        # Verify exit_json was called with the direct data (minus status)
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]

        # Should use the direct data content (without status field)
        expected_result = {
            "id": project_id,
            "type": "projects",
            "attributes": {"name": "direct-test-project"},
        }
        assert call_args["project"] == expected_result
        assert call_args["changed"] is False

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_warnings_field_in_result(self, mock_get_project_by_id, mock_terraform_client, mock_ansible_module):
        """Test that warnings field is properly initialized in result."""
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-warnings123"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"project_id": project_id}
        mock_client = Mock()

        project_data = {
            "id": project_id,
            "type": "projects",
            "attributes": {"name": "warnings-test-project"},
            "status": 200,
        }

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_project_by_id.return_value = project_data

        main()

        # Verify exit_json was called with warnings field
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]

        assert "warnings" in call_args
        assert call_args["warnings"] == []  # Should be empty list

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_client_parameters_passed_correctly(self, mock_get_project_by_id, mock_terraform_client, mock_ansible_module):
        """Test that client is initialized with correct parameters."""
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-params123"
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "project_id": project_id,
            "hostname": "app.terraform.io",
            "token": "test-token",
            "organization": "test-org",
        }
        mock_client = Mock()

        project_data = {"id": project_id, "type": "projects", "attributes": {"name": "test"}}

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_project_by_id.return_value = project_data

        main()

        # Verify TerraformClient was called with correct parameters including check_mode
        mock_terraform_client.assert_called_once()
        call_args = mock_terraform_client.call_args[1]

        expected_params = {
            "project_id": project_id,
            "hostname": "app.terraform.io",
            "token": "test-token",
            "organization": "test-org",
            "check_mode": True,  # This should be added
        }

        assert call_args == expected_params
