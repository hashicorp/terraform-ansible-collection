# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/ssh_keys.py (pytfe adapter)."""

from unittest.mock import Mock, patch

import pytest
from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.ssh_keys import (
    create_ssh_key,
    delete_ssh_key,
    get_ssh_key,
    get_ssh_key_by_name,
    list_ssh_keys,
    update_ssh_key,
)


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestListSSHKeys:
    def test_success(self):
        adapter = Mock()
        adapter.client.ssh_keys.list.return_value = iter(
            [_make_model({"id": "sshkey-1", "name": "a"}), _make_model({"id": "sshkey-2", "name": "b"})]
        )
        assert list_ssh_keys(adapter, "my-org") == [
            {"id": "sshkey-1", "name": "a"},
            {"id": "sshkey-2", "name": "b"},
        ]
        adapter.client.ssh_keys.list.assert_called_once_with("my-org")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.ssh_keys.list.side_effect = NotFound("nope")
        assert list_ssh_keys(adapter, "my-org") == []


class TestGetSSHKey:
    def test_success(self):
        adapter = Mock()
        adapter.client.ssh_keys.read.return_value = _make_model({"id": "sshkey-1", "name": "a"})
        assert get_ssh_key(adapter, "sshkey-1") == {"id": "sshkey-1", "name": "a"}
        adapter.client.ssh_keys.read.assert_called_once_with("sshkey-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.ssh_keys.read.side_effect = NotFound("missing")
        assert get_ssh_key(adapter, "sshkey-missing") is None


class TestGetSSHKeyByName:
    def test_match(self):
        adapter = Mock()
        adapter.client.ssh_keys.list.return_value = iter(
            [_make_model({"id": "sshkey-1", "name": "a"}), _make_model({"id": "sshkey-2", "name": "b"})]
        )
        assert get_ssh_key_by_name(adapter, "org", "b") == {"id": "sshkey-2", "name": "b"}

    def test_no_match(self):
        adapter = Mock()
        adapter.client.ssh_keys.list.return_value = iter([])
        assert get_ssh_key_by_name(adapter, "org", "ghost") is None


class TestCreateSSHKey:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.ssh_keys.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.ssh_keys.SSHKeyCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "sshkey-1", "name": "a"})

        data = {"name": "a", "value": "PEM"}
        result = create_ssh_key(adapter, "my-org", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.ssh_keys.create
        assert args[1] == "my-org"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "sshkey-1", "name": "a"}


class TestUpdateSSHKey:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.ssh_keys.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.ssh_keys.SSHKeyUpdateOptions")
    def test_update_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "sshkey-1", "name": "renamed"})

        result = update_ssh_key(adapter, "sshkey-1", {"name": "renamed"})

        mock_opts_cls.model_validate.assert_called_once_with({"name": "renamed"})
        args, _ = mock_safe_call.call_args
        assert args[0] is adapter.client.ssh_keys.update
        assert args[1] == "sshkey-1"
        assert args[2] is opts
        assert result == {"id": "sshkey-1", "name": "renamed"}


class TestDeleteSSHKey:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.ssh_keys.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_ssh_key(adapter, "sshkey-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.ssh_keys.delete
        assert args[1] == "sshkey-1"
        assert "error_context" in kwargs


class TestErrorPropagation:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.ssh_keys.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.ssh_keys.SSHKeyCreateOptions")
    def test_create_propagates(self, _opts, mock_safe_call):
        mock_safe_call.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            create_ssh_key(Mock(), "my-org", {"name": "a", "value": "PEM"})
