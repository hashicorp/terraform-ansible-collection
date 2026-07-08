# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/registry_module.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_module import (
    create_registry_module,
    create_registry_module_version,
    create_registry_module_with_vcs,
    delete_registry_module_by_name,
    delete_registry_module_provider,
    delete_registry_module_version,
    get_registry_module,
    get_registry_module_version,
    update_registry_module,
    upload_registry_module_version,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.registry_module"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestGetRegistryModule:
    @patch(f"{MU_PATH}.RegistryModuleID")
    def test_success(self, mock_id_cls):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id
        adapter.client.registry_modules.read.return_value = _make_model(
            {
                "id": "mod-1",
                "name": "vpc",
                "provider": "aws",
            }
        )

        module_id = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "registry_name": "private",
        }
        result = get_registry_module(adapter, module_id)

        assert result == {"id": "mod-1", "name": "vpc", "provider": "aws"}
        adapter.client.registry_modules.read.assert_called_once_with(mock_id)

    @patch(f"{MU_PATH}.RegistryModuleID")
    def test_not_found_returns_none(self, mock_id_cls):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id
        adapter.client.registry_modules.read.side_effect = NotFound("missing")

        module_id = {"organization": "my-org", "name": "vpc", "provider": "aws"}
        assert get_registry_module(adapter, module_id) is None


class TestGetRegistryModuleVersion:
    @patch(f"{MU_PATH}.RegistryModuleID")
    def test_success(self, mock_id_cls):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id
        adapter.client.registry_modules.read_version.return_value = _make_model(
            {
                "id": "modver-1",
                "version": "1.0.0",
            }
        )

        module_id = {"organization": "my-org", "name": "vpc", "provider": "aws"}
        result = get_registry_module_version(adapter, module_id, "1.0.0")

        assert result == {"id": "modver-1", "version": "1.0.0"}
        adapter.client.registry_modules.read_version.assert_called_once_with(mock_id, "1.0.0")

    @patch(f"{MU_PATH}.RegistryModuleID")
    def test_not_found_returns_none(self, mock_id_cls):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id
        adapter.client.registry_modules.read_version.side_effect = NotFound("missing")

        module_id = {"organization": "my-org", "name": "vpc", "provider": "aws"}
        assert get_registry_module_version(adapter, module_id, "1.0.0") is None


class TestCreateRegistryModule:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryModuleCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model(
            {
                "id": "mod-1",
                "name": "vpc",
                "provider": "aws",
            }
        )

        data = {"name": "vpc", "provider": "aws", "registry_name": "private"}
        result = create_registry_module(adapter, "my-org", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_modules.create
        assert args[1] == "my-org"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "mod-1", "name": "vpc", "provider": "aws"}


class TestCreateRegistryModuleWithVCS:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryModuleCreateWithVCSConnectionOptions")
    def test_create_with_vcs_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model(
            {
                "id": "mod-1",
                "name": "vpc",
                "provider": "aws",
            }
        )

        data = {
            "vcs_repo": {
                "identifier": "org/repo",
                "oauth_token_id": "ot-123",
            }
        }
        result = create_registry_module_with_vcs(adapter, data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_modules.create_with_vcs_connection
        assert args[1] is opts
        assert result == {"id": "mod-1", "name": "vpc", "provider": "aws"}


class TestCreateRegistryModuleVersion:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryModuleCreateVersionOptions")
    @patch(f"{MU_PATH}.RegistryModuleID")
    def test_create_version_uses_sdk_options(self, mock_id_cls, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model(
            {
                "id": "modver-1",
                "version": "1.0.0",
            }
        )

        module_id = {"organization": "my-org", "name": "vpc", "provider": "aws"}
        data = {"version": "1.0.0"}
        result = create_registry_module_version(adapter, module_id, data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_modules.create_version
        assert args[1] is mock_id
        assert args[2] is opts
        assert result == {"id": "modver-1", "version": "1.0.0"}


class TestUpdateRegistryModule:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryModuleUpdateOptions")
    @patch(f"{MU_PATH}.RegistryModuleID")
    def test_update_uses_sdk_options(self, mock_id_cls, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model(
            {
                "id": "mod-1",
                "name": "vpc",
                "no_code": True,
            }
        )

        module_id = {"organization": "my-org", "name": "vpc", "provider": "aws"}
        data = {"no_code": True}
        result = update_registry_module(adapter, module_id, data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_modules.update
        assert args[1] is mock_id
        assert args[2] is opts
        assert result == {"id": "mod-1", "name": "vpc", "no_code": True}


class TestDeleteRegistryModuleByName:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryModuleID")
    def test_delete_by_name(self, mock_id_cls, mock_safe_call):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id

        module_id = {"organization": "my-org", "name": "vpc"}
        delete_registry_module_by_name(adapter, module_id)

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_modules.delete_by_name
        assert args[1] is mock_id
        assert "error_context" in kwargs


class TestDeleteRegistryModuleProvider:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryModuleID")
    def test_delete_provider(self, mock_id_cls, mock_safe_call):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id

        module_id = {"organization": "my-org", "name": "vpc", "provider": "aws"}
        delete_registry_module_provider(adapter, module_id)

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_modules.delete_provider
        assert args[1] is mock_id
        assert "error_context" in kwargs


class TestDeleteRegistryModuleVersion:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryModuleID")
    def test_delete_version(self, mock_id_cls, mock_safe_call):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id

        module_id = {"organization": "my-org", "name": "vpc", "provider": "aws"}
        delete_registry_module_version(adapter, module_id, "1.0.0")

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_modules.delete_version
        assert args[1] is mock_id
        assert args[2] == "1.0.0"
        assert "error_context" in kwargs


class TestUploadRegistryModuleVersion:
    @patch(f"{MU_PATH}.safe_api_call")
    def test_upload(self, mock_safe_call):
        adapter = Mock()
        upload_url = "https://example.com/upload"
        archive_content = b"fake archive content"

        upload_registry_module_version(adapter, upload_url, archive_content)

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_modules.upload_tar_gzip
        assert args[1] == upload_url
        # args[2] is the BytesIO object
        assert args[2].read() == archive_content
        assert "error_context" in kwargs
