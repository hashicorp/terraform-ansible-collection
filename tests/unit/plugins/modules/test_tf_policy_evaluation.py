# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the tf_policy_evaluation module (override action)."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.tf_policy_evaluation import main, state_overridden

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.tf_policy_evaluation"


def _mock_module(params, check_mode=False):
    mock_module = Mock()
    mock_module.params = params
    mock_module.check_mode = check_mode
    mock_adapter = Mock()
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_adapter)
    mock_context.__exit__ = Mock(return_value=False)
    mock_module.client.return_value = mock_context
    return mock_module, mock_adapter


class TestStateOverridden:
    def test_awaiting_override_transitions(self):
        adapter = Mock()
        params = {"evaluation_id": "tfpeval-1", "comment": "approved"}
        with (
            patch(f"{MODULE_PATH}.get_evaluation", return_value={"id": "tfpeval-1", "status": "awaiting_override"}),
            patch(f"{MODULE_PATH}.override_evaluation", return_value={"id": "tfpeval-1", "status": "overridden"}) as mock_override,
        ):
            result = state_overridden(adapter, params, check_mode=False)
        mock_override.assert_called_once_with(adapter, "tfpeval-1", comment="approved")
        assert result == {"changed": True, "id": "tfpeval-1", "status": "overridden"}

    def test_already_overridden_is_noop(self):
        adapter = Mock()
        params = {"evaluation_id": "tfpeval-1", "comment": None}
        with (
            patch(f"{MODULE_PATH}.get_evaluation", return_value={"id": "tfpeval-1", "status": "overridden"}),
            patch(f"{MODULE_PATH}.override_evaluation") as mock_override,
        ):
            result = state_overridden(adapter, params, check_mode=False)
        mock_override.assert_not_called()
        assert result["changed"] is False
        assert "already in status" in result["msg"]

    def test_check_mode_does_not_call_api(self):
        adapter = Mock()
        params = {"evaluation_id": "tfpeval-1", "comment": None}
        with (
            patch(f"{MODULE_PATH}.get_evaluation", return_value={"id": "tfpeval-1", "status": "awaiting_override"}),
            patch(f"{MODULE_PATH}.override_evaluation") as mock_override,
        ):
            result = state_overridden(adapter, params, check_mode=True)
        mock_override.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_missing_evaluation_raises(self):
        adapter = Mock()
        params = {"evaluation_id": "tfpeval-missing", "comment": None}
        with patch(f"{MODULE_PATH}.get_evaluation", return_value=None):
            try:
                state_overridden(adapter, params, check_mode=False)
                raise AssertionError("expected ValueError")
            except ValueError as e:
                assert "not found" in str(e)


class TestMain:
    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_argument_spec(self, mock_module_class):
        mock_module, _adapter = _mock_module({"evaluation_id": "tfpeval-1", "comment": None, "state": "overridden"})
        mock_module_class.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_overridden", return_value={"changed": False, "id": "tfpeval-1"}):
            main()

        call_kwargs = mock_module_class.call_args[1]
        argument_spec = call_kwargs["argument_spec"]
        assert argument_spec["evaluation_id"]["required"] is True
        assert argument_spec["state"]["choices"] == ["overridden"]
        assert argument_spec["state"]["default"] == "overridden"
        assert call_kwargs["supports_check_mode"] is True

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_dispatches_to_state_overridden(self, mock_module_class):
        mock_module, mock_adapter = _mock_module({"evaluation_id": "tfpeval-1", "comment": "ok", "state": "overridden"})
        mock_module_class.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_overridden", return_value={"changed": True, "id": "tfpeval-1", "status": "overridden"}) as mock_state:
            main()

        mock_state.assert_called_once_with(mock_adapter, mock_module.params, mock_module.check_mode)
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True
        assert result["status"] == "overridden"

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_fails_on_exception(self, mock_module_class):
        mock_module, _adapter = _mock_module({"evaluation_id": "tfpeval-missing", "comment": None, "state": "overridden"})
        mock_module_class.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_overridden", side_effect=ValueError("tf-policy evaluation with ID tfpeval-missing not found")):
            main()

        mock_module.fail_json.assert_called_once()
        assert "not found" in mock_module.fail_json.call_args[1]["msg"]
