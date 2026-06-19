# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        TeamProjectAccessAddOptions,
        TeamProjectAccessListOptions,
        TeamProjectAccessProjectPermissionsOptions,
        TeamProjectAccessUpdateOptions,
        TeamProjectAccessWorkspacePermissionsOptions,
    )
    from pytfe.models.project import Project
    from pytfe.models.team import Team
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class TeamProjectAccessListOptions:  # type: ignore[no-redef]
        pass

    class TeamProjectAccessAddOptions:  # type: ignore[no-redef]
        pass

    class TeamProjectAccessUpdateOptions:  # type: ignore[no-redef]
        pass

    class TeamProjectAccessProjectPermissionsOptions:  # type: ignore[no-redef]
        pass

    class TeamProjectAccessWorkspacePermissionsOptions:  # type: ignore[no-redef]
        pass

    class Team:  # type: ignore[no-redef]
        pass

    class Project:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call

# Flat param names → TeamProjectAccessProjectPermissionsOptions kwarg names
_PROJECT_ACCESS_PARAM_MAP = {
    "project_settings": "settings",
    "project_teams": "teams",
    "project_variable_sets": "variable_sets",
}

# Flat param names → TeamProjectAccessWorkspacePermissionsOptions kwarg names
_WORKSPACE_ACCESS_PARAM_MAP = {
    "workspace_runs": "runs",
    "workspace_sentinel_mocks": "sentinel_mocks",
    "workspace_state_versions": "state_versions",
    "workspace_variables": "variables",
    "workspace_create": "create",
    "workspace_delete": "delete",
    "workspace_locking": "locking",
    "workspace_move": "move",
    "workspace_run_tasks": "run_tasks",
}

# model_dump() key names for TeamProjectAccessProjectPermissions → flat param names
_PROJECT_ACCESS_RESPONSE_MAP = {
    "project_settings_permission": "project_settings",
    "project_teams_permission": "project_teams",
    "project_variable_sets_permission": "project_variable_sets",
}

# model_dump() key names for TeamProjectAccessWorkspacePermissions → flat param names
_WORKSPACE_ACCESS_RESPONSE_MAP = {
    "runs": "workspace_runs",
    "sentinel_mocks": "workspace_sentinel_mocks",
    "state_versions": "workspace_state_versions",
    "variables": "workspace_variables",
    "create": "workspace_create",
    "delete": "workspace_delete",
    "locking": "workspace_locking",
    "move": "workspace_move",
    "run_tasks": "workspace_run_tasks",
}


