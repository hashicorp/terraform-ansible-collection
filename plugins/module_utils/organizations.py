# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Organization adapter for pytfe SDK integration.

Provides CRUD helpers plus the org-level read endpoints that live on the
same SDK resource (capacity, entitlements). These are bundled here so the
Ansible module and info plugin share a single implementation surface.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        OrganizationCreateOptions,
        OrganizationUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class OrganizationCreateOptions:  # type: ignore[no-redef]
        pass

    class OrganizationUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_organization(adapter: TerraformClient, name: str) -> Optional[Dict[str, Any]]:
    """Read an organization by name.

    Args:
        adapter: Authenticated TerraformClient.
        name: Organization name (also serves as the ID in TFC/TFE).

    Returns:
        Formatted organization dict, or ``None`` if the organization does not exist.
    """
    try:
        org = adapter.client.organizations.read(name)
        return format_response(org)
    except NotFound:
        return None


def list_organizations(adapter: TerraformClient) -> List[Dict[str, Any]]:
    """List all organizations accessible to the authenticated user.

    Args:
        adapter: Authenticated TerraformClient.

    Returns:
        A list of formatted organization dicts.
    """
    try:
        result: Iterable[Any] = adapter.client.organizations.list()
        return [format_response(org) for org in result]
    except NotFound:
        return []


def create_organization(adapter: TerraformClient, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new organization.

    Args:
        adapter: Authenticated TerraformClient.
        data: Organization attributes (must include ``name`` and ``email``).

    Returns:
        Formatted dict of the newly created organization.
    """
    options = OrganizationCreateOptions.model_validate(data)
    org = safe_api_call(
        adapter.client.organizations.create,
        options,
        error_context=f"Failed to create organization {data.get('name')}",
    )
    return format_response(org)


def update_organization(adapter: TerraformClient, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing organization.

    Args:
        adapter: Authenticated TerraformClient.
        name: The organization name (ID).
        data: Attributes to update.

    Returns:
        Formatted dict of the updated organization.
    """
    options = OrganizationUpdateOptions.model_validate(data)
    org = safe_api_call(
        adapter.client.organizations.update,
        name,
        options,
        error_context=f"Failed to update organization {name}",
    )
    return format_response(org)


def delete_organization(adapter: TerraformClient, name: str) -> None:
    """Delete an organization by name.

    Args:
        adapter: Authenticated TerraformClient.
        name: The organization name (ID).
    """
    safe_api_call(
        adapter.client.organizations.delete,
        name,
        error_context=f"Failed to delete organization {name}",
    )


def get_organization_capacity(adapter: TerraformClient, name: str) -> Optional[Dict[str, Any]]:
    """Read the run capacity (pending/running) for an organization.

    Args:
        adapter: Authenticated TerraformClient.
        name: The organization name.

    Returns:
        Dict with capacity counts, or ``None`` if the organization is missing.
    """
    try:
        capacity = adapter.client.organizations.read_capacity(name)
        return format_response(capacity)
    except NotFound:
        return None


def get_organization_entitlements(adapter: TerraformClient, name: str) -> Optional[Dict[str, Any]]:
    """Read feature entitlements for an organization.

    Args:
        adapter: Authenticated TerraformClient.
        name: The organization name.

    Returns:
        Dict of feature entitlement flags, or ``None`` if the organization is missing.
    """
    try:
        entitlements = adapter.client.organizations.read_entitlements(name)
        return format_response(entitlements)
    except NotFound:
        return None
