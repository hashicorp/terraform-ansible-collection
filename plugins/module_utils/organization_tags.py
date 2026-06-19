# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""Organization tags adapter for pytfe SDK integration."""

from __future__ import annotations

from typing import List, Set

try:
    from pytfe.errors import NotFound
    from pytfe.models.organization_tags import AddWorkspacesToTagOptions, OrganizationTagsDeleteOptions
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class OrganizationTagsDeleteOptions:  # type: ignore[no-redef]
        def __init__(self, ids: list) -> None:
            self.ids = ids

    class AddWorkspacesToTagOptions:  # type: ignore[no-redef]
        def __init__(self, workspace_ids: list) -> None:
            self.workspace_ids = workspace_ids


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient


def list_organization_tag_ids(adapter: TerraformClient, organization: str) -> Set[str]:
    """Return the set of tag IDs currently present in the organization (empty set when none exist)."""
    try:
        return {tag.id for tag in adapter.client.organization_tags.list(organization) if tag.id}
    except NotFound:
        return set()


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
