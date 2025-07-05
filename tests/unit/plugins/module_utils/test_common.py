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
from plugins.module_utils.terraform import (
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

    def test_json_to_dict_invalid_json(self):
        """Test converting invalid JSON raises AnsibleError."""
        mixin = ClientMixin()
        json_str = '{"key": "value"'  # Missing closing brace

        with pytest.raises(AnsibleError, match="Failed to decode JSON string"):
            mixin.json_to_dict(json_str)

