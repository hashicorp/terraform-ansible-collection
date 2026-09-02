# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/registry_provider_platform.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider_platform import (
    create_registry_provider_platform,
    delete_registry_provider_platform,
    get_registry_provider_platform,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider_platform"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


_PLATFORM_PARAMS = {
    "organization": "my-org",
    "provider_name": "aws",
    "namespace": "my-org",
    "registry_name": "private",
    "version": "1.0.0",
    "os": "linux",
    "arch": "amd64",
    "shasum": "abc123def456abc123def456abc123def456abc123def456abc123def456abc123",
    "filename": "terraform-provider-aws_1.0.0_linux_amd64.zip",
}


class TestGetRegistryProviderPlatform:
    @patch(f"{MU_PATH}.RegistryProviderPlatformID")
    @patch(f"{MU_PATH}.RegistryName")
    def test_success(self, mock_registry_name, mock_id_cls):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id
        adapter.client.registry_provider_platforms.read.return_value = _make_model(
            {
                "id": "provpltfm-1",
                "os": "linux",
                "arch": "amd64",
                "filename": "terraform-provider-aws_1.0.0_linux_amd64.zip",
                "shasum": "abc123",
            }
        )

        result = get_registry_provider_platform(adapter, _PLATFORM_PARAMS)

        assert result == {
            "id": "provpltfm-1",
            "os": "linux",
            "arch": "amd64",
            "filename": "terraform-provider-aws_1.0.0_linux_amd64.zip",
            "shasum": "abc123",
        }
        adapter.client.registry_provider_platforms.read.assert_called_once_with(mock_id)

    @patch(f"{MU_PATH}.RegistryProviderPlatformID")
    @patch(f"{MU_PATH}.RegistryName")
    def test_not_found_returns_none(self, mock_registry_name, mock_id_cls):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id
        adapter.client.registry_provider_platforms.read.side_effect = NotFound("missing")

        result = get_registry_provider_platform(adapter, _PLATFORM_PARAMS)

        assert result is None


class TestCreateRegistryProviderPlatform:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryProviderVersionID")
    @patch(f"{MU_PATH}.RegistryProviderPlatformCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_version_id_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_version_id = Mock()
        mock_version_id_cls.return_value = mock_version_id
        mock_safe_call.return_value = _make_model(
            {
                "id": "provpltfm-1",
                "os": "linux",
                "arch": "amd64",
                "filename": "terraform-provider-aws_1.0.0_linux_amd64.zip",
                "shasum": "abc123",
            }
        )

        result = create_registry_provider_platform(adapter, _PLATFORM_PARAMS)

        mock_opts_cls.model_validate.assert_called_once_with(
            {
                "os": "linux",
                "arch": "amd64",
                "shasum": "abc123def456abc123def456abc123def456abc123def456abc123def456abc123",
                "filename": "terraform-provider-aws_1.0.0_linux_amd64.zip",
            }
        )
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_provider_platforms.create
        assert args[1] is mock_version_id
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {
            "id": "provpltfm-1",
            "os": "linux",
            "arch": "amd64",
            "filename": "terraform-provider-aws_1.0.0_linux_amd64.zip",
            "shasum": "abc123",
        }


class TestDeleteRegistryProviderPlatform:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryProviderPlatformID")
    @patch(f"{MU_PATH}.RegistryName")
    def test_delete(self, mock_registry_name, mock_id_cls, mock_safe_call):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id

        delete_registry_provider_platform(adapter, _PLATFORM_PARAMS)

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_provider_platforms.delete
        assert args[1] is mock_id
        assert "error_context" in kwargs
