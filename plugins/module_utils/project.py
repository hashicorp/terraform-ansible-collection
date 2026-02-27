# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Project adapter module for pytfe SDK integration.

This module provides standalone functions that wrap the pytfe SDK's Projects service,
allowing Ansible modules to interact with Terraform Cloud/Enterprise projects through
the pytfe library instead of direct REST calls.

Each function:
- Accepts a TerraformClient instance and project-specific parameters
- Uses pytfe SDK methods (client.projects.*)
- Wraps responses in API response format expected by Ansible modules
- Handles pytfe.errors.NotFound as empty dict (404 not found)
- Translates other SDK exceptions to TerraformError
"""

from typing import Any, Dict, List, Optional

from pytfe.errors import NotFound

from .client import TerraformClient
from .exceptions import TerraformError


def _wrap_response(data: Any) -> Dict[str, Any]:
    """Convert pytfe SDK response to REST API format.

    Converts pytfe Pydantic models (flat structure) to the REST API
    nested structure with "attributes" and "relationships" keys.

    Args:
        data: Pydantic model from pytfe SDK or dict

    Returns:
        Dictionary in REST API response format with "attributes" and "relationships"
    """
    # Convert Pydantic to dict if needed
    if hasattr(data, "model_dump"):
        data_dict = data.model_dump(mode="json", exclude_none=True)
    else:
        data_dict = data if isinstance(data, dict) else {}

    # Determine the type from pytfe attributes
    pytfe_type = type(data).__name__ if hasattr(data, "__class__") else ""

    # Special handling for different types
    if "TagBinding" in pytfe_type or "tag" in pytfe_type.lower():
        # TagBinding models have key, value as flat attributes
        return {
            "id": data_dict.get("id"),
            "type": "tag-bindings",
            "attributes": {
                "key": data_dict.get("key"),
                "value": data_dict.get("value"),
            }
        }

    # Default handling for projects and other resources
    attributes = {}
    relationships = {}

    # Map pytfe fields to REST API attribute names for projects
    field_mapping = {
        "name": "name",
        "description": "description",
        "execution_mode": "default-execution-mode",
        "auto_destroy_activity_duration": "auto-destroy-activity-duration",
        "setting_overwrites": "setting-overwrites",
        "default_agent_pool_id": "default-agent-pool-id",
    }

    for pytfe_field, rest_field in field_mapping.items():
        if pytfe_field in data_dict and data_dict[pytfe_field] is not None:
            attributes[rest_field] = data_dict[pytfe_field]

    # Build relationships if default_agent_pool_id exists
    if "default_agent_pool_id" in data_dict and data_dict["default_agent_pool_id"]:
        relationships["default-agent-pool"] = {
            "data": {"id": data_dict["default_agent_pool_id"]}
        }

    # Return REST API response structure
    return {
        "id": data_dict.get("id"),
        "type": "projects",
        "attributes": attributes,
        "relationships": relationships,
    }





def _wrap_list_response(items: List[Any]) -> List[Dict[str, Any]]:
    """Wrap a list of pytfe SDK responses.

    Args:
        items: List of Pydantic models from pytfe SDK

    Returns:
        List of dicts in API format
    """
    return [_wrap_response(item) for item in items] if items else []


def get_project_by_id(client: TerraformClient, project_id: str) -> Dict[str, Any]:
    """
    Retrieve a project by its ID using the pytfe SDK.

    Args:
        client: TerraformClient instance
        project_id: The unique ID of the project to retrieve

    Returns:
        Dictionary containing the project data wrapped in API format, or empty dict if not found

    Raises:
        TerraformError: If the SDK operation fails (other than 404)
    """
    try:
        project = client.safe_api_call(
            client.client.projects.read,
            project_id,
            error_context=f"Failed to retrieve project {project_id}",
        )
        return {"data": _wrap_response(project)}
    except NotFound:
        # Project doesn't exist - return empty dict
        return {}


def get_project_by_name(client: TerraformClient, organization: str, name: str) -> Dict[str, Any]:
    """
    Retrieve a project by name within an organization using the pytfe SDK.

    Args:
        client: TerraformClient instance
        organization: The organization name
        name: The project name to search for

    Returns:
        Dictionary containing the first matching project, or empty dict if not found

    Raises:
        TerraformError: If the SDK operation fails
    """
    try:
        # Use the pytfe SDK's list method to get all projects
        projects = client.safe_api_call(
            client.client.projects.list,
            organization,
            error_context=f"Failed to list projects in organization {organization}",
        )

        # Find the first project matching the name
        if projects:
            for project in projects:
                project_data = _wrap_response(project)
                # Now checking REST API format attributes
                if project_data.get("attributes", {}).get("name") == name:
                    return {"data": project_data}

        return {}
    except NotFound:
        return {}


def create_project(
    client: TerraformClient,
    organization: str,
    name: str,
    description: Optional[str] = None,
    tag_bindings: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Create a new project using the pytfe SDK.

    Args:
        client: TerraformClient instance
        organization: The organization name
        name: The project name
        description: Optional project description
        tag_bindings: Optional list of tag binding dicts with 'key' and 'value' (ignored - tag bindings must be added separately)
        **kwargs: Additional project attributes (auto_destroy_activity_duration, execution_mode, etc.)

    Returns:
        Dictionary containing the created project data wrapped in API format

    Raises:
        TerraformError: If the SDK operation fails
    """
    try:
        # Build the ProjectCreateOptions payload
        project_options = {
            "name": name,
        }

        if description:
            project_options["description"] = description

        # Add any additional attributes from kwargs (excluding tag_bindings which are handled separately)
        for key, value in kwargs.items():
            if value is not None and key != "tag_bindings":
                project_options[key] = value

        # Create the project using pytfe SDK
        project = client.safe_api_call(
            client.client.projects.create,
            organization,
            project_options,
            error_context=f"Failed to create project {name} in organization {organization}",
        )

        return {"data": _wrap_response(project)}
    except Exception as e:
        if isinstance(e, TerraformError):
            raise
        raise TerraformError(f"Failed to create project: {str(e)}") from e


