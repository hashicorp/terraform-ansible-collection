# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Team adapter for pytfe SDK integration.

This module provides functions that handle team-specific
operations using the pytfe SDK, including create, read, update, delete, list,
and membership management operations (add/remove users and organization memberships).

Example:
    adapter = TerraformClient(tfe_token="my-token", tfe_address="https://app.terraform.io")
    with adapter:
        team = get_team(adapter, 'team-123')
        teams = list_teams(adapter, 'my-org')
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        TeamCreateOptions,
        TeamIncludeOpt,
        TeamListOptions,
        TeamUpdateOptions,
    )
    from pytfe.models.team import OrganizationAccessOptions
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class TeamIncludeOpt:  # type: ignore[no-redef]
        pass

    class TeamListOptions:  # type: ignore[no-redef]
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


def get_team(adapter: TerraformClient, team_id: str, include: Optional[list[str]] = None) -> Dict[str, Any] | None:
    """
    Retrieves a specified team from Terraform Cloud/Enterprise by its ID.

    Sends a GET request using the pytfe SDK to fetch details of a team identified by its unique ID.
    If the team is not found, returns None. If successful, returns the team data with an added
    "status" field. For any other error, raises a TerraformError.

    Args:
        adapter (TerraformClient): An authenticated client used to interact with the Terraform API.
        team_id (str): The unique ID of the team to retrieve.
        include (Optional[list[str]]): List of relations to include (e.g., ['users', 'organization-memberships']).

    Returns:
        dict: A dictionary containing the team data if found, or None if the team is not found.
    """
    try:
        if include:
            team = adapter.client.teams.read(team_id, include=include)
        else:
            team = adapter.client.teams.read(team_id)
        return format_response(team)
    except NotFound:
        # team was not found
        # This should not raise an exception
        return None


def list_teams(
    adapter: TerraformClient,
    organization: str,
    page_size: Optional[int] = None,
    query: Optional[str] = None,
    names: Optional[list[str]] = None,
    include: Optional[list[str]] = None,
) -> list[Dict[str, Any]]:
    """
    Lists all teams in the given organization.

    Sends a GET request using the pytfe SDK to fetch teams from the organization.
    Supports filtering and pagination options.

    Args:
        adapter (TerraformClient): An authenticated client.
        organization (str): The name of the Terraform organization.
        page_size (Optional[int]): Number of items per page.
        query (Optional[str]): Search query string to filter teams by name.
        names (Optional[list[str]]): List of team names to filter by.
        include (Optional[list[str]]): List of relations to include.

    Returns:
        list: A list of team dictionaries.
    """
    try:
        payload: dict[str, Any] = {}

        if page_size is not None:
            payload["page_size"] = page_size

        if query is not None:
            payload["query"] = query

        if names is not None:
            payload["names"] = names

        if include is not None:
            payload["include"] = include

        options = _build_team_options(
            TeamListOptions,
            payload,
        )

        teams = list(
            safe_api_call(
                adapter.client.teams.list,
                organization,
                options,
            )
        )

        return [format_response(team) for team in teams]

    except NotFound:
        # No teams found
        return []


def _build_team_options(option_class, payload: Dict[str, Any]):
    """
    Build pytfe options object safely across pytfe versions.
    """

    payload = dict(payload)

    # Build organization access object safely
    if "organization_access" in payload and isinstance(payload["organization_access"], dict):
        org_payload = payload["organization_access"]

        try:
            payload["organization_access"] = OrganizationAccessOptions(**org_payload)
        except TypeError:
            org_obj = OrganizationAccessOptions()

            for key, value in org_payload.items():
                try:
                    setattr(org_obj, key, value)
                except Exception:
                    pass

            payload["organization_access"] = org_obj

    # Build main options object safely
    try:
        return option_class(**payload)

    except TypeError:
        obj = option_class()

        for key, value in payload.items():
            try:
                setattr(obj, key, value)
            except Exception:
                pass

        return obj


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


def add_users_to_team(adapter: TerraformClient, team_id: str, usernames: list[str]) -> None:
    """
    Add users to a team by their usernames.

    Args:
        adapter (TerraformClient): An authenticated client.
        team_id (str): The ID of the team.
        usernames (list[str]): List of usernames to add.

    Returns:
        None
    """
    safe_api_call(
        adapter.client.teams.add_users,
        team_id,
        usernames,
        error_context=f"Failed to add users to team {team_id}",
    )


def remove_users_from_team(adapter: TerraformClient, team_id: str, usernames: list[str]) -> None:
    """
    Remove users from a team by their usernames.

    Args:
        adapter (TerraformClient): An authenticated client.
        team_id (str): The ID of the team.
        usernames (list[str]): List of usernames to remove.

    Returns:
        None
    """
    safe_api_call(
        adapter.client.teams.remove_users,
        team_id,
        usernames,
        error_context=f"Failed to remove users from team {team_id}",
    )


def list_team_users(adapter: TerraformClient, team_id: str) -> list[Dict[str, Any]]:
    """
    List all users in a team.

    Args:
        adapter (TerraformClient): An authenticated client.
        team_id (str): The ID of the team.

    Returns:
        list: A list of user dictionaries.
    """
    try:
        users = list(adapter.client.teams.list_users(team_id))
        return [format_response(user) for user in users]
    except NotFound:
        return []


def add_organization_memberships_to_team(adapter: TerraformClient, team_id: str, organization_membership_ids: list[str]) -> None:
    """
    Add organization memberships to a team.

    Args:
        adapter (TerraformClient): An authenticated client.
        team_id (str): The ID of the team.
        organization_membership_ids (list[str]): List of organization membership IDs to add.

    Returns:
        None
    """
    safe_api_call(
        adapter.client.teams.add_organization_memberships,
        team_id,
        organization_membership_ids,
        error_context=f"Failed to add organization memberships to team {team_id}",
    )


def remove_organization_memberships_from_team(adapter: TerraformClient, team_id: str, organization_membership_ids: list[str]) -> None:
    """
    Remove organization memberships from a team.

    Args:
        adapter (TerraformClient): An authenticated client.
        team_id (str): The ID of the team.
        organization_membership_ids (list[str]): List of organization membership IDs to remove.

    Returns:
        None
    """
    safe_api_call(
        adapter.client.teams.remove_organization_memberships,
        team_id,
        organization_membership_ids,
        error_context=f"Failed to remove organization memberships from team {team_id}",
    )


def list_team_organization_memberships(adapter: TerraformClient, team_id: str) -> list[Dict[str, Any]]:
    """
    List all organization memberships in a team.

    Args:
        adapter (TerraformClient): An authenticated client.
        team_id (str): The ID of the team.

    Returns:
        list: A list of organization membership dictionaries.
    """
    try:
        memberships = list(adapter.client.teams.list_organization_memberships(team_id))
        return [format_response(membership) for membership in memberships]
    except NotFound:
        return []
