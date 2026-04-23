from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        Project,
        VariableSetApplyToProjectsOptions,
        VariableSetApplyToWorkspacesOptions,
        VariableSetCreateOptions,
        VariableSetIncludeOpt,
        VariableSetListOptions,
        VariableSetReadOptions,
        VariableSetRemoveFromProjectsOptions,
        VariableSetRemoveFromWorkspacesOptions,
        VariableSetUpdateOptions,
        Workspace,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class Project:  # type: ignore[no-redef]
        pass

    class VariableSetApplyToProjectsOptions:  # type: ignore[no-redef]
        pass

    class VariableSetApplyToWorkspacesOptions:  # type: ignore[no-redef]
        pass

    class VariableSetCreateOptions:  # type: ignore[no-redef]
        pass

    class VariableSetIncludeOpt:  # type: ignore[no-redef]
        WORKSPACES = "workspaces"
        PROJECTS = "projects"

    class VariableSetListOptions:  # type: ignore[no-redef]
        pass

    class VariableSetReadOptions:  # type: ignore[no-redef]
        pass

    class VariableSetRemoveFromProjectsOptions:  # type: ignore[no-redef]
        pass

    class VariableSetRemoveFromWorkspacesOptions:  # type: ignore[no-redef]
        pass

    class VariableSetUpdateOptions:  # type: ignore[no-redef]
        pass

    class Workspace:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_variable_sets(adapter: TerraformClient, organization: str) -> List[Dict[str, Any]]:
    """List variable sets under an organization."""
    try:
        return [format_response(vs) for vs in adapter.client.variable_sets.list(organization)]
    except NotFound:
        return []


def get_variable_set(
    adapter: TerraformClient,
    variable_set_id: str,
    include_relations: bool = False,
) -> Optional[Dict[str, Any]]:
    """Read a variable set by its ID.

    When ``include_relations`` is True, attached workspaces and projects are
    embedded in the response — required for attachment drift detection.
    """
    try:
        options = None
        if include_relations:
            options = VariableSetReadOptions(include=[VariableSetIncludeOpt.WORKSPACES, VariableSetIncludeOpt.PROJECTS])
        variable_set = adapter.client.variable_sets.read(variable_set_id, options=options)
        return format_response(variable_set)
    except NotFound:
        return None


def get_variable_set_by_name(
    adapter: TerraformClient,
    organization: str,
    name: str,
) -> Optional[Dict[str, Any]]:
    """Look up a variable set by (organization, name)."""
    for variable_set in list_variable_sets(adapter, organization):
        if variable_set.get("name") == name:
            return variable_set
    return None


def create_variable_set(
    adapter: TerraformClient,
    organization: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a variable set under the given organization."""
    options = VariableSetCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.variable_sets.create,
        organization,
        options,
        error_context=f"Failed to create variable set {data.get('name')!r} in organization {organization!r}",
    )
    return format_response(response)


def update_variable_set(
    adapter: TerraformClient,
    variable_set_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Update an existing variable set."""
    options = VariableSetUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.variable_sets.update,
        variable_set_id,
        options,
        error_context=f"Failed to update variable set {variable_set_id}",
    )
    return format_response(response)


def delete_variable_set(adapter: TerraformClient, variable_set_id: str) -> None:
    """Delete a variable set by ID."""
    safe_api_call(
        adapter.client.variable_sets.delete,
        variable_set_id,
        error_context=f"Failed to delete variable set {variable_set_id}",
    )


def apply_to_workspaces(adapter: TerraformClient, variable_set_id: str, workspace_ids: List[str]) -> None:
    """Attach the variable set to the given workspaces (no-op if empty)."""
    if not workspace_ids:
        return
    options = VariableSetApplyToWorkspacesOptions(workspaces=[Workspace(id=wid) for wid in workspace_ids])
    safe_api_call(
        adapter.client.variable_sets.apply_to_workspaces,
        variable_set_id,
        options,
        error_context=f"Failed to attach variable set {variable_set_id} to workspaces {workspace_ids}",
    )


def remove_from_workspaces(adapter: TerraformClient, variable_set_id: str, workspace_ids: List[str]) -> None:
    """Detach the variable set from the given workspaces (no-op if empty)."""
    if not workspace_ids:
        return
    options = VariableSetRemoveFromWorkspacesOptions(workspaces=[Workspace(id=wid) for wid in workspace_ids])
    safe_api_call(
        adapter.client.variable_sets.remove_from_workspaces,
        variable_set_id,
        options,
        error_context=f"Failed to detach variable set {variable_set_id} from workspaces {workspace_ids}",
    )


def apply_to_projects(adapter: TerraformClient, variable_set_id: str, project_ids: List[str]) -> None:
    """Attach the variable set to the given projects (no-op if empty)."""
    if not project_ids:
        return
    options = VariableSetApplyToProjectsOptions(projects=[Project(id=pid) for pid in project_ids])
    safe_api_call(
        adapter.client.variable_sets.apply_to_projects,
        variable_set_id,
        options,
        error_context=f"Failed to attach variable set {variable_set_id} to projects {project_ids}",
    )


def remove_from_projects(adapter: TerraformClient, variable_set_id: str, project_ids: List[str]) -> None:
    """Detach the variable set from the given projects (no-op if empty)."""
    if not project_ids:
        return
    options = VariableSetRemoveFromProjectsOptions(projects=[Project(id=pid) for pid in project_ids])
    safe_api_call(
        adapter.client.variable_sets.remove_from_projects,
        variable_set_id,
        options,
        error_context=f"Failed to detach variable set {variable_set_id} from projects {project_ids}",
    )
