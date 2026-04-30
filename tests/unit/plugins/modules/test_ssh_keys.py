# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/ssh_keys.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.ssh_keys import (
    _fetch_ssh_key,
    main,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.ssh_keys"


class TestFetch:
    def test_by_id(self):
        with patch(f"{MODULE_PATH}.get_ssh_key", return_value={"id": "sshkey-1"}) as mock_get:
            assert _fetch_ssh_key(Mock(), {"ssh_key_id": "sshkey-1"}) == {"id": "sshkey-1"}
            mock_get.assert_called_once()

    def test_by_name(self):
        with patch(f"{MODULE_PATH}.get_ssh_key_by_name", return_value={"id": "sshkey-1", "name": "a"}) as mock_get:
            result = _fetch_ssh_key(Mock(), {"organization": "org", "name": "a"})
        assert result["id"] == "sshkey-1"
        mock_get.assert_called_once()

    def test_nothing_given(self):
        assert _fetch_ssh_key(Mock(), {}) is None


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_when_missing(self, adapter):
        params = {"organization": "org", "name": "a", "value": "PEM", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value=None), patch(
            f"{MODULE_PATH}.create_ssh_key", return_value={"id": "sshkey-1", "name": "a"}
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once_with(adapter, "org", {"name": "a", "value": "PEM"})
        assert result["changed"] is True
        assert result["id"] == "sshkey-1"

    def test_create_check_mode(self, adapter):
        params = {"organization": "org", "name": "a", "value": "PEM", "check_mode": True}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value=None), patch(f"{MODULE_PATH}.create_ssh_key") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_create_without_value_raises(self, adapter):
        params = {"organization": "org", "name": "a", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value=None):
            with pytest.raises(ValueError, match="value"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_organization_raises(self, adapter):
        params = {"name": "a", "value": "PEM", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value=None):
            with pytest.raises(ValueError, match="organization"):
                state_present(adapter, params, check_mode=False)

    def test_idempotent_same_name(self, adapter):
        current = {"id": "sshkey-1", "name": "a"}
        params = {"organization": "org", "name": "a", "value": "PEM", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value=current), patch(f"{MODULE_PATH}.update_ssh_key") as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "sshkey-1"

    def test_rename_on_drift(self, adapter):
        current = {"id": "sshkey-1", "name": "old"}
        params = {"ssh_key_id": "sshkey-1", "name": "new", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value=current), patch(
            f"{MODULE_PATH}.update_ssh_key", return_value={"id": "sshkey-1", "name": "new"}
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_called_once_with(adapter, "sshkey-1", {"name": "new"})
        assert result["changed"] is True
        assert result["name"] == "new"

    def test_rename_check_mode(self, adapter):
        current = {"id": "sshkey-1", "name": "old"}
        params = {"ssh_key_id": "sshkey-1", "name": "new", "check_mode": True}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value=current), patch(f"{MODULE_PATH}.update_ssh_key") as mock_update:
            result = state_present(adapter, params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_value_change_alone_is_idempotent(self, adapter):
        """The API never returns 'value'; supplying a new value with the same name is a no-op."""
        current = {"id": "sshkey-1", "name": "a"}
        params = {"organization": "org", "name": "a", "value": "NEW_PEM", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value=current), patch(f"{MODULE_PATH}.update_ssh_key") as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False

    def test_sdk_error_propagates(self, adapter):
        params = {"organization": "org", "name": "a", "value": "PEM", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value=None), patch(f"{MODULE_PATH}.create_ssh_key", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                state_present(adapter, params, check_mode=False)


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_existing(self, adapter):
        params = {"organization": "org", "name": "a", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value={"id": "sshkey-1"}), patch(f"{MODULE_PATH}.delete_ssh_key") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "sshkey-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_already_absent(self, adapter):
        params = {"organization": "org", "name": "ghost", "check_mode": False}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value=None), patch(f"{MODULE_PATH}.delete_ssh_key") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        params = {"ssh_key_id": "sshkey-1", "check_mode": True}
        with patch(f"{MODULE_PATH}._fetch_ssh_key", return_value={"id": "sshkey-1"}), patch(f"{MODULE_PATH}.delete_ssh_key") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestMain:
    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_argument_spec(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"organization": "org", "name": "a", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", side_effect=Exception("stop")):
            with pytest.raises(AssertionError):
                main()

        call_kwargs = mock_ansible_module.call_args[1]
        argument_spec = call_kwargs["argument_spec"]
        assert argument_spec["state"]["choices"] == ["present", "absent"]
        assert argument_spec["value"]["no_log"] is True
        assert call_kwargs["supports_check_mode"] is True
        assert "mutually_exclusive" not in call_kwargs
        assert ("ssh_key_id", "name") in call_kwargs["required_one_of"]

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_present_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"organization": "org", "name": "a", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", return_value={"changed": True, "id": "sshkey-1"}) as mock_present:
            with pytest.raises(SystemExit):
                main()
        mock_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_absent_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"ssh_key_id": "sshkey-1", "state": "absent"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_absent", return_value={"changed": True, "msg": "SSH key sshkey-1 has been deleted successfully"}) as mock_absent:
            with pytest.raises(SystemExit):
                main()
        mock_absent.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_propagates_errors_via_fail_json(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"organization": "org", "name": "a", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", side_effect=RuntimeError("boom")):
            with pytest.raises(AssertionError):
                main()
        assert mock_module.failed is True
        assert "boom" in mock_module.fail_args["msg"]