def update_project(
    client: TerraformClient,
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tag_bindings: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Update an existing project using the pytfe SDK.

    Args:
        client: TerraformClient instance
        project_id: The project ID to update
        name: Optional new project name
        description: Optional new project description
        tag_bindings: Optional list of tag binding dicts with 'key' and 'value'
        **kwargs: Additional project attributes to update

    Returns:
        Dictionary containing the updated project data wrapped in API format

    Raises:
        TerraformError: If the SDK operation fails
    """
    try:
        # Build the ProjectUpdateOptions payload
        project_options = {}

        if name is not None:
            project_options["name"] = name

        if description is not None:
            project_options["description"] = description

        # Add any additional attributes from kwargs (excluding tag_bindings)
        for key, value in kwargs.items():
            if value is not None and key != "tag_bindings":
                project_options[key] = value

        # Update the project using pytfe SDK
        project = client.safe_api_call(
            client.client.projects.update,
            project_id,
            project_options,
            error_context=f"Failed to update project {project_id}",
        )

        # Handle tag bindings separately after project update
        if tag_bindings:
            try:
                # Delete existing tag bindings and add new ones
                delete_project_tag_bindings(client, project_id)
                add_project_tag_bindings(client, project_id, tag_bindings)
            except Exception as e:
                # Log warning but don't fail - project was updated
                pass

        return {"data": _wrap_response(project)}
    except NotFound:
        raise TerraformError(f"Project {project_id} not found")
    except Exception as e:
        if isinstance(e, TerraformError):
            raise
        raise TerraformError(f"Failed to update project: {str(e)}") from e


def delete_project(client: TerraformClient, project_id: str) -> None:
    """
    Delete a project using the pytfe SDK.

    Args:
        client: TerraformClient instance
        project_id: The project ID to delete

    Returns:
        None

    Raises:
        TerraformError: If the SDK operation fails
    """
    try:
        client.safe_api_call(
            client.client.projects.delete,
            project_id,
            error_context=f"Failed to delete project {project_id}",
        )
    except NotFound:
        raise TerraformError(f"Project {project_id} not found")
    except Exception as e:
        if isinstance(e, TerraformError):
            raise
        raise TerraformError(f"Failed to delete project: {str(e)}") from e


def get_project_tag_bindings(client: TerraformClient, project_id: str) -> Dict[str, Any]:
    """
    Get tag bindings for a project using the pytfe SDK.

    Args:
        client: TerraformClient instance
        project_id: The project ID

    Returns:
        Dictionary with tag bindings data wrapped in API format

    Raises:
        TerraformError: If the SDK operation fails
    """
    try:
        tag_bindings = client.safe_api_call(
            client.client.projects.list_tag_bindings,
            project_id,
            error_context=f"Failed to retrieve tag bindings for project {project_id}",
        )

        # Convert each tag binding Pydantic model to dict
        wrapped_bindings = _wrap_list_response(tag_bindings) if tag_bindings else []
        return {"data": wrapped_bindings}
    except NotFound:
        return {"data": []}
    except Exception as e:
        if isinstance(e, TerraformError):
            raise
        raise TerraformError(f"Failed to get tag bindings: {str(e)}") from e


def add_project_tag_bindings(client: TerraformClient, project_id: str, tag_bindings: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Add/update tag bindings for a project using the pytfe SDK.

    Args:
        client: TerraformClient instance
        project_id: The project ID
        tag_bindings: List of dicts with 'key' and 'value' fields

    Returns:
        Dictionary with added tag bindings wrapped in API format

    Raises:
        TerraformError: If the SDK operation fails
    """
    try:
        # Convert list of dicts to pytfe SDK format
        result = client.safe_api_call(
            client.client.projects.add_tag_bindings,
            project_id,
            tag_bindings,
            error_context=f"Failed to add tag bindings to project {project_id}",
        )

        # Convert response Pydantic models to dicts
        wrapped_bindings = _wrap_list_response(result) if result else []
        return {"data": wrapped_bindings}
    except NotFound:
        raise TerraformError(f"Project {project_id} not found")
    except Exception as e:
        if isinstance(e, TerraformError):
            raise
        raise TerraformError(f"Failed to add tag bindings: {str(e)}") from e


def delete_project_tag_bindings(client: TerraformClient, project_id: str) -> None:
    """
    Delete all tag bindings from a project using the pytfe SDK.

    Args:
        client: TerraformClient instance
        project_id: The project ID

    Returns:
        None

    Raises:
        TerraformError: If the SDK operation fails
    """
    try:
        client.safe_api_call(
            client.client.projects.delete_tag_bindings,
            project_id,
            error_context=f"Failed to delete tag bindings for project {project_id}",
        )
    except NotFound:
        raise TerraformError(f"Project {project_id} not found")
    except Exception as e:
        if isinstance(e, TerraformError):
            raise
        raise TerraformError(f"Failed to delete tag bindings: {str(e)}") from e


def list_projects(
    client: TerraformClient,
    organization: str,
    query_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    List all projects in an organization using the pytfe SDK.

    Args:
        client: TerraformClient instance
        organization: The organization name
        query_params: Optional query parameters for filtering/pagination

    Returns:
        Dictionary with list of projects wrapped in API format

    Raises:
        TerraformError: If the SDK operation fails
    """
    try:
        projects = client.safe_api_call(
            client.client.projects.list,
            organization,
            error_context=f"Failed to list projects in organization {organization}",
        )

        # Convert each project Pydantic model to dict
        wrapped_projects = _wrap_list_response(projects) if projects else []
        return {"data": wrapped_projects}
    except NotFound:
        return {"data": []}
    except Exception as e:
        if isinstance(e, TerraformError):
            raise
        raise TerraformError(f"Failed to list projects: {str(e)}") from e
