# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/policy_set_parameter.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set_parameter import (
    create_policy_set_parameter,
    delete_policy_set_parameter,
    get_policy_set_parameter,
    get_policy_set_parameter_by_key,
    list_policy_set_parameters,
    update_policy_set_parameter,
)

MOD = "ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set_parameter"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestListPolicySetParameters:
    def test_success(self):
        adapter = Mock()
        adapter.client.policy_set_parameters.list.return_value = iter([_make_model({"id": "var-1", "key": "a"})])
        assert list_policy_set_parameters(adapter, "polset-1") == [{"id": "var-1", "key": "a"}]
        adapter.client.policy_set_parameters.list.assert_called_once_with("polset-1")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.policy_set_parameters.list.side_effect = NotFound("nope")
        assert list_policy_set_parameters(adapter, "polset-1") == []


class TestGetPolicySetParameter:
    def test_success(self):
        adapter = Mock()
        adapter.client.policy_set_parameters.read.return_value = _make_model({"id": "var-1", "key": "a"})
        assert get_policy_set_parameter(adapter, "polset-1", "var-1") == {"id": "var-1", "key": "a"}
        adapter.client.policy_set_parameters.read.assert_called_once_with("polset-1", "var-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.policy_set_parameters.read.side_effect = NotFound("missing")
        assert get_policy_set_parameter(adapter, "polset-1", "var-missing") is None


class TestGetPolicySetParameterByKey:
    def test_match(self):
        adapter = Mock()
        adapter.client.policy_set_parameters.list.return_value = iter([_make_model({"id": "var-1", "key": "a"}), _make_model({"id": "var-2", "key": "b"})])
        assert get_policy_set_parameter_by_key(adapter, "polset-1", "b") == {"id": "var-2", "key": "b"}

    def test_no_match(self):
        adapter = Mock()
        adapter.client.policy_set_parameters.list.return_value = iter([])
        assert get_policy_set_parameter_by_key(adapter, "polset-1", "ghost") is None


class TestCreatePolicySetParameter:
    @patch(f"{MOD}.safe_api_call")
    @patch(f"{MOD}.PolicySetParameterCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "var-1", "key": "a"})

        data = {"key": "a", "value": "1"}
        result = create_policy_set_parameter(adapter, "polset-1", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, _kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policy_set_parameters.create
        assert args[1] == "polset-1"
        assert args[2] is opts
        assert result == {"id": "var-1", "key": "a"}


class TestUpdatePolicySetParameter:
    @patch(f"{MOD}.safe_api_call")
    @patch(f"{MOD}.PolicySetParameterUpdateOptions")
    def test_update_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "var-1", "value": "2"})

        result = update_policy_set_parameter(adapter, "polset-1", "var-1", {"value": "2"})

        args, _kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policy_set_parameters.update
        assert args[1] == "polset-1"
        assert args[2] == "var-1"
        assert args[3] is opts
        assert result == {"id": "var-1", "value": "2"}


class TestDeletePolicySetParameter:
    @patch(f"{MOD}.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_policy_set_parameter(adapter, "polset-1", "var-1")
        args, _kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policy_set_parameters.delete
        assert args[1] == "polset-1"
        assert args[2] == "var-1"
