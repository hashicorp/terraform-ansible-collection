# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/run_trigger.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.run_trigger import (
    _resolve_sourceable_id,
    _resolve_workspace_id,
    main,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.run_trigger"


class TestResolveIds:
    def test_direct_workspace_id(self):
        assert _resolve_workspace_id(Mock(), {"workspace_id": "ws-abc"}) == "ws-abc"

    def test_workspace_by_name(self):
        adapter = Mock()
        with patch(f"{MODULE_PATH}.get_workspace", return_value={"id": "ws-resolved"}) as mock_get:
            result = _resolve_workspace_id(adapter, {"workspace": "tgt", "organization": "org"})
        assert result == "ws-resolved"
        mock_get.assert_called_once_with(adapter, "org", "tgt")

    def test_workspace_not_found(self):
        with patch(f"{MODULE_PATH}.get_workspace", return_value=None):
            assert _resolve_workspace_id(Mock(), {"workspace": "ghost", "organization": "org"}) is None

    def test_workspace_nothing_given(self):
        assert _resolve_workspace_id(Mock(), {}) is None

    def test_direct_sourceable_id(self):
        assert _resolve_sourceable_id(Mock(), {"sourceable_id": "ws-src"}) == "ws-src"

    def test_sourceable_by_name(self):
        adapter = Mock()
        with patch(f"{MODULE_PATH}.get_workspace", return_value={"id": "ws-src"}) as mock_get:
            result = _resolve_sourceable_id(adapter, {"sourceable_workspace": "src", "organization": "org"})
        assert result == "ws-src"
        mock_get.assert_called_once_with(adapter, "org", "src")


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_when_missing(self, adapter):
        params = {"workspace_id": "ws-target", "sourceable_id": "ws-src", "check_mode": False}
        with patch(f"{MODULE_PATH}.find_run_trigger", return_value=None), patch(
            f"{MODULE_PATH}.create_run_trigger",
            return_value={"id": "rt-1", "sourceable": {"id": "ws-src"}, "workspace": {"id": "ws-target"}},
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)

        mock_create.assert_called_once_with(adapter, "ws-target", "ws-src")
        assert result["changed"] is True
        assert result["id"] == "rt-1"

    def test_create_check_mode(self, adapter):
        params = {"workspace_id": "ws-target", "sourceable_id": "ws-src", "check_mode": True}
        with patch(f"{MODULE_PATH}.find_run_trigger", return_value=None), patch(f"{MODULE_PATH}.create_run_trigger") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_idempotent_when_exists(self, adapter):
        params = {"workspace_id": "ws-target", "sourceable_id": "ws-src", "check_mode": False}
        with patch(f"{MODULE_PATH}.find_run_trigger", return_value={"id": "rt-1"}), patch(f"{MODULE_PATH}.create_run_trigger") as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "rt-1"

    def test_missing_workspace_raises(self, adapter):
        params = {"sourceable_id": "ws-src", "check_mode": False}
        with pytest.raises(ValueError, match="target workspace"):
            state_present(adapter, params, check_mode=False)

    def test_missing_sourceable_raises(self, adapter):
        params = {"workspace_id": "ws-target", "check_mode": False}
        with pytest.raises(ValueError, match="source workspace"):
            state_present(adapter, params, check_mode=False)

    def test_create_propagates_sdk_error(self, adapter):
        params = {"workspace_id": "ws-target", "sourceable_id": "ws-src", "check_mode": False}
        with patch(f"{MODULE_PATH}.find_run_trigger", return_value=None), patch(
            f"{MODULE_PATH}.create_run_trigger", side_effect=RuntimeError("api failure")
        ):
            with pytest.raises(RuntimeError, match="api failure"):
                state_present(adapter, params, check_mode=False)


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_by_id(self, adapter):
        params = {"run_trigger_id": "rt-1", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_run_trigger", return_value={"id": "rt-1"}), patch(f"{MODULE_PATH}.delete_run_trigger") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "rt-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_delete_by_id_already_absent(self, adapter):
        params = {"run_trigger_id": "rt-missing", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_run_trigger", return_value=None), patch(f"{MODULE_PATH}.delete_run_trigger") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_by_pair(self, adapter):
        params = {"workspace_id": "ws-target", "sourceable_id": "ws-src", "check_mode": False}
        with patch(f"{MODULE_PATH}.find_run_trigger", return_value={"id": "rt-1"}), patch(f"{MODULE_PATH}.delete_run_trigger") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "rt-1")
        assert result["changed"] is True

    def test_delete_pair_not_found_noop(self, adapter):
        params = {"workspace_id": "ws-target", "sourceable_id": "ws-src", "check_mode": False}
        with patch(f"{MODULE_PATH}.find_run_trigger", return_value=None), patch(f"{MODULE_PATH}.delete_run_trigger") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        params = {"run_trigger_id": "rt-1", "check_mode": True}
        with patch(f"{MODULE_PATH}.get_run_trigger", return_value={"id": "rt-1"}), patch(f"{MODULE_PATH}.delete_run_trigger") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_delete_unresolvable_target_noop(self, adapter):
        params = {"workspace": "ghost", "organization": "org", "sourceable_id": "ws-src", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_workspace", return_value=None):
            result = state_absent(adapter, params, check_mode=False)
        assert result["changed"] is False
        assert "absent" in result["msg"]


class TestMain:
    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_argument_spec(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"workspace_id": "ws-target", "sourceable_id": "ws-src", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", side_effect=Exception("stop")):
            with pytest.raises(AssertionError):
                main()

        call_kwargs = mock_ansible_module.call_args[1]
        argument_spec = call_kwargs["argument_spec"]
        assert argument_spec["state"]["choices"] == ["present", "absent"]
        assert call_kwargs["supports_check_mode"] is True
        assert ("workspace_id", "workspace") in call_kwargs["mutually_exclusive"]
        assert ("sourceable_id", "sourceable_workspace") in call_kwargs["mutually_exclusive"]
        assert ["workspace", "organization"] in call_kwargs["required_together"]

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_present_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"workspace_id": "ws-target", "sourceable_id": "ws-src", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", return_value={"changed": True, "id": "rt-1"}) as mock_present:
            with pytest.raises(SystemExit):
                main()

        mock_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True
        assert mock_module.exit_args["id"] == "rt-1"

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_absent_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"run_trigger_id": "rt-1", "state": "absent"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_absent", return_value={"changed": True, "msg": "Run trigger rt-1 has been deleted successfully"}) as mock_absent:
            with pytest.raises(SystemExit):
                main()

        mock_absent.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_propagates_errors_via_fail_json(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"workspace_id": "ws-target", "sourceable_id": "ws-src", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", side_effect=RuntimeError("boom")):
            with pytest.raises(AssertionError):
                main()

        assert mock_module.failed is True
        assert "boom" in mock_module.fail_args["msg"]
