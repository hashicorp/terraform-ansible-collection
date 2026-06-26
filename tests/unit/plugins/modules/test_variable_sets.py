# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/variable_sets.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.variable_sets import (
    _build_desired_attrs,
    _build_parent,
    _extract_ids,
    _filter_current_attrs,
    _reconcile_attachments,
    _resolve_variable_set,
    _validate_attachment_scope,
    main,
    state_absent,
    state_present,
)

MODULE = "ansible_collections.hashicorp.terraform.plugins.modules.variable_sets"


class TestHelpers:
    def test_build_desired_attrs(self):
        params = {
            "name": "a",
            "description": None,
            "global": False,
            "priority": True,
            "variable_set_id": "ignored",
            "organization": "my-org",
            "workspace_ids": ["ws-1"],
            "tfe_token": "secret",
            "state": "present",
        }
        assert _build_desired_attrs(params) == {"name": "a", "global": False, "priority": True}

    def test_filter_current_attrs(self):
        have = {"name": "a", "description": "d", "global": False, "priority": False, "id": "varset-1"}
        want = {"name": "a", "priority": True}
        assert _filter_current_attrs(have, want) == {"name": "a", "priority": False}

    def test_extract_ids(self):
        assert _extract_ids([{"id": "a"}, {"id": "b"}, {"no_id": True}]) == ["a", "b"]
        assert _extract_ids(None) == []
        assert _extract_ids([]) == []

    def test_reconcile_attachments_none_means_untouched(self):
        to_add, to_remove, final = _reconcile_attachments(None, ["ws-1"])
        assert to_add == set() and to_remove == set()
        assert final == ["ws-1"]

    def test_reconcile_attachments_diff(self):
        to_add, to_remove, final = _reconcile_attachments(["ws-b", "ws-c"], ["ws-a", "ws-b"])
        assert to_add == {"ws-c"}
        assert to_remove == {"ws-a"}
        assert final == ["ws-b", "ws-c"]

    def test_reconcile_attachments_empty_detaches_all(self):
        to_add, to_remove, final = _reconcile_attachments([], ["ws-1", "ws-2"])
        assert to_add == set()
        assert to_remove == {"ws-1", "ws-2"}
        assert final == []

    def test_validate_attachment_scope_rejects_global_with_workspaces(self):
        with pytest.raises(ValueError, match="global"):
            _validate_attachment_scope({"global": True, "workspace_ids": ["ws-1"]}, current_global=None)

    def test_validate_attachment_scope_uses_current_when_desired_omitted(self):
        with pytest.raises(ValueError, match="global"):
            _validate_attachment_scope({"project_ids": ["prj-1"]}, current_global=True)

    def test_validate_attachment_scope_non_global_passes(self):
        _validate_attachment_scope({"global": False, "workspace_ids": ["ws-1"]}, current_global=False)

    def test_build_parent_project(self):
        assert _build_parent({"parent_project_id": "prj-1"}) == {"project": {"id": "prj-1"}}

    def test_build_parent_organization(self):
        assert _build_parent({"parent_organization_name": "my-org"}) == {"organization": {"name": "my-org"}}

    def test_build_parent_project_takes_precedence(self):
        assert _build_parent({"parent_project_id": "prj-1", "parent_organization_name": "my-org"}) == {"project": {"id": "prj-1"}}

    def test_build_parent_none(self):
        assert _build_parent({}) is None


