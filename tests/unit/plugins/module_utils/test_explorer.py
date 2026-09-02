# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/explorer.py (pytfe adapter)."""

from unittest.mock import Mock, patch

import pytest
from pytfe.errors import NotFound, TFEError

from ansible_collections.hashicorp.terraform.plugins.module_utils.explorer import (
    create_saved_view,
    delete_saved_view,
    get_saved_view,
    get_saved_view_by_name,
    get_saved_view_results,
    list_saved_views,
    query_explorer,
    update_saved_view,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.explorer"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestQueryExplorer:
    def test_success(self):
        adapter = Mock()
        row1 = _make_model({"id": "ws-1", "type": "visibility-workspace", "attributes": {"workspace_name": "demo"}})
        row2 = _make_model({"id": "ws-2", "type": "visibility-workspace", "attributes": {}})
        adapter.client.explorer.query.return_value = iter([row1, row2])
        opts = Mock()

        result = query_explorer(adapter, "my-org", opts)

        assert [r["id"] for r in result] == ["ws-1", "ws-2"]
        adapter.client.explorer.query.assert_called_once_with("my-org", opts)

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.explorer.query.side_effect = NotFound("nope")
        assert query_explorer(adapter, "my-org", Mock()) == []

    def test_unexpected_error_propagates(self):
        adapter = Mock()
        adapter.client.explorer.query.side_effect = TFEError("boom")
        with pytest.raises(TFEError):
            query_explorer(adapter, "my-org", Mock())


class TestListSavedViews:
    def test_success(self):
        adapter = Mock()
        adapter.client.explorer.list_saved_views.return_value = iter([_make_model({"id": "sq-1", "name": "a"}), _make_model({"id": "sq-2", "name": "b"})])
        result = list_saved_views(adapter, "my-org")
        assert result == [{"id": "sq-1", "name": "a"}, {"id": "sq-2", "name": "b"}]
        adapter.client.explorer.list_saved_views.assert_called_once_with("my-org")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.explorer.list_saved_views.side_effect = NotFound("nope")
        assert list_saved_views(adapter, "my-org") == []


class TestGetSavedView:
    def test_success(self):
        adapter = Mock()
        adapter.client.explorer.read_saved_view.return_value = _make_model({"id": "sq-1", "name": "a"})
        result = get_saved_view(adapter, "my-org", "sq-1")
        assert result == {"id": "sq-1", "name": "a"}
        adapter.client.explorer.read_saved_view.assert_called_once_with("my-org", "sq-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.explorer.read_saved_view.side_effect = NotFound("missing")
        assert get_saved_view(adapter, "my-org", "sq-missing") is None

    def test_unexpected_error_propagates(self):
        adapter = Mock()
        adapter.client.explorer.read_saved_view.side_effect = TFEError("server error")
        with pytest.raises(TFEError):
            get_saved_view(adapter, "my-org", "sq-1")


class TestGetSavedViewByName:
    def test_match(self):
        adapter = Mock()
        adapter.client.explorer.list_saved_views.return_value = iter([_make_model({"id": "sq-1", "name": "a"}), _make_model({"id": "sq-2", "name": "b"})])
        result = get_saved_view_by_name(adapter, "my-org", "b")
        assert result == {"id": "sq-2", "name": "b"}

    def test_no_match(self):
        adapter = Mock()
        adapter.client.explorer.list_saved_views.return_value = iter([])
        assert get_saved_view_by_name(adapter, "my-org", "ghost") is None


class TestGetSavedViewResults:
    def test_success(self):
        adapter = Mock()
        row = _make_model({"id": "ws-1", "type": "visibility-workspace", "attributes": {}})
        adapter.client.explorer.saved_view_results.return_value = iter([row])

        result = get_saved_view_results(adapter, "my-org", "sq-1")

        assert result == [{"id": "ws-1", "type": "visibility-workspace", "attributes": {}}]
        adapter.client.explorer.saved_view_results.assert_called_once_with("my-org", "sq-1")

    def test_not_found_propagates(self):
        adapter = Mock()
        adapter.client.explorer.saved_view_results.side_effect = NotFound("gone")
        with pytest.raises(NotFound):
            get_saved_view_results(adapter, "my-org", "sq-missing")

    def test_unexpected_error_propagates(self):
        adapter = Mock()
        adapter.client.explorer.saved_view_results.side_effect = TFEError("internal error")
        with pytest.raises(TFEError):
            get_saved_view_results(adapter, "my-org", "sq-1")


class TestCreateSavedView:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.ExplorerSavedViewCreateOptions")
    def test_create_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "sq-1", "name": "my-view"})

        data = {"name": "my-view", "query_type": "workspaces", "query": {"query_type": "workspaces"}}
        result = create_saved_view(adapter, "my-org", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.explorer.create_saved_view
        assert args[1] == "my-org"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "sq-1", "name": "my-view"}


class TestUpdateSavedView:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.ExplorerSavedViewUpdateOptions")
    def test_update_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "sq-1", "name": "renamed"})

        data = {"name": "renamed", "query": {"query_type": "workspaces"}}
        result = update_saved_view(adapter, "my-org", "sq-1", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.explorer.update_saved_view
        assert args[1] == "my-org"
        assert args[2] == "sq-1"
        assert args[3] is opts
        assert "error_context" in kwargs
        assert result == {"id": "sq-1", "name": "renamed"}


class TestDeleteSavedView:
    @patch(f"{MU_PATH}.safe_api_call")
    def test_delete(self, mock_safe_call):
        adapter = Mock()
        delete_saved_view(adapter, "my-org", "sq-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.explorer.delete_saved_view
        assert args[1] == "my-org"
        assert args[2] == "sq-1"
        assert "error_context" in kwargs
