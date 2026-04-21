# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/variable_sets.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.variable_sets import (
    apply_to_projects,
    apply_to_workspaces,
    create_variable_set,
    delete_variable_set,
    get_variable_set,
    get_variable_set_by_name,
    list_variable_sets,
    remove_from_projects,
    remove_from_workspaces,
    update_variable_set,
)

ADAPTER_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.variable_sets"


def _make_model(payload):
    model = Mock()
    model.model_dump.return_value = payload
    return model


class TestListVariableSets:
    def test_success(self):
        adapter = Mock()
        adapter.client.variable_sets.list.return_value = iter(
            [
                _make_model({"id": "varset-1", "name": "a"}),
                _make_model({"id": "varset-2", "name": "b"}),
            ]
        )
        assert list_variable_sets(adapter, "my-org") == [
            {"id": "varset-1", "name": "a"},
            {"id": "varset-2", "name": "b"},
        ]

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.variable_sets.list.side_effect = NotFound("none")
        assert list_variable_sets(adapter, "my-org") == []


class TestGetVariableSet:
    def test_success_no_relations(self):
        adapter = Mock()
        adapter.client.variable_sets.read.return_value = _make_model({"id": "varset-1", "name": "a"})
        assert get_variable_set(adapter, "varset-1") == {"id": "varset-1", "name": "a"}
        # options=None when include_relations is False
        _, kwargs = adapter.client.variable_sets.read.call_args
        assert kwargs.get("options") is None

    def test_success_with_relations_passes_read_options(self):
        adapter = Mock()
        adapter.client.variable_sets.read.return_value = _make_model(
            {"id": "varset-1", "workspaces": [{"id": "ws-1"}], "projects": []}
        )
        result = get_variable_set(adapter, "varset-1", include_relations=True)
        assert result["workspaces"][0]["id"] == "ws-1"
        _, kwargs = adapter.client.variable_sets.read.call_args
        assert kwargs["options"] is not None

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.variable_sets.read.side_effect = NotFound("missing")
        assert get_variable_set(adapter, "varset-missing") is None


class TestGetByName:
    def test_match(self):
        adapter = Mock()
        adapter.client.variable_sets.list.return_value = iter(
            [
                _make_model({"id": "varset-1", "name": "a"}),
                _make_model({"id": "varset-2", "name": "b"}),
            ]
        )
        assert get_variable_set_by_name(adapter, "my-org", "b") == {"id": "varset-2", "name": "b"}

    def test_no_match(self):
        adapter = Mock()
        adapter.client.variable_sets.list.return_value = iter([])
        assert get_variable_set_by_name(adapter, "my-org", "ghost") is None


class TestCreateVariableSet:
    @patch(f"{ADAPTER_PATH}.safe_api_call")
    @patch(f"{ADAPTER_PATH}.VariableSetCreateOptions")
    def test_create_uses_sdk_options(self, mock_options_cls, mock_safe_call):
        adapter = Mock()
        options = Mock()
        mock_options_cls.model_validate.return_value = options
        mock_safe_call.return_value = _make_model({"id": "varset-1", "name": "a", "global": False})

        data = {"name": "a", "global": False, "description": "x"}
        result = create_variable_set(adapter, "my-org", data)

        mock_options_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.variable_sets.create
        assert args[1] == "my-org"
        assert args[2] is options
        assert "error_context" in kwargs
        assert result == {"id": "varset-1", "name": "a", "global": False}


class TestUpdateVariableSet:
    @patch(f"{ADAPTER_PATH}.safe_api_call")
    @patch(f"{ADAPTER_PATH}.VariableSetUpdateOptions")
    def test_update_uses_sdk_options(self, mock_options_cls, mock_safe_call):
        adapter = Mock()
        options = Mock()
        mock_options_cls.model_validate.return_value = options
        mock_safe_call.return_value = _make_model({"id": "varset-1", "description": "new"})

        result = update_variable_set(adapter, "varset-1", {"description": "new"})

        mock_options_cls.model_validate.assert_called_once_with({"description": "new"})
        args, _ = mock_safe_call.call_args
        assert args[0] is adapter.client.variable_sets.update
        assert args[1] == "varset-1"
        assert args[2] is options
        assert result["description"] == "new"


class TestDeleteVariableSet:
    @patch(f"{ADAPTER_PATH}.safe_api_call")
    def test_delete(self, mock_safe_call):
        adapter = Mock()
        delete_variable_set(adapter, "varset-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.variable_sets.delete
        assert args[1] == "varset-1"
        assert "error_context" in kwargs


class TestAttachments:
    @patch(f"{ADAPTER_PATH}.safe_api_call")
    def test_apply_to_workspaces(self, mock_safe_call):
        adapter = Mock()
        apply_to_workspaces(adapter, "varset-1", ["ws-a", "ws-b"])
        args, _ = mock_safe_call.call_args
        assert args[0] is adapter.client.variable_sets.apply_to_workspaces
        assert args[1] == "varset-1"

    @patch(f"{ADAPTER_PATH}.safe_api_call")
    def test_apply_to_workspaces_empty_is_noop(self, mock_safe_call):
        adapter = Mock()
        apply_to_workspaces(adapter, "varset-1", [])
        mock_safe_call.assert_not_called()

    @patch(f"{ADAPTER_PATH}.safe_api_call")
    def test_remove_from_workspaces(self, mock_safe_call):
        adapter = Mock()
        remove_from_workspaces(adapter, "varset-1", ["ws-a"])
        args, _ = mock_safe_call.call_args
        assert args[0] is adapter.client.variable_sets.remove_from_workspaces

    @patch(f"{ADAPTER_PATH}.safe_api_call")
    def test_remove_from_workspaces_empty_is_noop(self, mock_safe_call):
        adapter = Mock()
        remove_from_workspaces(adapter, "varset-1", [])
        mock_safe_call.assert_not_called()

    @patch(f"{ADAPTER_PATH}.safe_api_call")
    def test_apply_to_projects(self, mock_safe_call):
        adapter = Mock()
        apply_to_projects(adapter, "varset-1", ["prj-a"])
        args, _ = mock_safe_call.call_args
        assert args[0] is adapter.client.variable_sets.apply_to_projects

    @patch(f"{ADAPTER_PATH}.safe_api_call")
    def test_remove_from_projects(self, mock_safe_call):
        adapter = Mock()
        remove_from_projects(adapter, "varset-1", ["prj-a"])
        args, _ = mock_safe_call.call_args
        assert args[0] is adapter.client.variable_sets.remove_from_projects
