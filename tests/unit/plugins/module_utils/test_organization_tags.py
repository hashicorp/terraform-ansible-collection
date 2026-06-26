# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/organization_tags.py."""

from unittest.mock import Mock

from ansible_collections.hashicorp.terraform.plugins.module_utils.organization_tags import (
    add_workspaces_to_tag,
    create_tag_on_workspace,
    delete_organization_tags,
    get_workspace_tag_ids,
    list_organization_tag_ids,
    list_organization_tags,
    resolve_tag_by_name,
)


class TestDeleteOrganizationTags:
    def test_delete(self):
        from pytfe.models.organization_tags import OrganizationTagsDeleteOptions

        adapter = Mock()
        delete_organization_tags(adapter, "my-org", ["tag-1", "tag-2"])
        adapter.client.organization_tags.delete.assert_called_once_with("my-org", OrganizationTagsDeleteOptions(ids=["tag-1", "tag-2"]))

    def test_delete_empty_is_noop(self):
        adapter = Mock()
        delete_organization_tags(adapter, "my-org", [])
        adapter.client.organization_tags.delete.assert_not_called()


class TestAddWorkspacesToTag:
    def test_add_workspaces_to_tag(self):
        from pytfe.models.organization_tags import AddWorkspacesToTagOptions

        adapter = Mock()
        add_workspaces_to_tag(adapter, "my-org", "tag-1", ["ws-a", "ws-b"])
        adapter.client.organization_tags.add_workspaces.assert_called_once_with("my-org", "tag-1", AddWorkspacesToTagOptions(workspace_ids=["ws-a", "ws-b"]))

    def test_add_workspaces_to_tag_empty_is_noop(self):
        adapter = Mock()
        add_workspaces_to_tag(adapter, "my-org", "tag-1", [])
        adapter.client.organization_tags.add_workspaces.assert_not_called()


class TestListOrganizationTagIds:
    def test_returns_set_of_ids(self):
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

    def test_not_found_returns_empty_set(self):
        from pytfe.errors import NotFound

        adapter = Mock()
        adapter.client.organization_tags.list.side_effect = NotFound("none")
        assert list_organization_tag_ids(adapter, "my-org") == set()


class TestListOrganizationTags:
    def test_returns_dicts(self):
        from pytfe.models.organization_tags import OrganizationTag

        adapter = Mock()
        adapter.client.organization_tags.list.return_value = iter(
            [
                OrganizationTag(id="tag-1", name="prod", instance_count=2),
                OrganizationTag(id="tag-2", name="dev", instance_count=0),
            ]
        )
        result = list_organization_tags(adapter, "my-org")
        assert result == [
            {"id": "tag-1", "name": "prod", "instance_count": 2},
            {"id": "tag-2", "name": "dev", "instance_count": 0},
        ]
        adapter.client.organization_tags.list.assert_called_once_with("my-org", None)

    def test_with_query(self):
        from pytfe.models.organization_tags import OrganizationTag, OrganizationTagsListOptions

        adapter = Mock()
        adapter.client.organization_tags.list.return_value = iter([OrganizationTag(id="tag-1", name="prod", instance_count=1)])
        result = list_organization_tags(adapter, "my-org", query="prod")
        assert result == [{"id": "tag-1", "name": "prod", "instance_count": 1}]
        adapter.client.organization_tags.list.assert_called_once_with("my-org", OrganizationTagsListOptions(query="prod"))

    def test_not_found_returns_empty_list(self):
        from pytfe.errors import NotFound

        adapter = Mock()
        adapter.client.organization_tags.list.side_effect = NotFound("none")
        assert list_organization_tags(adapter, "my-org") == []

    def test_with_filter_exclude_taggable_id(self):
        from pytfe.models.organization_tags import OrganizationTag, OrganizationTagsListOptions

        adapter = Mock()
        adapter.client.organization_tags.list.return_value = iter([OrganizationTag(id="tag-2", name="dev", instance_count=0)])
        result = list_organization_tags(adapter, "my-org", filter_exclude_taggable_id="ws-abc")
        assert result == [{"id": "tag-2", "name": "dev", "instance_count": 0}]
        # filter kwarg maps to filter[exclude][taggable][id] on the wire via by_alias
        adapter.client.organization_tags.list.assert_called_once_with("my-org", OrganizationTagsListOptions(filter="ws-abc"))

    def test_query_and_filter_combined(self):
        from pytfe.models.organization_tags import OrganizationTag, OrganizationTagsListOptions

        adapter = Mock()
        adapter.client.organization_tags.list.return_value = iter([OrganizationTag(id="tag-3", name="env:staging", instance_count=1)])
        result = list_organization_tags(adapter, "my-org", query="env", filter_exclude_taggable_id="ws-xyz")
        assert result == [{"id": "tag-3", "name": "env:staging", "instance_count": 1}]
        adapter.client.organization_tags.list.assert_called_once_with("my-org", OrganizationTagsListOptions(query="env", filter="ws-xyz"))


class TestGetWorkspaceTagIds:
    def test_returns_set_of_ids(self):
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

    def test_not_found_returns_empty_set(self):
        from pytfe.errors import NotFound

        adapter = Mock()
        adapter.client.workspaces.list_tags.side_effect = NotFound("none")
        assert get_workspace_tag_ids(adapter, "ws-abc") == set()


class TestResolveTagByName:
    def test_found_returns_id(self):
        from pytfe.models.organization_tags import OrganizationTag

        adapter = Mock()
        adapter.client.organization_tags.list.return_value = iter(
            [
                OrganizationTag(id="tag-1", name="prod"),
                OrganizationTag(id="tag-2", name="dev"),
            ]
        )
        assert resolve_tag_by_name(adapter, "my-org", "dev") == "tag-2"

    def test_not_found_returns_none(self):
        from pytfe.models.organization_tags import OrganizationTag

        adapter = Mock()
        adapter.client.organization_tags.list.return_value = iter([OrganizationTag(id="tag-1", name="prod")])
        assert resolve_tag_by_name(adapter, "my-org", "staging") is None

    def test_not_found_exception_returns_none(self):
        from pytfe.errors import NotFound

        adapter = Mock()
        adapter.client.organization_tags.list.side_effect = NotFound("none")
        assert resolve_tag_by_name(adapter, "my-org", "env") is None


class TestCreateTagOnWorkspace:
    def test_calls_add_tags(self):
        from pytfe.models.common import Tag
        from pytfe.models.workspace import WorkspaceAddTagsOptions

        adapter = Mock()
        create_tag_on_workspace(adapter, "ws-abc", "env:prod")
        adapter.client.workspaces.add_tags.assert_called_once_with("ws-abc", WorkspaceAddTagsOptions(tags=[Tag(name="env:prod")]))
