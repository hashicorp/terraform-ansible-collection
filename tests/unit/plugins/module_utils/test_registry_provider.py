# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider import (
    create_registry_provider,
    delete_registry_provider,
    get_registry_provider,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider"


def _make_model(payload):
    model = Mock()
    model.model_dump.return_value = payload
    return model


class TestRegistryProviderAdapter:
    def test_get_registry_provider_success(self):
        adapter = Mock()
        adapter.client.registry_providers.read.return_value = _make_model({"id": "regprov-1", "name": "aws"})

        result = get_registry_provider(adapter, "my-org", "private", "my-org", "aws")

        assert result == {"id": "regprov-1", "name": "aws"}
        adapter.client.registry_providers.read.assert_called_once()

    def test_get_registry_provider_not_found(self):
        from pytfe.errors import NotFound

        adapter = Mock()
        adapter.client.registry_providers.read.side_effect = NotFound("missing")

        result = get_registry_provider(adapter, "my-org", "private", "my-org", "aws")

        assert result is None

    @patch(f"{MU_PATH}.RegistryProviderCreateOptions")
    @patch(f"{MU_PATH}.safe_api_call")
    def test_create_registry_provider_uses_sdk_options(self, mock_safe_call, mock_options_cls):
        adapter = Mock()
        options = Mock()
        mock_options_cls.model_validate.return_value = options
        mock_safe_call.return_value = _make_model({"id": "regprov-1", "name": "aws"})

        result = create_registry_provider(
            adapter,
            "my-org",
            {"name": "aws", "namespace": "my-org", "registry_name": "private"},
        )

        mock_options_cls.model_validate.assert_called_once_with({"name": "aws", "namespace": "my-org", "registry_name": "private"})
        mock_safe_call.assert_called_once()
        assert result == {"id": "regprov-1", "name": "aws"}

    @patch(f"{MU_PATH}.safe_api_call")
    def test_delete_registry_provider_calls_safe_api_call(self, mock_safe_call):
        adapter = Mock()

        delete_registry_provider(adapter, "my-org", "private", "my-org", "aws")

        mock_safe_call.assert_called_once()
        assert mock_safe_call.call_args[0][0] == adapter.client.registry_providers.delete
