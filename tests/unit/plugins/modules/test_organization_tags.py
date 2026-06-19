# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/organization_tags.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.organization_tags import (
    add_workspaces_to_tag,
    delete_organization_tags,
    get_workspace_tag_ids,
    list_organization_tag_ids,
)
from ansible_collections.hashicorp.terraform.plugins.modules.organization_tags import (
    main,
    state_absent,
    state_present,
)

MODULE = "ansible_collections.hashicorp.terraform.plugins.modules.organization_tags"
MODULE_UTILS = "ansible_collections.hashicorp.terraform.plugins.module_utils.organization_tags"


class TestSdkHelpers:
    def test_delete(self):
        from pytfe.models.organization_tags import OrganizationTagsDeleteOptions

        adapter = Mock()
        delete_organization_tags(adapter, "my-org", ["tag-1", "tag-2"])
        adapter.client.organization_tags.delete.assert_called_once_with("my-org", OrganizationTagsDeleteOptions(ids=["tag-1", "tag-2"]))

    def test_delete_empty_is_noop(self):
        adapter = Mock()
        delete_organization_tags(adapter, "my-org", [])
        adapter.client.organization_tags.delete.assert_not_called()

    def test_add_workspaces_to_tag(self):
        from pytfe.models.organization_tags import AddWorkspacesToTagOptions

        adapter = Mock()
        add_workspaces_to_tag(adapter, "my-org", "tag-1", ["ws-a", "ws-b"])
        adapter.client.organization_tags.add_workspaces.assert_called_once_with("my-org", "tag-1", AddWorkspacesToTagOptions(workspace_ids=["ws-a", "ws-b"]))

    def test_add_workspaces_to_tag_empty_is_noop(self):
        adapter = Mock()
        add_workspaces_to_tag(adapter, "my-org", "tag-1", [])
        adapter.client.organization_tags.add_workspaces.assert_not_called()

    def test_list_organization_tag_ids(self):
        from pytfe.models.organization_tags import OrganizationTag

        adapter = Mock()
        adapter.client.organization_tags.list.return_value = iter(
            [
                OrganizationTag(id="tag-1", name="prod"),
                OrganizationTag(id="tag-2", name="dev"),
            ]
        )
        result = list_organization_tag_ids(adapter, "my-org")
        assert result == {"tag-1", "tag-2"}
        adapter.client.organization_tags.list.assert_called_once_with("my-org")

    def test_list_organization_tag_ids_not_found_returns_empty(self):
        from pytfe.errors import NotFound

        adapter = Mock()
        adapter.client.organization_tags.list.side_effect = NotFound("none")
        assert list_organization_tag_ids(adapter, "my-org") == set()

    def test_get_workspace_tag_ids(self):
        from pytfe.models.common import Tag

        adapter = Mock()
        adapter.client.workspaces.list_tags.return_value = iter(
            [
                Tag(id="tag-1", name="prod"),
                Tag(id="tag-3", name="staging"),
            ]
        )
        result = get_workspace_tag_ids(adapter, "ws-abc")
        assert result == {"tag-1", "tag-3"}
        adapter.client.workspaces.list_tags.assert_called_once_with("ws-abc")

    def test_get_workspace_tag_ids_not_found_returns_empty(self):
        from pytfe.errors import NotFound

        adapter = Mock()
        adapter.client.workspaces.list_tags.side_effect = NotFound("none")
        assert get_workspace_tag_ids(adapter, "ws-abc") == set()


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
        assert "name" not in call_args["argument_spec"]
        assert call_args["mutually_exclusive"] == [("tag_id", "ids")]
        assert call_args["required_if"] == [("state", "present", ["tag_id", "workspace_ids"])]
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
