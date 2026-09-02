# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_agent(adapter: TerraformClient, agent_id: str) -> Optional[Dict[str, Any]]:
    """Read a single agent by its ID. Returns None if not found."""
    try:
        agent = adapter.client.agents.read(agent_id)
        return format_response(agent)
    except NotFound:
        return None


def delete_agent(adapter: TerraformClient, agent_id: str) -> None:
    """Delete an agent by its ID."""
    safe_api_call(
        adapter.client.agents.delete,
        agent_id,
        error_context=f"Failed to delete agent {agent_id}",
    )
