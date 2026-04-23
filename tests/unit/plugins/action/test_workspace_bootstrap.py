# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import MagicMock, Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.action.workspace_bootstrap import ActionModule

MOD = "ansible_collections.hashicorp.terraform.plugins.action.workspace_bootstrap"


def _make_action(args):
    task = Mock(args=args)
    task.async_val = 0
    return ActionModule(
        task=task,
        connection=Mock(),
        play_context=Mock(),
        loader=Mock(),
        templar=Mock(),
        shared_loader_obj=Mock(),
    )


@pytest.fixture
def patched_client():
    with patch(f"{MOD}.TerraformClient") as mock_class:
        mock_client = Mock()
        ctx = MagicMock()
        ctx.__enter__.return_value = mock_client
        ctx.__exit__.return_value = False
        mock_class.from_mapping.return_value = ctx
        yield mock_client, mock_class


class TestWorkspaceReconcile:

    @patch(f"{MOD}.get_workspace")
    @patch(f"{MOD}.create_workspace")
    def test_create_when_missing(self, mock_create, mock_get, patched_client):
        mock_get.return_value = None
        mock_create.return_value = {"data": {"id": "ws-new"}}
        action = _make_action({"organization": "acme", "workspace": "web", "settings": {"description": "x"}})
        result = action.run()
        assert result["changed"] is True
        assert result["workspace_id"] == "ws-new"
        assert result["components"]["workspace"]["action"] == "created"

    @patch(f"{MOD}.get_workspace")
    def test_no_change_when_matching(self, mock_get, patched_client):
        mock_get.return_value = {"id": "ws-1", "description": "x", "auto_apply": False}
        action = _make_action({
            "organization": "acme", "workspace": "web",
            "settings": {"description": "x", "auto_apply": False},
        })
        result = action.run()
        assert result["components"]["workspace"]["action"] == "none"
        assert result["changed"] is False

    @patch(f"{MOD}.update_workspace")
    @patch(f"{MOD}.get_workspace")
    def test_updates_on_drift(self, mock_get, mock_update, patched_client):
        mock_get.return_value = {"id": "ws-1", "description": "old"}
        action = _make_action({
            "organization": "acme", "workspace": "web",
            "settings": {"description": "new"},
        })
        result = action.run()
        assert result["components"]["workspace"]["action"] == "updated"
        assert result["changed"] is True
        mock_update.assert_called_once()


class TestVariablesReconcile:

    @patch(f"{MOD}._list_workspace_variables")
    @patch(f"{MOD}.delete_variable")
    @patch(f"{MOD}.update_variable")
    @patch(f"{MOD}.create_variable")
    @patch(f"{MOD}.get_variable_by_key")
    @patch(f"{MOD}.get_workspace_by_id")
    def test_create_update_delete(
        self, mock_get_ws, mock_get_var, mock_create, mock_update, mock_delete, mock_list, patched_client
    ):
        mock_get_ws.return_value = {"id": "ws-1"}
        # var "a" missing -> create ; var "b" drift -> update
        mock_get_var.side_effect = lambda adapter, ws, key, category="terraform": (
            None if key == "a" else {"id": "var-b", "value": "old", "category": "terraform"}
        )
        mock_list.return_value = [
            {"id": "var-a", "key": "a", "category": "terraform"},
            {"id": "var-b", "key": "b", "category": "terraform"},
            {"id": "var-c", "key": "c", "category": "terraform"},
        ]
        args = {
            "workspace_id": "ws-1",
            "variables": [
                {"key": "a", "value": "1"},
                {"key": "b", "value": "new"},
            ],
            "reconcile": True,
        }
        result = _make_action(args).run()
        summary = result["components"]["variables"]
        assert "a" in summary["created"]
        assert "b" in summary["updated"]
        assert "c" in summary["deleted"]
        assert summary["changed"] is True
        mock_create.assert_called_once()
        mock_update.assert_called_once()
        mock_delete.assert_called_once()


