from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        VariableCreateOptions,
        VariableUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class VariableCreateOptions:  # type: ignore[no-redef]
        pass

    class VariableUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_variables(adapter: TerraformClient, workspace_id: str) -> List[Dict[str, Any]]:
    """List workspace-owned variables (does not include varset-inherited values)."""
    try:
        return [format_response(v) for v in adapter.client.variables.list(workspace_id)]
    except NotFound:
        return []


def get_variable(adapter: TerraformClient, workspace_id: str, variable_id: str) -> Optional[Dict[str, Any]]:
    """Read a variable by its ID under the given workspace."""
    try:
        variable = adapter.client.variables.read(workspace_id, variable_id)
        return format_response(variable)
    except NotFound:
        return None


def get_variable_by_key(adapter: TerraformClient, workspace_id: str, key: str, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Look up a variable by (key[, category]) within a workspace.

    TFE/C allows the same ``key`` to exist under different categories (e.g. an
    ``env`` and a ``terraform`` variable named ``FOO``). When ``category`` is
    given, both must match; otherwise the first key match wins.
    """
    for variable in list_variables(adapter, workspace_id):
        if variable.get("key") != key:
            continue
        if category is not None and variable.get("category") != category:
            continue
        return variable
    return None


def create_variable(adapter: TerraformClient, workspace_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a variable under the given workspace."""
    options = VariableCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.variables.create,
        workspace_id,
        options,
        error_context=f"Failed to create variable {data.get('key')!r} on workspace {workspace_id}",
    )
    return format_response(response)


def update_variable(adapter: TerraformClient, workspace_id: str, variable_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update values of an existing variable."""
    options = VariableUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.variables.update,
        workspace_id,
        variable_id,
        options,
        error_context=f"Failed to update variable {variable_id} on workspace {workspace_id}",
    )
    return format_response(response)


def delete_variable(adapter: TerraformClient, workspace_id: str, variable_id: str) -> None:
    """Delete a variable by its ID."""
    safe_api_call(
        adapter.client.variables.delete,
        workspace_id,
        variable_id,
        error_context=f"Failed to delete variable {variable_id} on workspace {workspace_id}",
    )
