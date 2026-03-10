# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output import (
    _extract_data_from_response,
    _format_output_data,
    _handle_api_response,
    get_output_by_name,
    get_specific_output,
    get_workspace_outputs,
    resolve_workspace_id,
)


class TestHandleApiResponse:
    """Tests for _handle_api_response helper function."""

    def test_handle_api_response_success_200(self):
        """Test successful API response with 200 status."""
        response = {"status": 200, "data": {"id": "test-123"}}
        result = _handle_api_response(response)
        assert result == response

    def test_handle_api_response_not_found_404(self):
        """Test API response returns empty dict on 404."""
        response = {"status": 404}
        result = _handle_api_response(response)
        assert result == {}

    @pytest.mark.parametrize("status_code", [400, 401, 403, 500, 503])
    def test_handle_api_response_error_statuses(self, status_code):
        """Test API response raises TerraformError on error status codes."""
        response = {"status": status_code, "error": "Something went wrong"}
        with pytest.raises(TerraformError) as exc_info:
            _handle_api_response(response)
        assert exc_info.value.args[0] == response


class TestExtractDataFromResponse:
    """Tests for _extract_data_from_response helper function."""

    def test_extract_simple_data(self):
        """Test extraction when data is at top level."""
        response = {"data": {"id": "test-123", "type": "outputs"}}
        result = _extract_data_from_response(response)
        assert result == {"id": "test-123", "type": "outputs"}

    def test_extract_nested_data(self):
        """Test extraction when data is nested."""
        response = {
            "data": {
                "data": {"id": "test-456", "type": "outputs"},
                "status": 200,
            },
        }
        result = _extract_data_from_response(response)
        assert result == {"id": "test-456", "type": "outputs"}

    def test_extract_no_data_key(self):
        """Test extraction when no data key exists."""
        response = {"id": "test-789", "type": "outputs"}
        result = _extract_data_from_response(response)
        assert result == response

    def test_extract_data_is_list(self):
        """Test extraction when data is a list."""
        response = {"data": [{"id": "out-1"}, {"id": "out-2"}]}
        result = _extract_data_from_response(response)
        assert result == [{"id": "out-1"}, {"id": "out-2"}]


class TestFormatOutputData:
    """Tests for _format_output_data helper function."""

    def test_format_non_sensitive_output(self):
        """Test formatting non-sensitive output."""
        raw_output = {
            "id": "wsout-123",
            "attributes": {
                "name": "server_id",
                "value": "i-1234567890abcdef0",
                "sensitive": False,
                "type": "string",
                "detailed-type": "string",
            },
        }
        result = _format_output_data(raw_output)

        assert result["id"] == "wsout-123"
        assert result["name"] == "server_id"
        assert result["value"] == "i-1234567890abcdef0"
        assert result["sensitive"] is False
        assert result["type"] == "string"
        assert result["detailed_type"] == "string"

    def test_format_sensitive_output_with_null_value(self):
        """Test formatting sensitive output with null value (should be masked)."""
        raw_output = {
            "id": "wsout-456",
            "attributes": {
                "name": "api_token",
                "value": None,
                "sensitive": True,
                "type": "string",
                "detailed-type": "string",
            },
        }
        result = _format_output_data(raw_output)

        assert result["id"] == "wsout-456"
        assert result["name"] == "api_token"
        assert result["value"] == "<sensitive>"
        assert result["sensitive"] is True

    def test_format_sensitive_output_with_value(self):
        """Test formatting sensitive output with actual value."""
        raw_output = {
            "id": "wsout-789",
            "attributes": {
                "name": "password",
                "value": "secret123",
                "sensitive": True,
                "type": "string",
                "detailed-type": "string",
            },
        }
        result = _format_output_data(raw_output)

        assert result["value"] == "secret123"
        assert result["sensitive"] is True

    def test_format_complex_type_output(self):
        """Test formatting output with complex type."""
        raw_output = {
            "id": "wsout-complex",
            "attributes": {
                "name": "config",
                "value": {"key1": "value1", "key2": "value2"},
                "sensitive": False,
                "type": "object",
                "detailed-type": ["object", {"key1": "string", "key2": "string"}],
            },
        }
        result = _format_output_data(raw_output)

        assert result["value"] == {"key1": "value1", "key2": "value2"}
        assert result["type"] == "object"
        assert result["detailed_type"] == ["object", {"key1": "string", "key2": "string"}]


