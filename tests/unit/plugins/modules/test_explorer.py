# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/explorer.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.explorer import (
    _desired_payload,
    _fetch_saved_view,
    _has_drift,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.explorer"


class TestFetchSavedView:
    def test_by_view_id(self):
        adapter = Mock()
        with patch(f"{MODULE_PATH}.get_saved_view", return_value={"id": "sq-1"}) as mock_get:
            result = _fetch_saved_view(adapter, {"organization": "org", "view_id": "sq-1"})
        assert result == {"id": "sq-1"}
        mock_get.assert_called_once_with(adapter, "org", "sq-1")

    def test_by_name(self):
        with patch(f"{MODULE_PATH}.get_saved_view_by_name", return_value={"id": "sq-1", "name": "a"}) as mock_get:
            result = _fetch_saved_view(Mock(), {"organization": "org", "name": "a"})
        assert result["id"] == "sq-1"
        mock_get.assert_called_once()

    def test_no_view_id_or_name_returns_none(self):
        result = _fetch_saved_view(Mock(), {"organization": "org"})
        assert result is None


class TestDesiredPayload:
    def test_includes_name(self):
        params = {"name": "my-view", "query_type": None, "query": None}
        assert _desired_payload(params) == {"name": "my-view"}

    def test_includes_query_type_as_python_name(self):
        # model_validate accepts Python names directly (populate_by_name=True)
        params = {"query_type": "workspaces", "name": None, "query": None}
        assert _desired_payload(params) == {"query_type": "workspaces"}

    def test_includes_query(self):
        params = {"name": "v", "query_type": "workspaces", "query": {"query_type": "workspaces", "filter": []}}
        payload = _desired_payload(params)
        assert payload["query"] == {"query_type": "workspaces", "filter": []}
        assert payload["query_type"] == "workspaces"

    def test_empty_params(self):
        assert _desired_payload({}) == {}


