# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the override_policy_check addition to plugins/module_utils/policy_check.py."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_check import override_policy_check

MOD = "ansible_collections.hashicorp.terraform.plugins.module_utils.policy_check"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestOverridePolicyCheck:
    @patch(f"{MOD}.safe_api_call")
    def test_override_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        mock_safe_call.return_value = _make_model({"id": "polchk-1", "status": "overridden"})

        result = override_policy_check(adapter, "polchk-1")

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policy_checks.override
        assert args[1] == "polchk-1"
        assert "error_context" in kwargs
        assert result == {"id": "polchk-1", "status": "overridden"}