def _normalize_response(tpa_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten nested team/project relationship objects and permission sub-dicts.

    ``format_response`` returns ``{"team": {"id": ...}, "project": {"id": ...}}``.
    This helper promotes ``team_id`` and ``project_id`` to the top level and removes
    the nested dicts so callers can do simple equality checks.
    """
    result = dict(tpa_dict)

    # Flatten relationship objects
    team = result.pop("team", None)
    if isinstance(team, dict):
        result["team_id"] = team.get("id")

    project = result.pop("project", None)
    if isinstance(project, dict):
        result["project_id"] = project.get("id")

    # Flatten nested project_access and workspace_access sub-dicts to the top level
    # under prefixed param names so the module can do simple dict_diff comparisons.
    project_access = result.pop("project_access", None)
    if isinstance(project_access, dict):
        for response_key, param_key in _PROJECT_ACCESS_RESPONSE_MAP.items():
            if response_key in project_access:
                result[param_key] = project_access[response_key]

    workspace_access = result.pop("workspace_access", None)
    if isinstance(workspace_access, dict):
        for response_key, param_key in _WORKSPACE_ACCESS_RESPONSE_MAP.items():
            if response_key in workspace_access:
                result[param_key] = workspace_access[response_key]

    return result


def list_team_project_accesses(adapter: TerraformClient, project_id: str) -> List[Dict[str, Any]]:
    """List all team access grants for a project.

    Args:
        adapter: Authenticated TerraformClient.
        project_id: The project ID to list access grants for.

    Returns:
        List of normalized team-project access dicts.
    """
    try:
        list_options = TeamProjectAccessListOptions(project_id=project_id)
        return [_normalize_response(format_response(tpa)) for tpa in adapter.client.team_project_accesses.list(list_options)]
    except NotFound:
        return []


def get_team_project_access_by_id(adapter: TerraformClient, tpa_id: str) -> Optional[Dict[str, Any]]:
    """Read a team-project access grant by its ID.

    Args:
        adapter: Authenticated TerraformClient.
        tpa_id: The team-project access ID (e.g. ``tpa-xxx``).

    Returns:
        Normalized dict if found, None otherwise.
    """
    try:
        tpa = adapter.client.team_project_accesses.read(tpa_id)
        return _normalize_response(format_response(tpa))
    except NotFound:
        return None


def get_team_project_access(
    adapter: TerraformClient,
    project_id: str,
    team_id: str,
) -> Optional[Dict[str, Any]]:
    """Find an access grant by project and team IDs.

    Args:
        adapter: Authenticated TerraformClient.
        project_id: The project to search.
        team_id: The team whose grant to find.

    Returns:
        Normalized dict if found, None otherwise.
    """
    for tpa in list_team_project_accesses(adapter, project_id):
        if tpa.get("team_id") == team_id:
            return tpa
    return None


def _build_project_access_options(options_dict: Dict[str, Any]) -> Optional[Any]:
    """Build TeamProjectAccessProjectPermissionsOptions from flat params if any are set."""
    kwargs = {api_key: options_dict[param_key] for param_key, api_key in _PROJECT_ACCESS_PARAM_MAP.items() if options_dict.get(param_key) is not None}
    if not kwargs:
        return None
    return TeamProjectAccessProjectPermissionsOptions(**kwargs)


def _build_workspace_access_options(options_dict: Dict[str, Any]) -> Optional[Any]:
    """Build TeamProjectAccessWorkspacePermissionsOptions from flat params if any are set."""
    kwargs = {api_key: options_dict[param_key] for param_key, api_key in _WORKSPACE_ACCESS_PARAM_MAP.items() if options_dict.get(param_key) is not None}
    if not kwargs:
        return None
    return TeamProjectAccessWorkspacePermissionsOptions(**kwargs)


def add_team_project_access(
    adapter: TerraformClient,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    """Grant a team access to a project.

    Args:
        adapter: Authenticated TerraformClient.
        options: Dict containing ``team_id``, ``project_id``, ``access``,
            and any optional flat permission fields.

    Returns:
        Normalized dict of the created grant.
    """
    add_options = TeamProjectAccessAddOptions(
        access=options["access"],
        team=Team(id=options["team_id"]),
        project=Project(id=options["project_id"]),
        project_access=_build_project_access_options(options),
        workspace_access=_build_workspace_access_options(options),
    )
    response = safe_api_call(
        adapter.client.team_project_accesses.add,
        add_options,
        error_context=f"Failed to grant team {options.get('team_id')} access to project {options.get('project_id')}",
    )
    return _normalize_response(format_response(response))


def update_team_project_access(
    adapter: TerraformClient,
    tpa_id: str,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    """Update an existing team-project access grant.

    Args:
        adapter: Authenticated TerraformClient.
        tpa_id: The access grant ID to update.
        options: Dict of fields to update (access + flat permission fields).

    Returns:
        Normalized dict of the updated grant.
    """
    update_options = TeamProjectAccessUpdateOptions(
        access=options.get("access"),
        project_access=_build_project_access_options(options),
        workspace_access=_build_workspace_access_options(options),
    )
    response = safe_api_call(
        adapter.client.team_project_accesses.update,
        tpa_id,
        update_options,
        error_context=f"Failed to update team-project access grant {tpa_id}",
    )
    return _normalize_response(format_response(response))


def remove_team_project_access(adapter: TerraformClient, tpa_id: str) -> None:
    """Remove a team-project access grant.

    Args:
        adapter: Authenticated TerraformClient.
        tpa_id: The access grant ID to remove.
    """
    safe_api_call(
        adapter.client.team_project_accesses.remove,
        tpa_id,
        error_context=f"Failed to remove team-project access grant {tpa_id}",
    )
