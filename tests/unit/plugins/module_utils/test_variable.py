# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/variable.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.variable import (
    create_variable,
    delete_variable,
    get_variable,
    get_variable_by_key,
    list_variables,
    update_variable,
)


def _make_model(payload):
    model = Mock()
    model.model_dump.return_value = payload
    return model


class TestListVariables:
    def test_success(self):
        adapter = Mock()
        adapter.client.variables.list.return_value = iter(
            [
                _make_model({"id": "var-1", "key": "region"}),
                _make_model({"id": "var-2", "key": "AWS_REGION"}),
            ]
        )

        result = list_variables(adapter, "ws-abc")

        assert result == [
            {"id": "var-1", "key": "region"},
            {"id": "var-2", "key": "AWS_REGION"},
        ]
        adapter.client.variables.list.assert_called_once_with("ws-abc")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.variables.list.side_effect = NotFound("none")
        assert list_variables(adapter, "ws-abc") == []


class TestGetVariable:
    def test_success(self):
        adapter = Mock()
        adapter.client.variables.read.return_value = _make_model({"id": "var-1", "key": "region"})
        assert get_variable(adapter, "ws-abc", "var-1") == {"id": "var-1", "key": "region"}
        adapter.client.variables.read.assert_called_once_with("ws-abc", "var-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.variables.read.side_effect = NotFound("missing")
        assert get_variable(adapter, "ws-abc", "var-missing") is None


class TestGetVariableByKey:
    def test_matches_key(self):
        adapter = Mock()
        adapter.client.variables.list.return_value = iter(
            [
                _make_model({"id": "var-1", "key": "region", "category": "terraform"}),
                _make_model({"id": "var-2", "key": "AWS_REGION", "category": "env"}),
            ]
        )
        assert get_variable_by_key(adapter, "ws-abc", "AWS_REGION") == {
            "id": "var-2",
            "key": "AWS_REGION",
            "category": "env",
        }

    def test_category_disambiguates_same_key(self):
        adapter = Mock()
        adapter.client.variables.list.return_value = iter(
            [
                _make_model({"id": "var-1", "key": "FOO", "category": "terraform"}),
                _make_model({"id": "var-2", "key": "FOO", "category": "env"}),
            ]
        )
        result = get_variable_by_key(adapter, "ws-abc", "FOO", category="env")
        assert result["id"] == "var-2"

    def test_no_match_returns_none(self):
        adapter = Mock()
        adapter.client.variables.list.return_value = iter([])
        assert get_variable_by_key(adapter, "ws-abc", "region") is None


class TestCreateVariable:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.variable.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.variable.VariableCreateOptions")
    def test_create_uses_sdk_options(self, mock_options_cls, mock_safe_call):
        adapter = Mock()
        options = Mock()
        mock_options_cls.model_validate.return_value = options
        mock_safe_call.return_value = _make_model({"id": "var-1", "key": "region", "value": "us-east-1"})

        data = {"key": "region", "value": "us-east-1", "category": "terraform"}
        result = create_variable(adapter, "ws-abc", data)

        mock_options_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.variables.create
        assert args[1] == "ws-abc"
        assert args[2] is options
        assert "error_context" in kwargs
        assert result == {"id": "var-1", "key": "region", "value": "us-east-1"}


class TestUpdateVariable:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.variable.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.variable.VariableUpdateOptions")
    def test_update_uses_sdk_options(self, mock_options_cls, mock_safe_call):
        adapter = Mock()
        options = Mock()
        mock_options_cls.model_validate.return_value = options
        mock_safe_call.return_value = _make_model({"id": "var-1", "value": "us-west-2"})

        result = update_variable(adapter, "ws-abc", "var-1", {"value": "us-west-2"})

        mock_options_cls.model_validate.assert_called_once_with({"value": "us-west-2"})
        args, _ = mock_safe_call.call_args
        assert args[0] is adapter.client.variables.update
        assert args[1] == "ws-abc"
        assert args[2] == "var-1"
        assert args[3] is options
        assert result == {"id": "var-1", "value": "us-west-2"}


class TestDeleteVariable:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.variable.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_variable(adapter, "ws-abc", "var-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.variables.delete
        assert args[1] == "ws-abc"
        assert args[2] == "var-1"
        assert "error_context" in kwargs
