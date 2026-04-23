# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        SSHKeyCreateOptions,
        SSHKeyUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class SSHKeyCreateOptions:  # type: ignore[no-redef]
        pass

    class SSHKeyUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_ssh_keys(adapter: TerraformClient, organization: str) -> List[Dict[str, Any]]:
    """List SSH keys for an organization."""
    try:
        return [format_response(k) for k in adapter.client.ssh_keys.list(organization)]
    except NotFound:
        return []


def get_ssh_key(adapter: TerraformClient, ssh_key_id: str) -> Optional[Dict[str, Any]]:
    """Read a single SSH key by its ID. Returns None if not found."""
    try:
        key = adapter.client.ssh_keys.read(ssh_key_id)
        return format_response(key)
    except NotFound:
        return None


def get_ssh_key_by_name(adapter: TerraformClient, organization: str, name: str) -> Optional[Dict[str, Any]]:
    """Locate an SSH key by name within an organization."""
    for key in list_ssh_keys(adapter, organization):
        if key.get("name") == name:
            return key
    return None


def create_ssh_key(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an SSH key under the given organization."""
    options = SSHKeyCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.ssh_keys.create,
        organization,
        options,
        error_context=f"Failed to create SSH key {data.get('name')!r} in organization {organization}",
    )
    return format_response(response)


def update_ssh_key(adapter: TerraformClient, ssh_key_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing SSH key. Only ``name`` is mutable via the TFE API."""
    options = SSHKeyUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.ssh_keys.update,
        ssh_key_id,
        options,
        error_context=f"Failed to update SSH key {ssh_key_id}",
    )
    return format_response(response)


def delete_ssh_key(adapter: TerraformClient, ssh_key_id: str) -> None:
    """Delete an SSH key by its ID."""
    safe_api_call(
        adapter.client.ssh_keys.delete,
        ssh_key_id,
        error_context=f"Failed to delete SSH key {ssh_key_id}",
    )
