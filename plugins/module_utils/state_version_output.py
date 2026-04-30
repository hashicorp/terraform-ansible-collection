# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Dict, List

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace


def _format_output_data(output_data: Dict) -> Dict[str, Any]:
    """
    Format a single output data object into standardized format.

    Masks null sensitive values as '<sensitive>'

    Args:
        output_data: Raw output data from API

    Returns:
        dict: Formatted output with standardized keys
    """
    is_sensitive = output_data.get("sensitive", False)
    raw_value = output_data.get("value")

    value = "<sensitive>" if (is_sensitive and raw_value is None) else raw_value

    return {
        "id": output_data.get("id"),
        "name": output_data.get("name"),
        "sensitive": is_sensitive,
        "type": output_data.get("type"),
        "value": value,
        "detailed_type": output_data.get("detailed-type"),
    }


def resolve_workspace_id(
    adapter: TerraformClient,
    workspace_id: str = None,
    workspace: str = None,
    organization: str = None,
) -> str:
    """
    Resolve workspace ID from flexible input parameters.

    This is a convenience wrapper that handles multiple input patterns for
    workspace identification in state version output operations:
    - If workspace_id is provided directly, returns it as-is
    - If workspace and organization are provided, fetches workspace data
      via get_workspace() from module_utils/workspace.py and extracts the ID

    Args:
        client: An authenticated client instance
        workspace_id: Direct workspace ID (optional)
        workspace: Workspace name (optional, requires organization)
        organization: Organization name (optional, requires workspace)

    Returns:
        str: The resolved workspace ID

    Raises:
        ValueError: If workspace cannot be resolved, required parameters are
                   missing, or workspace is not found

    """

    if workspace_id:
        return workspace_id

    if not (workspace and organization):
        raise ValueError(
            "Either workspace_id or both workspace and organization must be provided",
        )

    workspace_data = get_workspace(adapter, organization, workspace)
    if not workspace_data:
        raise ValueError(
            f"Workspace '{workspace}' was not found in organization '{organization}'.",
        )

    resolved_id = workspace_data.get("id")

    if not resolved_id:
        raise ValueError(
            f"Invalid workspace data returned for '{workspace}' in '{organization}'.",
        )

    return resolved_id


def get_specific_output(adapter: TerraformClient, state_version_output_id: str, display_sensitive: bool = False) -> Dict[str, Any]:
    """
    Retrieve a specific state version output by ID and format it.

    Args:
        adapter: An authenticated TerraformClient instance
        state_version_output_id: The output ID to retrieve
        display_sensitive: If False (default), mask sensitive values with '<sensitive>'.
                          If True, return actual values even for sensitive outputs.

    Returns:
        dict: Formatted output data with keys:
            - id: Output ID
            - name: Output name
            - value: Output value (masked if sensitive and display_sensitive=False)
            - type: Terraform type
            - detailed_type: Detailed type information
            - sensitive: Whether output is marked sensitive

    Raises:
        ValueError: If output is not found
    """
    try:
        response = adapter.client.state_version_outputs.read(state_version_output_id)
    except NotFound:
        raise ValueError(f"State version output with ID '{state_version_output_id}' was not found.")

    actual_data = format_response(response)

    # attributes = actual_data.get("attributes", {})
    is_sensitive = actual_data.get("sensitive", False)
    raw_value = actual_data.get("value")

    # Apply masking based on display_sensitive flag
    value = raw_value if (display_sensitive or not is_sensitive) else "<sensitive>"

    return {
        "id": actual_data.get("id"),
        "name": actual_data.get("name"),
        "sensitive": is_sensitive,
        "type": actual_data.get("type"),
        "value": value,
        "detailed_type": actual_data.get("detailed-type"),
    }


def get_workspace_outputs(adapter: TerraformClient, workspace_id: str, display_sensitive: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieve all current state version outputs for a workspace and format them.

    Args:
        adapter: An authenticated client instance
        workspace_id: The workspace ID
        display_sensitive: If True, make individual API calls to get actual sensitive values.
                          If False (default), sensitive values will be '<sensitive>'.

    Returns:
        list: List of formatted output data dictionaries

    Raises:
        ValueError: If workspace is not found or response structure is invalid
    """
    try:
        response = list(adapter.client.state_version_outputs.read_current(workspace_id))
    except NotFound:
        raise ValueError(f"Workspace with ID '{workspace_id}' was not found.")

    outputs_data = response

    if not outputs_data:
        return []

    formatted_outputs = []
    for output in outputs_data:
        formatted = _format_output_data(format_response(output))

        if display_sensitive and formatted.get("sensitive") and formatted.get("id"):
            try:
                formatted = get_specific_output(adapter, formatted["id"], display_sensitive=True)
            except ValueError:
                pass

        formatted_outputs.append(formatted)

    return formatted_outputs


def get_output_by_name(adapter: TerraformClient, workspace_id: str, name: str, display_sensitive: bool = False) -> Dict[str, Any]:
    """
    Get a specific output by name from workspace outputs.

    Args:
        adapter: An authenticated client instance
        workspace_id: The workspace ID
        name: Name of the output to find
        display_sensitive: If True and output is sensitive, fetch it individually to get actual value.
                          If False (default), sensitive values will be '<sensitive>'.

    Returns:
        dict: Formatted output data for the named output

    Raises:
        ValueError: If output is not found or workspace is invalid
    """
    outputs = get_workspace_outputs(adapter, workspace_id, display_sensitive=False)

    for output in outputs:
        if output.get("name") == name:
            if display_sensitive and output.get("sensitive") and output.get("id"):
                try:
                    return get_specific_output(adapter, output.get("id"), display_sensitive=True)
                except ValueError:
                    # If individual fetch fails, returns the already retrieved output
                    pass

            return output

    raise ValueError(f"Output with name '{name}' not found in workspace '{workspace_id}'.")
