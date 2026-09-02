# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/policy.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.policy import (
    create_policy,
    delete_policy,
    download_policy_content,
    get_policy,
    get_policy_by_name,
    list_policies,
    update_policy,
    upload_policy_content,
)

MOD = "ansible_collections.hashicorp.terraform.plugins.module_utils.policy"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestListPolicies:
    def test_success(self):
        adapter = Mock()
        adapter.client.policies.list.return_value = iter([_make_model({"id": "pol-1", "name": "a"}), _make_model({"id": "pol-2", "name": "b"})])
        assert list_policies(adapter, "my-org") == [{"id": "pol-1", "name": "a"}, {"id": "pol-2", "name": "b"}]
        adapter.client.policies.list.assert_called_once_with("my-org")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.policies.list.side_effect = NotFound("nope")
        assert list_policies(adapter, "my-org") == []


class TestGetPolicy:
    def test_success(self):
        adapter = Mock()
        adapter.client.policies.read.return_value = _make_model({"id": "pol-1", "name": "a"})
        assert get_policy(adapter, "pol-1") == {"id": "pol-1", "name": "a"}

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.policies.read.side_effect = NotFound("missing")
        assert get_policy(adapter, "pol-missing") is None


class TestGetPolicyByName:
    def test_match(self):
        adapter = Mock()
        adapter.client.policies.list.return_value = iter([_make_model({"id": "pol-1", "name": "a"}), _make_model({"id": "pol-2", "name": "b"})])
        assert get_policy_by_name(adapter, "org", "b") == {"id": "pol-2", "name": "b"}

    def test_no_match(self):
        adapter = Mock()
        adapter.client.policies.list.return_value = iter([])
        assert get_policy_by_name(adapter, "org", "ghost") is None


class TestCreatePolicy:
    @patch(f"{MOD}.safe_api_call")
    @patch(f"{MOD}.PolicyCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "pol-1", "name": "a"})

        data = {"name": "a", "kind": "sentinel", "enforcement_level": "hard-mandatory"}
        result = create_policy(adapter, "my-org", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policies.create
        assert args[1] == "my-org"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "pol-1", "name": "a"}


class TestUpdatePolicy:
    @patch(f"{MOD}.safe_api_call")
    @patch(f"{MOD}.PolicyUpdateOptions")
    def test_update_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "pol-1", "enforcement_level": "advisory"})

        result = update_policy(adapter, "pol-1", {"enforcement_level": "advisory"})

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policies.update
        assert args[1] == "pol-1"
        assert args[2] is opts
        assert result == {"id": "pol-1", "enforcement_level": "advisory"}


class TestDeletePolicy:
    @patch(f"{MOD}.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_policy(adapter, "pol-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policies.delete
        assert args[1] == "pol-1"
        assert "error_context" in kwargs


class TestUploadPolicyContent:
    @patch(f"{MOD}.safe_api_call")
    def test_upload_encodes_content(self, mock_safe_call):
        adapter = Mock()
        upload_policy_content(adapter, "pol-1", "main = rule { true }")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policies.upload
        assert args[1] == "pol-1"
        assert args[2] == b"main = rule { true }"
        assert "error_context" in kwargs


class TestDownloadPolicyContent:
    def test_success_decodes_content(self):
        adapter = Mock()
        adapter.client.policies.download.return_value = b"main = rule { true }"
        assert download_policy_content(adapter, "pol-1") == "main = rule { true }"

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.policies.download.side_effect = NotFound("missing")
        assert download_policy_content(adapter, "pol-1") is None

    def test_empty_content_returns_none(self):
        adapter = Mock()
        adapter.client.policies.download.return_value = b""
        assert download_policy_content(adapter, "pol-1") is None
