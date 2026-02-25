# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
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

        AnsibleTerraformModule(argument_spec=custom_argspec, supports_check_mode=True, required_together=[["workspace", "organization"]])

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


class TestTerraformClientCleanup:
    """Test TerraformClient cleanup method."""

    def test_cleanup_handles_no_client(self):
        """Test cleanup handles case when client was never created."""
        client = TerraformClient(tfe_token="test-token")

        # Don't access client, just call cleanup
        client.cleanup()  # Should not raise error

        assert client._client is None
        assert client._config is None
