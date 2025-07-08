# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import os
import sys

from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from ansible.errors import AnsibleError


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from plugins.module_utils.common import (
    ArchivistClient,
    ClientMixin,
    TerraformClient,
    TerraformModule,
)
from plugins.module_utils.exceptions import (
    TerraformHostnameNotFoundError,
    TerraformSSLValidationError,
    TerraformTokenNotFoundError,
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

        assert "tf_token" in auth_spec
        assert auth_spec["tf_token"]["required"] is False
        assert "fallback" in auth_spec["tf_token"]
        assert "tf_hostname" in auth_spec
        assert auth_spec["tf_hostname"]["required"] is False
        assert auth_spec["tf_hostname"]["default"] == "app.terraform.io"
        assert "fallback" in auth_spec["tf_hostname"]
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
            self.session.headers = {"Content-Type": "application/vnd.api+json"}

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
        mock_response.status_code = 200
        mock_response.content = b'{"data": "test"}'

        client.session.request.return_value = mock_response

        result = client.get("/test")

        assert result == {"status": 200, "data": {"data": "test"}}
        client.session.request.assert_called_once_with(
            "GET",
            "https://api.terraform.io/api/v2/test",
            data=None,
        )

    def test_make_request_decorator_data_conversion_methods(self):
        """Test make_request decorator with data conversion methods (POST, PUT, PATCH, DELETE)."""
        client = self.MockClient()

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": "123"}'

        client.session.request.return_value = mock_response

        test_data = {"name": "test"}

        # Test POST
        result = client.post("/test", test_data)
        assert result == {"status": 201, "data": {"id": "123"}}
        client.session.request.assert_called_with(
            "POST",
            "https://api.terraform.io/api/v2/test",
            data='{"name": "test"}',
        )

        # Test PUT
        result = client.put("/test", test_data)
        assert result == {"status": 201, "data": {"id": "123"}}
        client.session.request.assert_called_with(
            "PUT",
            "https://api.terraform.io/api/v2/test",
            data='{"name": "test"}',
        )

        # Test PATCH
        result = client.patch("/test", test_data)
        assert result == {"status": 201, "data": {"id": "123"}}
        client.session.request.assert_called_with(
            "PATCH",
            "https://api.terraform.io/api/v2/test",
            data='{"name": "test"}',
        )

        # Test DELETE
        result = client.delete("/test")
        assert result == {"status": 201, "data": {"id": "123"}}
        client.session.request.assert_called_with(
            "DELETE",
            "https://api.terraform.io/api/v2/test",
            data=None,
        )

    def test_make_request_decorator_error_response(self):
        """Test make_request decorator with error response."""
        client = self.MockClient()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason = "Not Found"

        client.session.request.return_value = mock_response

        with pytest.raises(AnsibleError, match="Failed to GET /test: Not Found \\(404\\)"):
            client.get("/test")

    def test_make_request_decorator_with_keys_to_include(self):
        """Test make_request decorator with keys_to_include parameter."""
        client = self.MockClient()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"id": "123", "name": "test", "secret": "hidden"}'

        client.session.request.return_value = mock_response

        result = client.get("/test", keys_to_include=["id", "name"])

        assert result == {"status": 200, "data": {"id": "123", "name": "test"}}
        assert "secret" not in result["data"]

    def test_make_request_decorator_path_normalization(self):
        """Test make_request decorator handles paths."""
        client = self.MockClient()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"data": "test"}'

        client.session.request.return_value = mock_response

        # Test path without leading slash
        client.get("test")

        client.session.request.assert_called_once_with(
            "GET",
            "https://api.terraform.io/api/v2/test",
            data=None,
        )


