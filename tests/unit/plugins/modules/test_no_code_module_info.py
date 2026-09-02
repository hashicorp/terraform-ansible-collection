# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/no_code_module_info.py."""

from unittest.mock import Mock, patch

import pytest

MOD_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.no_code_module_info"


@pytest.fixture
def mock_adapter():
    return Mock()


class TestNoCodeModuleInfo:
    @patch(f"{MOD_PATH}.get_no_code_module")
    def test_returns_module_when_found(self, mock_get, mock_adapter):
        mock_get.return_value = {"id": "nocode-1", "enabled": True}

        result = mock_get(mock_adapter, "nocode-1")

        assert result == {"id": "nocode-1", "enabled": True}
        mock_get.assert_called_once_with(mock_adapter, "nocode-1")

    @patch(f"{MOD_PATH}.get_no_code_module")
    def test_returns_none_when_not_found(self, mock_get, mock_adapter):
        mock_get.return_value = None

        result = mock_get(mock_adapter, "nocode-missing")

        assert result is None
        mock_get.assert_called_once_with(mock_adapter, "nocode-missing")
