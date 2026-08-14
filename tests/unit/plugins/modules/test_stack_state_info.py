# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/stack_state_info.py."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.stack_state_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.stack_state_info"


def _mock_module(params, check_mode=False):
    """Create a mock AnsibleTerraformModule with a connected mock adapter."""
    mock_module = Mock()
    mock_module.params = params
    mock_module.check_mode = check_mode
    mock_module.exit_json = Mock(side_effect=SystemExit(0))
    mock_module.fail_json = Mock(side_effect=SystemExit(1))

    mock_adapter = Mock()
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_adapter)
    mock_context.__exit__ = Mock(return_value=False)
    mock_module.client.return_value = mock_context
    return mock_module, mock_adapter


STACK_STATE = {
    "id": "sts-abc123",
    "generation": 3,
    "status": "completed",
    "deployment": "dev",
    "is_current": True,
    "resource_instance_count": 7,
    "components": [
        {
            "address": "component.ns",
            "component_address": "component.ns",
            "instance_correlator": "abc123==",
            "component_correlator": "xyz789==",
            "resource_instance_count": 1,
        }
    ],
}


_ST_ID = "st-parent01"


class TestStackStateInfoArgSpec:
    """Verify the argument specification contract."""

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_declares_required_one_of(self, mock_cls):
        """required_one_of must be declared for stack_state_id / stack_id."""
        mock_module, _adapter = _mock_module({"stack_state_id": "sts-abc123", "stack_id": None})
        mock_cls.return_value = mock_module

        with patch(f"{MODULE_PATH}.get_stack_state", return_value=STACK_STATE):
            try:
                main()
            except SystemExit:
                pass

        call_kwargs = mock_cls.call_args[1]
        assert ("stack_state_id", "stack_id") in call_kwargs["required_one_of"]
        assert ("stack_state_id", "stack_id") in call_kwargs["mutually_exclusive"]
        assert call_kwargs["argument_spec"]["stack_state_id"]["type"] == "str"
        assert call_kwargs["argument_spec"]["stack_id"]["type"] == "str"


class TestStackStateInfoSuccess:
    """Successful lookup by stack_state_id."""

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.get_stack_state")
    def test_lookup_by_id_found(self, mock_get, mock_cls):
        """Returns stack_state dict with changed=False on a successful lookup."""
        mock_module, mock_adapter = _mock_module({"stack_state_id": "sts-abc123", "stack_id": None})
        mock_cls.return_value = mock_module
        mock_get.return_value = STACK_STATE

        try:
            main()
        except SystemExit:
            pass

        mock_get.assert_called_once_with(mock_adapter, "sts-abc123")
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert result["stack_state"] == STACK_STATE

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.get_stack_state")
    def test_check_mode_returns_state_unchanged(self, mock_get, mock_cls):
        """In check mode the state is still read and changed remains False."""
        mock_module, mock_adapter = _mock_module({"stack_state_id": "sts-abc123", "stack_id": None}, check_mode=True)
        mock_cls.return_value = mock_module
        mock_get.return_value = STACK_STATE

        try:
            main()
        except SystemExit:
            pass

        mock_get.assert_called_once_with(mock_adapter, "sts-abc123")
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert result["stack_state"]["id"] == "sts-abc123"

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.list_stack_states")
    def test_list_by_stack_id_success(self, mock_list, mock_cls):
        """Providing stack_id returns stack_states list."""
        states = [STACK_STATE, {**STACK_STATE, "id": "sts-def456"}]
        mock_module, mock_adapter = _mock_module({"stack_state_id": None, "stack_id": _ST_ID})
        mock_cls.return_value = mock_module
        mock_list.return_value = states

        try:
            main()
        except SystemExit:
            pass

        mock_list.assert_called_once_with(mock_adapter, _ST_ID)
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert result["stack_states"] == states

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.list_stack_states")
    def test_list_by_stack_id_empty(self, mock_list, mock_cls):
        """A stack with no states returns an empty list (no error)."""
        mock_module, mock_adapter = _mock_module({"stack_state_id": None, "stack_id": _ST_ID})
        mock_cls.return_value = mock_module
        mock_list.return_value = []

        try:
            main()
        except SystemExit:
            pass

        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert result["stack_states"] == []


class TestStackStateInfoNotFound:
    """fail_json is called when the state does not exist."""

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.get_stack_state")
    def test_not_found_calls_fail_json(self, mock_get, mock_cls):
        """When helper returns None, fail_json is called with 'not found' message."""
        mock_module, _adapter = _mock_module({"stack_state_id": "sts-missing", "stack_id": None})
        mock_cls.return_value = mock_module
        mock_get.return_value = None

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        msg = mock_module.fail_json.call_args[1]["msg"]
        assert "not found" in msg.lower()
        assert "sts-missing" in msg


class TestStackStateInfoException:
    """Unexpected exceptions are passed through fail_json."""

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.get_stack_state")
    def test_unexpected_exception_calls_fail_json(self, mock_get, mock_cls):
        """Any unexpected SDK/helper exception causes fail_json to be called."""
        mock_module, _adapter = _mock_module({"stack_state_id": "sts-abc123", "stack_id": None})
        mock_cls.return_value = mock_module
        mock_get.side_effect = RuntimeError("unexpected SDK failure")

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        msg = mock_module.fail_json.call_args[1]["msg"]
        assert "unexpected SDK failure" in msg
