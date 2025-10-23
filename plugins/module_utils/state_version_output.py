# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from typing import Any, Dict, List

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace


def _handle_api_response(response: Dict) -> Dict:
    """
    Handle common API response patterns for Terraform Cloud/Enterprise requests.

    Args:
        response: The response dictionary from the API call

    Returns:
        dict: The response if successful, empty dict if not found

    Raises:
        TerraformError: If the request fails with a non-404 or non-200 status code
    """
    response_status = response.get("status")

    if response_status == 404:
        return {}
    elif response_status == 200:
        return response
    else:
        raise TerraformError(response)


def _extract_data_from_response(response: Dict[str, Any]) -> Any:
    """
    Extract actual data from TerraformClient response structure.
    Handles potential nested 'data' keys in responses.

    Args:
        response: Response from TerraformClient

    Returns:
        The actual data from the response
    """
    outer_data = response.get("data", response)
    if isinstance(outer_data, dict) and "data" in outer_data:
        return outer_data["data"]
    return outer_data


def _format_output_data(output_data: Dict) -> Dict[str, Any]:
    """
    Format a single output data object into standardized format.

    Masks null sensitive values as '<sensitive>'

    Args:
        output_data: Raw output data from API

    Returns:
        dict: Formatted output with standardized keys
    """
    attributes = output_data.get("attributes", {})
    is_sensitive = attributes.get("sensitive", False)
    raw_value = attributes.get("value")

    value = "<sensitive>" if (is_sensitive and raw_value is None) else raw_value

    return {
        "id": output_data.get("id"),
        "name": attributes.get("name"),
        "sensitive": is_sensitive,
        "type": attributes.get("type"),
        "value": value,
        "detailed_type": attributes.get("detailed-type"),
    }


def resolve_workspace_id(
    client: TerraformClient,
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

    workspace_data = get_workspace(client, organization, workspace)
    if not workspace_data:
        raise ValueError(
            f"Workspace '{workspace}' was not found in organization '{organization}'.",
        )

    workspace_data = _extract_data_from_response(workspace_data)
    resolved_id = workspace_data.get("id")

    if not resolved_id:
        raise ValueError(
            f"Invalid workspace data returned for '{workspace}' in '{organization}'.",
        )

    return resolved_id


def get_specific_output(client: TerraformClient, state_version_output_id: str, display_sensitive: bool = False) -> Dict[str, Any]:
    """
    Retrieve a specific state version output by ID and format it.

    Args:
        client: An authenticated TerraformClient instance
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
        TerraformError: If API call fails
    """
    response = client.get(f"/state-version-outputs/{state_version_output_id}")
    response = _handle_api_response(response)

    if not response:
        raise ValueError(f"State version output with ID '{state_version_output_id}' was not found.")

    actual_data = _extract_data_from_response(response)

    if not actual_data or not actual_data.get("id"):
        raise ValueError(f"State version output with ID '{state_version_output_id}' was not found.")

    attributes = actual_data.get("attributes", {})
    is_sensitive = attributes.get("sensitive", False)
    raw_value = attributes.get("value")

    # Apply masking based on display_sensitive flag
    value = raw_value if (display_sensitive or not is_sensitive) else "<sensitive>"

    return {
        "id": actual_data.get("id"),
        "name": attributes.get("name"),
        "sensitive": is_sensitive,
        "type": attributes.get("type"),
        "value": value,
        "detailed_type": attributes.get("detailed-type"),
    }


def get_workspace_outputs(client: TerraformClient, workspace_id: str, display_sensitive: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieve all current state version outputs for a workspace and format them.

    Args:
        client: An authenticated client instance
        workspace_id: The workspace ID
        display_sensitive: If True, make individual API calls to get actual sensitive values.
                          If False (default), sensitive values will be '<sensitive>'.

    Returns:
        list: List of formatted output data dictionaries

    Raises:
        ValueError: If workspace is not found or response structure is invalid
        TerraformError: If API call fails
    """
    response = client.get(f"/workspaces/{workspace_id}/current-state-version-outputs")
    response = _handle_api_response(response)

    if not response:
        raise ValueError(f"Workspace with ID '{workspace_id}' was not found.")

    outputs_data = _extract_data_from_response(response)

    if isinstance(outputs_data, dict) and "data" in outputs_data:
        outputs_data = outputs_data["data"]

    if not isinstance(outputs_data, list):
        raise ValueError(f"Unexpected response structure for workspace '{workspace_id}'.")

    if not outputs_data:
        return []

    if not display_sensitive:
        return [_format_output_data(output) for output in outputs_data]

    formatted_outputs = []
    for output in outputs_data:
        is_sensitive = output.get("attributes", {}).get("sensitive", False)

        if is_sensitive:
            output_id = output.get("id")
            if output_id:
                try:
                    detailed = get_specific_output(client, output_id, display_sensitive=True)
                    formatted_outputs.append(detailed)
                    continue
                except Exception:
                    pass

        formatted_outputs.append(_format_output_data(output))

    return formatted_outputs


def get_output_by_name(client: TerraformClient, workspace_id: str, name: str, display_sensitive: bool = False) -> Dict[str, Any]:
    """
    Get a specific output by name from workspace outputs.

    Args:
        client: An authenticated client instance
        workspace_id: The workspace ID
        name: Name of the output to find
        display_sensitive: If True and output is sensitive, fetch it individually to get actual value.
                          If False (default), sensitive values will be '<sensitive>'.

    Returns:
        dict: Formatted output data for the named output

    Raises:
        ValueError: If output is not found or workspace is invalid
        TerraformError: If API call fails
    """
    outputs = get_workspace_outputs(client, workspace_id, display_sensitive=False)

    for output in outputs:
        if output.get("name") == name:
            if display_sensitive and output.get("sensitive") and output.get("id"):
                try:
                    return get_specific_output(client, output.get("id"), display_sensitive=True)
                except Exception:
                    pass

            return output

    raise ValueError(f"Output with name '{name}' not found in workspace '{workspace_id}'.")
