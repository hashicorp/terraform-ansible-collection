# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/registry_provider_platform_info.py."""

from unittest.mock import Mock, patch

import pytest

MOD_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_platform_info"


@pytest.fixture
def mock_adapter():
    return Mock()


_PLATFORM_PARAMS = {
    "organization": "my-org",
    "provider_name": "aws",
    "namespace": "my-org",
    "registry_name": "private",
    "version": "1.0.0",
    "os": "linux",
    "arch": "amd64",
}


class TestRegistryProviderPlatformInfo:
    @patch(f"{MOD_PATH}.get_registry_provider_platform")
    def test_info_returns_platform(self, mock_get, mock_adapter):
        """get_registry_provider_platform returns the platform when found."""
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_platform_info import main

        platform = {
            "id": "provpltfm-1",
            "os": "linux",
            "arch": "amd64",
            "filename": "terraform-provider-aws_1.0.0_linux_amd64.zip",
            "shasum": "abc123",
        }
        mock_get.return_value = platform

        # Verify the function is called correctly
        with patch(f"{MOD_PATH}.AnsibleTerraformModule") as mock_module_cls:
            mock_module = Mock()
            mock_module.params = _PLATFORM_PARAMS
            mock_module.check_mode = False
            mock_module_cls.return_value = mock_module

            # Simulate context manager for client
            mock_adapter_instance = Mock()
            mock_module.client.return_value.__enter__ = Mock(return_value=mock_adapter_instance)
            mock_module.client.return_value.__exit__ = Mock(return_value=False)

            mock_get.return_value = platform

            main()

            mock_module.exit_json.assert_called_once()
            call_kwargs = mock_module.exit_json.call_args[1]
            assert call_kwargs["registry_provider_platform"] == platform
            assert call_kwargs["changed"] is False

    @patch(f"{MOD_PATH}.get_registry_provider_platform")
    def test_info_fails_when_not_found(self, mock_get, mock_adapter):
        """fail_json is called when platform is not found."""
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_platform_info import main

        mock_get.return_value = None

        with patch(f"{MOD_PATH}.AnsibleTerraformModule") as mock_module_cls:
            mock_module = Mock()
            mock_module.params = _PLATFORM_PARAMS
            mock_module.check_mode = False
            mock_module_cls.return_value = mock_module

            mock_adapter_instance = Mock()
            mock_module.client.return_value.__enter__ = Mock(return_value=mock_adapter_instance)
            mock_module.client.return_value.__exit__ = Mock(return_value=False)

            main()

            mock_module.fail_json.assert_called_once()
            error_msg = mock_module.fail_json.call_args[1]["msg"]
            assert "not found" in error_msg
