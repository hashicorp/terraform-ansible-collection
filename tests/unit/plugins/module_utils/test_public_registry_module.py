# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/public_registry_module.py (pytfe adapter)."""

from unittest.mock import Mock

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.public_registry_module import (
    get_public_registry_module,
    get_public_registry_module_latest,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.public_registry_module"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestGetPublicRegistryModuleLatest:
    def test_success(self):
        adapter = Mock()
        adapter.client.registry.latest_for_provider.return_value = _make_model(
            {
                "id": "hashicorp/consul/aws/0.1.0",
                "namespace": "hashicorp",
                "name": "consul",
                "provider": "aws",
                "version": "0.1.0",
                "verified": True,
            }
        )

        result = get_public_registry_module_latest(adapter, "hashicorp", "consul", "aws")

        assert result["id"] == "hashicorp/consul/aws/0.1.0"
        assert result["namespace"] == "hashicorp"
        assert result["name"] == "consul"
        assert result["provider"] == "aws"
        assert result["version"] == "0.1.0"
        assert result["verified"] is True
        adapter.client.registry.latest_for_provider.assert_called_once_with("hashicorp", "consul", "aws")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.registry.latest_for_provider.side_effect = NotFound("not found")

        result = get_public_registry_module_latest(adapter, "nonexistent", "nomodule", "aws")

        assert result is None
        adapter.client.registry.latest_for_provider.assert_called_once_with("nonexistent", "nomodule", "aws")


class TestGetPublicRegistryModule:
    def test_success(self):
        adapter = Mock()
        adapter.client.registry.get_module.return_value = _make_model(
            {
                "id": "hashicorp/consul/aws/0.1.0",
                "namespace": "hashicorp",
                "name": "consul",
                "provider": "aws",
                "version": "0.1.0",
                "verified": True,
            }
        )

        result = get_public_registry_module(adapter, "hashicorp", "consul", "aws", "0.1.0")

        assert result["id"] == "hashicorp/consul/aws/0.1.0"
        assert result["version"] == "0.1.0"
        adapter.client.registry.get_module.assert_called_once_with("hashicorp", "consul", "aws", "0.1.0")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.registry.get_module.side_effect = NotFound("not found")

        result = get_public_registry_module(adapter, "hashicorp", "consul", "aws", "99.99.99")

        assert result is None
        adapter.client.registry.get_module.assert_called_once_with("hashicorp", "consul", "aws", "99.99.99")
