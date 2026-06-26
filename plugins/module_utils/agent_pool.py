# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        AgentPoolCreateOptions,
        AgentPoolUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class AgentPoolCreateOptions:  # type: ignore[no-redef]
        pass

    class AgentPoolUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_agent_pools(adapter: TerraformClient, organization: str) -> List[Dict[str, Any]]:
    """List agent pools for an organization."""
    try:
        return [format_response(pool) for pool in adapter.client.agent_pools.list(organization)]
    except NotFound:
        return []


def get_agent_pool(adapter: TerraformClient, agent_pool_id: str) -> Optional[Dict[str, Any]]:
    """Read a single agent pool by its ID. Returns None if not found."""
    try:
        pool = adapter.client.agent_pools.read(agent_pool_id)
        return format_response(pool)
    except NotFound:
        return None


def get_agent_pool_by_name(adapter: TerraformClient, organization: str, name: str) -> Optional[Dict[str, Any]]:
    """Locate an agent pool by name within an organization."""
    for pool in list_agent_pools(adapter, organization):
        if pool.get("name") == name:
            return pool
    return None


def create_agent_pool(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an agent pool under the given organization."""
    options = AgentPoolCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.agent_pools.create,
        organization,
        options,
        error_context=f"Failed to create agent pool {data.get('name')!r} in organization {organization}",
    )
    return format_response(response)


def update_agent_pool(adapter: TerraformClient, agent_pool_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing agent pool."""
    options = AgentPoolUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.agent_pools.update,
        agent_pool_id,
        options,
        error_context=f"Failed to update agent pool {agent_pool_id}",
    )
    return format_response(response)


def delete_agent_pool(adapter: TerraformClient, agent_pool_id: str) -> None:
    """Delete an agent pool by its ID."""
    safe_api_call(
        adapter.client.agent_pools.delete,
        agent_pool_id,
        error_context=f"Failed to delete agent pool {agent_pool_id}",
    )
