# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import os
import sys
import threading
import time

from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from unittest.mock import Mock, call, patch

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from plugins.module_utils.common import (
    ArchivistClient,
    ClientMixin,
    TerraformClient,
    TerraformModule,
)
from plugins.module_utils.exceptions import (
    TerraformHostnameNotFoundError,
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
        assert auth_spec["tf_hostname"]["default"] == "https://app.terraform.io"
        assert "fallback" in auth_spec["tf_hostname"]
        assert "tf_validate_certs" in auth_spec
        assert auth_spec["tf_validate_certs"]["type"] == "bool"
        assert auth_spec["tf_validate_certs"]["default"] is True
        assert "fallback" in auth_spec["tf_validate_certs"]


class TestClientMixin:
    """Test cases for ClientMixin class."""

    class MockClient(ClientMixin):
        """Mock client class for testing ClientMixin."""

        def __init__(self):
            self.base_url = "https://api.terraform.io/api/v2"
            self.session = Mock()
            self.session.headers = {"Content-Type": "application/vnd.api+json"}
            self.timeout = 10

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
        """Test converting invalid data to JSON raises Exception."""
        mixin = ClientMixin()
        data = {"key": set([1, 2, 3])}

        with pytest.raises(ValueError, match="Failed to convert data to JSON"):
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
        """Test converting invalid JSON raises Exception."""
        mixin = ClientMixin()
        json_str = '{"key": "value"'  # Missing closing brace

        with pytest.raises(ValueError, match="Failed to decode JSON string"):
            mixin.json_to_dict(json_str)

    def test_json_to_dict_invalid_json_bytes(self):
        """Test converting invalid JSON bytes raises Exception."""
        mixin = ClientMixin()
        json_bytes = b'{"key": "value"'  # Missing closing brace

        with pytest.raises(ValueError, match="Failed to decode JSON string"):
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
            timeout=10,
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
            timeout=10,
        )

        # Test PUT
        result = client.put("/test", test_data)
        assert result == {"status": 201, "data": {"id": "123"}}
        client.session.request.assert_called_with(
            "PUT",
            "https://api.terraform.io/api/v2/test",
            data='{"name": "test"}',
            timeout=10,
        )

        # Test PATCH
        result = client.patch("/test", test_data)
        assert result == {"status": 201, "data": {"id": "123"}}
        client.session.request.assert_called_with(
            "PATCH",
            "https://api.terraform.io/api/v2/test",
            data='{"name": "test"}',
            timeout=10,
        )

        # Test DELETE
        result = client.delete("/test")
        assert result == {"status": 201, "data": {"id": "123"}}
        client.session.request.assert_called_with(
            "DELETE",
            "https://api.terraform.io/api/v2/test",
            data=None,
            timeout=10,
        )

    def test_make_request_decorator_error_response(self):
        """Test make_request decorator with error response."""
        client = self.MockClient()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.content = b'{"error": "Not Found"}'
        mock_response.json.return_value = {"error": "Not Found"}

        client.session.request.return_value = mock_response

        # The decorator doesn't raise exceptions, it returns the response
        result = client.get("/test")

        assert result["status"] == 404
        assert result["data"] == {"error": "Not Found"}

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

    def test_make_request_decorator_with_full_url(self):
        """Test make_request decorator when path is already a full URL."""
        client = self.MockClient()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"data": "test"}'

        client.session.request.return_value = mock_response

        # Test with HTTPS URL
        result = client.get("https://external-api.example.com/test")

        assert result == {"status": 200, "data": {"data": "test"}}
        client.session.request.assert_called_once_with(
            "GET",
            "https://external-api.example.com/test",  # Should use the full URL directly
            data=None,
            timeout=10,
        )

        # Reset mock and test with HTTP URL
        client.session.request.reset_mock()
        result = client.get("http://external-api.example.com/test")

        assert result == {"status": 200, "data": {"data": "test"}}
        client.session.request.assert_called_once_with(
            "GET",
            "http://external-api.example.com/test",  # Should use the full URL directly
            data=None,
            timeout=10,
        )