class TestResolveVariableSet:
    def test_by_id(self):
        adapter = Mock()
        with patch(f"{MODULE}.get_variable_set", return_value={"id": "varset-1"}) as mock_get:
            assert _resolve_variable_set(adapter, {"variable_set_id": "varset-1"}) == {"id": "varset-1"}
            mock_get.assert_called_once_with(adapter, "varset-1", include_relations=True)

    def test_by_name_double_fetches_with_relations(self):
        adapter = Mock()
        with patch(f"{MODULE}.get_variable_set_by_name", return_value={"id": "varset-9", "name": "n"}), patch(
            f"{MODULE}.get_variable_set", return_value={"id": "varset-9", "name": "n", "workspaces": []}
        ) as mock_get:
            result = _resolve_variable_set(adapter, {"name": "n", "organization": "my-org"})

        assert result["workspaces"] == []
        mock_get.assert_called_once_with(adapter, "varset-9", include_relations=True)

    def test_missing(self):
        adapter = Mock()
        with patch(f"{MODULE}.get_variable_set_by_name", return_value=None):
            assert _resolve_variable_set(adapter, {"name": "n", "organization": "my-org"}) is None


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def _base_params(self, **overrides):
        params = {
            "variable_set_id": None,
            "name": "shared-aws",
            "organization": "my-org",
            "description": "shared",
            "global": False,
            "priority": False,
            "workspace_ids": None,
            "project_ids": None,
            "state": "present",
            "check_mode": False,
        }
        params.update(overrides)
        return params

    def test_create_when_missing(self, adapter):
        params = self._base_params()
        with patch(f"{MODULE}._resolve_variable_set", return_value=None), patch(
            f"{MODULE}.create_variable_set",
            return_value={"id": "varset-1", "name": "shared-aws", "global": False},
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)

        mock_create.assert_called_once()
        args = mock_create.call_args.args
        assert args[1] == "my-org"
        assert args[2]["name"] == "shared-aws"
        assert args[2]["global"] is False
        assert result["changed"] is True
        assert result["id"] == "varset-1"

    def test_create_with_parent_project(self, adapter):
        params = self._base_params(parent_project_id="prj-1")
        with patch(f"{MODULE}._resolve_variable_set", return_value=None), patch(
            f"{MODULE}.create_variable_set",
            return_value={"id": "varset-1", "name": "shared-aws", "global": False},
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)

        args = mock_create.call_args.args
        assert args[2]["parent"] == {"project": {"id": "prj-1"}}
        assert result["changed"] is True

    def test_create_requires_name(self, adapter):
        params = self._base_params(name=None)
        with patch(f"{MODULE}._resolve_variable_set", return_value=None):
            with pytest.raises(ValueError, match="name"):
                state_present(adapter, params, check_mode=False)

    def test_create_requires_organization(self, adapter):
        params = self._base_params(organization=None)
        with patch(f"{MODULE}._resolve_variable_set", return_value=None):
            with pytest.raises(ValueError, match="organization"):
                state_present(adapter, params, check_mode=False)

    def test_create_check_mode(self, adapter):
        params = self._base_params()
        with patch(f"{MODULE}._resolve_variable_set", return_value=None), patch(f"{MODULE}.create_variable_set") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_idempotent_no_diff(self, adapter):
        current = {
            "id": "varset-1",
            "name": "shared-aws",
            "description": "shared",
            "global": False,
            "priority": False,
            "workspaces": [],
            "projects": [],
        }
        params = self._base_params()
        with patch(f"{MODULE}._resolve_variable_set", return_value=current), patch(f"{MODULE}.update_variable_set") as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "varset-1"

    def test_update_on_attr_drift(self, adapter):
        current = {
            "id": "varset-1",
            "name": "shared-aws",
            "description": "old",
            "global": False,
            "priority": False,
            "workspaces": [],
            "projects": [],
        }
        params = self._base_params(description="new")
        with patch(f"{MODULE}._resolve_variable_set", return_value=current), patch(
            f"{MODULE}.update_variable_set",
            return_value={"id": "varset-1", "name": "shared-aws", "description": "new"},
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
        mock_update.assert_called_once()
        args = mock_update.call_args.args
        assert args[1] == "varset-1"
        assert args[2]["description"] == "new"
        assert result["changed"] is True

    def test_attachment_add_and_remove(self, adapter):
        current = {
            "id": "varset-1",
            "name": "shared-aws",
            "description": "shared",
            "global": False,
            "priority": False,
            "workspaces": [{"id": "ws-a"}, {"id": "ws-b"}],
            "projects": [],
        }
        params = self._base_params(workspace_ids=["ws-b", "ws-c"])
        with patch(f"{MODULE}._resolve_variable_set", return_value=current), patch(f"{MODULE}.update_variable_set") as mock_update, patch(
            f"{MODULE}.apply_to_workspaces"
        ) as mock_apply, patch(f"{MODULE}.remove_from_workspaces") as mock_remove:
            result = state_present(adapter, params, check_mode=False)

        # No attribute drift → no update call.
        mock_update.assert_not_called()
        mock_remove.assert_called_once_with(adapter, "varset-1", ["ws-a"])
        mock_apply.assert_called_once_with(adapter, "varset-1", ["ws-c"])
        assert result["changed"] is True
        assert result["workspace_ids"] == ["ws-b", "ws-c"]

    def test_attachment_empty_list_detaches_all(self, adapter):
        current = {
            "id": "varset-1",
            "name": "shared-aws",
            "description": "shared",
            "global": False,
            "priority": False,
            "workspaces": [{"id": "ws-a"}],
            "projects": [{"id": "prj-a"}],
        }
        params = self._base_params(workspace_ids=[], project_ids=[])
        with patch(f"{MODULE}._resolve_variable_set", return_value=current), patch(f"{MODULE}.remove_from_workspaces") as mock_rm_ws, patch(
            f"{MODULE}.remove_from_projects"
        ) as mock_rm_pr, patch(f"{MODULE}.apply_to_workspaces") as mock_app_ws, patch(f"{MODULE}.apply_to_projects") as mock_app_pr:
            result = state_present(adapter, params, check_mode=False)

        mock_rm_ws.assert_called_once_with(adapter, "varset-1", ["ws-a"])
        mock_rm_pr.assert_called_once_with(adapter, "varset-1", ["prj-a"])
        mock_app_ws.assert_not_called()
        mock_app_pr.assert_not_called()
        assert result["changed"] is True
        assert result["workspace_ids"] == []
        assert result["project_ids"] == []

    def test_attachment_idempotent_when_already_matching(self, adapter):
        current = {
            "id": "varset-1",
            "name": "shared-aws",
            "description": "shared",
            "global": False,
            "priority": False,
            "workspaces": [{"id": "ws-a"}, {"id": "ws-b"}],
            "projects": [],
        }
        params = self._base_params(workspace_ids=["ws-b", "ws-a"])
        with patch(f"{MODULE}._resolve_variable_set", return_value=current), patch(f"{MODULE}.apply_to_workspaces") as mock_apply, patch(
            f"{MODULE}.remove_from_workspaces"
        ) as mock_remove:
            result = state_present(adapter, params, check_mode=False)

        mock_apply.assert_not_called()
        mock_remove.assert_not_called()
        assert result["changed"] is False

    def test_rejects_workspace_ids_on_global(self, adapter):
        params = self._base_params(**{"global": True, "workspace_ids": ["ws-1"]})
        with patch(f"{MODULE}._resolve_variable_set", return_value=None):
            with pytest.raises(ValueError, match="global"):
                state_present(adapter, params, check_mode=False)

    def test_rejects_attachments_when_currently_global(self, adapter):
        """Desired `global` omitted but the server-side set is global."""
        current = {"id": "varset-1", "name": "shared-aws", "global": True, "workspaces": [], "projects": []}
        params = self._base_params(**{"global": None, "workspace_ids": ["ws-1"]})
        with patch(f"{MODULE}._resolve_variable_set", return_value=current):
            with pytest.raises(ValueError, match="global"):
                state_present(adapter, params, check_mode=False)

    def test_update_check_mode(self, adapter):
        current = {
            "id": "varset-1",
            "name": "shared-aws",
            "description": "old",
            "global": False,
            "priority": False,
            "workspaces": [],
            "projects": [],
        }
        params = self._base_params(description="new")
        with patch(f"{MODULE}._resolve_variable_set", return_value=current), patch(f"{MODULE}.update_variable_set") as mock_update:
            result = state_present(adapter, params, check_mode=True)
        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_existing(self, adapter):
        params = {"variable_set_id": "varset-1", "state": "absent", "check_mode": False}
        with patch(f"{MODULE}._resolve_variable_set", return_value={"id": "varset-1"}), patch(f"{MODULE}.delete_variable_set") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "varset-1")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_delete_absent_is_noop(self, adapter):
        params = {"variable_set_id": "varset-ghost", "state": "absent", "check_mode": False}
        with patch(f"{MODULE}._resolve_variable_set", return_value=None), patch(f"{MODULE}.delete_variable_set") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        params = {"variable_set_id": "varset-1", "state": "absent", "check_mode": True}
        with patch(f"{MODULE}._resolve_variable_set", return_value={"id": "varset-1"}), patch(f"{MODULE}.delete_variable_set") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestMain:
    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_argument_spec(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"name": "a", "organization": "my-org", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", side_effect=Exception("stop")):
            with pytest.raises(AssertionError):
                main()

        call_kwargs = mock_ansible_module.call_args[1]
        argument_spec = call_kwargs["argument_spec"]
        assert argument_spec["state"]["choices"] == ["present", "absent"]
        assert argument_spec["global"]["type"] == "bool"
        assert argument_spec["workspace_ids"]["type"] == "list"
        assert argument_spec["workspace_ids"]["elements"] == "str"
        assert "workspace_id" not in argument_spec
        assert "project_id" not in argument_spec
        assert ("variable_set_id", "name") in call_kwargs["mutually_exclusive"]
        assert call_kwargs["supports_check_mode"] is True
        assert ("variable_set_id", "name") in call_kwargs["required_one_of"]

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_main_present_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"name": "a", "organization": "my-org", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", return_value={"changed": True, "id": "varset-1"}) as mock_present:
            with pytest.raises(SystemExit):
                main()

        mock_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True
        assert mock_module.exit_args["id"] == "varset-1"

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_main_absent_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"variable_set_id": "varset-1", "state": "absent"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(
            f"{MODULE}.state_absent",
            return_value={"changed": True, "msg": "Variable set varset-1 has been deleted successfully"},
        ) as mock_absent:
            with pytest.raises(SystemExit):
                main()

        mock_absent.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_main_propagates_errors_via_fail_json(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"name": "a", "organization": "my-org", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", side_effect=RuntimeError("boom")):
            with pytest.raises(AssertionError):
                main()

        assert mock_module.failed is True
        assert "boom" in mock_module.fail_args["msg"]
