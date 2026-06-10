# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/variable_set_variable.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.variable_set_variable import (
    _build_desired_state,
    _filter_current_state,
    _resolve_variable_set_id,
    _strip_unverifiable_sensitive_value,
    state_absent,
    state_present,
)

MODULE = "ansible_collections.hashicorp.terraform.plugins.modules.variable_set_variable"


class TestHelpers:
    def test_build_desired_state(self):
        params = {
            "key": "region",
            "value": "us-east-1",
            "description": None,
            "category": "terraform",
            "hcl": None,
            "sensitive": None,
            "variable_set_id": "varset-1",
            "tfe_token": "secret",
            "state": "present",
        }
        assert _build_desired_state(params) == {"key": "region", "value": "us-east-1", "category": "terraform"}

    def test_filter_current_state(self):
        have = {"key": "region", "value": "us-east-1", "category": "terraform", "id": "var-1"}
        want = {"key": "region", "value": "eu-west-1"}
        assert _filter_current_state(have, want) == {"key": "region", "value": "us-east-1"}

    def test_strip_sensitive_value_from_both_sides(self):
        have = {"value": "old", "sensitive": True}
        want = {"value": "new", "sensitive": True}
        _strip_unverifiable_sensitive_value(have, want)
        assert "value" not in have
        assert "value" not in want

    def test_strip_keeps_value_for_non_sensitive(self):
        have = {"value": "old", "sensitive": False}
        want = {"value": "new", "sensitive": False}
        _strip_unverifiable_sensitive_value(have, want)
        assert have["value"] == "old"
        assert want["value"] == "new"


class TestResolveVariableSetId:
    def test_by_id(self):
        adapter = Mock()
        assert _resolve_variable_set_id(adapter, {"variable_set_id": "varset-1"}) == "varset-1"

    def test_by_name(self):
        adapter = Mock()
        with patch(f"{MODULE}.get_variable_set_by_name", return_value={"id": "varset-9", "name": "n"}):
            assert _resolve_variable_set_id(adapter, {"variable_set_name": "n", "organization": "my-org"}) == "varset-9"

    def test_missing(self):
        adapter = Mock()
        with patch(f"{MODULE}.get_variable_set_by_name", return_value=None):
            assert _resolve_variable_set_id(adapter, {"variable_set_name": "n", "organization": "my-org"}) is None


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def _base_params(self, **overrides):
        params = {
            "variable_set_id": "varset-1",
            "variable_set_name": None,
            "organization": None,
            "variable_id": None,
            "key": "region",
            "value": "us-east-1",
            "description": None,
            "category": "terraform",
            "hcl": None,
            "sensitive": None,
            "state": "present",
            "check_mode": False,
        }
        params.update(overrides)
        return params

    def test_unresolvable_variable_set_raises(self, adapter):
        params = self._base_params(variable_set_id=None, variable_set_name=None)
        with pytest.raises(ValueError, match="variable set"):
            state_present(adapter, params, check_mode=False)

    def test_create_when_missing(self, adapter):
        params = self._base_params()
        with patch(f"{MODULE}._fetch_variable", return_value=None), patch(
            f"{MODULE}.create_variable_set_variable",
            return_value={"id": "var-1", "key": "region", "value": "us-east-1", "category": "terraform"},
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)

        mock_create.assert_called_once()
        args = mock_create.call_args.args
        assert args[1] == "varset-1"
        assert args[2]["key"] == "region"
        assert result["changed"] is True
        assert result["id"] == "var-1"

    def test_create_requires_key(self, adapter):
        params = self._base_params(key=None)
        with patch(f"{MODULE}._fetch_variable", return_value=None):
            with pytest.raises(ValueError, match="key"):
                state_present(adapter, params, check_mode=False)

    def test_create_requires_category(self, adapter):
        params = self._base_params(category=None)
        with patch(f"{MODULE}._fetch_variable", return_value=None):
            with pytest.raises(ValueError, match="category"):
                state_present(adapter, params, check_mode=False)

    def test_create_check_mode(self, adapter):
        params = self._base_params()
        with patch(f"{MODULE}._fetch_variable", return_value=None), patch(f"{MODULE}.create_variable_set_variable") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_idempotent_no_diff(self, adapter):
        current = {"id": "var-1", "key": "region", "value": "us-east-1", "category": "terraform"}
        params = self._base_params()
        with patch(f"{MODULE}._fetch_variable", return_value=current), patch(f"{MODULE}.update_variable_set_variable") as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "var-1"

    def test_update_on_value_drift(self, adapter):
        current = {"id": "var-1", "key": "region", "value": "us-east-1", "category": "terraform"}
        params = self._base_params(value="eu-west-1")
        with patch(f"{MODULE}._fetch_variable", return_value=current), patch(
            f"{MODULE}.update_variable_set_variable",
            return_value={"id": "var-1", "key": "region", "value": "eu-west-1", "category": "terraform"},
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_called_once()
        args = mock_update.call_args.args
        assert args[1] == "varset-1"
        assert args[2] == "var-1"
        assert args[3]["value"] == "eu-west-1"
        # category must not be part of the update payload.
        assert "category" not in args[3]
        assert result["changed"] is True

    def test_category_change_rejected(self, adapter):
        current = {"id": "var-1", "key": "region", "value": "us-east-1", "category": "terraform"}
        params = self._base_params(category="env")
        with patch(f"{MODULE}._fetch_variable", return_value=current):
            with pytest.raises(ValueError, match="category"):
                state_present(adapter, params, check_mode=False)

    def test_sensitive_value_idempotent(self, adapter):
        current = {"id": "var-1", "key": "token", "category": "env", "sensitive": True}
        params = self._base_params(key="token", value="secret", category="env", sensitive=True)
        with patch(f"{MODULE}._fetch_variable", return_value=current), patch(f"{MODULE}.update_variable_set_variable") as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False

    def test_update_check_mode(self, adapter):
        current = {"id": "var-1", "key": "region", "value": "us-east-1", "category": "terraform"}
        params = self._base_params(value="eu-west-1")
        with patch(f"{MODULE}._fetch_variable", return_value=current), patch(f"{MODULE}.update_variable_set_variable") as mock_update:
            result = state_present(adapter, params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_existing(self, adapter):
        params = {"variable_set_id": "varset-1", "variable_id": "var-1", "key": None, "state": "absent", "check_mode": False}
        with patch(f"{MODULE}._fetch_variable", return_value={"id": "var-1"}), patch(f"{MODULE}.delete_variable_set_variable") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "varset-1", "var-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_delete_absent_is_noop(self, adapter):
        params = {"variable_set_id": "varset-1", "variable_id": "var-ghost", "key": None, "state": "absent", "check_mode": False}
        with patch(f"{MODULE}._fetch_variable", return_value=None), patch(f"{MODULE}.delete_variable_set_variable") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_unresolvable_variable_set_is_noop(self, adapter):
        params = {"variable_set_id": None, "variable_set_name": "n", "organization": "my-org", "variable_id": "var-1", "state": "absent", "check_mode": False}
        with patch(f"{MODULE}.get_variable_set_by_name", return_value=None), patch(f"{MODULE}.delete_variable_set_variable") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        params = {"variable_set_id": "varset-1", "variable_id": "var-1", "key": None, "state": "absent", "check_mode": True}
        with patch(f"{MODULE}._fetch_variable", return_value={"id": "var-1"}), patch(f"{MODULE}.delete_variable_set_variable") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]