class TestResolveWorkspaceId:
    """Tests for resolve_workspace_id function."""

    @pytest.fixture
    def mock_client(self):
        """Provide a mock TerraformClient."""
        return Mock()

    def test_resolve_with_direct_workspace_id(self, mock_client):
        """Test that direct workspace_id is returned as-is."""
        result = resolve_workspace_id(mock_client, workspace_id="ws-direct123")
        assert result == "ws-direct123"
        mock_client.get.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.get_workspace")
    def test_resolve_with_workspace_and_org(self, mock_get_workspace, mock_client):
        """Test resolving workspace_id from workspace name and organization."""
        mock_get_workspace.return_value = {
            "data": {
                "id": "ws-resolved456",
                "type": "workspaces",
            },
        }

        result = resolve_workspace_id(
            mock_client,
            workspace="my-workspace",
            organization="my-org",
        )

        assert result == "ws-resolved456"
        mock_get_workspace.assert_called_once_with(mock_client, "my-org", "my-workspace")

    def test_resolve_missing_parameters(self, mock_client):
        """Test error when neither workspace_id nor workspace/org provided."""
        with pytest.raises(ValueError, match="Either workspace_id or both workspace and organization must be provided"):
            resolve_workspace_id(mock_client)

    def test_resolve_workspace_only_no_org(self, mock_client):
        """Test error when workspace provided without organization."""
        with pytest.raises(ValueError, match="Either workspace_id or both workspace and organization must be provided"):
            resolve_workspace_id(mock_client, workspace="my-workspace")

    def test_resolve_org_only_no_workspace(self, mock_client):
        """Test error when organization provided without workspace."""
        with pytest.raises(ValueError, match="Either workspace_id or both workspace and organization must be provided"):
            resolve_workspace_id(mock_client, organization="my-org")

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.get_workspace")
    def test_resolve_workspace_not_found(self, mock_get_workspace, mock_client):
        """Test error when workspace is not found."""
        mock_get_workspace.return_value = None

        with pytest.raises(ValueError, match="Workspace 'nonexistent' was not found in organization 'my-org'"):
            resolve_workspace_id(
                mock_client,
                workspace="nonexistent",
                organization="my-org",
            )

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.get_workspace")
    def test_resolve_invalid_workspace_data(self, mock_get_workspace, mock_client):
        """Test error when workspace data doesn't contain ID."""
        mock_get_workspace.return_value = {
            "data": {
                "type": "workspaces",
                # Missing 'id' key
            },
        }

        with pytest.raises(ValueError, match="Invalid workspace data returned"):
            resolve_workspace_id(
                mock_client,
                workspace="my-workspace",
                organization="my-org",
            )


