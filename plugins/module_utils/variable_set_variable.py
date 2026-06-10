# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Helpers for variable-set-scoped variables (distinct from workspace variables)."""

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        VariableSetVariableCreateOptions,
        VariableSetVariableListOptions,
        VariableSetVariableUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class VariableSetVariableCreateOptions:  # type: ignore[no-redef]
        pass

    class VariableSetVariableListOptions:  # type: ignore[no-redef]
        pass

    class VariableSetVariableUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call

SENSITIVE_PLACEHOLDER = "<sensitive>"


def list_variable_set_variables(adapter: TerraformClient, variable_set_id: str) -> List[Dict[str, Any]]:
    """List all variables owned by the given variable set."""
    try:
        options = VariableSetVariableListOptions(page_size=100)
        return [format_response(v) for v in adapter.client.variable_set_variables.list(variable_set_id, options)]
    except NotFound:
        return []


def mask_sensitive(variables: List[Dict[str, Any]], display_sensitive: bool = False) -> List[Dict[str, Any]]:
    """Replace sensitive variable values with a placeholder unless explicitly requested."""
    if display_sensitive:
        return variables
    masked: List[Dict[str, Any]] = []
    for v in variables:
        if v.get("sensitive"):
            clone = dict(v)
            clone["value"] = SENSITIVE_PLACEHOLDER
            masked.append(clone)
        else:
            masked.append(v)
    return masked


def get_variable_set_variable(
    adapter: TerraformClient,
    variable_set_id: str,
    variable_id: str,
) -> Optional[Dict[str, Any]]:
    """Read a single variable-set variable by its ID."""
    try:
        variable = adapter.client.variable_set_variables.read(variable_set_id, variable_id)
        return format_response(variable)
    except NotFound:
        return None


def get_variable_set_variable_by_key(
    adapter: TerraformClient,
    variable_set_id: str,
    key: str,
) -> Optional[Dict[str, Any]]:
    """Resolve a variable-set variable by its key."""
    for v in list_variable_set_variables(adapter, variable_set_id):
        if v.get("key") == key:
            return v
    return None


def create_variable_set_variable(
    adapter: TerraformClient,
    variable_set_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a variable within the given variable set."""
    options = VariableSetVariableCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.variable_set_variables.create,
        variable_set_id,
        options,
        error_context=f"Failed to create variable {data.get('key')!r} in variable set {variable_set_id}",
    )
    return format_response(response)


def update_variable_set_variable(
    adapter: TerraformClient,
    variable_set_id: str,
    variable_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Update an existing variable within a variable set."""
    options = VariableSetVariableUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.variable_set_variables.update,
        variable_set_id,
        variable_id,
        options,
        error_context=f"Failed to update variable {variable_id} in variable set {variable_set_id}",
    )
    return format_response(response)


def delete_variable_set_variable(
    adapter: TerraformClient,
    variable_set_id: str,
    variable_id: str,
) -> None:
    """Delete a variable from a variable set by its ID."""
    safe_api_call(
        adapter.client.variable_set_variables.delete,
        variable_set_id,
        variable_id,
        error_context=f"Failed to delete variable {variable_id} in variable set {variable_set_id}",
    )
