# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import AgentTokenCreateOptions
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class AgentTokenCreateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_agent_token(adapter: TerraformClient, agent_token_id: str) -> Optional[Dict[str, Any]]:
    """Read a single agent token by its ID. Returns None if not found."""
    try:
        token = adapter.client.agent_tokens.read(agent_token_id)
        return format_response(token)
    except NotFound:
        return None


def create_agent_token(adapter: TerraformClient, agent_pool_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an agent token under the given agent pool."""
    options = AgentTokenCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.agent_tokens.create,
        agent_pool_id,
        options,
        error_context=f"Failed to create agent token in pool {agent_pool_id}",
    )
    return format_response(response)


def delete_agent_token(adapter: TerraformClient, agent_token_id: str) -> None:
    """Delete an agent token by its ID."""
    safe_api_call(
        adapter.client.agent_tokens.delete,
        agent_token_id,
        error_context=f"Failed to delete agent token {agent_token_id}",
    )
