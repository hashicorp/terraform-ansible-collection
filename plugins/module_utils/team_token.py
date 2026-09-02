# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import TeamTokenCreateOptions
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class TeamTokenCreateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_team_token(adapter: TerraformClient, team_id: str) -> Optional[Dict[str, Any]]:
    """Read the team token associated with team_id. Returns None if not found."""
    try:
        token = adapter.client.team_tokens.read(team_id=team_id)
        return format_response(token)
    except NotFound:
        return None


def get_team_token_by_id(adapter: TerraformClient, token_id: str) -> Optional[Dict[str, Any]]:
    """Read a team token by its token ID. Returns None if not found."""
    try:
        token = adapter.client.team_tokens.read_by_id(token_id=token_id)
        return format_response(token)
    except NotFound:
        return None


def create_team_token(adapter: TerraformClient, team_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a team token.

    Uses create_with_options() when description or expired_at is supplied so that
    both attributes are transmitted to the API.  A truthy description triggers the
    named-token endpoint; expired_at alone keeps the team-level token behavior.
    Falls back to create() when no options are needed.
    """
    description = data.get("description") or None  # normalise "" to None
    expired_at = data.get("expired_at")

    if description is not None or expired_at is not None:
        opts_data: Dict[str, Any] = {}
        if description is not None:
            opts_data["description"] = description
        if expired_at is not None:
            opts_data["expired_at"] = expired_at
        options = TeamTokenCreateOptions.model_validate(opts_data)
        response = safe_api_call(
            adapter.client.team_tokens.create_with_options,
            team_id=team_id,
            options=options,
            error_context=f"Failed to create team token for team {team_id}",
        )
    else:
        response = safe_api_call(
            adapter.client.team_tokens.create,
            team_id=team_id,
            error_context=f"Failed to create team token for team {team_id}",
        )
    return format_response(response)


def delete_team_token(adapter: TerraformClient, team_id: str) -> None:
    """Delete the team token associated with team_id."""
    safe_api_call(
        adapter.client.team_tokens.delete,
        team_id=team_id,
        error_context=f"Failed to delete team token for team {team_id}",
    )


def delete_team_token_by_id(adapter: TerraformClient, token_id: str) -> None:
    """Delete a team token by its token ID."""
    safe_api_call(
        adapter.client.team_tokens.delete_by_id,
        token_id=token_id,
        error_context=f"Failed to delete team token {token_id}",
    )
