# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/stack_state.py."""

from unittest.mock import Mock

import pytest
from pytfe.errors import NotFound, TFEError

from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_state import (
    get_stack_state,
    list_stack_states,
)


def _make_model(payload):
    """Create a mock pytfe model that returns the given payload from model_dump."""
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestGetStackState:
    def test_success(self):
        """get_stack_state calls read() with the given ID and returns formatted dict."""
        adapter = Mock()
        expected = {
            "id": "sts-abc123",
            "generation": 3,
            "status": "current",
            "deployment": "dev",
            "is_current": True,
            "resource_instance_count": 7,
        }
        adapter.client.stack_states.read.return_value = _make_model(expected)

        result = get_stack_state(adapter, "sts-abc123")

        adapter.client.stack_states.read.assert_called_once_with("sts-abc123")
        assert result == expected

    def test_not_found_returns_none(self):
        """get_stack_state returns None when pytfe raises NotFound."""
        adapter = Mock()
        adapter.client.stack_states.read.side_effect = NotFound("missing")

        result = get_stack_state(adapter, "sts-missing")

        adapter.client.stack_states.read.assert_called_once_with("sts-missing")
        assert result is None

    def test_format_response_called(self):
        """format_response() is called with the object returned by pytfe read()."""
        from unittest.mock import patch

        adapter = Mock()
        pytfe_model = _make_model({"id": "sts-abc123"})
        adapter.client.stack_states.read.return_value = pytfe_model

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.module_utils.stack_state.format_response",
            wraps=lambda x: x.model_dump(mode="json", exclude_none=True),
        ) as mock_fmt:
            get_stack_state(adapter, "sts-abc123")
            mock_fmt.assert_called_once_with(pytfe_model)

    def test_unexpected_exception_propagates(self):
        """Non-NotFound exceptions are NOT swallowed by get_stack_state."""
        adapter = Mock()
        adapter.client.stack_states.read.side_effect = RuntimeError("unexpected API failure")

        with pytest.raises(RuntimeError, match="unexpected API failure"):
            get_stack_state(adapter, "sts-abc123")


_ST_ID = "st-parent01"


class TestListStackStates:
    def test_returns_list_of_states(self):
        adapter = Mock()
        payload = {"id": "sts-abc123", "generation": 3, "status": "current"}
        model = Mock()
        model.model_dump.return_value = payload
        adapter.client.stack_states.list.return_value = [model]

        result = list_stack_states(adapter, _ST_ID)

        adapter.client.stack_states.list.assert_called_once_with(_ST_ID)
        assert result == [payload]

    def test_empty_iterator_returns_empty_list(self):
        adapter = Mock()
        adapter.client.stack_states.list.return_value = []
        result = list_stack_states(adapter, _ST_ID)
        assert result == []

    def test_not_found_returns_empty_list(self):
        adapter = Mock()
        adapter.client.stack_states.list.side_effect = NotFound("missing")
        assert list_stack_states(adapter, _ST_ID) == []

    def test_tfe_error_returns_empty_list(self):
        """TFEError (e.g. failed deployment with no states) returns [] instead of raising."""
        adapter = Mock()
        adapter.client.stack_states.list.side_effect = TFEError("Unknown error.")
        assert list_stack_states(adapter, _ST_ID) == []
