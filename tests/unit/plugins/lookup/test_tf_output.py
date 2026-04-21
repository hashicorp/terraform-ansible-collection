# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import MagicMock, Mock, patch

import pytest
from ansible.errors import AnsibleError

from ansible_collections.hashicorp.terraform.plugins.lookup.tf_output import LookupModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError


@pytest.fixture
def lookup_plugin():
    return LookupModule()


@pytest.fixture
def patched_client():
    """Patch TerraformClient so `from_mapping(...)` yields a configurable client via context manager.

    Yields a tuple (mock_client, mock_class) so tests can assert on the client
    passed into helpers and on the class itself (e.g. from_mapping kwargs).
    """
    with patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.TerraformClient") as mock_class:
        mock_client = Mock()
        ctx = MagicMock()
        ctx.__enter__.return_value = mock_client
        ctx.__exit__.return_value = False
        mock_class.from_mapping.return_value = ctx
        yield mock_client, mock_class


class TestTfOutputLookup:
    """Tests for the tf_output lookup plugin."""

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_specific_output")
    def test_lookup_by_output_id(self, mock_get_specific, patched_client, lookup_plugin):
        mock_client, mock_class = patched_client
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

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_specific_output")
    def test_lookup_by_output_id_with_display_sensitive(self, mock_get_specific, patched_client, lookup_plugin):
        mock_client, mock_class = patched_client
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

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_by_name_with_workspace_id(self, mock_resolve, mock_get_by_name, patched_client, lookup_plugin):
        mock_client, mock_class = patched_client
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

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_by_name_with_workspace_and_org(self, mock_resolve, mock_get_by_name, patched_client, lookup_plugin):
        mock_client, mock_class = patched_client
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

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_workspace_outputs")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_all_outputs_with_workspace_id(self, mock_resolve, mock_get_outputs, patched_client, lookup_plugin):
        mock_client, mock_class = patched_client
        mock_resolve.return_value = "ws-123"
        mock_get_outputs.return_value = [
            {"id": "wsout-1", "name": "output1", "value": "value1", "sensitive": False, "type": "string", "detailed_type": "string"},
            {"id": "wsout-2", "name": "output2", "value": "<sensitive>", "sensitive": True, "type": "string", "detailed_type": "string"},
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

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_workspace_outputs")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_all_outputs_with_workspace_and_org(self, mock_resolve, mock_get_outputs, patched_client, lookup_plugin):
        mock_client, mock_class = patched_client
        mock_resolve.return_value = "ws-resolved-456"
        mock_get_outputs.return_value = [
            {"id": "wsout-public", "name": "public_ip", "value": "192.0.2.1", "sensitive": False, "type": "string", "detailed_type": "string"},
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
        with pytest.raises(AnsibleError, match="state_version_output_id is mutually exclusive"):
            lookup_plugin.run(
                [],
                None,
                state_version_output_id="wsout-123",
                workspace_id="ws-456",
                tf_validate_certs=True,
            )

    def test_lookup_mutually_exclusive_with_name(self, lookup_plugin):
        with pytest.raises(AnsibleError, match="state_version_output_id is mutually exclusive"):
            lookup_plugin.run(
                [],
                None,
                state_version_output_id="wsout-123",
                name="output_name",
                tf_validate_certs=True,
            )

    def test_lookup_missing_required_params(self, lookup_plugin):
        with pytest.raises(
            AnsibleError,
            match="Either state_version_output_id or workspace identification \\(workspace_id or both workspace and organization\\) must be provided",
        ):
            lookup_plugin.run(
                [],
                None,
                tf_validate_certs=True,
            )

    def test_lookup_workspace_without_organization(self, lookup_plugin):
        with pytest.raises(AnsibleError, match="organization is required when workspace is specified"):
            lookup_plugin.run(
                [],
                None,
                workspace="my-workspace",
                tf_validate_certs=True,
            )

    def test_lookup_organization_without_workspace(self, lookup_plugin):
        with pytest.raises(AnsibleError, match="workspace is required when organization is specified"):
            lookup_plugin.run(
                [],
                None,
                organization="my-org",
                tf_validate_certs=True,
            )

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_workspace_not_found(self, mock_resolve, patched_client, lookup_plugin):
        mock_resolve.side_effect = ValueError("Workspace 'nonexistent' was not found in organization 'my-org'")

        with pytest.raises(AnsibleError, match="Output lookup failed - resource not found"):
            lookup_plugin.run(
                [],
                None,
                workspace="nonexistent",
                organization="my-org",
                tf_validate_certs=True,
            )

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_specific_output")
    def test_lookup_output_not_found_by_id(self, mock_get_specific, patched_client, lookup_plugin):
        mock_get_specific.side_effect = ValueError("State version output with ID 'wsout-notfound' was not found")

        with pytest.raises(AnsibleError, match="Output lookup failed - resource not found"):
            lookup_plugin.run(
                [],
                None,
                state_version_output_id="wsout-notfound",
                tf_validate_certs=True,
            )

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_output_name_not_found(self, mock_resolve, mock_get_by_name, patched_client, lookup_plugin):
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

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_specific_output")
    def test_lookup_api_error(self, mock_get_specific, patched_client, lookup_plugin):
        mock_get_specific.side_effect = TerraformError({"status": 500, "error": "Internal server error"})

        with pytest.raises(AnsibleError, match="Output lookup failed - API error"):
            lookup_plugin.run(
                [],
                None,
                state_version_output_id="wsout-123",
                tf_validate_certs=True,
            )

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_complex_value_types(self, mock_resolve, mock_get_by_name, patched_client, lookup_plugin):
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

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_list_value_type(self, mock_resolve, mock_get_by_name, patched_client, lookup_plugin):
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

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_sensitive_masked_by_default(self, mock_resolve, mock_get_by_name, patched_client, lookup_plugin):
        mock_client, mock_class = patched_client
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

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_output_by_name")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_sensitive_revealed_with_flag(self, mock_resolve, mock_get_by_name, patched_client, lookup_plugin):
        mock_client, mock_class = patched_client
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

    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_workspace_outputs")
    @patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.resolve_workspace_id")
    def test_lookup_empty_workspace(self, mock_resolve, mock_get_outputs, patched_client, lookup_plugin):
        mock_resolve.return_value = "ws-empty"
        mock_get_outputs.return_value = []

        result = lookup_plugin.run(
            [],
            None,
            workspace_id="ws-empty",
            tf_validate_certs=True,
        )
        assert result == []

    def test_lookup_defaults_tfe_address(self, patched_client, lookup_plugin):
        """from_mapping should receive the default tfe_address when none is provided."""
        mock_client, mock_class = patched_client
        with patch("ansible_collections.hashicorp.terraform.plugins.lookup.tf_output.get_specific_output") as mock_get:
            mock_get.return_value = {"id": "test", "name": "test", "value": "test", "sensitive": False}

            lookup_plugin.run(
                [],
                None,
                state_version_output_id="wsout-123",
            )
            passed = mock_class.from_mapping.call_args[0][0]
            assert passed.get("tfe_address") == "https://app.terraform.io"


if __name__ == "__main__":
    pytest.main([__file__])
