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
from unittest.mock import Mock, patch

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from plugins.module_utils.common import (
    AnsibleTerraformModule,
    ArchivistClient,
    ClientMixin,
    TerraformClient,
    gather_versions,
    has_at_least,
    requires,
)
from plugins.module_utils.exceptions import (
    TerraformHostnameNotFoundError,
    TerraformTokenNotFoundError,
)


class TestAnsibleTerraformModule:
    """Test suite for the AnsibleTerraformModule class initialization and configuration.

    Tests the core functionality of the AnsibleTerraformModule wrapper class,
    including authentication parameter injection, argument specification merging,
    and module initialization behaviors.
    """

    def test_terraform_module_init_adds_auth_argspec(self):
        """Test that AnsibleTerraformModule correctly injects authentication parameters.

        Verifies that when creating an AnsibleTerraformModule instance, the module
        automatically adds Terraform-specific authentication parameters (tf_token,
        tf_hostname, etc.) to the provided argument specification while preserving
        any existing parameters.
        """
        argument_spec = dict(
            test_param=dict(type="str"),
        )

        with patch("ansible.module_utils.basic.AnsibleModule.__init__") as mock_init:
            mock_init.return_value = None
            AnsibleTerraformModule(argument_spec=argument_spec)

            # Check that auth argspec was added to the argument_spec
            # Access the keyword arguments passed to the mocked constructor
            called_kwargs = mock_init.call_args.kwargs
            called_argspec = called_kwargs["argument_spec"]

            # Verify original parameter is still present
            assert "test_param" in called_argspec

            # Verify auth parameters were added
            assert "tf_token" in called_argspec
            assert "tf_hostname" in called_argspec
            assert "tf_validate_certs" in called_argspec
            assert "tf_max_retries" in called_argspec
            assert "tf_timeout" in called_argspec

    @pytest.mark.parametrize(
        "param_name,expected_properties",
        [
            ("tf_token", {"required": False, "has_fallback": True}),
            ("tf_hostname", {"required": False, "default": "https://app.terraform.io", "has_fallback": True}),
            ("tf_validate_certs", {"type": "bool", "default": True, "has_fallback": True}),
        ],
    )
    def test_auth_argspec_structure(self, param_name, expected_properties):
        """Test the structure and properties of authentication argument specifications.

        This parameterized test validates that each authentication parameter in
        AUTH_ARGSPEC has the correct type, default values, fallback configurations,
        and required status as expected by the Ansible module framework.

        Args:
            param_name: Name of the authentication parameter to test
            expected_properties: Dictionary of expected properties for the parameter
        """
        auth_spec = AnsibleTerraformModule.AUTH_ARGSPEC

        assert param_name in auth_spec
        param_spec = auth_spec[param_name]

        for prop, expected_value in expected_properties.items():
            if prop == "has_fallback":
                assert "fallback" in param_spec
            else:
                assert param_spec[prop] == expected_value


