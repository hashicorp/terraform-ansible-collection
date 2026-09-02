# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/policy_set.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set import (
    create_policy_set,
    delete_policy_set,
    get_policy_set,
    get_policy_set_by_name,
    list_policy_sets,
    sync_relationship,
    update_policy_set,
)

MOD = "ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestListPolicySets:
    def test_success(self):
        adapter = Mock()
        adapter.client.policy_sets.list.return_value = iter([_make_model({"id": "polset-1", "name": "a"})])
        assert list_policy_sets(adapter, "my-org") == [{"id": "polset-1", "name": "a"}]

    def test_normalizes_global_alias(self):
        adapter = Mock()
        adapter.client.policy_sets.list.return_value = iter([_make_model({"id": "polset-1", "name": "a", "Global": False})])

        assert list_policy_sets(adapter, "my-org") == [{"id": "polset-1", "name": "a", "global": False}]

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.policy_sets.list.side_effect = NotFound("nope")
        assert list_policy_sets(adapter, "my-org") == []


class TestGetPolicySet:
    def test_success(self):
        adapter = Mock()
        adapter.client.policy_sets.read.return_value = _make_model({"id": "polset-1"})
        assert get_policy_set(adapter, "polset-1") == {"id": "polset-1"}

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.policy_sets.read.side_effect = NotFound("missing")
        assert get_policy_set(adapter, "polset-missing") is None


class TestGetPolicySetByName:
    def test_match(self):
        adapter = Mock()
        adapter.client.policy_sets.list.return_value = iter([_make_model({"id": "polset-1", "name": "a"}), _make_model({"id": "polset-2", "name": "b"})])
        assert get_policy_set_by_name(adapter, "org", "b") == {"id": "polset-2", "name": "b"}

    def test_no_match(self):
        adapter = Mock()
        adapter.client.policy_sets.list.return_value = iter([])
        assert get_policy_set_by_name(adapter, "org", "ghost") is None


class TestCreatePolicySet:
    @patch(f"{MOD}.safe_api_call")
    @patch(f"{MOD}.PolicySetCreateOptions")
    def test_create_attrs_only(self, mock_opts_cls, mock_safe_call):
        # Regression: pytfe's PolicySets.create() raises AttributeError if
        # relationship data is present in the options (model_dump() turns
        # nested models into dicts, then pytfe does dict.id on them) - this
        # adapter must never pass relationship keys through to create().
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "polset-1", "name": "a"})

        data = {"name": "a", "kind": "sentinel"}
        result = create_policy_set(adapter, "my-org", data)

        mock_opts_cls.model_validate.assert_called_once_with(data)
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policy_sets.create
        assert args[1] == "my-org"
        assert args[2] is opts
        assert result == {"id": "polset-1", "name": "a"}


class TestUpdatePolicySet:
    @patch(f"{MOD}.safe_api_call")
    @patch(f"{MOD}.PolicySetUpdateOptions")
    def test_update_uses_sdk_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "polset-1", "description": "new"})

        result = update_policy_set(adapter, "polset-1", {"description": "new"})

        mock_opts_cls.model_validate.assert_called_once_with({"description": "new"})
        args, _kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policy_sets.update
        assert args[1] == "polset-1"
        assert result == {"id": "polset-1", "description": "new"}


class TestDeletePolicySet:
    @patch(f"{MOD}.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_policy_set(adapter, "polset-1")
        args, _kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policy_sets.delete
        assert args[1] == "polset-1"


class TestSyncRelationship:
    @patch(f"{MOD}.safe_api_call")
    def test_add_only(self, mock_safe_call):
        adapter = Mock()
        sync_relationship(adapter, "polset-1", "policies", add_ids=["pol-1"], remove_ids=[])
        mock_safe_call.assert_called_once()
        args, _kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policy_sets.add_policies
        assert args[1] == "polset-1"

    @patch(f"{MOD}.safe_api_call")
    def test_remove_only(self, mock_safe_call):
        adapter = Mock()
        sync_relationship(adapter, "polset-1", "workspaces", add_ids=[], remove_ids=["ws-1"])
        mock_safe_call.assert_called_once()
        args, _kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.policy_sets.remove_workspaces
        assert args[1] == "polset-1"

    @patch(f"{MOD}.safe_api_call")
    def test_add_and_remove(self, mock_safe_call):
        adapter = Mock()
        sync_relationship(adapter, "polset-1", "projects", add_ids=["prj-1"], remove_ids=["prj-2"])
        assert mock_safe_call.call_count == 2
        called_methods = {call.args[0] for call in mock_safe_call.call_args_list}
        assert adapter.client.policy_sets.add_projects in called_methods
        assert adapter.client.policy_sets.remove_projects in called_methods

    @patch(f"{MOD}.safe_api_call")
    def test_no_ids_is_noop(self, mock_safe_call):
        adapter = Mock()
        sync_relationship(adapter, "polset-1", "project_exclusions", add_ids=[], remove_ids=[])
        mock_safe_call.assert_not_called()
