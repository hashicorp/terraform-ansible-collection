# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/explorer_info.py."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.explorer_info import _build_query_options, main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.explorer_info"


def _mock_module(params, check_mode=False):
    mock_module = Mock()
    mock_module.params = params
    mock_module.check_mode = check_mode

    mock_adapter = Mock()
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_adapter)
    mock_context.__exit__ = Mock(return_value=False)
    mock_module.client.return_value = mock_context
    return mock_module, mock_adapter


class TestBuildQueryOptions:
    def test_all_params_mapped(self):
        params = {
            "view_type": "workspaces",
            "filters": [{"index": 0, "field": "workspace_name", "operator": "contains", "value": "prod"}],
            "sort": "-workspace_name",
            "fields": "workspace_name,id",
            "page_number": 1,
            "page_size": 10,
        }
        opts = _build_query_options(params)
        assert opts.view_type.value == "workspaces"
        assert opts.sort == "-workspace_name"
        assert opts.fields == "workspace_name,id"
        assert opts.page_number == 1
        assert opts.page_size == 10
        assert len(opts.filters) == 1
        assert opts.filters[0].field == "workspace_name"

    def test_no_filters_produces_none(self):
        params = {"view_type": "workspaces", "filters": None, "sort": None, "fields": None, "page_number": None, "page_size": None}
        assert _build_query_options(params).filters is None

    def test_filter_index_defaults_to_enumeration_position(self):
        params = {
            "view_type": "workspaces",
            "filters": [
                {"field": "workspace_name", "operator": "is", "value": "prod"},
                {"field": "workspace_name", "operator": "is", "value": "dev"},
            ],
            "sort": None,
            "fields": None,
            "page_number": None,
            "page_size": None,
        }
        opts = _build_query_options(params)
        assert opts.filters[0].index == 0
        assert opts.filters[1].index == 1

    def test_all_view_types_accepted(self):
        for vt in ("workspaces", "tf_versions", "providers", "modules"):
            opts = _build_query_options({"view_type": vt, "filters": None, "sort": None, "fields": None, "page_number": None, "page_size": None})
            assert opts.view_type.value == vt


class TestExplorerInfoViewTypeBranch:
    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.query_explorer")
    def test_ad_hoc_query_returns_rows(self, mock_query, mock_module_class):
        rows = [{"id": "ws-1", "type": "visibility-workspace", "attributes": {"workspace_name": "demo"}}]
        mock_module, mock_adapter = _mock_module(
            {
                "organization": "my-org",
                "view_type": "workspaces",
                "view_id": None,
                "filters": None,
                "sort": None,
                "fields": None,
                "page_number": None,
                "page_size": None,
            }
        )
        mock_module_class.return_value = mock_module
        mock_query.return_value = rows

        main()

        mock_query.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["rows"] == rows
        assert result["changed"] is False
        assert "saved_view" not in result

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.query_explorer")
    def test_ad_hoc_query_not_found_returns_empty_rows(self, mock_query, mock_module_class):
        mock_module, mock_adapter = _mock_module(
            {
                "organization": "my-org",
                "view_type": "workspaces",
                "view_id": None,
                "filters": None,
                "sort": None,
                "fields": None,
                "page_number": None,
                "page_size": None,
            }
        )
        mock_module_class.return_value = mock_module
        mock_query.return_value = []

        main()

        result = mock_module.exit_json.call_args[1]
        assert result["rows"] == []


class TestExplorerInfoViewIdBranch:
    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.get_saved_view_results")
    @patch(f"{MODULE_PATH}.get_saved_view")
    def test_saved_view_returns_view_and_rows(self, mock_get_view, mock_get_results, mock_module_class):
        view = {"id": "sq-1", "name": "my-view", "query_type": "workspaces"}
        rows = [{"id": "ws-1", "type": "visibility-workspace", "attributes": {}}]
        mock_module, mock_adapter = _mock_module({"organization": "my-org", "view_id": "sq-1", "view_type": None})
        mock_module_class.return_value = mock_module
        mock_get_view.return_value = view
        mock_get_results.return_value = rows

        main()

        mock_get_view.assert_called_once_with(mock_adapter, "my-org", "sq-1")
        mock_get_results.assert_called_once_with(mock_adapter, "my-org", "sq-1")
        result = mock_module.exit_json.call_args[1]
        assert result["saved_view"] == view
        assert result["rows"] == rows

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.get_saved_view")
    def test_saved_view_not_found_fails(self, mock_get_view, mock_module_class):
        mock_module, _mock_adapter = _mock_module({"organization": "my-org", "view_id": "sq-missing", "view_type": None})
        mock_module_class.return_value = mock_module
        mock_get_view.return_value = None

        main()

        mock_module.fail_json.assert_called_once()
        assert "not found" in mock_module.fail_json.call_args[1]["msg"]
