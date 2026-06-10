# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/variable_set_variable.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.variable_set_variable import (
    SENSITIVE_PLACEHOLDER,
    create_variable_set_variable,
    delete_variable_set_variable,
    get_variable_set_variable,
    get_variable_set_variable_by_key,
    list_variable_set_variables,
    mask_sensitive,
    update_variable_set_variable,
)

ADAPTER_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.variable_set_variable"


def _make_model(payload):
    model = Mock()
    model.model_dump.return_value = payload
    return model


class TestListVariableSetVariables:
    def test_success(self):
        adapter = Mock()
        adapter.client.variable_set_variables.list.return_value = iter(
            [
                _make_model({"id": "var-1", "key": "a"}),
                _make_model({"id": "var-2", "key": "b"}),
            ]
        )
        assert list_variable_set_variables(adapter, "varset-1") == [
            {"id": "var-1", "key": "a"},
            {"id": "var-2", "key": "b"},
        ]

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.variable_set_variables.list.side_effect = NotFound("none")
        assert list_variable_set_variables(adapter, "varset-1") == []


class TestMaskSensitive:
    def test_masks_sensitive_by_default(self):
        variables = [
            {"key": "a", "value": "plain", "sensitive": False},
            {"key": "b", "value": "secret", "sensitive": True},
        ]
        masked = mask_sensitive(variables)
        assert masked[0]["value"] == "plain"
        assert masked[1]["value"] == SENSITIVE_PLACEHOLDER
        # Original is not mutated.
        assert variables[1]["value"] == "secret"

    def test_display_sensitive_returns_as_is(self):
        variables = [{"key": "b", "value": "secret", "sensitive": True}]
        assert mask_sensitive(variables, display_sensitive=True) is variables


class TestGetVariableSetVariable:
    def test_success(self):
        adapter = Mock()
        adapter.client.variable_set_variables.read.return_value = _make_model({"id": "var-1", "key": "a"})
        assert get_variable_set_variable(adapter, "varset-1", "var-1") == {"id": "var-1", "key": "a"}
        adapter.client.variable_set_variables.read.assert_called_once_with("varset-1", "var-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.variable_set_variables.read.side_effect = NotFound("missing")
        assert get_variable_set_variable(adapter, "varset-1", "var-missing") is None


class TestGetByKey:
    def test_match(self):
        adapter = Mock()
        adapter.client.variable_set_variables.list.return_value = iter(
            [
                _make_model({"id": "var-1", "key": "a"}),
                _make_model({"id": "var-2", "key": "b"}),
            ]
        )
        assert get_variable_set_variable_by_key(adapter, "varset-1", "b") == {"id": "var-2", "key": "b"}

    def test_no_match(self):
        adapter = Mock()
        adapter.client.variable_set_variables.list.return_value = iter([])
        assert get_variable_set_variable_by_key(adapter, "varset-1", "ghost") is None


class TestCreateVariableSetVariable:
    @patch(f"{ADAPTER_PATH}.safe_api_call")
    @patch(f"{ADAPTER_PATH}.VariableSetVariableCreateOptions")
    def test_create_uses_sdk_options(self, mock_options_cls, mock_safe_call):
        adapter = Mock()
        options = Mock()
        mock_options_cls.model_validate.return_value = options
        mock_safe_call.return_value = _make_model({"id": "var-1", "key": "a"})

        data = {"key": "a", "value": "x", "category": "terraform"}
        result = create_variable_set_variable(adapter, "varset-1", data)

        mock_options_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.variable_set_variables.create
        assert args[1] == "varset-1"
        assert args[2] is options
        assert "error_context" in kwargs
        assert result == {"id": "var-1", "key": "a"}


class TestUpdateVariableSetVariable:
    @patch(f"{ADAPTER_PATH}.safe_api_call")
    @patch(f"{ADAPTER_PATH}.VariableSetVariableUpdateOptions")
    def test_update_uses_sdk_options(self, mock_options_cls, mock_safe_call):
        adapter = Mock()
        options = Mock()
        mock_options_cls.model_validate.return_value = options
        mock_safe_call.return_value = _make_model({"id": "var-1", "value": "new"})

        result = update_variable_set_variable(adapter, "varset-1", "var-1", {"value": "new"})

        mock_options_cls.model_validate.assert_called_once_with({"value": "new"})
        args = mock_safe_call.call_args.args
        assert args[0] is adapter.client.variable_set_variables.update
        assert args[1] == "varset-1"
        assert args[2] == "var-1"
        assert args[3] is options
        assert result["value"] == "new"


class TestDeleteVariableSetVariable:
    @patch(f"{ADAPTER_PATH}.safe_api_call")
    def test_delete(self, mock_safe_call):
        adapter = Mock()
        delete_variable_set_variable(adapter, "varset-1", "var-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.variable_set_variables.delete
        assert args[1] == "varset-1"
        assert args[2] == "var-1"
        assert "error_context" in kwargs
