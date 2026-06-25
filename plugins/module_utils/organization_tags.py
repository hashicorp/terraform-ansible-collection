# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""Organization tags adapter for pytfe SDK integration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

try:
    from pytfe.errors import NotFound
    from pytfe.models.common import Tag
    from pytfe.models.organization_tags import AddWorkspacesToTagOptions, OrganizationTagsDeleteOptions, OrganizationTagsListOptions
    from pytfe.models.workspace import WorkspaceAddTagsOptions
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class OrganizationTagsDeleteOptions:  # type: ignore[no-redef]
        def __init__(self, ids: list) -> None:
            self.ids = ids

    class AddWorkspacesToTagOptions:  # type: ignore[no-redef]
        def __init__(self, workspace_ids: list) -> None:
            self.workspace_ids = workspace_ids

    class Tag:  # type: ignore[no-redef]
        def __init__(self, id: Optional[str] = None, name: str = "") -> None:
            self.id = id
            self.name = name

    class WorkspaceAddTagsOptions:  # type: ignore[no-redef]
        def __init__(self, tags: list) -> None:
            self.tags = tags

    class OrganizationTagsListOptions:  # type: ignore[no-redef]
        def __init__(self, query: Optional[str] = None, filter: Optional[str] = None) -> None:
            self.query = query
            self.filter = filter


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient


def list_organization_tags(
    adapter: TerraformClient,
    organization: str,
    query: Optional[str] = None,
    filter_exclude_taggable_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return all tags in the organization as a list of dicts (id, name, instance_count).

    Args:
        query: Partial tag name filter (maps to ``?q=`` on the API).
        filter_exclude_taggable_id: Workspace (or other taggable) ID whose already-associated
            tags are excluded from the results.  Maps to
            ``?filter[exclude][taggable][id]=`` on the API.
    """

    if query or filter_exclude_taggable_id:
        options = OrganizationTagsListOptions(
            query=query,
            filter=filter_exclude_taggable_id,
        )
    else:
        options = None

    try:
        return [{"id": tag.id, "name": tag.name, "instance_count": tag.instance_count} for tag in adapter.client.organization_tags.list(organization, options)]
    except NotFound:
        return []


def list_organization_tag_ids(adapter: TerraformClient, organization: str) -> Set[str]:
    """Return the set of tag IDs currently present in the organization (empty set when none exist)."""
    try:
        return {tag.id for tag in adapter.client.organization_tags.list(organization) if tag.id}
    except NotFound:
        return set()


def resolve_tag_by_name(adapter: TerraformClient, organization: str, name: str) -> Optional[str]:
    """Return the tag ID of the first tag whose name matches *name*, or None if absent."""
    try:
        for tag in adapter.client.organization_tags.list(organization):
            if tag.name == name:
                return tag.id
    except NotFound:
        pass
    return None


def create_tag_on_workspace(adapter: TerraformClient, workspace_id: str, name: str) -> None:
    """Create an org-level tag by name and associate it with *workspace_id* in one API call."""
    adapter.client.workspaces.add_tags(
        workspace_id,
        WorkspaceAddTagsOptions(tags=[Tag(name=name)]),
    )


def get_workspace_tag_ids(adapter: TerraformClient, workspace_id: str) -> Set[str]:
    """Return the set of tag IDs currently attached to a workspace (empty set on NotFound)."""
    try:
        return {tag.id for tag in adapter.client.workspaces.list_tags(workspace_id) if tag.id}
    except NotFound:
        return set()


def delete_organization_tags(adapter: TerraformClient, organization: str, tag_ids: List[str]) -> None:
    """Delete one or more tags from an organization (no-op if empty)."""
    if not tag_ids:
        return
    adapter.client.organization_tags.delete(organization, OrganizationTagsDeleteOptions(ids=tag_ids))


def add_workspaces_to_tag(adapter: TerraformClient, organization: str, tag_id: str, workspace_ids: List[str]) -> None:
    """Associate workspaces with an existing tag via POST /api/v2/tags/{tag_id}/relationships/workspaces."""
    if not workspace_ids:
        return
    adapter.client.organization_tags.add_workspaces(organization, tag_id, AddWorkspacesToTagOptions(workspace_ids=workspace_ids))
