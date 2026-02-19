# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Unit tests for client.py module.

These tests verify the AnsibleTerraformModule wrapper and TerraformClient
class functionality including authentication, error handling, and SDK integration.
"""

from unittest.mock import Mock, patch

import pytest
from pytfe.errors import AuthError, NotFound, ServerError, TFEError

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
    TerraformTokenNotFoundError,
)


class TestAnsibleTerraformModule:
    """Test AnsibleTerraformModule wrapper class."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.client.AnsibleModule")
    def test_module_initialization_merges_argspecs(self, mock_ansible_module):
        """Test that module initialization merges AUTH_ARGSPEC with custom argspec."""
        custom_argspec = {
            "workspace": {"type": "str", "required": True},
            "organization": {"type": "str", "required": True},
        }
        
        AnsibleTerraformModule(argument_spec=custom_argspec)
        
        # Verify AnsibleModule was called with merged argspec
        mock_ansible_module.assert_called_once()
        call_kwargs = mock_ansible_module.call_args[1]
        merged_spec = call_kwargs["argument_spec"]
        
        # Should contain both auth and custom fields
        assert "tfe_token" in merged_spec
        assert "tfe_address" in merged_spec
        assert "workspace" in merged_spec
        assert "organization" in merged_spec

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.client.AnsibleModule")
    def test_module_initialization_with_additional_kwargs(self, mock_ansible_module):
        """Test module initialization passes additional kwargs to AnsibleModule."""
        custom_argspec = {"workspace": {"type": "str"}}
        
        AnsibleTerraformModule(
            argument_spec=custom_argspec,
            supports_check_mode=True,
            required_together=[["workspace", "organization"]]
        )
        
        # Verify kwargs were passed through
        call_kwargs = mock_ansible_module.call_args[1]
        assert call_kwargs["supports_check_mode"] is True
        assert call_kwargs["required_together"] == [["workspace", "organization"]]

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.client.AnsibleModule")
    def test_attribute_delegation(self, mock_ansible_module):
        """Test that attributes are delegated to underlying AnsibleModule."""
        # Setup mock module with some attributes
        mock_instance = Mock()
        mock_instance.params = {"workspace": "test"}
        mock_instance.check_mode = False
        mock_ansible_module.return_value = mock_instance
        
        module = AnsibleTerraformModule(argument_spec={})
        
        # Access attributes through wrapper
        assert module.params == {"workspace": "test"}
        assert module.check_mode is False

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.client.AnsibleModule")
    def test_method_delegation(self, mock_ansible_module):
        """Test that methods are delegated to underlying AnsibleModule."""
        mock_instance = Mock()
        mock_ansible_module.return_value = mock_instance
        
        module = AnsibleTerraformModule(argument_spec={})
        
        # Call methods on wrapper
        module.exit_json(changed=True)
        module.fail_json(msg="error")
        module.warn("warning")
        
        # Verify methods were called on underlying module
        mock_instance.exit_json.assert_called_once_with(changed=True)
        mock_instance.fail_json.assert_called_once_with(msg="error")
        mock_instance.warn.assert_called_once_with("warning")


class TestTerraformClientInitialization:
    """Test TerraformClient initialization."""

    def test_client_initialization_with_token(self):
        """Test client initializes successfully with token."""
        client = TerraformClient(tfe_token="test-token")
        
        assert client.token == "test-token"
        assert client.address == "https://app.terraform.io"

    def test_client_initialization_without_token_raises_error(self):
        """Test client raises error when initialized without token."""
        with pytest.raises(TerraformTokenNotFoundError) as excinfo:
            TerraformClient()
        
        assert "Authentication token is required" in str(excinfo.value)


class TestTerraformClientLazyLoading:
    """Test TerraformClient lazy loading of config and client."""

    def test_config_lazy_loading(self):
        """Test config is lazy-loaded on first access."""
        client = TerraformClient(tfe_token="test-token")
        
        # Config should not exist yet
        assert client._config is None
        
        # Access config triggers creation
        config = client.config
        
        assert config is not None
        assert client._config is not None


