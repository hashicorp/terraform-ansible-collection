# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/registry_provider_version.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider_version import (
    create_registry_provider_version,
    delete_registry_provider_version,
    get_registry_provider_version,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider_version"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


PROVIDER_ID = {
    "organization_name": "my-org",
    "registry_name": "private",
    "namespace": "my-org",
    "name": "aws",
}


class TestGetRegistryProviderVersion:
    @patch(f"{MU_PATH}.RegistryProviderVersionID")
    def test_success(self, mock_id_cls):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id
        adapter.client.registry_provider_versions.read.return_value = _make_model(
            {
                "id": "provver-1",
                "version": "1.0.0",
                "key_id": "ABCD1234",
                "protocols": ["5.0"],
            }
        )

        result = get_registry_provider_version(adapter, PROVIDER_ID, "1.0.0")

        assert result == {
            "id": "provver-1",
            "version": "1.0.0",
            "key_id": "ABCD1234",
            "protocols": ["5.0"],
        }
        adapter.client.registry_provider_versions.read.assert_called_once_with(mock_id)
        mock_id_cls.assert_called_once_with(
            organization_name="my-org",
            registry_name=mock_id_cls.call_args[1]["registry_name"],
            namespace="my-org",
            name="aws",
            version="1.0.0",
        )

    @patch(f"{MU_PATH}.RegistryProviderVersionID")
    def test_not_found_returns_none(self, mock_id_cls):
        adapter = Mock()
        mock_id_cls.return_value = Mock()
        adapter.client.registry_provider_versions.read.side_effect = NotFound("missing")

        result = get_registry_provider_version(adapter, PROVIDER_ID, "1.0.0")

        assert result is None

    @patch(f"{MU_PATH}.RegistryProviderVersionID")
    def test_uses_registry_name_from_provider_id(self, mock_id_cls):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id
        adapter.client.registry_provider_versions.read.return_value = _make_model({"id": "provver-1", "version": "2.0.0"})

        provider_id = dict(PROVIDER_ID, registry_name="private")
        get_registry_provider_version(adapter, provider_id, "2.0.0")

        call_kwargs = mock_id_cls.call_args[1]
        assert call_kwargs["version"] == "2.0.0"
        assert call_kwargs["name"] == "aws"


class TestCreateRegistryProviderVersion:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryProviderVersionCreateOptions")
    @patch(f"{MU_PATH}.RegistryProviderID")
    def test_create_uses_sdk_options(self, mock_pid_cls, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        mock_pid = Mock()
        mock_pid_cls.return_value = mock_pid
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model(
            {
                "id": "provver-1",
                "version": "1.0.0",
                "key_id": "ABCD1234",
                "protocols": ["5.0"],
            }
        )

        data = {"version": "1.0.0", "key_id": "ABCD1234", "protocols": ["5.0"]}
        result = create_registry_provider_version(adapter, PROVIDER_ID, data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_provider_versions.create
        assert args[1] is mock_pid
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {
            "id": "provver-1",
            "version": "1.0.0",
            "key_id": "ABCD1234",
            "protocols": ["5.0"],
        }

    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryProviderVersionCreateOptions")
    @patch(f"{MU_PATH}.RegistryProviderID")
    def test_error_context_contains_version_and_provider(self, mock_pid_cls, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        mock_pid_cls.return_value = Mock()
        mock_opts_cls.model_validate.return_value = Mock()
        mock_safe_call.return_value = _make_model({"id": "provver-1"})

        data = {"version": "3.1.2", "key_id": "KEY123", "protocols": ["5.0"]}
        create_registry_provider_version(adapter, PROVIDER_ID, data)

        _args, kwargs = mock_safe_call.call_args
        error_ctx = kwargs["error_context"]
        assert "3.1.2" in error_ctx
        assert "aws" in error_ctx
        assert "my-org" in error_ctx


class TestDeleteRegistryProviderVersion:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryProviderVersionID")
    def test_delete_calls_sdk(self, mock_id_cls, mock_safe_call):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id

        delete_registry_provider_version(adapter, PROVIDER_ID, "1.0.0")

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.registry_provider_versions.delete
        assert args[1] is mock_id
        assert "error_context" in kwargs

    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryProviderVersionID")
    def test_delete_error_context_contains_version_and_provider(self, mock_id_cls, mock_safe_call):
        adapter = Mock()
        mock_id_cls.return_value = Mock()

        delete_registry_provider_version(adapter, PROVIDER_ID, "2.5.0")

        _args, kwargs = mock_safe_call.call_args
        error_ctx = kwargs["error_context"]
        assert "2.5.0" in error_ctx
        assert "aws" in error_ctx

    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.RegistryProviderVersionID")
    def test_delete_returns_none(self, mock_id_cls, mock_safe_call):
        adapter = Mock()
        mock_id_cls.return_value = Mock()
        mock_safe_call.return_value = None

        result = delete_registry_provider_version(adapter, PROVIDER_ID, "1.0.0")

        assert result is None

    @patch(f"{MU_PATH}.RegistryProviderVersionID")
    def test_version_id_built_with_correct_fields(self, mock_id_cls):
        adapter = Mock()
        mock_id = Mock()
        mock_id_cls.return_value = mock_id
        adapter.client.registry_provider_versions.delete = Mock(return_value=None)

        with patch(f"{MU_PATH}.safe_api_call") as mock_safe:
            mock_safe.return_value = None
            delete_registry_provider_version(adapter, PROVIDER_ID, "1.2.3")

        call_kwargs = mock_id_cls.call_args[1]
        assert call_kwargs["organization_name"] == "my-org"
        assert call_kwargs["namespace"] == "my-org"
        assert call_kwargs["name"] == "aws"
        assert call_kwargs["version"] == "1.2.3"
