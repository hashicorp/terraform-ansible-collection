# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/no_code_module.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.no_code_module import (
    create_no_code_module,
    delete_no_code_module,
    get_no_code_module,
    update_no_code_module,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.no_code_module"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestGetNoCodeModule:
    def test_success(self):
        adapter = Mock()
        adapter.client.no_code_modules.read.return_value = _make_model(
            {
                "id": "nocode-1",
                "enabled": True,
            }
        )

        result = get_no_code_module(adapter, "nocode-1")

        assert result == {"id": "nocode-1", "enabled": True}
        adapter.client.no_code_modules.read.assert_called_once_with("nocode-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.no_code_modules.read.side_effect = NotFound("missing")

        assert get_no_code_module(adapter, "nocode-1") is None


class TestCreateNoCodeModule:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.NoCodeModuleCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model(
            {
                "id": "nocode-1",
                "enabled": True,
            }
        )

        data = {"registry_module_id": "mod-1", "enabled": True}
        result = create_no_code_module(adapter, "my-org", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.no_code_modules.create
        assert args[1] == "my-org"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "nocode-1", "enabled": True}


class TestUpdateNoCodeModule:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.NoCodeModuleUpdateOptions")
    def test_update_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model(
            {
                "id": "nocode-1",
                "enabled": False,
            }
        )

        data = {"enabled": False}
        result = update_no_code_module(adapter, "nocode-1", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.no_code_modules.update
        assert args[1] == "nocode-1"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "nocode-1", "enabled": False}


class TestDeleteNoCodeModule:
    @patch(f"{MU_PATH}.safe_api_call")
    def test_delete(self, mock_safe_call):
        adapter = Mock()

        delete_no_code_module(adapter, "nocode-1")

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.no_code_modules.delete
        assert args[1] == "nocode-1"
        assert "error_context" in kwargs