class TestTerraformClientErrorHandling:
    """Test TerraformClient error handling methods."""

    def test_handle_error_with_not_found(self):
        """Test handle_error wraps NotFound exceptions."""
        client = TerraformClient(tfe_token="test-token")
        error = NotFound("Workspace not found")
        
        with pytest.raises(TerraformError) as excinfo:
            client.handle_error(error)
        
        assert "Resource not found" in str(excinfo.value)
        assert "Workspace not found" in str(excinfo.value)

    def test_handle_error_with_auth_error(self):
        """Test handle_error wraps AuthError exceptions."""
        client = TerraformClient(tfe_token="test-token")
        error = AuthError("Invalid credentials")
        
        with pytest.raises(TerraformError) as excinfo:
            client.handle_error(error)
        
        assert "Authentication error" in str(excinfo.value)
        assert "Invalid credentials" in str(excinfo.value)

    def test_handle_error_with_server_error(self):
        """Test handle_error wraps ServerError exceptions."""
        client = TerraformClient(tfe_token="test-token")
        error = ServerError("Internal server error")
        
        with pytest.raises(TerraformError) as excinfo:
            client.handle_error(error)
        
        assert "Server error" in str(excinfo.value)
        assert "Internal server error" in str(excinfo.value)

    def test_handle_error_with_generic_tfe_error(self):
        """Test handle_error wraps generic TFEError exceptions."""
        client = TerraformClient(tfe_token="test-token")
        error = TFEError("Generic TFE error")
        
        with pytest.raises(TerraformError) as excinfo:
            client.handle_error(error)
        
        assert "Generic TFE error" in str(excinfo.value)

    def test_handle_error_with_context(self):
        """Test handle_error includes context in error message."""
        client = TerraformClient(tfe_token="test-token")
        error = NotFound("Workspace not found")
        
        with pytest.raises(TerraformError) as excinfo:
            client.handle_error(error, context="Failed to retrieve workspace")
        
        assert "Failed to retrieve workspace" in str(excinfo.value)
        assert "Resource not found" in str(excinfo.value)

    def test_handle_error_with_details_attribute(self):
        """Test handle_error extracts details from TFEError if available."""
        client = TerraformClient(tfe_token="test-token")
        error = TFEError("Error occurred")
        error.details = {"field": "invalid value"}
        
        with pytest.raises(TerraformError) as excinfo:
            client.handle_error(error)
        
        assert "Details:" in str(excinfo.value)


class TestTerraformClientSafeApiCall:
    """Test TerraformClient safe_api_call method."""

    def test_safe_api_call_success(self):
        """Test safe_api_call executes operation successfully."""
        client = TerraformClient(tfe_token="test-token")
        mock_operation = Mock(return_value={"id": "ws-123", "name": "test"})
        
        result = client.safe_api_call(mock_operation, "arg1", kwarg1="value1")
        
        mock_operation.assert_called_once_with("arg1", kwarg1="value1")
        assert result == {"id": "ws-123", "name": "test"}

    def test_safe_api_call_with_tfe_error(self):
        """Test safe_api_call handles TFEError."""
        client = TerraformClient(tfe_token="test-token")
        mock_operation = Mock(side_effect=NotFound("Resource not found"))
        
        with pytest.raises(TerraformError) as excinfo:
            client.safe_api_call(mock_operation, error_context="Failed to get resource")
        
        assert "Failed to get resource" in str(excinfo.value)
        assert "Resource not found" in str(excinfo.value)

    def test_safe_api_call_with_generic_exception(self):
        """Test safe_api_call handles generic exceptions."""
        client = TerraformClient(tfe_token="test-token")
        mock_operation = Mock(side_effect=ValueError("Invalid input"))
        
        with pytest.raises(TerraformError) as excinfo:
            client.safe_api_call(mock_operation)
        
        assert "Unexpected error" in str(excinfo.value)
        assert "Invalid input" in str(excinfo.value)

    def test_safe_api_call_extracts_error_context_from_kwargs(self):
        """Test safe_api_call extracts and removes error_context from kwargs."""
        client = TerraformClient(tfe_token="test-token")
        mock_operation = Mock(return_value="success")
        
        result = client.safe_api_call(
            mock_operation,
            "arg1",
            kwarg1="value1",
            error_context="Custom context"
        )
        
        # error_context should not be passed to operation
        mock_operation.assert_called_once_with("arg1", kwarg1="value1")
        assert result == "success"


class TestTerraformClientFormatResponse:
    """Test TerraformClient format_response method."""

    def test_format_response_converts_to_dict(self):
        """Test format_response converts SDK response to dictionary."""
        client = TerraformClient(tfe_token="test-token")
        
        # Mock SDK response object with model_dump method
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "type": "workspaces",
        }
        
        result = client.format_response(mock_response)
        
        mock_response.model_dump.assert_called_once_with(mode="json", exclude_none=True)
        assert result["id"] == "ws-123"
        assert result["name"] == "test-workspace"
        assert result["type"] == "workspaces"

    def test_format_response_excludes_none_values(self):
        """Test format_response excludes None values."""
        client = TerraformClient(tfe_token="test-token")
        
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "description": None,  # Should be excluded
        }
        
        result = client.format_response(mock_response)
        
        # Verify exclude_none parameter was used
        mock_response.model_dump.assert_called_with(mode="json", exclude_none=True)


class TestTerraformClientCleanup:
    """Test TerraformClient cleanup method."""

    def test_cleanup_handles_no_client(self):
        """Test cleanup handles case when client was never created."""
        client = TerraformClient(tfe_token="test-token")
        
        # Don't access client, just call cleanup
        client.cleanup()  # Should not raise error
        
        assert client._client is None
        assert client._config is None