class TestGetSpecificOutput:
    """Tests for get_specific_output function."""

    @pytest.fixture
    def mock_client(self):
        """Provide a mock TerraformClient."""
        return Mock()

    def test_get_specific_output_success_non_sensitive(self, mock_client):
        """Test retrieving non-sensitive output by ID."""
        mock_client.get.return_value = {
            "status": 200,
            "data": {
                "id": "wsout-123",
                "type": "state-version-outputs",
                "attributes": {
                    "name": "server_id",
                    "value": "i-1234567890abcdef0",
                    "sensitive": False,
                    "type": "string",
                    "detailed-type": "string",
                },
            },
        }

        result = get_specific_output(mock_client, "wsout-123")

        assert result["id"] == "wsout-123"
        assert result["name"] == "server_id"
        assert result["value"] == "i-1234567890abcdef0"
        assert result["sensitive"] is False
        mock_client.get.assert_called_once_with("/state-version-outputs/wsout-123")

    def test_get_specific_output_sensitive_masked(self, mock_client):
        """Test retrieving sensitive output (value should be masked by default)."""
        mock_client.get.return_value = {
            "status": 200,
            "data": {
                "id": "wsout-456",
                "type": "state-version-outputs",
                "attributes": {
                    "name": "api_token",
                    "value": "secret-token-value",
                    "sensitive": True,
                    "type": "string",
                    "detailed-type": "string",
                },
            },
        }

        result = get_specific_output(mock_client, "wsout-456", display_sensitive=False)

        assert result["value"] == "<sensitive>"
        assert result["sensitive"] is True

    def test_get_specific_output_sensitive_displayed(self, mock_client):
        """Test retrieving sensitive output with display_sensitive=True."""
        mock_client.get.return_value = {
            "status": 200,
            "data": {
                "id": "wsout-789",
                "type": "state-version-outputs",
                "attributes": {
                    "name": "password",
                    "value": "actual-secret-password",
                    "sensitive": True,
                    "type": "string",
                    "detailed-type": "string",
                },
            },
        }

        result = get_specific_output(mock_client, "wsout-789", display_sensitive=True)

        assert result["value"] == "actual-secret-password"
        assert result["sensitive"] is True

    def test_get_specific_output_not_found(self, mock_client):
        """Test error when output ID is not found."""
        mock_client.get.return_value = {"status": 404}

        with pytest.raises(ValueError, match="State version output with ID 'wsout-notfound' was not found"):
            get_specific_output(mock_client, "wsout-notfound")

    def test_get_specific_output_api_error(self, mock_client):
        """Test TerraformError on API failure."""
        mock_client.get.return_value = {"status": 500, "error": "Internal server error"}

        with pytest.raises(TerraformError):
            get_specific_output(mock_client, "wsout-error")

    def test_get_specific_output_complex_type(self, mock_client):
        """Test retrieving output with complex object type."""
        mock_client.get.return_value = {
            "status": 200,
            "data": {
                "id": "wsout-complex",
                "type": "state-version-outputs",
                "attributes": {
                    "name": "config",
                    "value": {
                        "database": {"host": "db.example.com", "port": 5432},
                        "cache": {"host": "cache.example.com"},
                    },
                    "sensitive": False,
                    "type": "object",
                    "detailed-type": ["object", {"database": "object", "cache": "object"}],
                },
            },
        }

        result = get_specific_output(mock_client, "wsout-complex")

        assert isinstance(result["value"], dict)
        assert result["value"]["database"]["host"] == "db.example.com"
        assert result["type"] == "object"


class TestGetWorkspaceOutputs:
    """Tests for get_workspace_outputs function."""

    @pytest.fixture
    def mock_client(self):
        """Provide a mock TerraformClient."""
        return Mock()

    def test_get_workspace_outputs_multiple_outputs(self, mock_client):
        """Test retrieving multiple outputs from workspace."""
        mock_client.get.return_value = {
            "status": 200,
            "data": [
                {
                    "id": "wsout-1",
                    "attributes": {
                        "name": "output1",
                        "value": "value1",
                        "sensitive": False,
                        "type": "string",
                        "detailed-type": "string",
                    },
                },
                {
                    "id": "wsout-2",
                    "attributes": {
                        "name": "output2",
                        "value": None,
                        "sensitive": True,
                        "type": "string",
                        "detailed-type": "string",
                    },
                },
            ],
        }

        result = get_workspace_outputs(mock_client, "ws-123")

        assert len(result) == 2
        assert result[0]["name"] == "output1"
        assert result[0]["value"] == "value1"
        assert result[1]["name"] == "output2"
        assert result[1]["value"] == "<sensitive>"
        mock_client.get.assert_called_once_with("/workspaces/ws-123/current-state-version-outputs")

    def test_get_workspace_outputs_empty(self, mock_client):
        """Test retrieving outputs from workspace with no outputs."""
        mock_client.get.return_value = {
            "status": 200,
            "data": [],
        }

        result = get_workspace_outputs(mock_client, "ws-empty")

        assert result == []

    def test_get_workspace_outputs_workspace_not_found(self, mock_client):
        """Test error when workspace is not found."""
        mock_client.get.return_value = {"status": 404}

        with pytest.raises(ValueError, match="Workspace with ID 'ws-notfound' was not found"):
            get_workspace_outputs(mock_client, "ws-notfound")

    def test_get_workspace_outputs_with_display_sensitive(self, mock_client):
        """Test retrieving outputs with display_sensitive=True makes individual calls."""
        # First call returns list of outputs
        mock_client.get.return_value = {
            "status": 200,
            "data": [
                {
                    "id": "wsout-sensitive",
                    "attributes": {
                        "name": "secret",
                        "value": None,
                        "sensitive": True,
                        "type": "string",
                        "detailed-type": "string",
                    },
                },
                {
                    "id": "wsout-normal",
                    "attributes": {
                        "name": "public",
                        "value": "public-value",
                        "sensitive": False,
                        "type": "string",
                        "detailed-type": "string",
                    },
                },
            ],
        }

        # Mock the individual get call for sensitive output
        def mock_get_side_effect(endpoint):
            if endpoint == "/workspaces/ws-123/current-state-version-outputs":
                return mock_client.get.return_value
            elif endpoint == "/state-version-outputs/wsout-sensitive":
                return {
                    "status": 200,
                    "data": {
                        "id": "wsout-sensitive",
                        "attributes": {
                            "name": "secret",
                            "value": "actual-secret-value",
                            "sensitive": True,
                            "type": "string",
                            "detailed-type": "string",
                        },
                    },
                }

        mock_client.get.side_effect = mock_get_side_effect

        result = get_workspace_outputs(mock_client, "ws-123", display_sensitive=True)

        assert len(result) == 2
        assert result[0]["value"] == "actual-secret-value"
        assert result[1]["value"] == "public-value"

    def test_get_workspace_outputs_api_error(self, mock_client):
        """Test TerraformError on API failure."""
        mock_client.get.return_value = {"status": 500}

        with pytest.raises(TerraformError):
            get_workspace_outputs(mock_client, "ws-error")


