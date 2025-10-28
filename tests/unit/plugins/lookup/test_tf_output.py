# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest

from ansible.errors import AnsibleError

from ansible_collections.hashicorp.terraform.plugins.lookup.tf_output import LookupModule


class TestTfOutputLookup:
    """Tests for the tf_output lookup plugin."""

    @pytest.fixture
    def lookup_plugin(self):
        """Provide a LookupModule instance."""
        return LookupModule()

    @pytest.fixture
    def mock_client(self):
        """Provide a mock TerraformClient."""
        return Mock()

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_specific_output")
    def test_lookup_by_output_id(self, mock_get_specific, mock_client_class, lookup_plugin):
        """Test lookup using state_version_output_id."""
        # Setup
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_get_specific.return_value = {
            "id": "wsout-123",
            "name": "server_id",
            "value": "i-1234567890abcdef",
            "sensitive": False,
            "type": "string",
            "detailed_type": "string",
        }
        result = lookup_plugin.run(
            [],
            None,
            state_version_output_id="wsout-123",
            tf_validate_certs=True,
        )
        assert result == ["i-1234567890abcdef"]
        mock_get_specific.assert_called_once_with(mock_client, "wsout-123", display_sensitive=False)

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_specific_output")
    def test_lookup_by_output_id_with_display_sensitive(self, mock_get_specific, mock_client_class, lookup_plugin):
        """Test lookup using state_version_output_id with display_sensitive=True."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_get_specific.return_value = {
            "id": "wsout-secret",
            "name": "api_token",
            "value": "secret-token-xyz",
            "sensitive": True,
            "type": "string",
            "detailed_type": "string",
        }
        result = lookup_plugin.run(
            [],
            None,
            state_version_output_id="wsout-secret",
            display_sensitive=True,
            tf_validate_certs=True,
        )
        assert result == ["secret-token-xyz"]
        mock_get_specific.assert_called_once_with(mock_client, "wsout-secret", display_sensitive=True)

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    def test_lookup_by_name_with_workspace_id(self, mock_get_by_name, mock_resolve, mock_client_class, lookup_plugin):
        """Test lookup using name and workspace_id."""
        # Setup
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"

        mock_get_by_name.return_value = {
            "id": "wsout-456",
            "name": "database_url",
            "value": "postgresql://localhost:5432/mydb",
            "sensitive": False,
            "type": "string",
            "detailed_type": "string",
        }
        result = lookup_plugin.run(
            [],
            None,
            name="database_url",
            workspace_id="ws-123",
            tf_validate_certs=True,
        )
        assert result == ["postgresql://localhost:5432/mydb"]
        mock_resolve.assert_called_once_with(mock_client, "ws-123", None, None)
        mock_get_by_name.assert_called_once_with(mock_client, "ws-123", "database_url", display_sensitive=False)

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    def test_lookup_by_name_with_workspace_and_org(self, mock_get_by_name, mock_resolve, mock_client_class, lookup_plugin):
        """Test lookup using name, workspace, and organization."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-resolved-789"

        mock_get_by_name.return_value = {
            "id": "wsout-app",
            "name": "app_version",
            "value": "1.2.3",
            "sensitive": False,
            "type": "string",
            "detailed_type": "string",
        }
        result = lookup_plugin.run(
            [],
            None,
            name="app_version",
            workspace="my-workspace",
            organization="my-org",
            tf_validate_certs=True,
        )
        assert result == ["1.2.3"]
        mock_resolve.assert_called_once_with(mock_client, None, "my-workspace", "my-org")
        mock_get_by_name.assert_called_once_with(mock_client, "ws-resolved-789", "app_version", display_sensitive=False)

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_workspace_outputs")
    def test_lookup_all_outputs_with_workspace_id(self, mock_get_outputs, mock_resolve, mock_client_class, lookup_plugin):
        """Test lookup returning all outputs from workspace using workspace_id."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"

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
        result = lookup_plugin.run(
            [],
            None,
            workspace_id="ws-123",
            tf_validate_certs=True,
        )
        assert len(result) == 2
        assert result[0]["name"] == "output1"
        assert result[1]["value"] == "<sensitive>"
        mock_resolve.assert_called_once_with(mock_client, "ws-123", None, None)
        mock_get_outputs.assert_called_once_with(mock_client, "ws-123", display_sensitive=False)

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_workspace_outputs")
    def test_lookup_all_outputs_with_workspace_and_org(self, mock_get_outputs, mock_resolve, mock_client_class, lookup_plugin):
        """Test lookup returning all outputs using workspace name and organization."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-resolved-456"

        mock_get_outputs.return_value = [
            {
                "id": "wsout-public",
                "name": "public_ip",
                "value": "192.0.2.1",
                "sensitive": False,
                "type": "string",
                "detailed_type": "string",
            },
        ]
        result = lookup_plugin.run(
            [],
            None,
            workspace="prod-workspace",
            organization="acme-corp",
            display_sensitive=True,
            tf_validate_certs=True,
        )
        assert result[0]["value"] == "192.0.2.1"
        mock_resolve.assert_called_once_with(mock_client, None, "prod-workspace", "acme-corp")
        mock_get_outputs.assert_called_once_with(mock_client, "ws-resolved-456", display_sensitive=True)

    def test_lookup_mutually_exclusive_params(self, lookup_plugin):
        """Test error when state_version_output_id is used with workspace params."""
        with pytest.raises(AnsibleError, match="state_version_output_id is mutually exclusive"):
            lookup_plugin.run(
                [],
                None,
                state_version_output_id="wsout-123",
                workspace_id="ws-456",
                tf_validate_certs=True,
            )

    def test_lookup_mutually_exclusive_with_name(self, lookup_plugin):
        """Test error when state_version_output_id is used with name."""
        with pytest.raises(AnsibleError, match="state_version_output_id is mutually exclusive"):
            lookup_plugin.run(
                [],
                None,
                state_version_output_id="wsout-123",
                name="output_name",
                tf_validate_certs=True,
            )

    def test_lookup_missing_required_params(self, lookup_plugin):
        """Test error when no identification parameters provided."""
        with pytest.raises(AnsibleError, match="Either state_version_output_id or workspace identification must be provided"):
            lookup_plugin.run(
                [],
                None,
                tf_validate_certs=True,
            )

    def test_lookup_workspace_without_organization(self, lookup_plugin):
        """Test error when workspace provided without organization."""
        with pytest.raises(AnsibleError, match="Either state_version_output_id or workspace identification must be provided"):
            lookup_plugin.run(
                [],
                None,
                workspace="my-workspace",
                tf_validate_certs=True,
            )

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_workspace_not_found(self, mock_resolve, mock_client_class, lookup_plugin):
        """Test error when workspace cannot be resolved."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.side_effect = ValueError("Workspace 'nonexistent' was not found in organization 'my-org'")

        with pytest.raises(AnsibleError, match="Output lookup failed - resource not found"):
            lookup_plugin.run(
                [],
                None,
                workspace="nonexistent",
                organization="my-org",
                tf_validate_certs=True,
            )

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_specific_output")
    def test_lookup_output_not_found_by_id(self, mock_get_specific, mock_client_class, lookup_plugin):
        """Test error when output ID is not found."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_get_specific.side_effect = ValueError("State version output with ID 'wsout-notfound' was not found")

        with pytest.raises(AnsibleError, match="Output lookup failed - resource not found"):
            lookup_plugin.run(
                [],
                None,
                state_version_output_id="wsout-notfound",
                tf_validate_certs=True,
            )

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    def test_lookup_output_name_not_found(self, mock_get_by_name, mock_resolve, mock_client_class, lookup_plugin):
        """Test error when output name doesn't exist in workspace."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"
        mock_get_by_name.side_effect = ValueError("Output with name 'nonexistent' not found in workspace 'ws-123'")

        with pytest.raises(AnsibleError, match="Output lookup failed - resource not found"):
            lookup_plugin.run(
                [],
                None,
                workspace_id="ws-123",
                name="nonexistent",
                tf_validate_certs=True,
            )

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_specific_output")
    def test_lookup_api_error(self, mock_get_specific, mock_client_class, lookup_plugin):
        """Test error handling for API failures."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError

        mock_get_specific.side_effect = TerraformError({"status": 500, "error": "Internal server error"})

        with pytest.raises(AnsibleError, match="Output lookup failed - API error"):
            lookup_plugin.run(
                [],
                None,
                state_version_output_id="wsout-123",
                tf_validate_certs=True,
            )

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    def test_lookup_complex_value_types(self, mock_get_by_name, mock_resolve, mock_client_class, lookup_plugin):
        """Test lookup with complex output value types (dict, list)."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"

        mock_get_by_name.return_value = {
            "id": "wsout-complex",
            "name": "config",
            "value": {
                "database": {"host": "db.example.com", "port": 5432},
                "redis": {"host": "redis.example.com", "port": 6379},
            },
            "sensitive": False,
            "type": "object",
            "detailed_type": ["object", {"database": "object", "redis": "object"}],
        }
        result = lookup_plugin.run(
            [],
            None,
            workspace_id="ws-123",
            name="config",
            tf_validate_certs=True,
        )
        assert isinstance(result[0], dict)
        assert result[0]["database"]["host"] == "db.example.com"
        assert result[0]["redis"]["port"] == 6379

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    def test_lookup_list_value_type(self, mock_get_by_name, mock_resolve, mock_client_class, lookup_plugin):
        """Test lookup with list output value type."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"

        mock_get_by_name.return_value = {
            "id": "wsout-list",
            "name": "instance_ids",
            "value": ["i-123", "i-456", "i-789"],
            "sensitive": False,
            "type": "list",
            "detailed_type": ["list", "string"],
        }
        result = lookup_plugin.run(
            [],
            None,
            workspace_id="ws-123",
            name="instance_ids",
            tf_validate_certs=True,
        )
        assert isinstance(result[0], list)
        assert len(result[0]) == 3
        assert result[0][0] == "i-123"

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    def test_lookup_sensitive_masked_by_default(self, mock_get_by_name, mock_resolve, mock_client_class, lookup_plugin):
        """Test that sensitive values are masked by default."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"

        mock_get_by_name.return_value = {
            "id": "wsout-secret",
            "name": "password",
            "value": "<sensitive>",
            "sensitive": True,
            "type": "string",
            "detailed_type": "string",
        }
        result = lookup_plugin.run(
            [],
            None,
            workspace_id="ws-123",
            name="password",
            tf_validate_certs=True,
        )
        assert result == ["<sensitive>"]
        mock_get_by_name.assert_called_once_with(mock_client, "ws-123", "password", display_sensitive=False)

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    def test_lookup_sensitive_revealed_with_flag(self, mock_get_by_name, mock_resolve, mock_client_class, lookup_plugin):
        """Test that sensitive values are revealed with display_sensitive=True."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-123"

        mock_get_by_name.return_value = {
            "id": "wsout-secret",
            "name": "password",
            "value": "actual-secret-password",
            "sensitive": True,
            "type": "string",
            "detailed_type": "string",
        }
        result = lookup_plugin.run(
            [],
            None,
            workspace_id="ws-123",
            name="password",
            display_sensitive=True,
            tf_validate_certs=True,
        )
        assert result == ["actual-secret-password"]
        mock_get_by_name.assert_called_once_with(mock_client, "ws-123", "password", display_sensitive=True)

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_workspace_outputs")
    def test_lookup_empty_workspace(self, mock_get_outputs, mock_resolve, mock_client_class, lookup_plugin):
        """Test lookup from workspace with no outputs."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_resolve.return_value = "ws-empty"
        mock_get_outputs.return_value = []

        result = lookup_plugin.run(
            [],
            None,
            workspace_id="ws-empty",
            tf_validate_certs=True,
        )
        assert result == []

    def test_lookup_validate_certs_default(self, lookup_plugin):
        """Test that tf_validate_certs defaults to True."""
        with patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient") as mock_client_class:
            with patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_specific_output") as mock_get:
                mock_get.return_value = {"id": "test", "name": "test", "value": "test", "sensitive": False}

                lookup_plugin.run(
                    [],
                    None,
                    state_version_output_id="wsout-123",
                )
                call_kwargs = mock_client_class.call_args[1]
                assert call_kwargs["tf_validate_certs"] is True


if __name__ == "__main__":
    pytest.main([__file__])