class TestTerraformClient:
    """Test cases for TerraformClient class."""

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_init_with_token(self, mock_session):
        """Test TerraformClient initialization with token."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = TerraformClient(
            tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True
        )

        assert client.hostname == "app.terraform.io"
        assert client._token == "test-token"
        assert client.verify is True
        assert client.session == mock_session_instance

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_init_custom_hostname(self, mock_session):
        """Test TerraformClient initialization with custom hostname."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = TerraformClient(
            tf_token="test-token", tf_hostname="custom.terraform.io", tf_validate_certs=True
        )

        assert client.hostname == "custom.terraform.io"
        assert client.base_url == "https://custom.terraform.io/api/v2"

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_init_with_http_url(self, mock_session):
        """Test TerraformClient initialization with HTTP URL."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = TerraformClient(
            tf_token="test-token",
            tf_hostname="http://custom.terraform.io",
            tf_validate_certs=False,  # Allow HTTP when SSL validation is disabled
        )

        assert client.base_url == "http://custom.terraform.io/api/v2"

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_init_with_https_url(self, mock_session):
        """Test TerraformClient initialization with HTTPS URL."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = TerraformClient(
            tf_token="test-token", tf_hostname="https://custom.terraform.io", tf_validate_certs=True
        )

        assert client.base_url == "https://custom.terraform.io/api/v2"

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_headers_default(self, mock_session):
        """Test TerraformClient sets default headers."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = TerraformClient(
            tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True
        )

        expected_headers = {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/vnd.api+json",
        }
        mock_session_instance.headers.update.assert_called_with(expected_headers)

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_headers_custom(self, mock_session):
        """Test TerraformClient with custom headers."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        custom_headers = {"User-Agent": "test-agent"}
        client = TerraformClient(
            tf_token="test-token",
            tf_hostname="app.terraform.io",
            tf_validate_certs=True,
            headers=custom_headers,
        )

        expected_headers = {"Authorization": "Bearer test-token"}
        mock_session_instance.headers.update.assert_called_with(expected_headers)

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_headers_with_auth(self, mock_session):
        """Test TerraformClient with custom headers including auth."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        custom_headers = {"Authorization": "Bearer custom-token"}
        client = TerraformClient(
            tf_token="test-token",
            tf_hostname="app.terraform.io",
            tf_validate_certs=True,
            headers=custom_headers,
        )

        # Should only call headers.update once with custom headers, not add default auth
        mock_session_instance.headers.update.assert_called_once_with(custom_headers)

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

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_session_creation(self, mock_session):
        """Test TerraformClient session creation."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = TerraformClient(
            tf_token="test-token",
            tf_hostname="app.terraform.io",
            tf_validate_certs=True,
            timeout=20,
        )

        # Check that session was created
        mock_session.assert_called_once()
        assert client.session == mock_session_instance

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_get_token_from_config_file(self, mock_session):
        """Test TerraformClient _get_token_from_config_file method."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = TerraformClient(
            tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True
        )

        # Method should return None (placeholder implementation)
        result = client._get_token_from_config_file()
        assert result is None

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_pre_checks_called(self, mock_session):
        """Test TerraformClient pre_checks method is called during initialization."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        with patch.object(TerraformClient, "pre_checks") as mock_pre_checks:
            client = TerraformClient(
                tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True
            )
            mock_pre_checks.assert_called_once()

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_inheritance(self, mock_session):
        """Test TerraformClient inherits from ClientMixin."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

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


class TestArchivistClient:
    """Test cases for ArchivistClient class."""

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_init_default_hostname(self, mock_session):
        """Test ArchivistClient initialization with default hostname."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = ArchivistClient(tf_validate_certs=True)

        assert client.hostname == "archivist.terraform.io"
        assert client.verify is True
        assert client.base_url == "https://archivist.terraform.io/v1"
        assert client.session == mock_session_instance

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_init_custom_hostname(self, mock_session):
        """Test ArchivistClient initialization with custom hostname."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = ArchivistClient(tf_hostname="custom.archivist.io", tf_validate_certs=True)

        assert client.hostname == "custom.archivist.io"
        assert client.base_url == "https://custom.archivist.io/v1"

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_init_with_http_url(self, mock_session):
        """Test ArchivistClient initialization with HTTP URL."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = ArchivistClient(tf_hostname="http://custom.archivist.io", tf_validate_certs=False)

        assert client.base_url == "http://custom.archivist.io/v1"

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_init_with_https_url(self, mock_session):
        """Test ArchivistClient initialization with HTTPS URL."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = ArchivistClient(tf_hostname="https://custom.archivist.io", tf_validate_certs=True)

        assert client.base_url == "https://custom.archivist.io/v1"

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_headers_default(self, mock_session):
        """Test ArchivistClient sets default headers."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = ArchivistClient(tf_validate_certs=True)

        expected_headers = {"Content-Type": "application/octet-stream"}
        mock_session_instance.headers.update.assert_called_with(expected_headers)

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_headers_custom(self, mock_session):
        """Test ArchivistClient with custom headers."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        custom_headers = {"User-Agent": "test-agent"}
        client = ArchivistClient(tf_validate_certs=True, headers=custom_headers)

        mock_session_instance.headers.update.assert_called_once_with(custom_headers)

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_session_creation(self, mock_session):
        """Test ArchivistClient session creation."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = ArchivistClient(tf_validate_certs=True, timeout=20)

        mock_session.assert_called_once()
        assert client.session == mock_session_instance

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_pre_checks_called(self, mock_session):
        """Test ArchivistClient pre_checks method is called during initialization."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        with patch.object(ArchivistClient, "pre_checks") as mock_pre_checks:
            client = ArchivistClient(tf_validate_certs=True)
            mock_pre_checks.assert_called_once()

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_inheritance(self, mock_session):
        """Test ArchivistClient inherits from ClientMixin."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = ArchivistClient(tf_validate_certs=True)

        assert hasattr(client, "sanitize_response")
        assert hasattr(client, "dict_to_json")
        assert hasattr(client, "json_to_dict")
        assert hasattr(client, "get")
        assert hasattr(client, "post")
        assert hasattr(client, "put")
        assert hasattr(client, "patch")
        assert hasattr(client, "delete")



    def test_archivist_client_init_no_hostname_raises_error(self):
        """Test ArchivistClient initialization without hostname raises error."""
        with pytest.raises(TerraformHostnameNotFoundError):
            ArchivistClient(tf_hostname="", tf_validate_certs=True)

    def test_archivist_client_init_http_with_ssl_validation_raises_error(self):
        """Test ArchivistClient initialization with HTTP URL and SSL validation raises error."""
        with pytest.raises(TerraformSSLValidationError):
            ArchivistClient(tf_hostname="http://archivist.terraform.io", tf_validate_certs=True)


