# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/policy_set_parameter.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.policy_set_parameter import (
    _strip_unverifiable_sensitive_value,
    state_absent,
    state_present,
)

MOD = "ansible_collections.hashicorp.terraform.plugins.modules.policy_set_parameter"


class TestStripUnverifiableSensitiveValue:
    def test_strips_when_sensitive(self):
        have = {"value": "old", "sensitive": True}
        want = {"value": "new", "sensitive": True}
        _strip_unverifiable_sensitive_value(have, want)
        assert "value" not in have
        assert "value" not in want

    def test_leaves_alone_when_not_sensitive(self):
        have = {"value": "old"}
        want = {"value": "new"}
        _strip_unverifiable_sensitive_value(have, want)
        assert have["value"] == "old"
        assert want["value"] == "new"


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def _params(self, **overrides):
        params = {
            "policy_set_id": "polset-1",
            "parameter_id": None,
            "key": "environment",
            "value": "prod",
            "sensitive": None,
            "state": "present",
            "check_mode": False,
        }
        params.update(overrides)
        return params

    def test_create_when_missing(self, adapter):
        params = self._params()
        with patch(f"{MOD}._fetch_parameter", return_value=None), patch(
            f"{MOD}.create_policy_set_parameter", return_value={"id": "var-1", "key": "environment"}
        ) as mock_create:
            result = state_present(adapter, "polset-1", params, check_mode=False)

        mock_create.assert_called_once_with(adapter, "polset-1", {"key": "environment", "value": "prod"})
        assert result["changed"] is True

    def test_create_check_mode(self, adapter):
        params = self._params(check_mode=True)
        with patch(f"{MOD}._fetch_parameter", return_value=None), patch(f"{MOD}.create_policy_set_parameter") as mock_create:
            result = state_present(adapter, "polset-1", params, check_mode=True)

        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_idempotent_no_diff(self, adapter):
        current = {"id": "var-1", "key": "environment", "value": "prod"}
        params = self._params()
        with patch(f"{MOD}._fetch_parameter", return_value=current), patch(f"{MOD}.update_policy_set_parameter") as mock_update:
            result = state_present(adapter, "polset-1", params, check_mode=False)

        mock_update.assert_not_called()
        assert result["changed"] is False

    def test_update_on_drift(self, adapter):
        current = {"id": "var-1", "key": "environment", "value": "staging"}
        params = self._params(value="prod")
        with patch(f"{MOD}._fetch_parameter", return_value=current), patch(
            f"{MOD}.update_policy_set_parameter", return_value={"id": "var-1", "value": "prod"}
        ) as mock_update:
            result = state_present(adapter, "polset-1", params, check_mode=False)

        mock_update.assert_called_once_with(adapter, "polset-1", "var-1", {"key": "environment", "value": "prod"})
        assert result["changed"] is True

    def test_sensitive_value_drift_is_not_verifiable(self, adapter):
        current = {"id": "var-1", "key": "api_key", "sensitive": True}
        params = self._params(key="api_key", value="new-secret", sensitive=True)
        with patch(f"{MOD}._fetch_parameter", return_value=current), patch(f"{MOD}.update_policy_set_parameter") as mock_update:
            result = state_present(adapter, "polset-1", params, check_mode=False)

        mock_update.assert_not_called()
        assert result["changed"] is False


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_existing(self, adapter):
        current = {"id": "var-1"}
        params = {"policy_set_id": "polset-1", "parameter_id": "var-1", "key": None, "state": "absent", "check_mode": False}
        with patch(f"{MOD}._fetch_parameter", return_value=current), patch(f"{MOD}.delete_policy_set_parameter") as mock_delete:
            result = state_absent(adapter, "polset-1", params, check_mode=False)

        mock_delete.assert_called_once_with(adapter, "polset-1", "var-1")
        assert result["changed"] is True

    def test_delete_absent_is_noop(self, adapter):
        params = {"policy_set_id": "polset-1", "parameter_id": "var-ghost", "key": None, "state": "absent", "check_mode": False}
        with patch(f"{MOD}._fetch_parameter", return_value=None):
            result = state_absent(adapter, "polset-1", params, check_mode=False)
        assert result["changed"] is False