class TestVariableSetsReconcile:

    @patch(f"{MOD}.apply_to_workspaces")
    @patch(f"{MOD}.get_variable_set")
    @patch(f"{MOD}.get_workspace_by_id")
    def test_attach_if_not_attached(self, mock_get_ws, mock_get_vs, mock_apply, patched_client):
        mock_get_ws.return_value = {"id": "ws-1"}
        mock_get_vs.return_value = {"id": "varset-1", "workspaces": []}
        args = {"workspace_id": "ws-1", "variable_sets": ["varset-1"]}
        result = _make_action(args).run()
        assert "varset-1" in result["components"]["variable_sets"]["attached"]
        mock_apply.assert_called_once()

    @patch(f"{MOD}.apply_to_workspaces")
    @patch(f"{MOD}.get_variable_set")
    @patch(f"{MOD}.get_workspace_by_id")
    def test_noop_if_already_attached(self, mock_get_ws, mock_get_vs, mock_apply, patched_client):
        mock_get_ws.return_value = {"id": "ws-1"}
        mock_get_vs.return_value = {"id": "varset-1", "workspaces": [{"id": "ws-1"}]}
        args = {"workspace_id": "ws-1", "variable_sets": ["varset-1"]}
        result = _make_action(args).run()
        assert result["components"]["variable_sets"]["attached"] == []
        mock_apply.assert_not_called()


class TestRunTriggersReconcile:

    @patch(f"{MOD}.list_run_triggers")
    @patch(f"{MOD}.delete_run_trigger")
    @patch(f"{MOD}.create_run_trigger")
    @patch(f"{MOD}.find_run_trigger")
    @patch(f"{MOD}.get_workspace_by_id")
    def test_create_and_reconcile_extras(
        self, mock_get_ws, mock_find, mock_create, mock_delete, mock_list, patched_client
    ):
        mock_get_ws.return_value = {"id": "ws-1"}
        mock_find.return_value = None
        mock_list.return_value = [
            {"id": "rt-old", "sourceable": {"id": "ws-old"}},
        ]
        args = {"workspace_id": "ws-1", "run_triggers": ["ws-src-new"], "reconcile": True}
        result = _make_action(args).run()
        summary = result["components"]["run_triggers"]
        assert "ws-src-new" in summary["created"]
        assert "rt-old" in summary["deleted"]
        mock_create.assert_called_once()
        mock_delete.assert_called_once()


class TestNotificationsReconcile:

    @patch(f"{MOD}.list_notification_configurations")
    @patch(f"{MOD}.delete_notification_configuration")
    @patch(f"{MOD}.update_notification_configuration")
    @patch(f"{MOD}.create_notification_configuration")
    @patch(f"{MOD}.get_notification_configuration_by_name")
    @patch(f"{MOD}.get_workspace_by_id")
    def test_create_update_delete_flow(
        self, mock_get_ws, mock_get_name, mock_create, mock_update, mock_delete, mock_list, patched_client
    ):
        mock_get_ws.return_value = {"id": "ws-1"}
        mock_get_name.side_effect = lambda adapter, ws, name: (
            None if name == "slack-new" else {"id": "nc-email", "name": "email", "destination_type": "email", "url": "x"}
        )
        mock_list.return_value = [
            {"id": "nc-email", "name": "email"},
            {"id": "nc-gone", "name": "gone"},
        ]
        args = {
            "workspace_id": "ws-1",
            "notifications": [
                {"name": "slack-new", "destination_type": "slack", "url": "https://hook"},
                {"name": "email", "destination_type": "email", "url": "new"},
            ],
            "reconcile": True,
        }
        result = _make_action(args).run()
        summary = result["components"]["notifications"]
        assert "slack-new" in summary["created"]
        assert "email" in summary["updated"]
        assert "gone" in summary["deleted"]


class TestErrorHandling:

    @patch(f"{MOD}.get_workspace")
    def test_value_error_surfaces(self, mock_get, patched_client):
        mock_get.return_value = None
        args = {"organization": "acme"}  # missing workspace name
        result = _make_action(args).run()
        assert result["failed"] is True

    @patch(f"{MOD}.get_workspace_by_id")
    def test_generic_exception_wrapped(self, mock_get_ws, patched_client):
        mock_get_ws.side_effect = RuntimeError("boom")
        result = _make_action({"workspace_id": "ws-1"}).run()
        assert result["failed"] is True
        assert "workspace_bootstrap failed" in result["msg"]
