# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/notification_configuration.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.notification_configuration import (
    _fetch_notification,
    _resolve_workspace_id,
    main,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.notification_configuration"


class TestResolveWorkspace:
    def test_direct_workspace_id(self):
        assert _resolve_workspace_id(Mock(), {"workspace_id": "ws-abc"}) == "ws-abc"

    def test_workspace_by_name(self):
        adapter = Mock()
        with patch(f"{MODULE_PATH}.get_workspace", return_value={"id": "ws-resolved"}) as mock_get:
            assert _resolve_workspace_id(adapter, {"workspace": "app", "organization": "org"}) == "ws-resolved"
        mock_get.assert_called_once_with(adapter, "org", "app")

    def test_workspace_not_found(self):
        with patch(f"{MODULE_PATH}.get_workspace", return_value=None):
            assert _resolve_workspace_id(Mock(), {"workspace": "ghost", "organization": "org"}) is None


class TestFetchNotification:
    def test_by_id(self):
        adapter = Mock()
        with patch(f"{MODULE_PATH}.get_notification_configuration", return_value={"id": "nc-1"}) as mock_get:
            assert _fetch_notification(adapter, None, {"notification_configuration_id": "nc-1"}) == {"id": "nc-1"}
        mock_get.assert_called_once_with(adapter, "nc-1")

    def test_by_name_requires_workspace(self):
        """Without a workspace_id we can't look up by name."""
        with patch(f"{MODULE_PATH}.get_notification_configuration_by_name") as mock_by_name:
            assert _fetch_notification(Mock(), None, {"name": "ops"}) is None
        mock_by_name.assert_not_called()

    def test_by_name_with_workspace(self):
        adapter = Mock()
        with patch(f"{MODULE_PATH}.get_notification_configuration_by_name", return_value={"id": "nc-2"}) as mock_by_name:
            assert _fetch_notification(adapter, "ws-x", {"name": "ops"}) == {"id": "nc-2"}
        mock_by_name.assert_called_once_with(adapter, "ws-x", "ops")


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def _present_params(self, **overrides):
        params = {
            "workspace_id": "ws-x",
            "name": "ops",
            "destination_type": "generic",
            "url": "https://hooks.example.com/x",
            "enabled": True,
            "triggers": ["run:needs_attention"],
            "check_mode": False,
        }
        params.update(overrides)
        return params

    def test_create_when_missing(self, adapter):
        with patch(f"{MODULE_PATH}._fetch_notification", return_value=None), patch(
            f"{MODULE_PATH}.create_notification_configuration",
            return_value={
                "id": "nc-new",
                "name": "ops",
                "destination_type": "generic",
                "url": "https://hooks.example.com/x",
                "enabled": True,
                "triggers": ["run:needs_attention"],
            },
        ) as mock_create:
            result = state_present(adapter, self._present_params(), check_mode=False)

        mock_create.assert_called_once()
        ws_arg, payload = mock_create.call_args.args[1], mock_create.call_args.args[2]
        assert ws_arg == "ws-x"
        assert payload["name"] == "ops"
        assert payload["destination_type"] == "generic"
        # check_mode is not an SDK key and must not leak into the payload
        assert "check_mode" not in payload
        assert result["changed"] is True
        assert result["id"] == "nc-new"

    def test_create_check_mode(self, adapter):
        with patch(f"{MODULE_PATH}._fetch_notification", return_value=None), patch(f"{MODULE_PATH}.create_notification_configuration") as mock_create:
            result = state_present(adapter, self._present_params(check_mode=True), check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_create_missing_workspace_raises(self, adapter):
        params = self._present_params(workspace_id=None)
        with patch(f"{MODULE_PATH}._fetch_notification", return_value=None):
            with pytest.raises(ValueError, match="workspace"):
                state_present(adapter, params, check_mode=False)

    def test_create_missing_destination_type_raises(self, adapter):
        params = self._present_params(destination_type=None)
        with patch(f"{MODULE_PATH}._fetch_notification", return_value=None):
            with pytest.raises(ValueError, match="destination_type"):
                state_present(adapter, params, check_mode=False)

    def test_idempotent_when_identical(self, adapter):
        current = {
            "id": "nc-1",
            "name": "ops",
            "destination_type": "generic",
            "url": "https://hooks.example.com/x",
            "enabled": True,
            "triggers": ["run:needs_attention"],
        }
        with patch(f"{MODULE_PATH}._fetch_notification", return_value=current), patch(f"{MODULE_PATH}.update_notification_configuration") as mock_update:
            result = state_present(adapter, self._present_params(), check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "nc-1"

    def test_drift_triggers_update(self, adapter):
        current = {
            "id": "nc-1",
            "name": "ops",
            "destination_type": "generic",
            "url": "https://hooks.example.com/x",
            "enabled": True,  # drift: user wants False
            "triggers": ["run:needs_attention"],
        }
        params = self._present_params(enabled=False)
        with patch(f"{MODULE_PATH}._fetch_notification", return_value=current), patch(
            f"{MODULE_PATH}.update_notification_configuration",
            return_value={**current, "enabled": False},
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_called_once()
        nc_id, diff = mock_update.call_args.args[1], mock_update.call_args.args[2]
        assert nc_id == "nc-1"
        assert diff == {"enabled": False}
        assert result["changed"] is True
        assert result["enabled"] is False

    def test_destination_type_change_is_rejected(self, adapter):
        current = {
            "id": "nc-1",
            "name": "ops",
            "destination_type": "slack",
            "url": "https://hooks.slack.com/x",
            "enabled": True,
            "triggers": [],
        }
        with patch(f"{MODULE_PATH}._fetch_notification", return_value=current):
            with pytest.raises(ValueError, match="destination_type"):
                state_present(adapter, self._present_params(destination_type="generic"), check_mode=False)

    def test_update_check_mode_skips_call(self, adapter):
        current = {
            "id": "nc-1",
            "name": "ops",
            "destination_type": "generic",
            "url": "https://hooks.example.com/x",
            "enabled": True,
            "triggers": ["run:needs_attention"],
        }
        with patch(f"{MODULE_PATH}._fetch_notification", return_value=current), patch(f"{MODULE_PATH}.update_notification_configuration") as mock_update:
            result = state_present(adapter, self._present_params(enabled=False, check_mode=True), check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_by_id(self, adapter):
        params = {"notification_configuration_id": "nc-1", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_notification", return_value={"id": "nc-1"}), patch(f"{MODULE_PATH}.delete_notification_configuration") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "nc-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_delete_already_absent_noop(self, adapter):
        params = {"notification_configuration_id": "nc-gone", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_notification", return_value=None), patch(f"{MODULE_PATH}.delete_notification_configuration") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        params = {"notification_configuration_id": "nc-1", "check_mode": True}
        with patch(f"{MODULE_PATH}._fetch_notification", return_value={"id": "nc-1"}), patch(f"{MODULE_PATH}.delete_notification_configuration") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestMain:
    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_argument_spec(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"workspace_id": "ws-x", "name": "ops", "destination_type": "generic", "url": "https://x", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", side_effect=Exception("stop")):
            with pytest.raises(AssertionError):
                main()

        call_kwargs = mock_ansible_module.call_args[1]
        argspec = call_kwargs["argument_spec"]
        assert argspec["state"]["choices"] == ["present", "absent"]
        assert argspec["destination_type"]["choices"] == ["generic", "slack", "microsoft-teams", "email"]
        assert argspec["token"]["no_log"] is True
        assert call_kwargs["supports_check_mode"] is True
        assert ("notification_configuration_id", "name") in call_kwargs["mutually_exclusive"]
        assert ("workspace_id", "workspace") in call_kwargs["mutually_exclusive"]
        assert ["workspace", "organization"] in call_kwargs["required_together"]
        assert ("notification_configuration_id", "name") in call_kwargs["required_one_of"]

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_present_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"workspace_id": "ws-x", "name": "ops", "destination_type": "generic", "url": "https://x", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", return_value={"changed": True, "id": "nc-1"}) as mock_present:
            with pytest.raises(SystemExit):
                main()

        mock_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True
        assert mock_module.exit_args["id"] == "nc-1"

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_absent_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"notification_configuration_id": "nc-1", "state": "absent"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_absent", return_value={"changed": True, "msg": "deleted"}) as mock_absent:
            with pytest.raises(SystemExit):
                main()

        mock_absent.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_propagates_errors_via_fail_json(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"workspace_id": "ws-x", "name": "ops", "destination_type": "generic", "url": "https://x", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", side_effect=RuntimeError("boom")):
            with pytest.raises(AssertionError):
                main()

        assert mock_module.failed is True
        assert "boom" in mock_module.fail_args["msg"]