class TestClientMixinAdditional:
    """Additional test cases for ClientMixin class covering missing functionality."""

    class MockClient(ClientMixin):
        """Mock client class for testing ClientMixin."""

        def __init__(self):
            self.base_url = "https://api.terraform.io/api/v2"
            self.session = Mock()
            self.session.headers = {"Content-Type": "application/vnd.api+json"}
            self.hostname: Optional[str] = "app.terraform.io"
            self.verify = True
            self._token: Optional[str] = "test-token"

    def test_head_method_placeholder(self):
        """Test head method (placeholder implementation)."""
        client = self.MockClient()

        result = client.head("/test")
        assert result is None

    def test_pre_checks_terraform_client_success(self):
        """Test pre_checks method for TerraformClient with valid configuration."""
        client = self.MockClient()

        client.pre_checks()

    @patch("plugins.module_utils.common.requests.Session")
    def test_pre_checks_archivist_client_success(self, mock_session):
        """Test pre_checks method for ArchivistClient (no token required)."""
        from plugins.module_utils.common import ArchivistClient

        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = ArchivistClient(tf_validate_certs=True)
        client.pre_checks()

    def test_pre_checks_missing_token_raises_error(self):
        """Test pre_checks method raises error when token is missing."""
        client = self.MockClient()
        client._token = None

        with pytest.raises(TerraformTokenNotFoundError):
            client.pre_checks()

    def test_pre_checks_missing_hostname_raises_error(self):
        """Test pre_checks method raises error when hostname is missing."""
        client = self.MockClient()
        client.hostname = None

        with pytest.raises(TerraformHostnameNotFoundError):
            client.pre_checks()

    def test_pre_checks_http_with_ssl_validation_raises_error(self):
        """Test pre_checks method raises error for HTTP with SSL validation."""
        client = self.MockClient()
        client.hostname = "http://app.terraform.io"
        client.verify = True

        with pytest.raises(TerraformSSLValidationError):
            client.pre_checks()

    @patch("plugins.module_utils.common.requests.Session")
    @patch("plugins.module_utils.common.requests.adapters.HTTPAdapter")
    @patch("plugins.module_utils.common.Retry")
    def test_create_session_detailed(self, mock_retry, mock_adapter, mock_session):
        """Test create_session method with detailed configuration."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_adapter_instance = Mock()
        mock_adapter.return_value = mock_adapter_instance
        mock_retry_instance = Mock()
        mock_retry.return_value = mock_retry_instance

        client = self.MockClient()

        session_args = {
            "base_url": "https://test.terraform.io/api/v2",
            "headers": {"Custom": "header"},
            "retries": 5,
            "timeout": 30,
            "validate_certs": True,
        }

        result = client.create_session(**session_args)

        mock_session.assert_called_once()
        assert result == mock_session_instance
        assert client.session == mock_session_instance

        mock_retry.assert_called_once_with(
            total=5,
            connect=5,
            read=5,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=frozenset(["GET", "POST", "PUT", "PATCH", "DELETE"]),
            raise_on_status=False,
        )

        mock_adapter.assert_called_once_with(max_retries=mock_retry_instance)
        mock_session_instance.mount.assert_called_once_with("https://", mock_adapter_instance)

    @patch("plugins.module_utils.common.requests.Session")
    @patch("plugins.module_utils.common.requests.adapters.HTTPAdapter")
    @patch("plugins.module_utils.common.Retry")
    def test_create_session_http_url(self, mock_retry, mock_adapter, mock_session):
        """Test create_session method with HTTP URL."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_adapter_instance = Mock()
        mock_adapter.return_value = mock_adapter_instance

        client = self.MockClient()

        session_args = {
            "base_url": "http://test.terraform.io/api/v2",
            "validate_certs": False,
        }

        result = client.create_session(**session_args)

        assert mock_session_instance.verify is False
        mock_session_instance.mount.assert_called_once_with("http://", mock_adapter_instance)

    def test_sanitize_response_nested_structures(self):
        """Test sanitizing response with deeply nested structures."""
        mixin = ClientMixin()
        response = {
            "data": {
                "id": "123",
                "attributes": {
                    "name": "test",
                    "secret": "hidden",
                    "nested": {"id": "456", "value": "keep", "private": "remove"},
                },
                "relationships": {"parent": {"data": {"id": "789", "type": "parent"}}},
            }
        }
        keys_to_include = ["id", "name", "value", "data", "type"]

        result = mixin.sanitize_response(response, keys_to_include)

        assert result["data"]["id"] == "123"
        assert result["data"]["attributes"]["name"] == "test"
        assert result["data"]["attributes"]["nested"]["id"] == "456"
        assert result["data"]["attributes"]["nested"]["value"] == "keep"
        assert result["data"]["relationships"]["parent"]["data"]["id"] == "789"
        assert result["data"]["relationships"]["parent"]["data"]["type"] == "parent"
        assert "secret" not in result["data"]["attributes"]
        assert "private" not in result["data"]["attributes"]["nested"]

    def test_sanitize_response_mixed_list_dict(self):
        """Test sanitizing response with mixed list and dict structures."""
        mixin = ClientMixin()
        response = {
            "items": [
                {"id": "1", "name": "item1", "secret": "hidden1"},
                {"id": "2", "name": "item2", "secret": "hidden2"},
            ],
            "meta": {"count": 2, "private": "remove"},
        }
        keys_to_include = ["id", "name", "count", "items", "meta"]

        result = mixin.sanitize_response(response, keys_to_include)

        assert len(result["items"]) == 2
        assert result["items"][0]["id"] == "1"
        assert result["items"][0]["name"] == "item1"
        assert result["meta"]["count"] == 2
        assert "secret" not in result["items"][0]
        assert "private" not in result["meta"]

    def test_make_request_decorator_non_json_response(self):
        """Test make_request decorator with non-JSON response."""
        client = self.MockClient()
        client.session.headers = {"Content-Type": "text/plain"}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"plain text response"

        client.session.request.return_value = mock_response

        result = client.get("/test")

        assert result == {"status": 200, "data": b"plain text response"}

    def test_make_request_decorator_empty_response(self):
        """Test make_request decorator with empty response."""
        client = self.MockClient()

        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.content = b""

        client.session.request.return_value = mock_response

        result = client.get("/test")

        assert result == {"status": 204, "data": b""}

    def test_make_request_decorator_status_edge_cases(self):
        """Test make_request decorator with edge case status codes."""
        client = self.MockClient()

        # Test 199 (should fail)
        mock_response = Mock()
        mock_response.status_code = 199
        mock_response.reason = "Unknown"
        client.session.request.return_value = mock_response

        with pytest.raises(AnsibleError, match="Failed to GET /test: Unknown \\(199\\)"):
            client.get("/test")

        # Test 300 (should fail)
        mock_response.status_code = 300
        mock_response.reason = "Multiple Choices"
        client.session.request.return_value = mock_response

        with pytest.raises(AnsibleError, match="Failed to GET /test: Multiple Choices \\(300\\)"):
            client.get("/test")

        # Test 299 (should succeed)
        mock_response.status_code = 299
        mock_response.content = b'{"success": true}'
        client.session.request.return_value = mock_response

        result = client.get("/test")
        assert result == {"status": 299, "data": {"success": True}}
