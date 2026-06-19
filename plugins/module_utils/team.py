# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Team adapter for pytfe SDK integration.

This module provides functions that handle team-specific
operations using the pytfe SDK, including create, read, update, and delete operations.

Example:
    adapter = TerraformClient(tfe_token="my-token", tfe_address="https://app.terraform.io")
    with adapter:
        team = get_team(adapter, 'team-123')
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        TeamCreateOptions,
        TeamUpdateOptions,
    )
    from pytfe.models.team import OrganizationAccessOptions
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class TeamCreateOptions:  # type: ignore[no-redef]
        pass

    class TeamUpdateOptions:  # type: ignore[no-redef]
        pass

    class OrganizationAccessOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import (
    format_response,
    safe_api_call,
)


def normalize_team_response(team_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize team response data to Ansible output format.

    Args:
        team_data: Team data from SDK response

    Returns:
        Normalized team data dictionary
    """
    normalized = {
        "id": team_data.get("id"),
        "name": team_data.get("name"),
        "visibility": team_data.get("visibility"),
        "sso_team_id": team_data.get("sso_team_id"),
        "allow_member_token_management": team_data.get("allow_member_token_management"),
        "user_count": team_data.get("user_count"),
        "is_unified": team_data.get("is_unified"),
    }

    if team_data.get("organization_access"):
        normalized["organization_access"] = team_data["organization_access"]

    if team_data.get("permissions"):
        normalized["permissions"] = team_data["permissions"]

    return normalized


def get_team(adapter: TerraformClient, team_id: str) -> Dict[str, Any] | None:
    """
    Retrieves a specified team from Terraform Cloud/Enterprise by its ID.

    Sends a GET request using the pytfe SDK to fetch details of a team identified by its unique ID.
    If the team is not found, returns None. For any other error, raises a TerraformError.

    Args:
        adapter (TerraformClient): An authenticated client used to interact with the Terraform API.
        team_id (str): The unique ID of the team to retrieve.

    Returns:
        dict: A dictionary containing the team data if found, or None if the team is not found.
    """
    try:
        team = adapter.client.teams.read(team_id)
        return format_response(team)
    except NotFound:
        # team was not found
        # This should not raise an exception
        return None


def _build_team_options(option_class, payload: Dict[str, Any]):
    """
    Build pytfe options object from payload dict.

    Args:
        option_class: The options class to instantiate (TeamCreateOptions, TeamUpdateOptions, etc.)
        payload: Dictionary of parameters

    Returns:
        Instance of option_class with parameters set
    """
    # Convert organization_access dict to OrganizationAccessOptions if present
    if "organization_access" in payload and isinstance(payload["organization_access"], dict):
        payload = dict(payload)  # Make a copy to avoid mutating input
        payload["organization_access"] = OrganizationAccessOptions(**payload["organization_access"])

    return option_class(**payload)


def create_team(
    adapter: TerraformClient,
    organization: str,
    name: str,
    visibility: Optional[str] = None,
    sso_team_id: Optional[str] = None,
    organization_access: Optional[Dict[str, Any]] = None,
    allow_member_token_management: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Creates a new team in the given organization.

    Args:
        adapter (TerraformClient): An authenticated client.
        organization (str): The name of the organization to create the team in.
        name (str): The name of the team.
        visibility (Optional[str]): The visibility of the team ("secret" or "organization").
        sso_team_id (Optional[str]): Optional SSO team ID.
        organization_access (Optional[Dict]): Organization access permissions for the team.
        allow_member_token_management (Optional[bool]): Whether team members can manage tokens.

    Returns:
        dict: The created team data.
    """

    payload: dict[str, Any] = {
        "name": name,
        "visibility": visibility,
        "sso_team_id": sso_team_id,
        "organization_access": organization_access,
        "allow_member_token_management": allow_member_token_management,
    }

    payload = {k: v for k, v in payload.items() if v is not None}

    options = _build_team_options(TeamCreateOptions, payload)

    team_response = safe_api_call(
        adapter.client.teams.create,
        organization,
        options,
    )

    return format_response(team_response)


def update_team(
    adapter: TerraformClient,
    team_id: str,
    name: Optional[str] = None,
    visibility: Optional[str] = None,
    sso_team_id: Optional[str] = None,
    organization_access: Optional[Dict[str, Any]] = None,
    allow_member_token_management: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Updates an existing team.

    Args:
        adapter (TerraformClient): An authenticated client.
        team_id (str): The ID of the team to update.
        name (Optional[str]): New name for the team.
        visibility (Optional[str]): New visibility for the team.
        sso_team_id (Optional[str]): New SSO team ID.
        organization_access (Optional[Dict]): New organization access permissions.
        allow_member_token_management (Optional[bool]): New token management permission.

    Returns:
        dict: The updated team data.
    """
    payload: dict[str, Any] = {
        "name": name,
        "visibility": visibility,
        "sso_team_id": sso_team_id,
        "organization_access": organization_access,
        "allow_member_token_management": allow_member_token_management,
    }

    payload = {k: v for k, v in payload.items() if v is not None}

    options = _build_team_options(TeamUpdateOptions, payload)

    team_response = safe_api_call(
        adapter.client.teams.update,
        team_id,
        options,
    )

    return format_response(team_response)


def delete_team(adapter: TerraformClient, team_id: str) -> None:
    """
    Deletes a team.

    Args:
        adapter (TerraformClient): An authenticated client.
        team_id (str): The ID of the team to delete.

    Returns:
        None
    """
    safe_api_call(
        adapter.client.teams.delete,
        team_id,
        error_context=f"Failed to delete team with ID {team_id}",
    )
