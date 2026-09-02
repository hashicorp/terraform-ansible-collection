# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/policy_set_version.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set_version import (
    create_policy_set_version,
    get_policy_set_version,
    upload_policy_set_version,
)

MOD = "ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set_version"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestCreatePolicySetVersion:
    @patch(f"{MOD}.safe_api_call")
    def test_create_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        mock_safe_call.return_value = _make_model({"id": "polsetver-1", "status": "pending"})
        result = create_policy_set_version(adapter, "polset-1")

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policy_set_versions.create
        assert args[1] == "polset-1"
        assert "error_context" in kwargs
        assert result == {"id": "polsetver-1", "status": "pending"}


class TestUploadPolicySetVersion:
    @patch(f"{MOD}.safe_api_call")
    def test_upload_reads_raw_object_first(self, mock_safe_call):
        adapter = Mock()
        raw_version = Mock()
        adapter.client.policy_set_versions.read.return_value = raw_version

        upload_policy_set_version(adapter, "polsetver-1", "./policies")

        adapter.client.policy_set_versions.read.assert_called_once_with("polsetver-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policy_set_versions.upload
        assert args[1] is raw_version
        assert args[2] == "./policies"
        assert "error_context" in kwargs


class TestGetPolicySetVersion:
    def test_success(self):
        adapter = Mock()
        adapter.client.policy_set_versions.read.return_value = _make_model({"id": "polsetver-1", "status": "ready"})
        assert get_policy_set_version(adapter, "polsetver-1") == {"id": "polsetver-1", "status": "ready"}

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.policy_set_versions.read.side_effect = NotFound("missing")
        assert get_policy_set_version(adapter, "polsetver-missing") is None
