# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/variable_set_variable.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.variable_set_variable import (
    _build_desired_state,
    _filter_current_state,
    _strip_unverifiable_sensitive_value,
    main,
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


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def _base_params(self, **overrides):
        params = {
            "variable_set_id": "varset-1",
            "variable_id": None,
            "key": "region",
            "value": "us-east-1",
            "description": None,
            "category": "terraform",
            "hcl": None,
            "sensitive": None,
            "state": "present",
        }
        params.update(overrides)
        return params

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
        params = {"variable_set_id": "varset-1", "variable_id": "var-1", "key": None, "state": "absent"}
        with patch(f"{MODULE}._fetch_variable", return_value={"id": "var-1"}), patch(f"{MODULE}.delete_variable_set_variable") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "varset-1", "var-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_delete_absent_is_noop(self, adapter):
        params = {"variable_set_id": "varset-1", "variable_id": "var-ghost", "key": None, "state": "absent"}
        with patch(f"{MODULE}._fetch_variable", return_value=None), patch(f"{MODULE}.delete_variable_set_variable") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        params = {"variable_set_id": "varset-1", "variable_id": "var-1", "key": None, "state": "absent"}
        with patch(f"{MODULE}._fetch_variable", return_value={"id": "var-1"}), patch(f"{MODULE}.delete_variable_set_variable") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestMain:
    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_argument_specification(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "variable_set_id": "varset-1",
            "variable_id": None,
            "key": "region",
            "value": "us-east-1",
            "description": None,
            "category": "terraform",
            "hcl": None,
            "sensitive": None,
            "state": "present",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", return_value={"changed": True}):
            with pytest.raises(SystemExit):
                main()

        call_kwargs = mock_ansible_module.call_args[1]
        argument_spec = call_kwargs["argument_spec"]
        assert argument_spec["variable_set_id"] == {"type": "str", "required": True}
        assert "variable_set_name" not in argument_spec
        assert "organization" not in argument_spec
        assert argument_spec["key"] == {"type": "str", "no_log": False}
        assert argument_spec["value"] == {"type": "str", "no_log": True}
        assert argument_spec["category"]["choices"] == ["terraform", "env"]
        assert argument_spec["state"]["choices"] == ["present", "absent"]
        assert "required_by" not in call_kwargs
        assert ("variable_id", "key") in call_kwargs["mutually_exclusive"]
        assert ("variable_id", "key") in call_kwargs["required_one_of"]
        assert call_kwargs["supports_check_mode"] is True

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_present_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "variable_set_id": "varset-1",
            "key": "region",
            "value": "us-east-1",
            "category": "terraform",
            "state": "present",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", return_value={"changed": True, "id": "var-1"}) as mock_present:
            with pytest.raises(SystemExit):
                main()

        mock_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True
        assert mock_module.exit_args["id"] == "var-1"

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_absent_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "variable_set_id": "varset-1",
            "variable_id": "var-1",
            "key": None,
            "state": "absent",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_absent", return_value={"changed": True, "msg": "Variable var-1 has been deleted successfully"}) as mock_absent:
            with pytest.raises(SystemExit):
                main()

        mock_absent.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_failure_calls_fail_json(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "variable_set_id": "varset-1",
            "key": "region",
            "state": "present",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", side_effect=ValueError("boom")):
            with pytest.raises(AssertionError):
                main()

        assert mock_module.failed is True
        assert "boom" in mock_module.fail_args["msg"]
