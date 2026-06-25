# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/organization_tags.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.organization_tags import (
    main,
    state_absent,
    state_present,
)

MODULE = "ansible_collections.hashicorp.terraform.plugins.modules.organization_tags"
MODULE_UTILS = "ansible_collections.hashicorp.terraform.plugins.module_utils.organization_tags"


class TestStatePresentByName:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def _make_tag_list(self, tags):
        """Return an iterator-producing side_effect for organization_tags.list calls."""
        from pytfe.models.organization_tags import OrganizationTag

        return [OrganizationTag(id=tid, name=n) for tid, n in tags]

    def test_create_new_tag_single_workspace(self, adapter):
        """Tag doesn't exist: create it on ws-a, ws-a already associated after creation."""
        params = {"organization": "org", "name": "env:prod", "tag_id": None, "workspace_ids": ["ws-a"]}
        # list returns empty (tag absent), then returns new tag after creation
        adapter.client.organization_tags.list.side_effect = [
            iter([]),
            iter(self._make_tag_list([("tag-new", "env:prod")])),
        ]
        # After creation ws-a already has the tag, so get_workspace_tag_ids returns it.
        adapter.client.workspaces.list_tags.return_value = iter([])
        with patch(f"{MODULE}.create_tag_on_workspace") as mock_create, patch(f"{MODULE}.get_workspace_tag_ids", return_value={"tag-new"}):
            result = state_present(adapter, params, check_mode=False)

        mock_create.assert_called_once_with(adapter, "ws-a", "env:prod")
        assert result["changed"] is True
        assert result["id"] == "tag-new"
        assert result["name"] == "env:prod"
        # ws-a already associated via create_tag_on_workspace, so ws_to_add is empty
        assert result["workspace_ids"] == []

    def test_create_new_tag_multiple_workspaces(self, adapter):
        """Tag doesn't exist: create on ws-a, then associate ws-b."""
        params = {"organization": "org", "name": "env:prod", "tag_id": None, "workspace_ids": ["ws-a", "ws-b"]}

        def fake_resolve(adp, org, name):
            # First call returns None (doesn't exist), second returns the new ID.
            if not hasattr(fake_resolve, "called"):
                fake_resolve.called = True
                return None
            return "tag-new"

        def fake_ws_tags(adp, ws_id):
            # ws-a already has the tag (just created there); ws-b does not.
            return {"tag-new"} if ws_id == "ws-a" else set()

        with patch(f"{MODULE}.resolve_tag_by_name", side_effect=fake_resolve), patch(f"{MODULE}.create_tag_on_workspace") as mock_create, patch(
            f"{MODULE}.get_workspace_tag_ids", side_effect=fake_ws_tags
        ), patch(f"{MODULE}.add_workspaces_to_tag") as mock_add:
            result = state_present(adapter, params, check_mode=False)

        mock_create.assert_called_once_with(adapter, "ws-a", "env:prod")
        mock_add.assert_called_once_with(adapter, "org", "tag-new", ["ws-b"])
        assert result["changed"] is True
        assert result["workspace_ids"] == ["ws-b"]
        assert result["name"] == "env:prod"

    def test_existing_tag_by_name_associates_missing(self, adapter):
        """Tag exists; ws-b not yet associated — should associate."""
        params = {"organization": "org", "name": "env:prod", "tag_id": None, "workspace_ids": ["ws-a", "ws-b"]}

        def fake_ws_tags(adp, ws_id):
            return {"tag-existing"} if ws_id == "ws-a" else set()

        with patch(f"{MODULE}.resolve_tag_by_name", return_value="tag-existing"), patch(f"{MODULE}.create_tag_on_workspace") as mock_create, patch(
            f"{MODULE}.get_workspace_tag_ids", side_effect=fake_ws_tags
        ), patch(f"{MODULE}.add_workspaces_to_tag") as mock_add:
            result = state_present(adapter, params, check_mode=False)

        mock_create.assert_not_called()
        mock_add.assert_called_once_with(adapter, "org", "tag-existing", ["ws-b"])
        assert result["changed"] is True
        assert result["id"] == "tag-existing"
        assert result["name"] == "env:prod"

    def test_existing_tag_all_associated_is_noop(self, adapter):
        """Tag exists, all workspaces already associated — no-op."""
        params = {"organization": "org", "name": "env:prod", "tag_id": None, "workspace_ids": ["ws-a"]}
        with patch(f"{MODULE}.resolve_tag_by_name", return_value="tag-existing"), patch(f"{MODULE}.create_tag_on_workspace") as mock_create, patch(
            f"{MODULE}.get_workspace_tag_ids", return_value={"tag-existing"}
        ), patch(f"{MODULE}.add_workspaces_to_tag") as mock_add:
            result = state_present(adapter, params, check_mode=False)

        mock_create.assert_not_called()
        mock_add.assert_not_called()
        assert result["changed"] is False
        assert "already" in result["msg"]
        assert result["name"] == "env:prod"

    def test_check_mode_new_tag_does_not_mutate(self, adapter):
        """Tag doesn't exist + check_mode: report would-be change, no API mutations."""
        params = {"organization": "org", "name": "env:prod", "tag_id": None, "workspace_ids": ["ws-a"]}
        with patch(f"{MODULE}.resolve_tag_by_name", return_value=None), patch(f"{MODULE}.create_tag_on_workspace") as mock_create, patch(
            f"{MODULE}.add_workspaces_to_tag"
        ) as mock_add:
            result = state_present(adapter, params, check_mode=True)

        mock_create.assert_not_called()
        mock_add.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]
        assert result["name"] == "env:prod"

    def test_no_tag_id_and_no_name_raises(self, adapter):
        params = {"organization": "org", "tag_id": None, "name": None, "workspace_ids": ["ws-a"]}
        with pytest.raises(ValueError, match="tag_id.*name|Either"):
            state_present(adapter, params, check_mode=False)


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_requires_workspace_ids(self, adapter):
        params = {"organization": "org", "tag_id": "tag-5", "workspace_ids": None}
        with pytest.raises(ValueError, match="workspace_ids"):
            state_present(adapter, params, check_mode=False)

    def test_associate_new_workspaces(self, adapter):
        params = {"organization": "org", "tag_id": "tag-5", "workspace_ids": ["ws-b", "ws-a"]}
        with patch(f"{MODULE}.get_workspace_tag_ids", return_value=set()), patch(f"{MODULE}.add_workspaces_to_tag") as mock_add:
            result = state_present(adapter, params, check_mode=False)

        mock_add.assert_called_once_with(adapter, "org", "tag-5", ["ws-a", "ws-b"])
        assert result["changed"] is True
        assert result["workspace_ids"] == ["ws-a", "ws-b"]
        assert result["id"] == "tag-5"

    def test_all_already_associated_is_noop(self, adapter):
        params = {"organization": "org", "tag_id": "tag-5", "workspace_ids": ["ws-a", "ws-b"]}
        # Both workspaces already carry tag-5.
        with patch(f"{MODULE}.get_workspace_tag_ids", return_value={"tag-5", "tag-9"}), patch(f"{MODULE}.add_workspaces_to_tag") as mock_add:
            result = state_present(adapter, params, check_mode=False)

        mock_add.assert_not_called()
        assert result["changed"] is False
        assert result["workspace_ids"] == []
        assert "already associated" in result["msg"]

    def test_partial_association_skips_existing(self, adapter):
        params = {"organization": "org", "tag_id": "tag-5", "workspace_ids": ["ws-a", "ws-b"]}

        def fake_tag_ids(adapter, ws_id):
            # ws-a already has tag-5; ws-b does not.
            return {"tag-5"} if ws_id == "ws-a" else set()

        with patch(f"{MODULE}.get_workspace_tag_ids", side_effect=fake_tag_ids), patch(f"{MODULE}.add_workspaces_to_tag") as mock_add:
            result = state_present(adapter, params, check_mode=False)

        mock_add.assert_called_once_with(adapter, "org", "tag-5", ["ws-b"])
        assert result["changed"] is True
        assert result["workspace_ids"] == ["ws-b"]

    def test_check_mode_does_not_mutate(self, adapter):
        params = {"organization": "org", "tag_id": "tag-5", "workspace_ids": ["ws-a"]}
        with patch(f"{MODULE}.get_workspace_tag_ids", return_value=set()), patch(f"{MODULE}.add_workspaces_to_tag") as mock_add:
            result = state_present(adapter, params, check_mode=True)

        mock_add.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_check_mode_all_present_is_noop(self, adapter):
        params = {"organization": "org", "tag_id": "tag-5", "workspace_ids": ["ws-a"]}
        with patch(f"{MODULE}.get_workspace_tag_ids", return_value={"tag-5"}), patch(f"{MODULE}.add_workspaces_to_tag") as mock_add:
            result = state_present(adapter, params, check_mode=True)

        mock_add.assert_not_called()
        assert result["changed"] is False


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_by_tag_id(self, adapter):
        params = {"organization": "org", "tag_id": "tag-9", "ids": None}
        with patch(f"{MODULE}.list_organization_tag_ids", return_value={"tag-9", "tag-1"}), patch(f"{MODULE}.delete_organization_tags") as mock_del:
            result = state_absent(adapter, params, check_mode=False)

        mock_del.assert_called_once_with(adapter, "org", ["tag-9"])
        assert result["changed"] is True
        assert result["ids"] == ["tag-9"]

    def test_delete_by_ids(self, adapter):
        params = {"organization": "org", "tag_id": None, "ids": ["tag-1", "tag-2"]}
        with patch(f"{MODULE}.list_organization_tag_ids", return_value={"tag-1", "tag-2", "tag-3"}), patch(f"{MODULE}.delete_organization_tags") as mock_del:
            result = state_absent(adapter, params, check_mode=False)

        mock_del.assert_called_once_with(adapter, "org", ["tag-1", "tag-2"])
        assert result["changed"] is True
        assert result["ids"] == ["tag-1", "tag-2"]

    def test_absent_tags_is_noop(self, adapter):
        params = {"organization": "org", "tag_id": "tag-9", "ids": None}
        # tag-9 is not present in the org.
        with patch(f"{MODULE}.list_organization_tag_ids", return_value={"tag-1"}), patch(f"{MODULE}.delete_organization_tags") as mock_del:
            result = state_absent(adapter, params, check_mode=False)

        mock_del.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_partial_existence(self, adapter):
        params = {"organization": "org", "tag_id": None, "ids": ["tag-1", "tag-x", "tag-2"]}
        # tag-x does not exist; only tag-1 and tag-2 should be deleted.
        with patch(f"{MODULE}.list_organization_tag_ids", return_value={"tag-1", "tag-2"}), patch(f"{MODULE}.delete_organization_tags") as mock_del:
            result = state_absent(adapter, params, check_mode=False)

        mock_del.assert_called_once_with(adapter, "org", ["tag-1", "tag-2"])
        assert result["ids"] == ["tag-1", "tag-2"]

    def test_no_identifier_raises(self, adapter):
        params = {"organization": "org", "tag_id": None, "ids": None}
        with pytest.raises(ValueError, match="tag_id.*ids|Either"):
            state_absent(adapter, params, check_mode=False)

    def test_delete_check_mode(self, adapter):
        params = {"organization": "org", "tag_id": "tag-9", "ids": None}
        with patch(f"{MODULE}.list_organization_tag_ids", return_value={"tag-9"}), patch(f"{MODULE}.delete_organization_tags") as mock_del:
            result = state_absent(adapter, params, check_mode=True)

        mock_del.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestMain:
    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_argument_specification(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "organization": "org",
            "state": "present",
            "tag_id": "tag-5",
            "workspace_ids": ["ws-a"],
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", return_value={"changed": True}):
            with pytest.raises(SystemExit):
                main()

        mock_ansible_module.assert_called_once()
        call_args = mock_ansible_module.call_args[1]
        assert call_args["argument_spec"]["organization"] == {"type": "str", "required": True}
        assert call_args["argument_spec"]["state"]["choices"] == ["present", "absent"]
        assert call_args["argument_spec"]["name"] == {"type": "str"}
        assert ("tag_id", "name") in call_args["mutually_exclusive"]
        assert ("tag_id", "ids") in call_args["mutually_exclusive"]
        assert ("name", "ids") in call_args["mutually_exclusive"]
        assert call_args["required_if"] == [("state", "present", ["workspace_ids"])]
        assert call_args["supports_check_mode"] is True

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_present_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "organization": "org",
            "state": "present",
            "tag_id": "tag-5",
            "workspace_ids": ["ws-a"],
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", return_value={"changed": True, "workspace_ids": ["ws-a"]}) as mock_present:
            with pytest.raises(SystemExit):
                main()

        mock_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_absent_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"organization": "org", "state": "absent", "ids": ["tag-1"]}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_absent", return_value={"changed": True, "ids": ["tag-1"]}) as mock_absent:
            with pytest.raises(SystemExit):
                main()

        mock_absent.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_failure_calls_fail_json(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "organization": "org",
            "state": "present",
            "tag_id": "tag-5",
            "workspace_ids": None,
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", side_effect=ValueError("boom")):
            with pytest.raises(AssertionError, match="boom"):
                main()

        assert mock_module.failed is True