class TestHasDrift:
    def test_name_drift(self):
        assert _has_drift({"name": "b"}, {"name": "a"}) is True

    def test_name_no_drift(self):
        assert _has_drift({"name": "a"}, {"name": "a"}) is False

    def test_query_type_drift(self):
        assert _has_drift({"query_type": "workspaces"}, {"query_type": "providers"}) is True

    def test_query_type_no_drift(self):
        assert _has_drift({"query_type": "workspaces"}, {"query_type": "workspaces"}) is False

    def test_inner_query_type_drift(self):
        params = {"query": {"query_type": "workspaces"}}
        current = {"query": {"query_type": "providers"}}
        assert _has_drift(params, current) is True

    def test_inner_query_type_no_drift(self):
        params = {"query": {"query_type": "workspaces"}}
        current = {"query": {"query_type": "workspaces"}}
        assert _has_drift(params, current) is False

    def test_filter_drift(self):
        params = {"query": {"query_type": "workspaces", "filter": [{"field": "workspace_name", "operator": "contains", "value": ["prod"]}]}}
        current = {"query": {"query_type": "workspaces", "filter": []}}
        assert _has_drift(params, current) is True

    def test_filter_no_drift(self):
        f = [{"field": "workspace_name", "operator": "contains", "value": ["prod"]}]
        params = {"query": {"query_type": "workspaces", "filter": f}}
        current = {"query": {"query_type": "workspaces", "filter": f}}
        assert _has_drift(params, current) is False

    def test_filter_order_independent(self):
        f1 = {"field": "workspace_name", "operator": "contains", "value": ["prod"]}
        f2 = {"field": "workspace_name", "operator": "is", "value": ["dev"]}
        params = {"query": {"filter": [f1, f2]}}
        current = {"query": {"filter": [f2, f1]}}
        assert _has_drift(params, current) is False

    def test_fields_drift(self):
        params = {"query": {"query_type": "workspaces", "fields": ["workspace_name", "id"]}}
        current = {"query": {"query_type": "workspaces", "fields": ["workspace_name"]}}
        assert _has_drift(params, current) is True

    def test_fields_no_drift(self):
        params = {"query": {"query_type": "workspaces", "fields": ["id", "workspace_name"]}}
        current = {"query": {"query_type": "workspaces", "fields": ["workspace_name", "id"]}}
        assert _has_drift(params, current) is False

    def test_fields_not_supplied_no_drift(self):
        # User did not supply fields; server has fields — should not be drift.
        params = {"query": {"query_type": "workspaces"}}
        current = {"query": {"query_type": "workspaces", "fields": ["workspace_name"]}}
        assert _has_drift(params, current) is False

    def test_sort_drift(self):
        params = {"query": {"query_type": "workspaces", "sort": ["-workspace_name"]}}
        current = {"query": {"query_type": "workspaces", "sort": []}}
        assert _has_drift(params, current) is True

    def test_sort_no_drift(self):
        params = {"query": {"query_type": "workspaces", "sort": ["-workspace_name"]}}
        current = {"query": {"query_type": "workspaces", "sort": ["-workspace_name"]}}
        assert _has_drift(params, current) is False

    def test_sort_order_is_significant(self):
        params = {"query": {"sort": ["a", "b"]}}
        current = {"query": {"sort": ["b", "a"]}}
        assert _has_drift(params, current) is True

    def test_sort_not_supplied_no_drift(self):
        params = {"query": {"query_type": "workspaces"}}
        current = {"query": {"query_type": "workspaces", "sort": ["-workspace_name"]}}
        assert _has_drift(params, current) is False

    def test_unspecified_top_level_no_drift(self):
        current = {"name": "a", "query_type": "workspaces", "query": {"query_type": "workspaces"}}
        assert _has_drift({"name": "a"}, current) is False

    def test_complete_no_drift(self):
        config = {
            "name": "a",
            "query_type": "workspaces",
            "query": {
                "query_type": "workspaces",
                "filter": [{"field": "workspace_name", "operator": "contains", "value": ["prod"]}],
                "fields": ["workspace_name", "id"],
                "sort": ["-workspace_name"],
            },
        }
        assert _has_drift(config, config) is False


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_when_missing(self, adapter):
        params = {
            "organization": "org",
            "name": "my-view",
            "query_type": "workspaces",
            "query": {"query_type": "workspaces"},
        }
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=None), patch(
            f"{MODULE_PATH}.create_saved_view",
            return_value={"id": "sq-1", "name": "my-view", "query_type": "workspaces"},
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once()
        assert result["changed"] is True
        assert result["id"] == "sq-1"

    def test_create_check_mode(self, adapter):
        params = {"organization": "org", "name": "my-view", "query_type": "workspaces", "query": {"query_type": "workspaces"}}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=None), patch(f"{MODULE_PATH}.create_saved_view") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_create_without_name_raises(self, adapter):
        params = {"organization": "org", "query_type": "workspaces", "query": {"query_type": "workspaces"}}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=None):
            with pytest.raises(ValueError, match="name"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_query_type_raises(self, adapter):
        params = {"organization": "org", "name": "my-view", "query": {"query_type": "workspaces"}}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=None):
            with pytest.raises(ValueError, match="query_type"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_query_raises(self, adapter):
        params = {"organization": "org", "name": "my-view", "query_type": "workspaces"}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=None):
            with pytest.raises(ValueError, match="query"):
                state_present(adapter, params, check_mode=False)

    def test_idempotent_no_drift(self, adapter):
        current = {"id": "sq-1", "name": "my-view", "query_type": "workspaces", "query": {"query_type": "workspaces"}}
        params = {"organization": "org", "name": "my-view", "query_type": "workspaces"}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=current), patch(f"{MODULE_PATH}.update_saved_view") as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "sq-1"

    def test_update_on_name_drift(self, adapter):
        current = {"id": "sq-1", "name": "old-name", "query_type": "workspaces", "query": {"query_type": "workspaces"}}
        params = {"organization": "org", "name": "new-name", "query_type": "workspaces"}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=current), patch(
            f"{MODULE_PATH}.update_saved_view",
            return_value={"id": "sq-1", "name": "new-name", "query_type": "workspaces"},
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_called_once_with(adapter, "org", "sq-1", {"name": "new-name", "query_type": "workspaces"})
        assert result["changed"] is True
        assert result["name"] == "new-name"

    def test_update_check_mode(self, adapter):
        current = {"id": "sq-1", "name": "old-name", "query_type": "workspaces"}
        params = {"organization": "org", "name": "new-name"}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=current), patch(f"{MODULE_PATH}.update_saved_view") as mock_update:
            result = state_present(adapter, params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_update_on_fields_drift(self, adapter):
        current = {"id": "sq-1", "name": "v", "query_type": "workspaces", "query": {"query_type": "workspaces", "fields": ["workspace_name"]}}
        params = {"organization": "org", "name": "v", "query": {"query_type": "workspaces", "fields": ["workspace_name", "id"]}}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=current), patch(
            f"{MODULE_PATH}.update_saved_view", return_value={**current, "query": {**current["query"], "fields": ["workspace_name", "id"]}}
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_called_once()
        assert result["changed"] is True

    def test_no_update_when_fields_no_drift(self, adapter):
        current = {"id": "sq-1", "name": "v", "query_type": "workspaces", "query": {"query_type": "workspaces", "fields": ["workspace_name", "id"]}}
        params = {"organization": "org", "name": "v", "query": {"query_type": "workspaces", "fields": ["id", "workspace_name"]}}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=current), patch(f"{MODULE_PATH}.update_saved_view") as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False

    def test_update_on_sort_drift(self, adapter):
        current = {"id": "sq-1", "name": "v", "query_type": "workspaces", "query": {"query_type": "workspaces", "sort": []}}
        params = {"organization": "org", "name": "v", "query": {"query_type": "workspaces", "sort": ["-workspace_name"]}}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=current), patch(
            f"{MODULE_PATH}.update_saved_view", return_value={**current, "query": {**current["query"], "sort": ["-workspace_name"]}}
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_called_once()
        assert result["changed"] is True

    def test_existing_no_drift_check_mode_no_mutation(self, adapter):
        current = {"id": "sq-1", "name": "my-view", "query_type": "workspaces", "query": {"query_type": "workspaces"}}
        params = {"organization": "org", "name": "my-view", "query_type": "workspaces"}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=current), patch(f"{MODULE_PATH}.create_saved_view") as mock_create, patch(
            f"{MODULE_PATH}.update_saved_view"
        ) as mock_update:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        mock_update.assert_not_called()
        assert result["changed"] is False

    def test_view_id_and_name_rename_semantics(self, adapter):
        current = {"id": "sq-1", "name": "original-name", "query_type": "workspaces", "query": {"query_type": "workspaces"}}
        params = {"organization": "org", "view_id": "sq-1", "name": "new-name", "query_type": "workspaces"}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=current), patch(
            f"{MODULE_PATH}.update_saved_view",
            return_value={"id": "sq-1", "name": "new-name", "query_type": "workspaces"},
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_called_once()
        assert result["changed"] is True
        assert result["name"] == "new-name"


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_present(self, adapter):
        current = {"id": "sq-1", "name": "my-view"}
        params = {"organization": "org", "view_id": "sq-1"}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=current), patch(f"{MODULE_PATH}.delete_saved_view") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "org", "sq-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_noop_when_absent(self, adapter):
        params = {"organization": "org", "view_id": "sq-missing"}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=None), patch(f"{MODULE_PATH}.delete_saved_view") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        current = {"id": "sq-1", "name": "my-view"}
        params = {"organization": "org", "view_id": "sq-1"}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=current), patch(f"{MODULE_PATH}.delete_saved_view") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_already_absent_check_mode_no_mutation(self, adapter):
        params = {"organization": "org", "view_id": "sq-missing"}
        with patch(f"{MODULE_PATH}._fetch_saved_view", return_value=None), patch(f"{MODULE_PATH}.delete_saved_view") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]
