# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/registry_provider_platform.py."""

from unittest.mock import Mock, patch

import pytest

MOD_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_platform"


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
    "shasum": "abc123def456abc123def456abc123def456abc123def456abc123def456abc123",
    "filename": "terraform-provider-aws_1.0.0_linux_amd64.zip",
}


class TestStatePresent:
    @patch(f"{MOD_PATH}.create_registry_provider_platform")
    @patch(f"{MOD_PATH}._fetch_registry_provider_platform")
    def test_platform_created_when_missing(self, mock_fetch, mock_create, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_platform import state_present

        mock_fetch.return_value = None
        mock_create.return_value = {
            "id": "provpltfm-1",
            "os": "linux",
            "arch": "amd64",
            "filename": "terraform-provider-aws_1.0.0_linux_amd64.zip",
            "shasum": "abc123",
        }

        result = state_present(mock_adapter, _PLATFORM_PARAMS, check_mode=False)

        assert result["changed"] is True
        assert result["id"] == "provpltfm-1"
        mock_create.assert_called_once()

    @patch(f"{MOD_PATH}.create_registry_provider_platform")
    @patch(f"{MOD_PATH}._fetch_registry_provider_platform")
    def test_platform_idempotent_when_exists(self, mock_fetch, mock_create, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_platform import state_present

        existing = {
            "id": "provpltfm-1",
            "os": "linux",
            "arch": "amd64",
            "filename": "terraform-provider-aws_1.0.0_linux_amd64.zip",
            "shasum": "abc123",
        }
        mock_fetch.return_value = existing

        result = state_present(mock_adapter, _PLATFORM_PARAMS, check_mode=False)

        assert result["changed"] is False
        assert result["id"] == "provpltfm-1"
        mock_create.assert_not_called()

    @patch(f"{MOD_PATH}.create_registry_provider_platform")
    @patch(f"{MOD_PATH}._fetch_registry_provider_platform")
    def test_platform_check_mode(self, mock_fetch, mock_create, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_platform import state_present

        mock_fetch.return_value = None

        result = state_present(mock_adapter, _PLATFORM_PARAMS, check_mode=True)

        assert result["changed"] is True
        assert "would be created" in result["msg"]
        mock_create.assert_not_called()

    def test_missing_shasum_filename_raises(self, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_platform import state_present

        params = {**_PLATFORM_PARAMS, "shasum": None, "filename": None}

        with pytest.raises(ValueError, match="'shasum' and 'filename' are required"):
            state_present(mock_adapter, params, check_mode=False)


class TestStateAbsent:
    @patch(f"{MOD_PATH}.delete_registry_provider_platform")
    @patch(f"{MOD_PATH}._fetch_registry_provider_platform")
    def test_platform_deleted(self, mock_fetch, mock_delete, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_platform import state_absent

        mock_fetch.return_value = {
            "id": "provpltfm-1",
            "os": "linux",
            "arch": "amd64",
        }

        result = state_absent(mock_adapter, _PLATFORM_PARAMS, check_mode=False)

        assert result["changed"] is True
        assert "deleted successfully" in result["msg"]
        mock_delete.assert_called_once()

    @patch(f"{MOD_PATH}.delete_registry_provider_platform")
    @patch(f"{MOD_PATH}._fetch_registry_provider_platform")
    def test_platform_already_absent(self, mock_fetch, mock_delete, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_platform import state_absent

        mock_fetch.return_value = None

        result = state_absent(mock_adapter, _PLATFORM_PARAMS, check_mode=False)

        assert result["changed"] is False
        assert "already absent" in result["msg"]
        mock_delete.assert_not_called()

    @patch(f"{MOD_PATH}.delete_registry_provider_platform")
    @patch(f"{MOD_PATH}._fetch_registry_provider_platform")
    def test_platform_delete_check_mode(self, mock_fetch, mock_delete, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_platform import state_absent

        mock_fetch.return_value = {
            "id": "provpltfm-1",
            "os": "linux",
            "arch": "amd64",
        }

        result = state_absent(mock_adapter, _PLATFORM_PARAMS, check_mode=True)

        assert result["changed"] is True
        assert "would be deleted" in result["msg"]
        mock_delete.assert_not_called()
