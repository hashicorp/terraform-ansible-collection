# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        ReservedTagKeyCreateOptions,
        ReservedTagKeyUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class ReservedTagKeyCreateOptions:  # type: ignore[no-redef]
        pass

    class ReservedTagKeyUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_reserved_tag_key(adapter: TerraformClient, reserved_tag_key_id: str) -> Optional[Dict[str, Any]]:
    """Lookup reserved tag key by ID.

    Note: pytfe's ReservedTagKeys service does not provide a read() method,
    so we cannot fetch a single reserved tag key by ID without knowing its organization.
    This function returns None, and the module handles updates by ID directly without pre-fetching.
    """
    return None


def get_reserved_tag_key_by_key(adapter: TerraformClient, organization: str, key: str) -> Optional[Dict[str, Any]]:
    """Locate a reserved tag key by key name within an organization."""
    try:
        for rtk in adapter.client.reserved_tag_key.list(organization):
            if rtk.key == key:
                return format_response(rtk)
    except NotFound:
        pass
    return None


def create_reserved_tag_key(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a reserved tag key under the given organization."""
    options = ReservedTagKeyCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.reserved_tag_key.create,
        organization,
        options,
        error_context=f"Failed to create reserved tag key {data.get('key')!r} in organization {organization}",
    )
    return format_response(response)


def update_reserved_tag_key(adapter: TerraformClient, reserved_tag_key_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing reserved tag key."""
    options = ReservedTagKeyUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.reserved_tag_key.update,
        reserved_tag_key_id,
        options,
        error_context=f"Failed to update reserved tag key {reserved_tag_key_id}",
    )
    return format_response(response)


def delete_reserved_tag_key(adapter: TerraformClient, reserved_tag_key_id: str) -> None:
    """Delete a reserved tag key by its ID."""
    safe_api_call(
        adapter.client.reserved_tag_key.delete,
        reserved_tag_key_id,
        error_context=f"Failed to delete reserved tag key {reserved_tag_key_id}",
    )


def try_delete_reserved_tag_key(adapter: TerraformClient, reserved_tag_key_id: str) -> bool:
    """Delete a reserved tag key by ID, returning False if not found.

    Returns:
        True if the resource was deleted, False if it did not exist.

    Raises:
        TerraformError: For any error other than NotFound.
    """
    try:
        adapter.client.reserved_tag_key.delete(reserved_tag_key_id)
        return True
    except NotFound:
        return False
