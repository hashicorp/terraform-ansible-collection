# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest

MOD_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.registry_provider"


@pytest.fixture
def mock_adapter():
    return Mock()


class TestStatePresent:
    @patch(f"{MOD_PATH}.get_registry_provider")
    @patch(f"{MOD_PATH}.create_registry_provider")
    def test_create_when_missing(self, mock_create, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider import state_present

        mock_get.return_value = None
        mock_create.return_value = {"id": "regprov-1", "name": "aws"}
        params = {"organization": "my-org", "namespace": "my-org", "name": "aws"}

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        assert result["id"] == "regprov-1"
        mock_create.assert_called_once()

    @patch(f"{MOD_PATH}.get_registry_provider")
    @patch(f"{MOD_PATH}.create_registry_provider")
    def test_idempotent_when_exists(self, mock_create, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider import state_present

        existing = {"id": "regprov-1", "name": "aws"}
        mock_get.return_value = existing
        params = {"organization": "my-org", "namespace": "my-org", "name": "aws"}

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is False
        assert result["id"] == "regprov-1"
        mock_create.assert_not_called()

    @patch(f"{MOD_PATH}.get_registry_provider")
    def test_create_check_mode(self, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider import state_present

        mock_get.return_value = None
        params = {"organization": "my-org", "namespace": "my-org", "name": "aws"}

        result = state_present(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "would be created" in result["msg"]

    def test_missing_required_fields_raises(self, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider import state_present

        params = {"organization": "my-org", "name": "aws"}

        with pytest.raises(ValueError, match="'organization', 'name', and 'namespace' are required"):
            state_present(mock_adapter, params, check_mode=False)


class TestStateAbsent:
    @patch(f"{MOD_PATH}.get_registry_provider")
    @patch(f"{MOD_PATH}.delete_registry_provider")
    def test_delete_when_present(self, mock_delete, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider import state_absent

        mock_get.return_value = {"id": "regprov-1", "name": "aws"}
        params = {"organization": "my-org", "namespace": "my-org", "name": "aws"}

        result = state_absent(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        assert "deleted successfully" in result["msg"]
        mock_delete.assert_called_once()

    @patch(f"{MOD_PATH}.get_registry_provider")
    def test_delete_check_mode(self, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider import state_absent

        mock_get.return_value = {"id": "regprov-1", "name": "aws"}
        params = {"organization": "my-org", "namespace": "my-org", "name": "aws"}

        result = state_absent(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "would be deleted" in result["msg"]

    @patch(f"{MOD_PATH}.get_registry_provider")
    def test_delete_already_absent(self, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider import state_absent

        mock_get.return_value = None
        params = {"organization": "my-org", "namespace": "my-org", "name": "aws"}

        result = state_absent(mock_adapter, params, check_mode=False)

        assert result["changed"] is False
        assert "already absent" in result["msg"]

    def test_missing_required_fields_raises(self, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider import state_absent

        params = {"organization": "my-org", "name": "aws"}

        with pytest.raises(ValueError, match="'organization', 'name', and 'namespace' are required"):
            state_absent(mock_adapter, params, check_mode=False)
