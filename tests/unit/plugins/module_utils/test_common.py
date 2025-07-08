# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from ansible.module_utils.six.moves.http_cookiejar import CookieJar

from ansible.errors import AnsibleError
from ansible.module_utils.urls import Request

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from plugins.module_utils.common import (
    TerraformModule,
    TerraformClient,
    ClientMixin,
)
from plugins.module_utils.exceptions import (
    TerraformTokenNotFoundError,
    TerraformHostnameNotFoundError,
    TerraformSSLValidationError,
)


class TestTerraformModuleUtil:
    """Test cases for TerraformModule class."""

    def test_terraform_module_init_adds_auth_argspec(self):
        """Test that TerraformModule adds authentication parameters to argspec."""
        test_argspec = {
            "test_param": dict(type="str", required=True),
        }

        with patch("ansible.module_utils.basic.AnsibleModule.__init__") as mock_init:
            mock_init.return_value = None
            TerraformModule(test_argspec)

            # Check that auth argspec was added
            called_argspec = mock_init.call_args[0][0]
            assert "tf_token" in called_argspec
            assert "tf_hostname" in called_argspec
            assert "tf_validate_certs" in called_argspec
            assert "test_param" in called_argspec

    def test_terraform_module_auth_argspec_structure(self):
        """Test the structure of AUTH_ARGSPEC."""
        auth_spec = TerraformModule.AUTH_ARGSPEC

        # Check tf_token
        assert "tf_token" in auth_spec
        assert auth_spec["tf_token"]["required"] is False
        assert "fallback" in auth_spec["tf_token"]

        # Check tf_hostname
        assert "tf_hostname" in auth_spec
        assert auth_spec["tf_hostname"]["required"] is False
        assert auth_spec["tf_hostname"]["default"] == "app.terraform.io"
        assert "fallback" in auth_spec["tf_hostname"]

        # Check tf_validate_certs
        assert "tf_validate_certs" in auth_spec
        assert auth_spec["tf_validate_certs"]["required"] is True
        assert "fallback" in auth_spec["tf_validate_certs"]

class TestClientMixin:
    """Test cases for ClientMixin class."""

    class MockClient(ClientMixin):
        """Mock client class for testing ClientMixin."""

        def __init__(self):
            self.base_url = "https://api.terraform.io/api/v2"
            self.session = Mock()

    def test_sanitize_response_dict_with_included_keys(self):
        """Test sanitizing dict response with keys to include."""
        mixin = ClientMixin()
        response = {
            "id": "123",
            "name": "test",
            "secret": "hidden",
            "nested": {"id": "456", "data": "value"},
        }
        keys_to_include = ["id", "name", "data"]

        result = mixin.sanitize_response(response, keys_to_include)

        assert result["id"] == "123"
        assert result["name"] == "test"
        assert "secret" not in result
        assert result["nested"]["id"] == "456"
        assert result["nested"]["data"] == "value"

    def test_sanitize_response_list(self):
        """Test sanitizing list response."""
        mixin = ClientMixin()
        response = [
            {"id": "1", "name": "test1", "secret": "hidden1"},
            {"id": "2", "name": "test2", "secret": "hidden2"},
        ]
        keys_to_include = ["id", "name"]

        result = mixin.sanitize_response(response, keys_to_include)

        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[0]["name"] == "test1"
        assert "secret" not in result[0]

    def test_sanitize_response_empty_result(self):
        """Test sanitizing response that results in empty data."""
        mixin = ClientMixin()
        response = {"secret": "hidden"}
        keys_to_include = ["id", "name"]

        result = mixin.sanitize_response(response, keys_to_include)

        assert result is None

    def test_dict_to_json_valid_data(self):
        """Test converting dict to JSON string."""
        mixin = ClientMixin()
        data = {"key": "value", "number": 42}

        result = mixin.dict_to_json(data)

        assert result == '{"key": "value", "number": 42}'

    def test_dict_to_json_invalid_data(self):
        """Test converting invalid data to JSON raises AnsibleError."""
        mixin = ClientMixin()
        # Create object that can't be JSON serialized
        data = {"key": set([1, 2, 3])}

        with pytest.raises(AnsibleError, match="Failed to convert data to JSON"):
            mixin.dict_to_json(data)

    def test_json_to_dict_valid_json(self):
        """Test converting JSON string to dict."""
        mixin = ClientMixin()
        json_str = '{"key": "value", "number": 42}'

        result = mixin.json_to_dict(json_str)

        assert result == {"key": "value", "number": 42}

    def test_json_to_dict_valid_json_bytes(self):
        """Test converting JSON bytes to dict (simulating HTTP response)."""
        mixin = ClientMixin()
        json_bytes = b'{"key": "value", "number": 42}'

        result = mixin.json_to_dict(json_bytes)

        assert result == {"key": "value", "number": 42}

    def test_json_to_dict_invalid_json(self):
        """Test converting invalid JSON raises AnsibleError."""
        mixin = ClientMixin()
        json_str = '{"key": "value"'  # Missing closing brace

        with pytest.raises(AnsibleError, match="Failed to decode JSON string"):
            mixin.json_to_dict(json_str)

    def test_json_to_dict_invalid_json_bytes(self):
        """Test converting invalid JSON bytes raises AnsibleError."""
        mixin = ClientMixin()
        json_bytes = b'{"key": "value"'  # Missing closing brace

        with pytest.raises(AnsibleError, match="Failed to decode JSON string"):
            mixin.json_to_dict(json_bytes)

    def test_make_request_decorator_get(self):
        """Test make_request decorator with GET method."""
        client = self.MockClient()

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"data": "test"}'

        client.session.open.return_value = mock_response

        result = client.get("/test")

        assert result == {"data": "test"}
        client.session.open.assert_called_once_with(
            "GET",
            "https://api.terraform.io/api/v2/test",
            data=None,
        )

    def test_make_request_decorator_post_with_data(self):
        """Test make_request decorator with POST method and data."""
        client = self.MockClient()

        # Mock session
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = b'{"id": "123"}'

        client.session.open.return_value = mock_response

        test_data = {"name": "test"}
        result = client.post("/test", test_data)

        assert result == {"id": "123"}
        client.session.open.assert_called_once_with(
            "POST",
            "https://api.terraform.io/api/v2/test",
            data='{"name": "test"}',
        )

    def test_make_request_decorator_patch_with_data(self):
        """Test make_request decorator with PATCH method and data."""
        client = self.MockClient()

        # Mock session
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"id": "123", "name": "updated"}'

        client.session.open.return_value = mock_response

        test_data = {"name": "updated"}
        result = client.patch("/test/123", test_data)

        assert result == {"id": "123", "name": "updated"}
        client.session.open.assert_called_once_with(
            "PATCH",
            "https://api.terraform.io/api/v2/test/123",
            data='{"name": "updated"}',
        )

    def test_make_request_decorator_error_response(self):
        """Test make_request decorator with error response."""
        client = self.MockClient()

        # Mock session
        mock_response = Mock()
        mock_response.status = 404
        mock_response.reason = "Not Found"

        client.session.open.return_value = mock_response

        with pytest.raises(AnsibleError, match="Failed to GET /test: Not Found \\(404\\)"):
            client.get("/test")

    def test_make_request_decorator_with_keys_to_include(self):
        """Test make_request decorator with keys_to_include parameter."""
        client = self.MockClient()

        # Mock session
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"id": "123", "name": "test", "secret": "hidden"}'

        client.session.open.return_value = mock_response

        result = client.get("/test", keys_to_include=["id", "name"])

        assert result == {"id": "123", "name": "test"}
        assert "secret" not in result

    def test_make_request_decorator_path_normalization(self):
        """Test make_request decorator normalizes paths."""
        client = self.MockClient()

        # Mock session
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"data": "test"}'

        client.session.open.return_value = mock_response

        # Test path without leading slash
        client.get("test")

        client.session.open.assert_called_once_with(
            "GET",
            "https://api.terraform.io/api/v2/test",
            data=None,
        )


