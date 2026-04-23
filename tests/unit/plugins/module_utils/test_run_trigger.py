# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/run_trigger.py (pytfe adapter)."""

from unittest.mock import Mock, patch

import pytest
from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.run_trigger import (
    create_run_trigger,
    delete_run_trigger,
    find_run_trigger,
    get_run_trigger,
    list_run_triggers,
)


def _make_model(payload):
    model = Mock()
    model.model_dump.return_value = payload
    return model


class TestListRunTriggers:
    def test_success(self):
        adapter = Mock()
        adapter.client.run_triggers.list.return_value = iter(
            [
                _make_model({"id": "rt-1", "sourceable": {"id": "ws-src1"}}),
                _make_model({"id": "rt-2", "sourceable": {"id": "ws-src2"}}),
            ]
        )
        result = list_run_triggers(adapter, "ws-target")
        assert result == [
            {"id": "rt-1", "sourceable": {"id": "ws-src1"}},
            {"id": "rt-2", "sourceable": {"id": "ws-src2"}},
        ]
        # Must pass RunTriggerListOptions (positional second arg)
        args, _ = adapter.client.run_triggers.list.call_args
        assert args[0] == "ws-target"

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.run_triggers.list.side_effect = NotFound("nope")
        assert list_run_triggers(adapter, "ws-target") == []


class TestGetRunTrigger:
    def test_success(self):
        adapter = Mock()
        adapter.client.run_triggers.read.return_value = _make_model({"id": "rt-1"})
        assert get_run_trigger(adapter, "rt-1") == {"id": "rt-1"}
        adapter.client.run_triggers.read.assert_called_once_with("rt-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.run_triggers.read.side_effect = NotFound("missing")
        assert get_run_trigger(adapter, "rt-missing") is None


class TestFindRunTrigger:
    def test_matches_by_sourceable_id(self):
        adapter = Mock()
        adapter.client.run_triggers.list.return_value = iter(
            [
                _make_model({"id": "rt-1", "sourceable": {"id": "ws-src1"}}),
                _make_model({"id": "rt-2", "sourceable": {"id": "ws-src2"}}),
            ]
        )
        result = find_run_trigger(adapter, "ws-target", "ws-src2")
        assert result["id"] == "rt-2"

    def test_no_match_returns_none(self):
        adapter = Mock()
        adapter.client.run_triggers.list.return_value = iter([])
        assert find_run_trigger(adapter, "ws-target", "ws-src1") is None


class TestCreateRunTrigger:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run_trigger.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run_trigger.RunTriggerCreateOptions")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run_trigger.Workspace")
    def test_create_uses_sdk_options(self, mock_workspace_cls, mock_options_cls, mock_safe_call):
        adapter = Mock()
        ws = Mock()
        opts = Mock()
        mock_workspace_cls.return_value = ws
        mock_options_cls.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "rt-1", "sourceable": {"id": "ws-src"}})

        result = create_run_trigger(adapter, "ws-target", "ws-src")

        mock_workspace_cls.assert_called_once_with(id="ws-src")
        mock_options_cls.assert_called_once_with(sourceable=ws)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.run_triggers.create
        assert args[1] == "ws-target"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "rt-1", "sourceable": {"id": "ws-src"}}


class TestDeleteRunTrigger:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run_trigger.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_run_trigger(adapter, "rt-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.run_triggers.delete
        assert args[1] == "rt-1"
        assert "error_context" in kwargs


class TestErrorPropagation:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run_trigger.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run_trigger.RunTriggerCreateOptions")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run_trigger.Workspace")
    def test_create_propagates_errors(self, _ws, _opts, mock_safe_call):
        mock_safe_call.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            create_run_trigger(Mock(), "ws-target", "ws-src")