class TestGetOutputByName:
    """Tests for get_output_by_name function."""

    @pytest.fixture
    def mock_client(self):
        """Provide a mock TerraformClient."""
        return Mock()

    def test_get_output_by_name_found(self, mock_client):
        """Test retrieving output by name when it exists."""
        mock_client.get.return_value = {
            "status": 200,
            "data": [
                {
                    "id": "wsout-1",
                    "attributes": {
                        "name": "server_id",
                        "value": "i-123456",
                        "sensitive": False,
                        "type": "string",
                        "detailed-type": "string",
                    },
                },
                {
                    "id": "wsout-2",
                    "attributes": {
                        "name": "api_token",
                        "value": None,
                        "sensitive": True,
                        "type": "string",
                        "detailed-type": "string",
                    },
                },
            ],
        }

        result = get_output_by_name(mock_client, "ws-123", "server_id")

        assert result["name"] == "server_id"
        assert result["value"] == "i-123456"
        assert result["id"] == "wsout-1"

    def test_get_output_by_name_not_found(self, mock_client):
        """Test error when output name doesn't exist."""
        mock_client.get.return_value = {
            "status": 200,
            "data": [
                {
                    "id": "wsout-1",
                    "attributes": {
                        "name": "other_output",
                        "value": "value",
                        "sensitive": False,
                        "type": "string",
                        "detailed-type": "string",
                    },
                },
            ],
        }

        with pytest.raises(ValueError, match="Output with name 'nonexistent' not found in workspace 'ws-123'"):
            get_output_by_name(mock_client, "ws-123", "nonexistent")

    def test_get_output_by_name_sensitive_with_display(self, mock_client):
        """Test retrieving sensitive output by name with display_sensitive=True."""

        # First call returns the list
        def mock_get_side_effect(endpoint):
            if endpoint == "/workspaces/ws-123/current-state-version-outputs":
                return {
                    "status": 200,
                    "data": [
                        {
                            "id": "wsout-secret",
                            "attributes": {
                                "name": "password",
                                "value": None,
                                "sensitive": True,
                                "type": "string",
                                "detailed-type": "string",
                            },
                        },
                    ],
                }
            elif endpoint == "/state-version-outputs/wsout-secret":
                return {
                    "status": 200,
                    "data": {
                        "id": "wsout-secret",
                        "attributes": {
                            "name": "password",
                            "value": "actual-password",
                            "sensitive": True,
                            "type": "string",
                            "detailed-type": "string",
                        },
                    },
                }

        mock_client.get.side_effect = mock_get_side_effect

        result = get_output_by_name(mock_client, "ws-123", "password", display_sensitive=True)

        assert result["value"] == "actual-password"
        assert result["sensitive"] is True


if __name__ == "__main__":
    pytest.main([__file__])
