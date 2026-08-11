# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/no_code_module.py."""

from unittest.mock import Mock, patch

import pytest

MOD_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.no_code_module"


@pytest.fixture
def mock_adapter():
    return Mock()


class TestFetchNoCodeModule:
    @patch(f"{MOD_PATH}.get_no_code_module")
    def test_fetch_by_id(self, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import _fetch_no_code_module

        mock_get.return_value = {"id": "nocode-1", "enabled": True}
        params = {"no_code_module_id": "nocode-1"}

        result = _fetch_no_code_module(mock_adapter, params)

        assert result == {"id": "nocode-1", "enabled": True}
        mock_get.assert_called_once_with(mock_adapter, "nocode-1")

    @patch(f"{MOD_PATH}.get_no_code_module")
    def test_fetch_returns_none_when_no_id(self, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import _fetch_no_code_module

        params = {"organization": "my-org"}

        result = _fetch_no_code_module(mock_adapter, params)

        assert result is None
        mock_get.assert_not_called()


class TestHasDrift:
    def test_no_drift_when_fields_match(self):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import _has_drift

        params = {"enabled": True, "version_pin": "1.0.0"}
        current = {"id": "nocode-1", "enabled": True, "version_pin": "1.0.0"}
        assert _has_drift(params, current) is False

    def test_drift_when_enabled_differs(self):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import _has_drift

        params = {"enabled": False}
        current = {"id": "nocode-1", "enabled": True}
        assert _has_drift(params, current) is True

    def test_drift_when_version_pin_differs(self):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import _has_drift

        params = {"version_pin": "2.0.0"}
        current = {"id": "nocode-1", "version_pin": "1.0.0"}
        assert _has_drift(params, current) is True

    def test_no_drift_when_fields_not_specified(self):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import _has_drift

        params = {}
        current = {"id": "nocode-1", "enabled": True}
        assert _has_drift(params, current) is False


class TestStatePresent:
    @patch(f"{MOD_PATH}.create_no_code_module")
    def test_create_when_no_id_provided(self, mock_create, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_present

        mock_create.return_value = {"id": "nocode-1", "enabled": True}
        params = {
            "organization": "my-org",
            "registry_module_id": "mod-1",
            "enabled": True,
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        assert result["id"] == "nocode-1"
        mock_create.assert_called_once_with(
            mock_adapter,
            "my-org",
            {"registry_module_id": "mod-1", "enabled": True},
        )

    @patch(f"{MOD_PATH}.create_no_code_module")
    def test_create_check_mode(self, mock_create, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_present

        params = {
            "organization": "my-org",
            "registry_module_id": "mod-1",
        }

        result = state_present(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "would be created" in result["msg"]
        mock_create.assert_not_called()

    def test_create_missing_organization_raises(self, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_present

        params = {"registry_module_id": "mod-1"}

        with pytest.raises(ValueError, match="'organization' is required"):
            state_present(mock_adapter, params, check_mode=False)

    def test_create_missing_registry_module_id_raises(self, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_present

        params = {"organization": "my-org"}

        with pytest.raises(ValueError, match="'registry_module_id' is required"):
            state_present(mock_adapter, params, check_mode=False)

    @patch(f"{MOD_PATH}._fetch_no_code_module")
    @patch(f"{MOD_PATH}.update_no_code_module")
    def test_update_when_drift(self, mock_update, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_present

        mock_fetch.return_value = {"id": "nocode-1", "enabled": True}
        mock_update.return_value = {"id": "nocode-1", "enabled": False}
        params = {
            "no_code_module_id": "nocode-1",
            "enabled": False,
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        assert result["enabled"] is False
        mock_update.assert_called_once_with(mock_adapter, "nocode-1", {"enabled": False})

    @patch(f"{MOD_PATH}._fetch_no_code_module")
    @patch(f"{MOD_PATH}.update_no_code_module")
    def test_update_idempotent_when_no_drift(self, mock_update, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_present

        current = {"id": "nocode-1", "enabled": True}
        mock_fetch.return_value = current
        params = {
            "no_code_module_id": "nocode-1",
            "enabled": True,
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is False
        assert result["id"] == "nocode-1"
        mock_update.assert_not_called()

    @patch(f"{MOD_PATH}._fetch_no_code_module")
    @patch(f"{MOD_PATH}.update_no_code_module")
    def test_update_check_mode(self, mock_update, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_present

        mock_fetch.return_value = {"id": "nocode-1", "enabled": True}
        params = {
            "no_code_module_id": "nocode-1",
            "enabled": False,
        }

        result = state_present(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "would be updated" in result["msg"]
        mock_update.assert_not_called()

    @patch(f"{MOD_PATH}._fetch_no_code_module")
    def test_update_not_found_raises(self, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_present

        mock_fetch.return_value = None
        params = {"no_code_module_id": "nocode-missing", "enabled": True}

        with pytest.raises(ValueError, match="was not found"):
            state_present(mock_adapter, params, check_mode=False)

    @patch(f"{MOD_PATH}._fetch_no_code_module")
    @patch(f"{MOD_PATH}._has_drift")
    @patch(f"{MOD_PATH}.update_no_code_module")
    def test_update_sends_only_specified_fields(self, mock_update, mock_has_drift, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_present

        mock_fetch.return_value = {"id": "nocode-1", "enabled": True, "version_pin": "1.0.0"}
        mock_has_drift.return_value = True
        mock_update.return_value = {"id": "nocode-1", "enabled": False, "version_pin": "1.0.0"}
        # Only enabled supplied; version_pin should NOT be in the update payload.
        params = {
            "no_code_module_id": "nocode-1",
            "enabled": False,
        }

        state_present(mock_adapter, params, check_mode=False)

        _args, call_kwargs = mock_update.call_args
        update_data = mock_update.call_args[0][2]
        assert "enabled" in update_data
        assert "version_pin" not in update_data


class TestStateAbsent:
    @patch(f"{MOD_PATH}.delete_no_code_module")
    @patch(f"{MOD_PATH}._fetch_no_code_module")
    def test_delete_when_exists(self, mock_fetch, mock_delete, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_absent

        mock_fetch.return_value = {"id": "nocode-1", "enabled": True}
        params = {"no_code_module_id": "nocode-1"}

        result = state_absent(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        assert "deleted successfully" in result["msg"]
        mock_delete.assert_called_once_with(mock_adapter, "nocode-1")

    @patch(f"{MOD_PATH}.delete_no_code_module")
    @patch(f"{MOD_PATH}._fetch_no_code_module")
    def test_delete_check_mode(self, mock_fetch, mock_delete, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_absent

        mock_fetch.return_value = {"id": "nocode-1", "enabled": True}
        params = {"no_code_module_id": "nocode-1"}

        result = state_absent(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "would be deleted" in result["msg"]
        mock_delete.assert_not_called()

    @patch(f"{MOD_PATH}._fetch_no_code_module")
    def test_delete_already_absent(self, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_absent

        mock_fetch.return_value = None
        params = {"no_code_module_id": "nocode-1"}

        result = state_absent(mock_adapter, params, check_mode=False)

        assert result["changed"] is False
        assert "already absent" in result["msg"]

    def test_delete_missing_id_raises(self, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.no_code_module import state_absent

        params = {}

        with pytest.raises(ValueError, match="'no_code_module_id' is required"):
            state_absent(mock_adapter, params, check_mode=False)
