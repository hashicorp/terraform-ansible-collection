# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/hyok_configuration.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.hyok_configuration import (
    create_hyok_configuration,
    delete_hyok_configuration,
    get_hyok_configuration,
    get_hyok_configuration_by_name,
    list_hyok_configurations,
    revoke_hyok_configuration,
    run_hyok_configuration_test,
)

MOD = "ansible_collections.hashicorp.terraform.plugins.module_utils.hyok_configuration"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestListHYOKConfigurations:
    def test_success(self):
        adapter = Mock()
        adapter.client.hyok_configurations.list.return_value = iter([_make_model({"id": "hyokc-1", "name": "a"}), _make_model({"id": "hyokc-2", "name": "b"})])
        assert list_hyok_configurations(adapter, "my-org") == [
            {"id": "hyokc-1", "name": "a"},
            {"id": "hyokc-2", "name": "b"},
        ]
        adapter.client.hyok_configurations.list.assert_called_once_with("my-org")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.hyok_configurations.list.side_effect = NotFound("nope")
        assert list_hyok_configurations(adapter, "my-org") == []


class TestGetHYOKConfiguration:
    def test_success(self):
        adapter = Mock()
        adapter.client.hyok_configurations.read.return_value = _make_model({"id": "hyokc-1", "name": "a"})
        assert get_hyok_configuration(adapter, "hyokc-1") == {"id": "hyokc-1", "name": "a"}
        adapter.client.hyok_configurations.read.assert_called_once_with("hyokc-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.hyok_configurations.read.side_effect = NotFound("missing")
        assert get_hyok_configuration(adapter, "hyokc-missing") is None


class TestGetHYOKConfigurationByName:
    def test_match(self):
        adapter = Mock()
        adapter.client.hyok_configurations.list.return_value = iter([_make_model({"id": "hyokc-1", "name": "a"}), _make_model({"id": "hyokc-2", "name": "b"})])
        assert get_hyok_configuration_by_name(adapter, "org", "b") == {"id": "hyokc-2", "name": "b"}

    def test_no_match(self):
        adapter = Mock()
        adapter.client.hyok_configurations.list.return_value = iter([])
        assert get_hyok_configuration_by_name(adapter, "org", "ghost") is None


class TestCreateHYOKConfiguration:
    @patch(f"{MOD}.safe_api_call")
    @patch(f"{MOD}.HYOKConfigurationCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "hyokc-1", "name": "a"})

        data = {
            "name": "a",
            "kek_id": "kek-1",
            "agent_pool_id": "apool-1",
            "oidc_configuration_id": "aoidc-1",
            "oidc_configuration_type": "aws-oidc-configurations",
        }
        result = create_hyok_configuration(adapter, "my-org", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.hyok_configurations.create
        assert args[1] == "my-org"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "hyokc-1", "name": "a"}

    @patch(f"{MOD}.safe_api_call")
    @patch(f"{MOD}.HYOKConfigurationCreateOptions")
    @patch(f"{MOD}.HYOKKMSOptions")
    def test_create_validates_kms_options(self, mock_kms_cls, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        kms_opts = Mock()
        mock_kms_cls.model_validate.return_value = kms_opts
        mock_safe_call.return_value = _make_model({"id": "hyokc-1"})

        data = {"name": "a", "kms_options": {"key_region": "us-east-1"}}
        create_hyok_configuration(adapter, "my-org", data)

        mock_kms_cls.model_validate.assert_called_once_with({"key_region": "us-east-1"})
        called_payload = mock_opts_cls.model_validate.call_args[0][0]
        assert called_payload["kms_options"] is kms_opts


class TestDeleteHYOKConfiguration:
    @patch(f"{MOD}.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_hyok_configuration(adapter, "hyokc-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.hyok_configurations.delete
        assert args[1] == "hyokc-1"
        assert "error_context" in kwargs


class TestRevokeHYOKConfiguration:
    @patch(f"{MOD}.safe_api_call")
    def test_revoke_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        revoke_hyok_configuration(adapter, "hyokc-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.hyok_configurations.revoke
        assert args[1] == "hyokc-1"
        assert "error_context" in kwargs


class TestTestHYOKConfiguration:
    @patch(f"{MOD}.safe_api_call")
    def test_test_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        run_hyok_configuration_test(adapter, "hyokc-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.hyok_configurations.test
        assert args[1] == "hyokc-1"
        assert "error_context" in kwargs
