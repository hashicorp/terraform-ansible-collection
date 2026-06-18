# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        TeamWorkspaceAccessAddOptions,
        TeamWorkspaceAccessUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class TeamWorkspaceAccessAddOptions:  # type: ignore[no-redef]
        pass

    class TeamWorkspaceAccessUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call

# Fields that belong to the access-permission set; used when building
# update payloads so only attributes the user explicitly set are sent.
_PERMISSION_FIELDS = frozenset(
    [
        "access",
        "runs",
        "variables",
        "state_versions",
        "sentinel_mocks",
        "workspace_locking",
        "run_tasks",
        "policy_overrides",
    ]
)


def list_team_workspace_accesses(adapter: TerraformClient, workspace_id: str) -> List[Dict[str, Any]]:
    """List all team access grants for a workspace.

    Args:
        adapter: Authenticated TerraformClient.
        workspace_id: The workspace ID to list access grants for.

    Returns:
        List of formatted team-workspace access dicts.
    """
    try:
        return [format_response(twa) for twa in adapter.client.team_workspace_accesses.list(workspace_id)]
    except NotFound:
        return []


def get_team_workspace_access_by_id(adapter: TerraformClient, twa_id: str) -> Optional[Dict[str, Any]]:
    """Read a team-workspace access grant by its ID.

    Args:
        adapter: Authenticated TerraformClient.
        twa_id: The team-workspace access ID (e.g. ``tws-xxx``).

    Returns:
        Formatted dict if found, None otherwise.
    """
    try:
        twa = adapter.client.team_workspace_accesses.read(twa_id)
        return format_response(twa)
    except NotFound:
        return None


def get_team_workspace_access(
    adapter: TerraformClient,
    workspace_id: str,
    team_id: str,
) -> Optional[Dict[str, Any]]:
    """Find an access grant by workspace and team IDs.

    Iterates the workspace's access grants and returns the first one
    that belongs to ``team_id``.

    Args:
        adapter: Authenticated TerraformClient.
        workspace_id: The workspace to search.
        team_id: The team whose grant to find.

    Returns:
        Formatted dict if found, None otherwise.
    """
    for twa in list_team_workspace_accesses(adapter, workspace_id):
        if twa.get("team_id") == team_id:
            return twa
    return None


def add_team_workspace_access(
    adapter: TerraformClient,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    """Grant a team access to a workspace.

    Args:
        adapter: Authenticated TerraformClient.
        options: Dict containing ``team_id``, ``workspace_id``, ``access``,
            and any optional permission fields.

    Returns:
        Formatted dict of the created grant.
    """
    add_options = TeamWorkspaceAccessAddOptions(**{k: v for k, v in options.items() if v is not None})
    response = safe_api_call(
        adapter.client.team_workspace_accesses.add,
        add_options,
        error_context=f"Failed to grant team {options.get('team_id')} access to workspace {options.get('workspace_id')}",
    )
    return format_response(response)


def update_team_workspace_access(
    adapter: TerraformClient,
    twa_id: str,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    """Update an existing team-workspace access grant.

    Args:
        adapter: Authenticated TerraformClient.
        twa_id: The access grant ID to update.
        options: Dict of permission fields to update. Only fields present
            in ``_PERMISSION_FIELDS`` are forwarded.

    Returns:
        Formatted dict of the updated grant.
    """
    update_kwargs = {k: v for k, v in options.items() if k in _PERMISSION_FIELDS and v is not None}
    update_options = TeamWorkspaceAccessUpdateOptions(**update_kwargs)
    response = safe_api_call(
        adapter.client.team_workspace_accesses.update,
        twa_id,
        update_options,
        error_context=f"Failed to update team-workspace access grant {twa_id}",
    )
    return format_response(response)


def remove_team_workspace_access(adapter: TerraformClient, twa_id: str) -> None:
    """Remove a team-workspace access grant.

    Args:
        adapter: Authenticated TerraformClient.
        twa_id: The access grant ID to remove.
    """
    safe_api_call(
        adapter.client.team_workspace_accesses.remove,
        twa_id,
        error_context=f"Failed to remove team-workspace access grant {twa_id}",
    )
