# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import MagicMock, Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.output import main


class TestOutputModule:
    """Tests for the output module."""

    @pytest.fixture
    def mock_module(self):
        """Provide a mock AnsibleTerraformModule."""
        module = MagicMock()
        module.params = {}
        module.exit_json = MagicMock()
        module.fail_json = MagicMock()
        return module

    @pytest.fixture
    def mock_client(self):
        """Provide a mock TerraformClient."""
        return Mock()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_specific_output")
    def test_get_specific_output_by_id(self, mock_get_specific, mock_client_class, mock_module_class):
        """Test retrieving a specific output by ID."""
        # Setup
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": "wsout-123",
            "workspace_id": None,
            "workspace": None,
            "organization": None,
            "name": None,
            "display_sensitive": False,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_get_specific.return_value = {
            "id": "wsout-123",
            "name": "server_id",
            "value": "i-1234567890",
            "sensitive": False,
            "type": "string",
            "detailed_type": "string",
        }

        main()

        mock_get_specific.assert_called_once_with(mock_client, "wsout-123", display_sensitive=False)
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False
        assert call_args["output"]["id"] == "wsout-123"
        assert call_args["output"]["name"] == "server_id"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_workspace_outputs")
    def test_get_all_workspace_outputs_by_workspace_id(self, mock_get_outputs, mock_resolve, mock_client_class, mock_module_class):
        """Test retrieving all outputs from a workspace using workspace_id."""
        # Setup
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": None,
            "workspace_id": "ws-456",
            "workspace": None,
            "organization": None,
            "name": None,
            "display_sensitive": False,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-456"

        mock_get_outputs.return_value = [
            {
                "id": "wsout-1",
                "name": "output1",
                "value": "value1",
                "sensitive": False,
                "type": "string",
                "detailed_type": "string",
            },
            {
                "id": "wsout-2",
                "name": "output2",
                "value": "<sensitive>",
                "sensitive": True,
                "type": "string",
                "detailed_type": "string",
            },
        ]

        main()

        mock_resolve.assert_called_once_with(mock_client, "ws-456", None, None)
        mock_get_outputs.assert_called_once_with(mock_client, "ws-456", display_sensitive=False)
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False
        assert len(call_args["outputs"]) == 2
        assert call_args["count"] == 2

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_workspace_outputs")
    def test_get_all_workspace_outputs_by_workspace_name(self, mock_get_outputs, mock_resolve, mock_client_class, mock_module_class):
        """Test retrieving all outputs using workspace name and organization."""
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": None,
            "workspace_id": None,
            "workspace": "my-workspace",
            "organization": "my-org",
            "name": None,
            "display_sensitive": True,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-resolved-789"

        mock_get_outputs.return_value = [
            {
                "id": "wsout-1",
                "name": "api_token",
                "value": "secret-token-123",
                "sensitive": True,
                "type": "string",
                "detailed_type": "string",
            },
        ]

        main()

        mock_resolve.assert_called_once_with(mock_client, None, "my-workspace", "my-org")
        mock_get_outputs.assert_called_once_with(mock_client, "ws-resolved-789", display_sensitive=True)
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["outputs"][0]["value"] == "secret-token-123"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_workspace_outputs")
    def test_get_empty_workspace_outputs(self, mock_get_outputs, mock_resolve, mock_client_class, mock_module_class):
        """Test retrieving outputs from workspace with no outputs."""
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": None,
            "workspace_id": "ws-empty",
            "workspace": None,
            "organization": None,
            "name": None,
            "display_sensitive": False,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-empty"
        mock_get_outputs.return_value = []

        main()

        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["outputs"] == []
        assert call_args["count"] == 0
        assert call_args["msg"] == "No outputs found for workspace."

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_output_by_name")
    def test_get_output_by_name_with_workspace_id(self, mock_get_by_name, mock_resolve, mock_client_class, mock_module_class):
        """Test retrieving a specific output by name using workspace_id."""
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": None,
            "workspace_id": "ws-123",
            "workspace": None,
            "organization": None,
            "name": "server_id",
            "display_sensitive": False,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"

        mock_get_by_name.return_value = {
            "id": "wsout-server",
            "name": "server_id",
            "value": "i-0123456789abcdef",
            "sensitive": False,
            "type": "string",
            "detailed_type": "string",
        }

        main()

        mock_resolve.assert_called_once_with(mock_client, "ws-123", None, None)
        mock_get_by_name.assert_called_once_with(mock_client, "ws-123", "server_id", display_sensitive=False)
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["output"]["name"] == "server_id"
        assert call_args["output"]["value"] == "i-0123456789abcdef"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_output_by_name")
    def test_get_output_by_name_with_workspace_and_org(self, mock_get_by_name, mock_resolve, mock_client_class, mock_module_class):
        """Test retrieving output by name using workspace name and organization."""
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": None,
            "workspace_id": None,
            "workspace": "prod-workspace",
            "organization": "acme-corp",
            "name": "database_url",
            "display_sensitive": True,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-prod-123"

        mock_get_by_name.return_value = {
            "id": "wsout-db",
            "name": "database_url",
            "value": "postgresql://user:pass@host:5432/db",
            "sensitive": True,
            "type": "string",
            "detailed_type": "string",
        }

        main()

        mock_resolve.assert_called_once_with(mock_client, None, "prod-workspace", "acme-corp")
        mock_get_by_name.assert_called_once_with(mock_client, "ws-prod-123", "database_url", display_sensitive=True)
        mock_module.exit_json.assert_called_once()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_specific_output")
    def test_output_not_found_by_id(self, mock_get_specific, mock_client_class, mock_module_class):
        """Test error handling when output ID is not found."""
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": "wsout-notfound",
            "workspace_id": None,
            "workspace": None,
            "organization": None,
            "name": None,
            "display_sensitive": False,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_get_specific.side_effect = ValueError("State version output with ID 'wsout-notfound' was not found.")

        main()

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "was not found" in call_args["msg"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    def test_workspace_not_found(self, mock_resolve, mock_client_class, mock_module_class):
        """Test error handling when workspace is not found."""
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": None,
            "workspace_id": None,
            "workspace": "nonexistent",
            "organization": "my-org",
            "name": None,
            "display_sensitive": False,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.side_effect = ValueError("Workspace 'nonexistent' was not found in organization 'my-org'.")

        main()

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "Workspace 'nonexistent' was not found" in call_args["msg"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_output_by_name")
    def test_output_name_not_found_in_workspace(self, mock_get_by_name, mock_resolve, mock_client_class, mock_module_class):
        """Test error handling when output name doesn't exist in workspace."""
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": None,
            "workspace_id": "ws-123",
            "workspace": None,
            "organization": None,
            "name": "nonexistent_output",
            "display_sensitive": False,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"
        mock_get_by_name.side_effect = ValueError("Output with name 'nonexistent_output' not found in workspace 'ws-123'.")

        main()

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "not found" in call_args["msg"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_specific_output")
    def test_api_error_handling(self, mock_get_specific, mock_client_class, mock_module_class):
        """Test handling of API errors."""
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": "wsout-123",
            "workspace_id": None,
            "workspace": None,
            "organization": None,
            "name": None,
            "display_sensitive": False,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError

        mock_get_specific.side_effect = TerraformError({"status": 500, "error": "Internal server error"})

        main()

        mock_module.fail_json.assert_called_once()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_workspace_outputs")
    def test_display_sensitive_false_masks_values(self, mock_get_outputs, mock_resolve, mock_client_class, mock_module_class):
        """Test that display_sensitive=False results in masked sensitive values."""
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": None,
            "workspace_id": "ws-123",
            "workspace": None,
            "organization": None,
            "name": None,
            "display_sensitive": False,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"

        mock_get_outputs.return_value = [
            {
                "id": "wsout-secret",
                "name": "secret_key",
                "value": "<sensitive>",
                "sensitive": True,
                "type": "string",
                "detailed_type": "string",
            },
        ]

        main()

        mock_get_outputs.assert_called_once_with(mock_client, "ws-123", display_sensitive=False)
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["outputs"][0]["value"] == "<sensitive>"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_workspace_outputs")
    def test_display_sensitive_true_shows_values(self, mock_get_outputs, mock_resolve, mock_client_class, mock_module_class):
        """Test that display_sensitive=True shows actual sensitive values."""
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": None,
            "workspace_id": "ws-123",
            "workspace": None,
            "organization": None,
            "name": None,
            "display_sensitive": True,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"

        mock_get_outputs.return_value = [
            {
                "id": "wsout-secret",
                "name": "secret_key",
                "value": "actual-secret-value-xyz",
                "sensitive": True,
                "type": "string",
                "detailed_type": "string",
            },
        ]

        main()

        mock_get_outputs.assert_called_once_with(mock_client, "ws-123", display_sensitive=True)
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["outputs"][0]["value"] == "actual-secret-value-xyz"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_workspace_outputs")
    def test_complex_output_types(self, mock_get_outputs, mock_resolve, mock_client_class, mock_module_class):
        """Test handling of complex output types (objects, lists)."""
        mock_module = MagicMock()
        mock_module.params = {
            "state_version_output_id": None,
            "workspace_id": "ws-123",
            "workspace": None,
            "organization": None,
            "name": None,
            "display_sensitive": False,
        }
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"

        mock_get_outputs.return_value = [
            {
                "id": "wsout-obj",
                "name": "config",
                "value": {"host": "example.com", "port": 443},
                "sensitive": False,
                "type": "object",
                "detailed_type": ["object", {"host": "string", "port": "number"}],
            },
            {
                "id": "wsout-list",
                "name": "instances",
                "value": ["i-123", "i-456", "i-789"],
                "sensitive": False,
                "type": "list",
                "detailed_type": ["list", "string"],
            },
        ]

        main()

        call_args = mock_module.exit_json.call_args[1]
        assert isinstance(call_args["outputs"][0]["value"], dict)
        assert isinstance(call_args["outputs"][1]["value"], list)
        assert call_args["outputs"][0]["value"]["host"] == "example.com"
        assert len(call_args["outputs"][1]["value"]) == 3


if __name__ == "__main__":
    pytest.main([__file__])
