# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/reserved_tag_keys.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.reserved_tag_keys import (
    _has_drift,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.reserved_tag_keys"


class TestHasDrift:
    def test_no_drift_when_nothing_supplied(self):
        current = {"id": "rtk-1", "key": "env", "disable_overrides": True}
        params = {}
        assert _has_drift(params, current) is False

    def test_drift_on_disable_overrides(self):
        current = {"id": "rtk-1", "key": "env", "disable_overrides": True}
        params = {"disable_overrides": False}
        assert _has_drift(params, current) is True

    def test_no_drift_when_disable_overrides_same(self):
        current = {"id": "rtk-1", "key": "env", "disable_overrides": True}
        params = {"disable_overrides": True}
        assert _has_drift(params, current) is False

    def test_drift_on_key(self):
        current = {"id": "rtk-1", "key": "old", "disable_overrides": True}
        params = {"key": "new"}
        assert _has_drift(params, current) is True

    def test_no_drift_when_key_same(self):
        current = {"id": "rtk-1", "key": "env", "disable_overrides": True}
        params = {"key": "env"}
        assert _has_drift(params, current) is False


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_when_missing(self, adapter):
        params = {"organization": "org", "key": "env", "disable_overrides": True, "check_mode": False}
        with patch(f"{MODULE_PATH}.get_reserved_tag_key_by_key", return_value=None), patch(
            f"{MODULE_PATH}.create_reserved_tag_key", return_value={"id": "rtk-1", "key": "env", "disable_overrides": True}
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once_with(adapter, "org", {"key": "env", "disable_overrides": True})
        assert result["changed"] is True
        assert result["id"] == "rtk-1"

    def test_create_check_mode(self, adapter):
        params = {"organization": "org", "key": "env", "disable_overrides": True, "check_mode": True}
        with patch(f"{MODULE_PATH}.get_reserved_tag_key_by_key", return_value=None), patch(f"{MODULE_PATH}.create_reserved_tag_key") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_create_without_disable_overrides_raises(self, adapter):
        params = {"organization": "org", "key": "env", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_reserved_tag_key_by_key", return_value=None):
            with pytest.raises(ValueError, match="disable_overrides"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_organization_raises(self, adapter):
        params = {"key": "env", "disable_overrides": True, "check_mode": False}
        with patch(f"{MODULE_PATH}.get_reserved_tag_key_by_key", return_value=None):
            with pytest.raises(ValueError, match="organization"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_key_raises(self, adapter):
        params = {"organization": "org", "disable_overrides": True, "check_mode": False}
        with patch(f"{MODULE_PATH}.get_reserved_tag_key_by_key", return_value=None):
            with pytest.raises(ValueError, match="key"):
                state_present(adapter, params, check_mode=False)

    def test_idempotent_same_settings(self, adapter):
        current = {"id": "rtk-1", "key": "env", "disable_overrides": True}
        params = {"organization": "org", "key": "env", "disable_overrides": True, "check_mode": False}
        with patch(f"{MODULE_PATH}.get_reserved_tag_key_by_key", return_value=current), patch(f"{MODULE_PATH}.update_reserved_tag_key") as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "rtk-1"

    def test_update_on_drift_by_key(self, adapter):
        current = {"id": "rtk-1", "key": "env", "disable_overrides": True}
        params = {"organization": "org", "key": "env", "disable_overrides": False, "check_mode": False}
        with patch(f"{MODULE_PATH}.get_reserved_tag_key_by_key", return_value=current), patch(
            f"{MODULE_PATH}.update_reserved_tag_key", return_value={"id": "rtk-1", "key": "env", "disable_overrides": False}
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
        # When key is provided, it's included in the update payload
        mock_update.assert_called_once_with(adapter, "rtk-1", {"key": "env", "disable_overrides": False})
        assert result["changed"] is True
        assert result["disable_overrides"] is False

    def test_update_by_id(self, adapter):
        params = {"reserved_tag_key_id": "rtk-1", "disable_overrides": False, "check_mode": False}
        with patch(f"{MODULE_PATH}.update_reserved_tag_key", return_value={"id": "rtk-1", "key": "env", "disable_overrides": False}) as mock_update:
            result = state_present(adapter, params, check_mode=False)
        # Only disable_overrides is provided, not key
        mock_update.assert_called_once_with(adapter, "rtk-1", {"disable_overrides": False})
        assert result["changed"] is True

    def test_update_check_mode(self, adapter):
        current = {"id": "rtk-1", "key": "env", "disable_overrides": True}
        params = {"organization": "org", "key": "env", "disable_overrides": False, "check_mode": True}
        with patch(f"{MODULE_PATH}.get_reserved_tag_key_by_key", return_value=current), patch(f"{MODULE_PATH}.update_reserved_tag_key") as mock_update:
            result = state_present(adapter, params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    # --- org+key path ---

    def test_delete_when_present(self, adapter):
        current = {"id": "rtk-1", "key": "env", "disable_overrides": True}
        params = {"organization": "org", "key": "env", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_reserved_tag_key_by_key", return_value=current), patch(f"{MODULE_PATH}.delete_reserved_tag_key") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "rtk-1")
        assert result["changed"] is True
        assert "deleted successfully" in result["msg"]

    def test_delete_check_mode(self, adapter):
        current = {"id": "rtk-1", "key": "env", "disable_overrides": True}
        params = {"organization": "org", "key": "env", "check_mode": True}
        with patch(f"{MODULE_PATH}.get_reserved_tag_key_by_key", return_value=current), patch(f"{MODULE_PATH}.delete_reserved_tag_key") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_no_op_when_absent(self, adapter):
        params = {"organization": "org", "key": "env", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_reserved_tag_key_by_key", return_value=None):
            result = state_absent(adapter, params, check_mode=False)
        assert result["changed"] is False
        assert "already absent" in result["msg"]

    # --- ID-only path ---

    def test_delete_by_id_when_present(self, adapter):
        params = {"reserved_tag_key_id": "rtk-1", "check_mode": False}
        with patch(f"{MODULE_PATH}.try_delete_reserved_tag_key", return_value=True) as mock_try_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_try_delete.assert_called_once_with(adapter, "rtk-1")
        assert result["changed"] is True
        assert "deleted successfully" in result["msg"]

    def test_delete_by_id_when_already_absent(self, adapter):
        params = {"reserved_tag_key_id": "rtk-1", "check_mode": False}
        with patch(f"{MODULE_PATH}.try_delete_reserved_tag_key", return_value=False) as mock_try_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_try_delete.assert_called_once_with(adapter, "rtk-1")
        assert result["changed"] is False
        assert "already absent" in result["msg"]

    def test_delete_by_id_check_mode(self, adapter):
        params = {"reserved_tag_key_id": "rtk-1", "check_mode": True}
        with patch(f"{MODULE_PATH}.try_delete_reserved_tag_key") as mock_try_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_try_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]
