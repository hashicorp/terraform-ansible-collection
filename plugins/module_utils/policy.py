# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Policy adapter for pytfe SDK integration.

Wraps ``client.policies`` (``/api/v2/organizations/{org}/policies``,
``/api/v2/policies/{id}``). Unlike SSH keys, policy content is round-trippable
- ``download()`` returns the uploaded bytes back - so drift on content can be
genuinely detected rather than treated as write-only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import PolicyCreateOptions, PolicyUpdateOptions
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class PolicyCreateOptions:  # type: ignore[no-redef]
        pass

    class PolicyUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_policies(adapter: TerraformClient, organization: str) -> List[Dict[str, Any]]:
    """List policies in an organization."""
    try:
        return [format_response(p) for p in adapter.client.policies.list(organization)]
    except NotFound:
        return []


def get_policy(adapter: TerraformClient, policy_id: str) -> Optional[Dict[str, Any]]:
    """Read a single policy by its ID. Returns None if not found."""
    try:
        return format_response(adapter.client.policies.read(policy_id))
    except NotFound:
        return None


def get_policy_by_name(adapter: TerraformClient, organization: str, name: str) -> Optional[Dict[str, Any]]:
    """Locate a policy by name within an organization."""
    for policy in list_policies(adapter, organization):
        if policy.get("name") == name:
            return policy
    return None


def create_policy(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a policy under the given organization. Does not upload content."""
    options = PolicyCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.policies.create,
        organization,
        options,
        error_context=f"Failed to create policy {data.get('name')!r} in organization {organization}",
    )
    return format_response(response)


def update_policy(adapter: TerraformClient, policy_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a policy's attributes (not content) by its ID."""
    options = PolicyUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.policies.update,
        policy_id,
        options,
        error_context=f"Failed to update policy {policy_id}",
    )
    return format_response(response)


def delete_policy(adapter: TerraformClient, policy_id: str) -> None:
    """Delete a policy by its ID."""
    safe_api_call(
        adapter.client.policies.delete,
        policy_id,
        error_context=f"Failed to delete policy {policy_id}",
    )


def upload_policy_content(adapter: TerraformClient, policy_id: str, content: str) -> None:
    """Upload policy content (Sentinel/OPA/tf-policy source) for a policy."""
    safe_api_call(
        adapter.client.policies.upload,
        policy_id,
        content.encode("utf-8"),
        error_context=f"Failed to upload content for policy {policy_id}",
    )


def download_policy_content(adapter: TerraformClient, policy_id: str) -> Optional[str]:
    """Download the currently uploaded policy content. None if never uploaded."""
    try:
        content = adapter.client.policies.download(policy_id)
        return content.decode("utf-8") if content else None
    except NotFound:
        return None
