# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/variable.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.variable import (
    _build_desired_state,
    _filter_current_state,
    _resolve_workspace_id,
    _strip_unverifiable_sensitive_value,
    main,
    state_absent,
    state_present,
)


MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.variable"


class TestHelpers:
    def test_build_desired_state_filters_non_sdk_and_none(self):
        params = {
            "variable_id": "var-1",  # not an SDK field
            "workspace_id": "ws-abc",  # not an SDK field
            "key": "region",
            "value": "us-east-1",
            "description": None,
            "category": "terraform",
            "hcl": False,
            "sensitive": None,
            "state": "present",
            "tfe_token": "secret",
        }
        assert _build_desired_state(params) == {
            "key": "region",
            "value": "us-east-1",
            "category": "terraform",
            "hcl": False,
        }

    def test_filter_current_state_projects_onto_want(self):
        have = {"key": "region", "value": "us-east-1", "category": "terraform", "id": "var-1"}
        want = {"key": "region", "value": "us-west-2"}
        assert _filter_current_state(have, want) == {"key": "region", "value": "us-east-1"}

    def test_strip_sensitive_value_server_side(self):
        have = {"key": "secret", "value": "", "sensitive": True}
        want = {"key": "secret", "value": "newval", "sensitive": True}
        _strip_unverifiable_sensitive_value(have, want)
        assert "value" not in have
        assert "value" not in want

    def test_strip_sensitive_value_when_desired_sensitive(self):
        have = {"key": "secret", "value": "oldvisible", "sensitive": False}
        want = {"key": "secret", "value": "newval", "sensitive": True}
        _strip_unverifiable_sensitive_value(have, want)
        assert "value" not in have
        assert "value" not in want

    def test_strip_sensitive_value_noop_when_not_sensitive(self):
        have = {"key": "k", "value": "old"}
        want = {"key": "k", "value": "new"}
        _strip_unverifiable_sensitive_value(have, want)
        assert have["value"] == "old"
        assert want["value"] == "new"


