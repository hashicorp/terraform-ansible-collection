# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/stack_diagnostic_info.py."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.stack_diagnostic_info import (
    main,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.stack_diagnostic_info"


class TestStackDiagnosticInfoMain:
    def _make_module(self, check_mode=False):
        module = Mock()
        module.params = {"stack_diagnostic_id": "std-abc123"}
        module.check_mode = check_mode
        module.exit_json = Mock(side_effect=SystemExit(0))
        module.fail_json = Mock(side_effect=SystemExit(1))

        adapter = Mock()
        client_ctx = Mock()
        client_ctx.__enter__ = Mock(return_value=adapter)
        client_ctx.__exit__ = Mock(return_value=False)
        module.client = Mock(return_value=client_ctx)
        return module, adapter

    def test_successful_lookup(self):
        module, adapter = self._make_module()
        diagnostic = {"id": "std-abc123", "severity": "error"}

        with (
            patch(f"{MODULE_PATH}.AnsibleTerraformModule", return_value=module),
            patch(f"{MODULE_PATH}.get_stack_diagnostic", return_value=diagnostic) as mock_get_stack_diagnostic,
        ):
            try:
                main()
            except SystemExit:
                pass

        mock_get_stack_diagnostic.assert_called_once_with(adapter, "std-abc123")
        module.exit_json.assert_called_once_with(changed=False, stack_diagnostic=diagnostic)

    def test_not_found_calls_fail_json(self):
        module, _adapter = self._make_module()

        with (
            patch(f"{MODULE_PATH}.AnsibleTerraformModule", return_value=module),
            patch(f"{MODULE_PATH}.get_stack_diagnostic", return_value=None),
        ):
            try:
                main()
            except SystemExit:
                pass

        module.fail_json.assert_called_once()
        assert "not found" in module.fail_json.call_args[1]["msg"].lower()

    def test_unexpected_exception_calls_fail_json(self):
        module, _adapter = self._make_module()

        with (
            patch(f"{MODULE_PATH}.AnsibleTerraformModule", return_value=module),
            patch(
                f"{MODULE_PATH}.get_stack_diagnostic",
                side_effect=RuntimeError("boom"),
            ),
        ):
            try:
                main()
            except SystemExit:
                pass

        module.fail_json.assert_called_once_with(msg="boom")

    def test_argument_spec(self):
        module, _adapter = self._make_module()

        with patch(f"{MODULE_PATH}.AnsibleTerraformModule", return_value=module) as mock_cls:
            try:
                main()
            except SystemExit:
                pass

        argument_spec = mock_cls.call_args.kwargs["argument_spec"]
        assert argument_spec["stack_diagnostic_id"]["required"] is True
        assert argument_spec["stack_diagnostic_id"]["type"] == "str"
        assert mock_cls.call_args.kwargs["supports_check_mode"] is True

    def test_check_mode_still_reads(self):
        module, adapter = self._make_module(check_mode=True)
        diagnostic = {"id": "std-abc123", "severity": "warning"}

        with (
            patch(f"{MODULE_PATH}.AnsibleTerraformModule", return_value=module),
            patch(f"{MODULE_PATH}.get_stack_diagnostic", return_value=diagnostic) as mock_get_stack_diagnostic,
        ):
            try:
                main()
            except SystemExit:
                pass

        mock_get_stack_diagnostic.assert_called_once_with(adapter, "std-abc123")
        module.exit_json.assert_called_once_with(changed=False, stack_diagnostic=diagnostic)
