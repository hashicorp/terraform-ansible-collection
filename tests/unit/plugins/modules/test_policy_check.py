# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/policy_check.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.policy_check import do_override, main

MOD = "ansible_collections.hashicorp.terraform.plugins.modules.policy_check"


class TestDoOverride:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_override_false_is_noop(self, adapter):
        params = {"policy_check_id": "polchk-1", "override": False}
        with patch(f"{MOD}.get_policy_check") as mock_get:
            result = do_override(adapter, params, check_mode=False)

        mock_get.assert_not_called()
        assert result["changed"] is False

    def test_not_found_raises(self, adapter):
        params = {"policy_check_id": "polchk-x", "override": True}
        with patch(f"{MOD}.get_policy_check", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                do_override(adapter, params, check_mode=False)

    def test_already_overridden_is_noop(self, adapter):
        params = {"policy_check_id": "polchk-1", "override": True}
        current = {"id": "polchk-1", "status": "overridden"}
        with patch(f"{MOD}.get_policy_check", return_value=current), patch(f"{MOD}.override_policy_check") as mock_override:
            result = do_override(adapter, params, check_mode=False)

        mock_override.assert_not_called()
        assert result["changed"] is False

    def test_check_mode_does_not_call_sdk(self, adapter):
        params = {"policy_check_id": "polchk-1", "override": True}
        current = {"id": "polchk-1", "status": "soft_failed"}
        with patch(f"{MOD}.get_policy_check", return_value=current), patch(f"{MOD}.override_policy_check") as mock_override:
            result = do_override(adapter, params, check_mode=True)

        mock_override.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_override_applied(self, adapter):
        params = {"policy_check_id": "polchk-1", "override": True}
        current = {"id": "polchk-1", "status": "soft_failed"}
        with patch(f"{MOD}.get_policy_check", return_value=current), patch(
            f"{MOD}.override_policy_check", return_value={"id": "polchk-1", "status": "overridden"}
        ) as mock_override:
            result = do_override(adapter, params, check_mode=False)

        mock_override.assert_called_once_with(adapter, "polchk-1")
        assert result["changed"] is True
        assert result["status"] == "overridden"


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


class TestMain:
    @patch(f"{MOD}.AnsibleTerraformModule")
    @patch(f"{MOD}.do_override")
    def test_main_invokes_do_override(self, mock_do_override, mock_module_class):
        mock_module, mock_adapter = _mock_module({"policy_check_id": "polchk-1", "override": True})
        mock_module_class.return_value = mock_module
        mock_do_override.return_value = {"changed": True, "id": "polchk-1"}

        main()

        args, _kwargs = mock_do_override.call_args
        assert args[0] is mock_adapter
        mock_module.exit_json.assert_called_once()

    @patch(f"{MOD}.AnsibleTerraformModule")
    @patch(f"{MOD}.do_override")
    def test_main_propagates_errors_via_fail_json(self, mock_do_override, mock_module_class):
        mock_module = _mock_module({"policy_check_id": "polchk-1", "override": True})[0]
        mock_module_class.return_value = mock_module
        mock_do_override.side_effect = ValueError("boom")

        main()

        mock_module.fail_json.assert_called_once()
        assert "boom" in mock_module.fail_json.call_args[1]["msg"]