class TestResolveWorkspaceId:
    def test_direct_id(self):
        adapter = Mock()
        params = {"workspace_id": "ws-abc"}
        assert _resolve_workspace_id(adapter, params) == "ws-abc"

    def test_by_name(self):
        adapter = Mock()
        params = {"workspace": "my-ws", "organization": "my-org"}
        with patch(f"{MODULE_PATH}.get_workspace", return_value={"id": "ws-resolved"}) as mock_get:
            assert _resolve_workspace_id(adapter, params) == "ws-resolved"
            mock_get.assert_called_once_with(adapter, "my-org", "my-ws")

    def test_missing_returns_none(self):
        adapter = Mock()
        assert _resolve_workspace_id(adapter, {}) is None

    def test_name_unresolvable_returns_none(self):
        adapter = Mock()
        params = {"workspace": "ghost", "organization": "my-org"}
        with patch(f"{MODULE_PATH}.get_workspace", return_value=None):
            assert _resolve_workspace_id(adapter, params) is None


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_when_missing(self, adapter):
        params = {
            "workspace_id": "ws-abc",
            "key": "region",
            "value": "us-east-1",
            "category": "terraform",
            "state": "present",
            "check_mode": False,
        }
        with patch(f"{MODULE_PATH}.get_variable_by_key", return_value=None), patch(
            f"{MODULE_PATH}.create_variable",
            return_value={"id": "var-1", "key": "region", "value": "us-east-1", "category": "terraform"},
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)

        mock_create.assert_called_once_with(
            adapter,
            "ws-abc",
            {"key": "region", "value": "us-east-1", "category": "terraform"},
        )
        assert result["changed"] is True
        assert result["id"] == "var-1"

    def test_create_without_category_raises(self, adapter):
        params = {
            "workspace_id": "ws-abc",
            "key": "region",
            "value": "us-east-1",
            "state": "present",
            "check_mode": False,
        }
        with patch(f"{MODULE_PATH}.get_variable_by_key", return_value=None):
            with pytest.raises(ValueError, match="category"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_workspace_raises(self, adapter):
        params = {"key": "region", "value": "x", "category": "terraform", "state": "present", "check_mode": False}
        with pytest.raises(ValueError, match="workspace"):
            state_present(adapter, params, check_mode=False)

    def test_create_check_mode(self, adapter):
        params = {
            "workspace_id": "ws-abc",
            "key": "region",
            "value": "us-east-1",
            "category": "terraform",
            "state": "present",
            "check_mode": True,
        }
        with patch(f"{MODULE_PATH}.get_variable_by_key", return_value=None), patch(
            f"{MODULE_PATH}.create_variable"
        ) as mock_create:
            result = state_present(adapter, params, check_mode=True)

        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_idempotent_no_diff(self, adapter):
        current = {
            "id": "var-1",
            "key": "region",
            "value": "us-east-1",
            "category": "terraform",
            "hcl": False,
            "sensitive": False,
        }
        params = {
            "workspace_id": "ws-abc",
            "key": "region",
            "value": "us-east-1",
            "category": "terraform",
            "state": "present",
            "check_mode": False,
        }
        with patch(f"{MODULE_PATH}.get_variable_by_key", return_value=current), patch(
            f"{MODULE_PATH}.update_variable"
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)

        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "var-1"

    def test_update_on_drift(self, adapter):
        current = {"id": "var-1", "key": "region", "value": "us-east-1", "category": "terraform"}
        params = {
            "workspace_id": "ws-abc",
            "key": "region",
            "value": "us-west-2",
            "category": "terraform",
            "state": "present",
            "check_mode": False,
        }
        with patch(f"{MODULE_PATH}.get_variable_by_key", return_value=current), patch(
            f"{MODULE_PATH}.update_variable",
            return_value={"id": "var-1", "key": "region", "value": "us-west-2", "category": "terraform"},
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)

        mock_update.assert_called_once_with(
            adapter,
            "ws-abc",
            "var-1",
            {"key": "region", "value": "us-west-2", "category": "terraform"},
        )
        assert result["changed"] is True
        assert result["value"] == "us-west-2"

    def test_update_check_mode(self, adapter):
        current = {"id": "var-1", "key": "region", "value": "old", "category": "terraform"}
        params = {
            "workspace_id": "ws-abc",
            "key": "region",
            "value": "new",
            "category": "terraform",
            "state": "present",
            "check_mode": True,
        }
        with patch(f"{MODULE_PATH}.get_variable_by_key", return_value=current), patch(
            f"{MODULE_PATH}.update_variable"
        ) as mock_update:
            result = state_present(adapter, params, check_mode=True)

        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_sensitive_value_change_is_idempotent(self, adapter):
        """Sensitive values aren't returned by the API; re-runs must not flap."""
        current = {"id": "var-1", "key": "SECRET", "value": "", "category": "env", "sensitive": True}
        params = {
            "workspace_id": "ws-abc",
            "key": "SECRET",
            "value": "rotated-value",
            "category": "env",
            "sensitive": True,
            "state": "present",
            "check_mode": False,
        }
        with patch(f"{MODULE_PATH}.get_variable_by_key", return_value=current), patch(
            f"{MODULE_PATH}.update_variable"
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)

        mock_update.assert_not_called()
        assert result["changed"] is False

    def test_category_change_raises(self, adapter):
        current = {"id": "var-1", "key": "FOO", "value": "x", "category": "terraform"}
        params = {
            "workspace_id": "ws-abc",
            "key": "FOO",
            "value": "x",
            "category": "env",
            "state": "present",
            "check_mode": False,
        }
        with patch(f"{MODULE_PATH}.get_variable_by_key", return_value=current):
            with pytest.raises(ValueError, match="category"):
                state_present(adapter, params, check_mode=False)

    def test_lookup_by_variable_id(self, adapter):
        current = {"id": "var-1", "key": "region", "value": "us-east-1", "category": "terraform"}
        params = {
            "workspace_id": "ws-abc",
            "variable_id": "var-1",
            "value": "us-east-1",
            "state": "present",
            "check_mode": False,
        }
        with patch(f"{MODULE_PATH}.get_variable", return_value=current) as mock_get, patch(
            f"{MODULE_PATH}.update_variable"
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)

        mock_get.assert_called_once_with(adapter, "ws-abc", "var-1")
        mock_update.assert_not_called()
        assert result["changed"] is False


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_existing(self, adapter):
        params = {"workspace_id": "ws-abc", "key": "region", "state": "absent", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_variable_by_key", return_value={"id": "var-1"}), patch(
            f"{MODULE_PATH}.delete_variable"
        ) as mock_delete:
            result = state_absent(adapter, params, check_mode=False)

        mock_delete.assert_called_once_with(adapter, "ws-abc", "var-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_delete_absent_is_noop(self, adapter):
        params = {"workspace_id": "ws-abc", "key": "ghost", "state": "absent", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_variable_by_key", return_value=None), patch(
            f"{MODULE_PATH}.delete_variable"
        ) as mock_delete:
            result = state_absent(adapter, params, check_mode=False)

        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        params = {"workspace_id": "ws-abc", "key": "region", "state": "absent", "check_mode": True}
        with patch(f"{MODULE_PATH}.get_variable_by_key", return_value={"id": "var-1"}), patch(
            f"{MODULE_PATH}.delete_variable"
        ) as mock_delete:
            result = state_absent(adapter, params, check_mode=True)

        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_delete_unresolvable_workspace_is_noop(self, adapter):
        params = {"workspace": "ghost", "organization": "my-org", "key": "region", "state": "absent", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_workspace", return_value=None):
            result = state_absent(adapter, params, check_mode=False)

        assert result["changed"] is False
        assert "absent" in result["msg"]


class TestMain:
    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_argument_spec(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"workspace_id": "ws-abc", "key": "region", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", side_effect=Exception("stop")):
            with pytest.raises(AssertionError):
                main()

        call_kwargs = mock_ansible_module.call_args[1]
        argument_spec = call_kwargs["argument_spec"]
        assert argument_spec["category"]["choices"] == ["terraform", "env"]
        assert argument_spec["state"]["choices"] == ["present", "absent"]
        assert argument_spec["value"]["no_log"] is True
        assert call_kwargs["supports_check_mode"] is True
        assert ("variable_id", "key") in call_kwargs["mutually_exclusive"]
        assert ("workspace_id", "workspace") in call_kwargs["mutually_exclusive"]
        assert ["workspace", "organization"] in call_kwargs["required_together"]

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_present_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"workspace_id": "ws-abc", "key": "region", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", return_value={"changed": True, "id": "var-1"}) as mock_present:
            with pytest.raises(SystemExit):
                main()

        mock_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True
        assert mock_module.exit_args["id"] == "var-1"

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_absent_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"workspace_id": "ws-abc", "key": "region", "state": "absent"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(
            f"{MODULE_PATH}.state_absent",
            return_value={"changed": True, "msg": "Variable var-1 has been deleted successfully"},
        ) as mock_absent:
            with pytest.raises(SystemExit):
                main()

        mock_absent.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_propagates_errors_via_fail_json(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"workspace_id": "ws-abc", "key": "region", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", side_effect=RuntimeError("boom")):
            with pytest.raises(AssertionError):
                main()

        assert mock_module.failed is True
        assert "boom" in mock_module.fail_args["msg"]