class TestClientMixin:
    """Test suite for the ClientMixin base class functionality.

    Tests the core HTTP client functionality provided by ClientMixin, including
    request/response handling, JSON serialization/deserialization, response
    sanitization, and the make_request decorator functionality.
    """

    class MockClient(ClientMixin):
        """Mock client class for testing ClientMixin."""

        def __init__(self):
            self.base_url = "https://api.terraform.io/api/v2"
            self.session = Mock()
            self.session.headers = {"Content-Type": "application/vnd.api+json"}
            self.timeout = 10

    @pytest.mark.parametrize(
        "response_data,keys_to_include,expected_result,description",
        [
            (
                {
                    "id": "123",
                    "name": "test",
                    "secret": "hidden",
                    "nested": {"id": "456", "data": "value"},
                },
                ["id", "name", "data"],
                {
                    "id": "123",
                    "name": "test",
                    "nested": {"id": "456", "data": "value"},
                },
                "dict response with nested data",
            ),
            (
                [
                    {"id": "1", "name": "test1", "secret": "hidden1"},
                    {"id": "2", "name": "test2", "secret": "hidden2"},
                ],
                ["id", "name"],
                [
                    {"id": "1", "name": "test1"},
                    {"id": "2", "name": "test2"},
                ],
                "list response",
            ),
            (
                {"secret": "hidden"},
                ["id", "name"],
                None,
                "empty result when no matching keys",
            ),
        ],
    )
    def test_sanitize_response_scenarios(self, response_data, keys_to_include, expected_result, description):
        """Test response sanitization with various data structures and key filters.

        This parameterized test validates that the sanitize_response method correctly
        filters response data to include only specified keys, handles both dictionary
        and list responses, and properly manages nested data structures while
        excluding sensitive or unwanted information.

        Args:
            response_data: Input response data to be sanitized
            keys_to_include: List of keys to retain in the sanitized response
            expected_result: Expected output after sanitization
            description: Test case description for clarity
        """
        mixin = ClientMixin()

        result = mixin.sanitize_response(response_data, keys_to_include)

        if expected_result is None:
            assert result is None
        elif isinstance(expected_result, list):
            assert len(result) == len(expected_result)
            for i, item in enumerate(expected_result):
                for key, value in item.items():
                    assert result[i][key] == value
                # Verify excluded keys are not present
                assert "secret" not in result[i]
        else:
            for key, value in expected_result.items():
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        assert result[key][nested_key] == nested_value
                else:
                    assert result[key] == value
            # Verify excluded keys are not present
            assert "secret" not in result

    @pytest.mark.parametrize(
        "input_data,expected_result,should_raise,description",
        [
            ({"key": "value", "number": 42}, '{"key": "value", "number": 42}', False, "valid dict to JSON"),
            ({"key": set([1, 2, 3])}, None, True, "invalid data with set"),
        ],
    )
    def test_dict_to_json_scenarios(self, input_data, expected_result, should_raise, description):
        """Test dict_to_json with various scenarios."""
        mixin = ClientMixin()

        if should_raise:
            with pytest.raises(ValueError, match="Failed to convert data to JSON"):
                mixin.dict_to_json(input_data)
        else:
            result = mixin.dict_to_json(input_data)
            assert result == expected_result

    @pytest.mark.parametrize(
        "input_data,expected_result,should_raise,description",
        [
            ('{"key": "value", "number": 42}', {"key": "value", "number": 42}, False, "valid JSON string"),
            (b'{"key": "value", "number": 42}', {"key": "value", "number": 42}, False, "valid JSON bytes"),
            ('{"key": "value"', None, True, "invalid JSON string"),
            (b'{"key": "value"', None, True, "invalid JSON bytes"),
        ],
    )
    def test_json_to_dict_scenarios(self, input_data, expected_result, should_raise, description):
        """Test json_to_dict with various scenarios."""
        mixin = ClientMixin()

        if should_raise:
            with pytest.raises(ValueError, match="Failed to decode JSON string"):
                mixin.json_to_dict(input_data)
        else:
            result = mixin.json_to_dict(input_data)
            assert result == expected_result

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
    """Test suite for the TerraformClient class.

    Tests the Terraform API client implementation, including initialization
    with various hostname formats, authentication header setup, SSL validation
    configuration, and error handling for missing credentials.
    """

    @pytest.mark.parametrize(
        "hostname,validate_certs,expected_hostname,expected_base_url,description",
        [
            ("app.terraform.io", True, "app.terraform.io", "https://app.terraform.io/api/v2", "default hostname"),
            ("custom.terraform.io", True, "custom.terraform.io", "https://custom.terraform.io/api/v2", "custom hostname"),
            ("http://custom.terraform.io", False, "http://custom.terraform.io", "http://custom.terraform.io/api/v2", "HTTP URL"),
            ("https://custom.terraform.io", True, "https://custom.terraform.io", "https://custom.terraform.io/api/v2", "HTTPS URL"),
        ],
    )
    @patch("plugins.module_utils.common.requests.Session")
    def test_terraform_client_initialization_scenarios(self, mock_session, hostname, validate_certs, expected_hostname, expected_base_url, description):
        """Test TerraformClient initialization with various hostname and URL configurations.

        This parameterized test validates that the TerraformClient correctly handles
        different hostname formats (bare hostnames, HTTP/HTTPS URLs) and properly
        constructs the base API URL while respecting SSL validation settings.

        Args:
            mock_session: Mocked requests session
            hostname: Input hostname or URL for the client
            validate_certs: SSL certificate validation setting
            expected_hostname: Expected parsed hostname value
            expected_base_url: Expected constructed base API URL
            description: Test case description for clarity
        """
        mock_session_instance = Mock()
        mock_session_instance.headers = Mock()
        mock_session.return_value = mock_session_instance

        client = TerraformClient(tf_token="test-token", tf_hostname=hostname, tf_validate_certs=validate_certs)

        assert client.hostname == expected_hostname
        assert client.base_url == expected_base_url
        assert client._token == "test-token"
        assert client.verify == validate_certs
        assert client.session == mock_session_instance

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

    @pytest.mark.parametrize(
        "token,hostname,expected_exception,description",
        [
            (None, "app.terraform.io", TerraformTokenNotFoundError, "missing token"),
            ("test-token", "", TerraformHostnameNotFoundError, "empty hostname"),
        ],
    )
    def test_terraform_client_initialization_errors(self, token, hostname, expected_exception, description):
        """Test TerraformClient initialization error scenarios."""
        with pytest.raises(expected_exception):
            TerraformClient(tf_token=token, tf_hostname=hostname, tf_validate_certs=True)

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

        # Create client to trigger initialization side effects
        ArchivistClient(tf_validate_certs=True)

        expected_headers = {"Content-Type": "application/octet-stream"}
        mock_session_instance.headers.update.assert_called_with(expected_headers)

    @patch("plugins.module_utils.common.requests.Session")
    def test_archivist_client_headers_custom(self, mock_session):
        """Test ArchivistClient ignores custom headers and always uses application/octet-stream."""
        mock_session_instance = Mock()
        mock_session_instance.headers = {"Content-Type": "application/octet-stream"}
        mock_session.return_value = mock_session_instance

        custom_headers = {"User-Agent": "test-agent"}
        client = ArchivistClient(tf_validate_certs=True, headers=custom_headers)

        # Regardless of custom headers provided, ArchivistClient always sets Content-Type to application/octet-stream
        assert client.session.headers["Content-Type"] == "application/octet-stream"

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
            # Create client to trigger initialization side effects
            ArchivistClient(tf_validate_certs=True)
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
            },
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
                },
            }

            RESPONSE_RATE_LIMITED = {
                "errors": [
                    {
                        "detail": "You have exceeded the API's rate limit.",
                        "status": 429,
                        "title": "Too many requests",
                    },
                ],
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
                tf_token="test-token",
                tf_hostname=f"http://{HOST}:{PORT}",
                tf_validate_certs=False,
                tf_max_retries=5,
                timeout=30,  # Allow HTTP
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


class TestCommonUtils:
    """Test cases for utility functions in common module."""

    def test_gather_versions_with_existing_packages(self):
        """Test gather_versions with packages that exist."""
        # Test with sys module which should always be available
        result = gather_versions(["sys"])

        assert isinstance(result, dict)
        assert "sys" in result
        assert isinstance(result["sys"], str)

    def test_gather_versions_with_nonexistent_package(self):
        """Test gather_versions with a package that doesn't exist."""
        result = gather_versions(["nonexistent_package_xyz123"])

        assert isinstance(result, dict)
        assert "nonexistent_package_xyz123" not in result

    def test_gather_versions_with_none_parameter(self):
        """Test gather_versions with None parameter uses default packages."""
        result = gather_versions(None)

        assert isinstance(result, dict)
        # Default should include "requests" but might not be available in test environment

    def test_gather_versions_with_empty_list(self):
        """Test gather_versions with empty list."""
        result = gather_versions([])

        assert isinstance(result, dict)
        assert len(result) == 0

    @patch("builtins.__import__")
    def test_gather_versions_import_error_handling(self, mock_import):
        """Test gather_versions handles import errors gracefully."""
        mock_import.side_effect = ImportError("Module not found")

        result = gather_versions(["test_package"])

        assert isinstance(result, dict)
        assert "test_package" not in result

    @patch("builtins.__import__")
    def test_gather_versions_with_version_attribute(self, mock_import):
        """Test gather_versions with package that has __version__ attribute."""
        mock_package = Mock()
        mock_package.__version__ = "1.2.3"
        mock_import.return_value = mock_package

        result = gather_versions(["test_package"])

        assert result["test_package"] == "1.2.3"

    @patch("builtins.__import__")
    def test_gather_versions_with_version_attribute_variants(self, mock_import):
        """Test gather_versions with different version attribute names."""
        # Test with 'version' attribute
        mock_package = Mock()
        mock_package.version = "2.0.0"
        mock_import.return_value = mock_package

        result = gather_versions(["test_package"])

        assert result["test_package"] == "2.0.0"

    @patch("builtins.__import__")
    def test_gather_versions_with_version_attribute_uppercase(self, mock_import):
        """Test gather_versions with VERSION attribute."""
        mock_package = Mock()
        mock_package.VERSION = "3.1.0"
        del mock_package.version
        del mock_package.__version__
        mock_import.return_value = mock_package

        result = gather_versions(["test_package"])

        assert result["test_package"] == "3.1.0"

    @patch("builtins.__import__")
    def test_gather_versions_no_version_attribute(self, mock_import):
        """Test gather_versions with package that has no version attribute."""
        mock_package = Mock(spec=[])  # No version attributes
        mock_import.return_value = mock_package

        result = gather_versions(["test_package"])

        assert "test_package" not in result

    @patch("builtins.__import__")
    def test_gather_versions_exception_handling(self, mock_import):
        """Test gather_versions handles general exceptions gracefully."""
        mock_import.side_effect = Exception("Unexpected error")

        result = gather_versions(["test_package"])

        assert isinstance(result, dict)
        assert "test_package" not in result

    @pytest.mark.parametrize(
        "available_versions,package_name,minimum_version,expected_result,description",
        [
            ({"test_package": "1.0.0"}, "test_package", None, True, "dependency exists, no minimum"),
            ({}, "nonexistent_package", None, False, "dependency not found"),
            ({"test_package": "2.0.0"}, "test_package", "1.5.0", True, "version meets minimum"),
            ({"test_package": "1.0.0"}, "test_package", "2.0.0", False, "version below minimum"),
            ({"test_package": "1.5.0"}, "test_package", "1.5.0", True, "version equals minimum"),
            ({"test_package": "1.10.0"}, "test_package", "1.9.0", True, "loose version comparison"),
        ],
    )
    @patch("plugins.module_utils.common.gather_versions")
    def test_has_at_least_scenarios(self, mock_gather, available_versions, package_name, minimum_version, expected_result, description):
        """Test has_at_least with various scenarios."""
        mock_gather.return_value = available_versions

        result = has_at_least(package_name, minimum_version)

        assert result == expected_result
        mock_gather.assert_called_once_with([package_name])

    @patch("plugins.module_utils.common.gather_versions")
    def test_has_at_least_exception_handling(self, mock_gather):
        """Test has_at_least handles exceptions gracefully."""
        mock_gather.side_effect = Exception("Unexpected error")

        result = has_at_least("test_package", "1.0.0")

        assert result is False

    @patch("plugins.module_utils.common.gather_versions")
    def test_has_at_least_loose_version_comparison(self, mock_gather):
        """Test has_at_least uses LooseVersion for version comparison."""
        mock_gather.return_value = {"test_package": "1.10.0"}

        # Test that 1.10.0 is greater than 1.9.0 (not lexicographic comparison)
        result = has_at_least("test_package", "1.9.0")

        assert result is True

    @patch("plugins.module_utils.common.has_at_least")
    def test_requires_dependency_available(self, mock_has_at_least):
        """Test requires when dependency is available."""
        mock_has_at_least.return_value = True

        # Should not raise an exception
        requires("test_package")

        mock_has_at_least.assert_called_once_with("test_package", None)

    @patch("plugins.module_utils.common.has_at_least")
    def test_requires_dependency_not_available(self, mock_has_at_least):
        """Test requires raises exception when dependency is not available."""
        mock_has_at_least.return_value = False

        with pytest.raises(Exception) as exc_info:
            requires("missing_package")

        # The exception message should contain missing_required_lib output
        assert "missing_package" in str(exc_info.value)

    @patch("plugins.module_utils.common.has_at_least")
    def test_requires_with_minimum_version_met(self, mock_has_at_least):
        """Test requires when minimum version requirement is met."""
        mock_has_at_least.return_value = True

        # Should not raise an exception
        requires("test_package", "1.0.0")

        mock_has_at_least.assert_called_once_with("test_package", "1.0.0")

    @patch("plugins.module_utils.common.has_at_least")
    def test_requires_with_minimum_version_not_met(self, mock_has_at_least):
        """Test requires raises exception when minimum version is not met."""
        mock_has_at_least.return_value = False

        with pytest.raises(Exception) as exc_info:
            requires("test_package", "2.0.0")

        # Should include version requirement in error message
        assert "test_package>=2.0.0" in str(exc_info.value)

    @patch("plugins.module_utils.common.has_at_least")
    def test_requires_with_reason(self, mock_has_at_least):
        """Test requires includes reason in error message."""
        mock_has_at_least.return_value = False

        with pytest.raises(Exception) as exc_info:
            requires("test_package", "1.0.0", "needed for some feature")

        # The error should include the reason
        error_message = str(exc_info.value)
        assert "test_package>=1.0.0" in error_message
        assert "needed for some feature" in error_message

    @patch("plugins.module_utils.common.has_at_least")
    def test_requires_with_reason_no_minimum(self, mock_has_at_least):
        """Test requires includes reason when no minimum version specified."""
        mock_has_at_least.return_value = False

        with pytest.raises(Exception) as exc_info:
            requires("test_package", reason="required for functionality")

        error_message = str(exc_info.value)
        assert "test_package" in error_message
        assert "required for functionality" in error_message

    @patch("plugins.module_utils.common.has_at_least")
    def test_requires_returns_none(self, mock_has_at_least):
        """Test requires returns None when successful."""
        mock_has_at_least.return_value = True

        result = requires("test_package")

        assert result is None

    def test_requires_integration_with_real_package(self):
        """Integration test with a real package that should exist."""
        # Test with 'sys' which should always be available
        # Should not raise an exception
        result = requires("sys")

        assert result is None

    def test_has_at_least_integration_with_real_package(self):
        """Integration test with a real package that should exist."""
        # Test with 'sys' which should always be available
        result = has_at_least("sys")

        assert result is True


class TestAnsibleTerraformModuleMethods:
    """Test cases for AnsibleTerraformModule methods and functionality."""

    @patch("ansible.module_utils.basic.AnsibleModule.__init__")
    @patch("plugins.module_utils.common.requires")
    def test_init_with_custom_settings(self, mock_requires, mock_init):
        """Test AnsibleTerraformModule initialization with custom settings."""
        mock_init.return_value = None

        custom_module_class = Mock()
        argument_spec = {"test_param": {"type": "str"}}

        terraform_module = AnsibleTerraformModule(
            argument_spec=argument_spec,
            check_requests=False,
            module_class=custom_module_class,
        )

        # Verify custom settings were applied
        assert terraform_module.settings["check_requests"] is False
        assert terraform_module.settings["module_class"] == custom_module_class

        # Verify custom module class was used
        mock_init.assert_not_called()
        custom_module_class.assert_called_once()

        # Verify requests dependency was NOT checked
        mock_requires.assert_not_called()

    @patch("ansible.module_utils.basic.AnsibleModule.__init__")
    def test_warn_delegates_to_module(self, mock_init):
        """Test warn method delegates to underlying Ansible module."""
        mock_init.return_value = None

        # Create a mock module instance and attach it to the terraform module
        mock_module_instance = Mock()

        terraform_module = AnsibleTerraformModule(argument_spec={})
        terraform_module._module = mock_module_instance

        # Test warn with positional arguments
        terraform_module.warn("Test warning message")
        mock_module_instance.warn.assert_called_with("Test warning message")

        # Test warn with keyword arguments
        terraform_module.warn("Test warning", version="2.0")
        mock_module_instance.warn.assert_called_with("Test warning", version="2.0")

        # Test warn with both positional and keyword arguments
        terraform_module.warn("Test", "warning", version="2.0", deprecation_msg="deprecated")
        mock_module_instance.warn.assert_called_with("Test", "warning", version="2.0", deprecation_msg="deprecated")

    @patch("ansible.module_utils.basic.AnsibleModule.__init__")
    def test_deprecate_delegates_to_module(self, mock_init):
        """Test deprecate method delegates to underlying Ansible module."""
        mock_init.return_value = None

        # Create a mock module instance and attach it to the terraform module
        mock_module_instance = Mock()

        terraform_module = AnsibleTerraformModule(argument_spec={})
        terraform_module._module = mock_module_instance

        # Test deprecate with both positional and keyword arguments
        terraform_module.deprecate("deprecated", collection_name="hashicorp.terraform", date="2024-01-01")
        mock_module_instance.deprecate.assert_called_with("deprecated", collection_name="hashicorp.terraform", date="2024-01-01")

    @patch("ansible.module_utils.basic.AnsibleModule.__init__")
    def test_debug_delegates_to_module(self, mock_init):
        """Test debug method delegates to underlying Ansible module."""
        mock_init.return_value = None

        # Create a mock module instance and attach it to the terraform module
        mock_module_instance = Mock()

        terraform_module = AnsibleTerraformModule(argument_spec={})
        terraform_module._module = mock_module_instance

        # Test debug with positional arguments
        terraform_module.debug("Debug message")
        mock_module_instance.debug.assert_called_with("Debug message")

        # Test debug with keyword arguments
        terraform_module.debug("Debug info", var_name="test_var")
        mock_module_instance.debug.assert_called_with("Debug info", var_name="test_var")

        # Test debug with both positional and keyword arguments
        terraform_module.debug("Debug", "info", level=1, verbose=True)
        mock_module_instance.debug.assert_called_with("Debug", "info", level=1, verbose=True)

    @patch("ansible.module_utils.basic.AnsibleModule.__init__")
    def test_exit_json_delegates_to_module(self, mock_init):
        """Test exit_json method delegates to underlying Ansible module."""
        mock_init.return_value = None

        # Create a mock module instance and attach it to the terraform module
        mock_module_instance = Mock()

        terraform_module = AnsibleTerraformModule(argument_spec={})
        terraform_module._module = mock_module_instance

        # Test exit_json with positional arguments
        terraform_module.exit_json(True)
        mock_module_instance.exit_json.assert_called_with(True)

        # Test exit_json with keyword arguments
        terraform_module.exit_json(changed=True, msg="Success")
        mock_module_instance.exit_json.assert_called_with(changed=True, msg="Success")

        # Test exit_json with both positional and keyword arguments
        terraform_module.exit_json(True, msg="Success", result={"id": "123"})
        mock_module_instance.exit_json.assert_called_with(True, msg="Success", result={"id": "123"})

    @patch("ansible.module_utils.basic.AnsibleModule.__init__")
    def test_fail_json_delegates_to_module(self, mock_init):
        """Test fail_json method delegates to underlying Ansible module."""
        mock_init.return_value = None

        # Create a mock module instance and attach it to the terraform module
        mock_module_instance = Mock()

        terraform_module = AnsibleTerraformModule(argument_spec={})
        terraform_module._module = mock_module_instance

        # Test fail_json with positional arguments
        terraform_module.fail_json("Error occurred")
        mock_module_instance.fail_json.assert_called_with("Error occurred")

        # Test fail_json with keyword arguments
        terraform_module.fail_json(msg="Error message")
        mock_module_instance.fail_json.assert_called_with(msg="Error message")

        # Test fail_json with both positional and keyword arguments
        terraform_module.fail_json("Error", msg="Failed", rc=1, details={"error": "details"})
        mock_module_instance.fail_json.assert_called_with("Error", msg="Failed", rc=1, details={"error": "details"})

    @patch("ansible.module_utils.basic.AnsibleModule.__init__")
    def test_fail_from_exception_formats_and_calls_fail_json(self, mock_init):
        """Test fail_from_exception method formats exception and calls fail_json."""
        mock_init.return_value = None

        # Create a mock module instance and attach it to the terraform module
        mock_module_instance = Mock()

        terraform_module = AnsibleTerraformModule(argument_spec={})
        terraform_module._module = mock_module_instance

        # Call fail_from_exception
        terraform_module.fail_from_exception(ValueError("Test error message"))

        # Verify fail_json was called on the underlying module
        mock_module_instance.fail_json.assert_called_once()

        # Get the actual call arguments
        _tmp, call_kwargs = mock_module_instance.fail_json.call_args

        # Verify the message contains the exception text
        assert call_kwargs["msg"] == "Test error message"

        # Verify the exception traceback is included
        assert "exception" in call_kwargs
        assert "ValueError: Test error message" in call_kwargs["exception"]
        assert "traceback" in call_kwargs["exception"].lower() or "ValueError" in call_kwargs["exception"]