class TestTerraformClient:
    """Test cases for TerraformClient class."""

    @patch("plugins.module_utils.common.Request")
    def test_terraform_client_init_with_token(self, mock_request):
        """Test TerraformClient initialization with token."""
        mock_request_instance = Mock()
        mock_request.return_value = mock_request_instance

        client = TerraformClient(
            tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True
        )

        assert client.hostname == "app.terraform.io"
        assert client._token == "test-token"
        assert client.verify is True
        assert client.session == mock_request_instance

    @patch("plugins.module_utils.common.Request")
    def test_terraform_client_init_custom_hostname(self, mock_request):
        """Test TerraformClient initialization with custom hostname."""
        mock_request_instance = Mock()
        mock_request.return_value = mock_request_instance

        client = TerraformClient(
            tf_token="test-token", tf_hostname="custom.terraform.io", tf_validate_certs=True
        )

        assert client.hostname == "custom.terraform.io"
        assert client.base_url == "https://custom.terraform.io/api/v2"

    @patch("plugins.module_utils.common.Request")
    def test_terraform_client_init_with_http_url(self, mock_request):
        """Test TerraformClient initialization with HTTP URL."""
        mock_request_instance = Mock()
        mock_request_instance.headers = Mock()
        mock_request.return_value = mock_request_instance

        client = TerraformClient(
            tf_token="test-token",
            tf_hostname="http://custom.terraform.io",
            tf_validate_certs=False,  # Allow HTTP when SSL validation is disabled
        )

        assert client.base_url == "http://custom.terraform.io/api/v2"

    @patch("plugins.module_utils.common.Request")
    def test_terraform_client_init_with_https_url(self, mock_request):
        """Test TerraformClient initialization with HTTPS URL."""
        mock_request_instance = Mock()
        mock_request.return_value = mock_request_instance

        client = TerraformClient(
            tf_token="test-token", tf_hostname="https://custom.terraform.io", tf_validate_certs=True
        )

        assert client.base_url == "https://custom.terraform.io/api/v2"

    @patch("plugins.module_utils.common.Request")
    def test_terraform_client_headers_default(self, mock_request):
        """Test TerraformClient sets default headers."""
        mock_request_instance = Mock()
        mock_request_instance.headers = Mock()
        mock_request.return_value = mock_request_instance

        client = TerraformClient(
            tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True
        )

        expected_headers = {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/vnd.api+json",
        }
        mock_request_instance.headers.update.assert_called_with(expected_headers)

    @patch("plugins.module_utils.common.Request")
    def test_terraform_client_headers_custom(self, mock_request):
        """Test TerraformClient with custom headers."""
        mock_request_instance = Mock()
        mock_request_instance.headers = Mock()
        mock_request.return_value = mock_request_instance

        custom_headers = {"User-Agent": "test-agent"}
        client = TerraformClient(
            tf_token="test-token",
            tf_hostname="app.terraform.io",
            tf_validate_certs=True,
            headers=custom_headers,
        )

        expected_headers = {"Authorization": "Bearer test-token"}
        mock_request_instance.headers.update.assert_called_with(expected_headers)

    @patch("plugins.module_utils.common.Request")
    def test_terraform_client_headers_with_auth(self, mock_request):
        """Test TerraformClient with custom headers including auth."""
        mock_request_instance = Mock()
        mock_request_instance.headers = Mock()
        mock_request.return_value = mock_request_instance

        custom_headers = {"Authorization": "Bearer custom-token"}
        client = TerraformClient(
            tf_token="test-token",
            tf_hostname="app.terraform.io",
            tf_validate_certs=True,
            headers=custom_headers,
        )

        # Should not add auth header if already present
        mock_request_instance.headers.update.assert_not_called()

    def test_terraform_client_init_no_token_raises_error(self):
        """Test TerraformClient initialization without token raises error."""
        with pytest.raises(TerraformTokenNotFoundError):
            TerraformClient(tf_hostname="app.terraform.io", tf_validate_certs=True)

    def test_terraform_client_init_no_hostname_raises_error(self):
        """Test TerraformClient initialization without hostname raises error."""
        with pytest.raises(TerraformHostnameNotFoundError):
            TerraformClient(tf_token="test-token", tf_hostname="", tf_validate_certs=True)

    def test_terraform_client_init_http_with_ssl_validation_raises_error(self):
        """Test TerraformClient initialization with HTTP URL and SSL validation raises error."""
        with pytest.raises(TerraformSSLValidationError):
            TerraformClient(
                tf_token="test-token", tf_hostname="http://app.terraform.io", tf_validate_certs=True
            )

    @patch("plugins.module_utils.common.Request")
    def test_terraform_client_session_args(self, mock_request):
        """Test TerraformClient session arguments."""
        mock_request_instance = Mock()
        mock_request_instance.headers = Mock()
        mock_request.return_value = mock_request_instance

        client = TerraformClient(
            tf_token="test-token",
            tf_hostname="app.terraform.io",
            tf_validate_certs=True,
            timeout=20,
        )

        expected_args = {
            "timeout": 20,
            "validate_certs": True,
            "headers": {},
            "cookies": mock_request.call_args[1]["cookies"],
            "follow_redirects": True,
        }

        # Check that Request was called with expected arguments
        mock_request.assert_called_once()
        call_args = mock_request.call_args[1]
        assert call_args["timeout"] == 20
        assert call_args["validate_certs"] is True
        assert call_args["follow_redirects"] is True
        assert isinstance(call_args["cookies"], CookieJar)

    @patch("plugins.module_utils.common.Request")
    def test_terraform_client_get_token_from_config_file(self, mock_request):
        """Test TerraformClient _get_token_from_config_file method."""
        mock_request_instance = Mock()
        mock_request_instance.headers = Mock()
        mock_request.return_value = mock_request_instance

        client = TerraformClient(
            tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True
        )

        # Method should return None (placeholder implementation)
        result = client._get_token_from_config_file()
        assert result is None

    @patch("plugins.module_utils.common.Request")
    def test_terraform_client_pre_checks_called(self, mock_request):
        """Test TerraformClient pre_checks method is called during initialization."""
        mock_request_instance = Mock()
        mock_request_instance.headers = Mock()
        mock_request.return_value = mock_request_instance

        with patch.object(TerraformClient, "pre_checks") as mock_pre_checks:
            client = TerraformClient(
                tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True
            )
            mock_pre_checks.assert_called_once()

    @patch("plugins.module_utils.common.Request")
    def test_terraform_client_inheritance(self, mock_request):
        """Test TerraformClient inherits from ClientMixin."""
        mock_request_instance = Mock()
        mock_request_instance.headers = Mock()
        mock_request.return_value = mock_request_instance

        client = TerraformClient(
            tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True
        )

        # Should have methods from ClientMixin
        assert hasattr(client, "sanitize_response")
        assert hasattr(client, "dict_to_json")
        assert hasattr(client, "json_to_dict")
        assert hasattr(client, "get")
        assert hasattr(client, "post")
        assert hasattr(client, "put")
        assert hasattr(client, "patch")
        assert hasattr(client, "delete")