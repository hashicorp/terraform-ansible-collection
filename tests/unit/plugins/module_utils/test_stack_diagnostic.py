# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/stack_diagnostic.py."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_diagnostic import (
    NotFound,
    get_stack_diagnostic,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.stack_diagnostic"


class TestGetStackDiagnostic:
    @patch(f"{MU_PATH}.format_response")
    def test_success(self, mock_format_response):
        adapter = Mock()
        diagnostic = Mock()
        adapter.client.stack_diagnostics.read.return_value = diagnostic
        mock_format_response.return_value = {"id": "std-abc123", "severity": "error"}

        result = get_stack_diagnostic(adapter, "std-abc123")

        adapter.client.stack_diagnostics.read.assert_called_once_with("std-abc123")
        mock_format_response.assert_called_once_with(diagnostic)
        assert result == {"id": "std-abc123", "severity": "error"}

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.stack_diagnostics.read.side_effect = NotFound("missing")

        assert get_stack_diagnostic(adapter, "std-missing") is None