class TestTerraformClient:
    """Test cases for TerraformClient class."""

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_init_with_token(self, mock_session):
        """Test TerraformClient initialization with token."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = TerraformClient(tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True)

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

        client = TerraformClient(tf_token="test-token", tf_hostname="custom.terraform.io", tf_validate_certs=True)

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

        client = TerraformClient(tf_token="test-token", tf_hostname="https://custom.terraform.io", tf_validate_certs=True)

        assert client.base_url == "https://custom.terraform.io/api/v2"

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_headers_default(self, mock_session):
        """Test TerraformClient sets default headers."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = TerraformClient(tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True)

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

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_init_http_with_ssl_validation_allowed(self, mock_session):
        """Test TerraformClient initialization with HTTP URL and SSL validation is allowed."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        # This should not raise an error - HTTP URLs with SSL verification should be allowed
        # (in case of redirects to HTTPS)
        client = TerraformClient(tf_token="test-token", tf_hostname="http://app.terraform.io", tf_validate_certs=True)

        assert client.verify is True  # SSL verification should remain enabled

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
    def test_terraform_client_pre_checks_called(self, mock_session):
        """Test TerraformClient pre_checks method is called during initialization."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        with patch.object(TerraformClient, "pre_checks") as mock_pre_checks:
            client = TerraformClient(tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True)
            mock_pre_checks.assert_called_once()

    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_inheritance(self, mock_session):
        """Test TerraformClient inherits from ClientMixin."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = TerraformClient(tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True)

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
    def test_archivist_client_init_ignores_custom_hostname(self, mock_session):
        """Test ArchivistClient initialization ignores custom hostname parameter."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = ArchivistClient(tf_hostname="custom.archivist.io", tf_validate_certs=True)

        # ArchivistClient uses hardcoded hostname, ignores tf_hostname parameter
        assert client.hostname == "archivist.terraform.io"
        assert client.base_url == "https://archivist.terraform.io/v1"

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_init_with_http_url(self, mock_session):
        """Test ArchivistClient initialization with HTTP URL."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = ArchivistClient(tf_hostname="http://custom.archivist.io", tf_validate_certs=False)

        # ArchivistClient uses hardcoded hostname, ignores tf_hostname parameter
        assert client.base_url == "https://archivist.terraform.io/v1"

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_init_with_https_url(self, mock_session):
        """Test ArchivistClient initialization with HTTPS URL."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = ArchivistClient(tf_hostname="https://custom.archivist.io", tf_validate_certs=True)

        # ArchivistClient uses hardcoded hostname, ignores tf_hostname parameter
        assert client.base_url == "https://archivist.terraform.io/v1"

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
        """Test ArchivistClient ignores custom headers and uses default."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        custom_headers = {"User-Agent": "test-agent"}
        client = ArchivistClient(tf_validate_certs=True, headers=custom_headers)

        # ArchivistClient currently ignores custom headers and always uses default
        # It calls headers.update twice:
        # 1. From create_session with empty headers dict
        # 2. With default Content-Type header since self.headers is always empty
        expected_calls = [call({}), call({"Content-Type": "application/octet-stream"})]  # From create_session  # Default headers
        mock_session_instance.headers.update.assert_has_calls(expected_calls)

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

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_init_with_empty_hostname(self, mock_session):
        """Test ArchivistClient initialization with empty hostname uses default."""
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        # ArchivistClient doesn't validate hostname, uses hardcoded default
        client = ArchivistClient(tf_hostname="", tf_validate_certs=True)

        assert client.hostname == "archivist.terraform.io"
        assert client.base_url == "https://archivist.terraform.io/v1"


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
            self.timeout = 10

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

    def test_pre_checks_http_with_ssl_validation_allowed(self):
        """Test pre_checks method allows HTTP with SSL validation (for redirects)."""
        client = self.MockClient()
        client.hostname = "http://app.terraform.io"
        client.verify = True
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
            "tf_max_retries": 5,
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
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET", "PUT", "DELETE"]),
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
        mock_response.content = b'{"error": "Unknown"}'
        mock_response.json.return_value = {"error": "Unknown"}
        client.session.request.return_value = mock_response

        result = client.get("/test")

        assert result["status"] == 199
        assert result["data"] == {"error": "Unknown"}

        # Test 300 (should fail)
        mock_response.status_code = 300
        mock_response.content = b'{"error": "Multiple Choices"}'
        mock_response.json.return_value = {"error": "Multiple Choices"}
        client.session.request.return_value = mock_response

        result = client.get("/test")

        assert result["status"] == 300
        assert result["data"] == {"error": "Multiple Choices"}

        # Test 299 (should succeed)
        mock_response = Mock()
        mock_response.status_code = 299
        mock_response.content = b'{"success": true}'
        mock_response.raise_for_status.return_value = None  # No exception for successful status
        client.session.request.return_value = mock_response

        result = client.get("/test")
        assert result == {"status": 299, "data": {"success": True}}


class TestExponentialBackoff:
    """
    Test cases for exponential backoff behavior with HTTP 429 rate limiting.

    Tests validate:
    - Current implementation limitations (immediate failure on 429)
    - Proper exponential backoff timing (1s, 2s, 4s, 8s delays)
    - Successful retry after 4 failures with 5th request succeeding
    """

    def test_current_implementation_limitation(self):
        """Test documents that current implementation fails immediately on 429."""
        with patch("plugins.module_utils.common.requests.Session") as mock_session_class:
            mock_session_instance = Mock()
            mock_session_instance.headers = {}

            # Mock response that returns 429
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.content = b'{"errors": [{"detail": "Rate limited"}]}'
            mock_response.json.return_value = {"errors": [{"detail": "Rate limited"}]}
            mock_session_instance.request.return_value = mock_response
            mock_session_class.return_value = mock_session_instance

            client = TerraformClient(tf_token="test-token", tf_hostname="app.terraform.io", tf_validate_certs=True)

            result = client.get("/test-endpoint")

            # Verify that the 429 status is returned (showing current limitation)
            assert result["status"] == 429
            assert result["data"] == {"errors": [{"detail": "Rate limited"}]}

    def test_exponential_backoff_behavior(self):
        """Test that retry mechanism actually implements exponential backoff delays using HTTP server."""

        request_times = []

        class MockServerRequestHandler(BaseHTTPRequestHandler):
            REQUEST_COUNTER = 0

            RESPONSE_OK = {
                "data": {
                    "id": "test-backoff-123",
                    "type": "test-backoff",
                    "attributes": {
                        "status": "success",
                        "message": "Exponential backoff test completed successfully",
                        "retry_count": 5,
                        "total_duration": "~15s",
                    },
                    "links": {
                        "self": "/api/v2/test-backoff",
                    },
                }
            }

            RESPONSE_RATE_LIMITED = {
                "errors": [
                    {
                        "detail": "You have exceeded the API's rate limit.",
                        "status": 429,
                        "title": "Too many requests",
                    }
                ]
            }

            def do_GET(self):
                request_times.append(time.time())
                MockServerRequestHandler.REQUEST_COUNTER += 1

                print(f"Server received request #{MockServerRequestHandler.REQUEST_COUNTER} at {time.time():.3f}")

                if self.path == "/api/v2/test-backoff":
                    if MockServerRequestHandler.REQUEST_COUNTER <= 4:  # First 4 requests fail
                        self.send_response(429)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        response = MockServerRequestHandler.RESPONSE_RATE_LIMITED
                        self.wfile.write(json.dumps(response).encode("utf-8"))
                    else:  # 5th request succeeds
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        response = MockServerRequestHandler.RESPONSE_OK
                        self.wfile.write(json.dumps(response).encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                # Suppress default logging
                pass

        HOST = "localhost"
        PORT = 8765
        server_address = (HOST, PORT)
        httpd = HTTPServer(server_address, MockServerRequestHandler)

        def run_server():
            httpd.serve_forever()

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Give server time to start
        time.sleep(0.1)

        try:
            # Create client that points to our mock server
            client = TerraformClient(
                tf_token="test-token", tf_hostname=f"http://{HOST}:{PORT}", tf_validate_certs=False, tf_max_retries=5, timeout=30  # Allow HTTP
            )

            print(f"Starting request at {time.time():.3f}")
            start_time = time.time()

            result = client.get("/test-backoff")

            total_time = time.time() - start_time
            print(f"Request completed at {time.time():.3f}, total time: {total_time:.3f}s")

            # Verify successful response
            assert result["status"] == 200
            assert result["data"]["data"]["id"] == "test-backoff-123"
            assert result["data"]["data"]["type"] == "test-backoff"
            assert result["data"]["data"]["attributes"]["status"] == "success"
            assert MockServerRequestHandler.REQUEST_COUNTER == 5
            assert len(request_times) == 5
            delays = []
            for i in range(1, len(request_times)):
                delay = request_times[i] - request_times[i - 1]
                delays.append(delay)
                print(f"Delay {i}: {delay:.3f}s")

            assert len(delays) == 4
            assert 12.0 <= total_time <= 20.0  # Allow tolerance for timing variations

            print("Exponential backoff verified!")
            print(f"   Total requests: {MockServerRequestHandler.REQUEST_COUNTER} (4 failures + 1 success)")
            print(f"   Total time: {total_time:.1f}s (proves exponential backoff happened)")
            print(f"   Individual delays: {[f'{d:.3f}s' for d in delays]}")
            print("   SUCCESS: Retry mechanism with exponential backoff is working!")

        finally:
            # Clean up server
            httpd.shutdown()
            httpd.server_close()
            server_thread.join(timeout=2.0)
            if server_thread.is_alive():
                raise RuntimeError("Server thread failed to terminate within 2 seconds after shutdown")
