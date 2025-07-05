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
