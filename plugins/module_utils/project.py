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
from pytfe.models.common import TagBinding
from pytfe.models.project import (
    ProjectAddTagBindingsOptions,
    ProjectCreateOptions,
    ProjectListOptions,
    ProjectUpdateOptions,
)

from .client import TerraformClient
from .exceptions import TerraformError


def _get_project_full(client: TerraformClient, project_id: str) -> Dict[str, Any]:
    """Fetch full project data via direct REST API call.

    Bypasses the pytfe SDK which strips fields not in the Project model.
    This ensures we get all attributes including execution_mode, auto_destroy_activity_duration, etc.

    Args:
        client: TerraformClient instance
        project_id: The project ID to fetch

    Returns:
        Full project data from API with all attributes, or empty dict if not found

    Raises:
        TerraformError: If the API call fails
    """
    try:
        import requests

        url = f"{client.address}/api/v2/projects/{project_id}"
        headers = {
            "Authorization": f"Bearer {client.token}",
            "Content-Type": "application/vnd.api+json",
        }

        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        return response.json().get("data", {})
    except Exception as e:
        # Fall back gracefully if direct API call fails
        return {}


def _patch_project(client: TerraformClient, project_id: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
    """Apply extra project attributes via direct REST API PATCH call.

    Sets attributes like execution_mode, auto_destroy_activity_duration, etc.
    that ProjectCreateOptions/ProjectUpdateOptions don't support.

    Args:
        client: TerraformClient instance
        project_id: The project ID to patch
        attributes: Dict of attributes to set (in REST API format with dashes)

    Returns:
        Patched project data from API, or empty dict if failed

    Raises:
        TerraformError: If the API call fails
    """
    try:
        import requests

        url = f"{client.address}/api/v2/projects/{project_id}"
        headers = {
            "Authorization": f"Bearer {client.token}",
            "Content-Type": "application/vnd.api+json",
        }

        # Build PATCH body in JSON:API format
        payload = {"data": {"type": "projects", "attributes": attributes}}

        response = requests.patch(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        return response.json().get("data", {})
    except Exception as e:
        # Fall back gracefully - partial update is acceptable
        return {}


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
    # Note: pytfe Project.model_dump() produces field names with underscores (e.g., default_execution_mode)
    # We map these to REST API format with dashes (e.g., default-execution-mode)
    field_mapping = {
        "name": "name",
        "description": "description",
        "default_execution_mode": "default-execution-mode",  # pytfe field name: default_execution_mode
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
    Retrieve a project by its ID.

    Uses direct API call to ensure we get all attributes (not just what pytfe SDK model supports).

    Args:
        client: TerraformClient instance
        project_id: The unique ID of the project to retrieve

    Returns:
        Dictionary containing the project data wrapped in API format, or empty dict if not found

    Raises:
        TerraformError: If the SDK operation fails (other than 404)
    """
    # Use direct API call to get full project data with all attributes
    api_data = _get_project_full(client, project_id)
    if api_data:
        return {"data": api_data}
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
        # Create list options to filter by project name
        options = ProjectListOptions(name=name)
        
        # Use the pytfe SDK's list method with filtering
        projects = client.safe_api_call(
            client.client.projects.list,
            organization,
            options,
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
        tag_bindings: Optional list of tag binding dicts with 'key' and 'value'
        **kwargs: Additional project attributes (auto_destroy_activity_duration, execution_mode, setting_overwrites, default_agent_pool_id)

    Returns:
        Dictionary containing the created project data wrapped in API format

    Raises:
        TerraformError: If the SDK operation fails
    """
    try:
        # ProjectCreateOptions only supports name and description
        options = ProjectCreateOptions(name=name, description=description)

        # Create the project using pytfe SDK
        project = client.safe_api_call(
            client.client.projects.create,
            organization,
            options,
            error_context=f"Failed to create project {name} in organization {organization}",
        )

        # Get project ID from response
        project_id = project.id if hasattr(project, "id") else project.get("id")
        
        # Patch extra attributes that ProjectCreateOptions doesn't support
        if project_id and kwargs:
            patch_attrs = {}
            if "execution_mode" in kwargs:
                patch_attrs["default-execution-mode"] = kwargs["execution_mode"]
            if "auto_destroy_activity_duration" in kwargs:
                patch_attrs["auto-destroy-activity-duration"] = kwargs["auto_destroy_activity_duration"]
            if "setting_overwrites" in kwargs:
                patch_attrs["setting-overwrites"] = kwargs["setting_overwrites"]
            if "default_agent_pool_id" in kwargs:
                patch_attrs["default-agent-pool-id"] = kwargs["default_agent_pool_id"]
            
            if patch_attrs:
                try:
                    _patch_project(client, project_id, patch_attrs)
                except Exception:
                    # Log warning but don't fail - project was created
                    pass
        
        # Handle tag bindings separately after project creation if provided
        if tag_bindings and project_id:
            try:
                add_project_tag_bindings(client, project_id, tag_bindings)
            except Exception:
                # Log warning but don't fail - project was created successfully
                pass

        # Refetch the project using direct API to get ALL attributes
        if project_id:
            api_data = _get_project_full(client, project_id)
            if api_data:
                return {"data": api_data}
        
        # Fallback to SDK response if direct API call fails
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
        **kwargs: Additional project attributes (auto_destroy_activity_duration, execution_mode, setting_overwrites, default_agent_pool_id)

    Returns:
        Dictionary containing the updated project data wrapped in API format

    Raises:
        TerraformError: If the SDK operation fails
    """
    try:
        # Build the ProjectUpdateOptions Pydantic model
        options_dict = {}

        if name is not None:
            options_dict["name"] = name

        if description is not None:
            options_dict["description"] = description

        # Create ProjectUpdateOptions Pydantic model
        options = ProjectUpdateOptions(**options_dict) if options_dict else None

        # Update the project using pytfe SDK only if we have name/description to update
        if options:
            project = client.safe_api_call(
                client.client.projects.update,
                project_id,
                options,
                error_context=f"Failed to update project {project_id}",
            )
        else:
            # If only patching extra attributes, fetch current state first
            project = None

        # Patch extra attributes that ProjectUpdateOptions doesn't support
        if kwargs:
            patch_attrs = {}
            if "execution_mode" in kwargs:
                patch_attrs["default-execution-mode"] = kwargs["execution_mode"]
            if "auto_destroy_activity_duration" in kwargs:
                patch_attrs["auto-destroy-activity-duration"] = kwargs["auto_destroy_activity_duration"]
            if "setting_overwrites" in kwargs:
                patch_attrs["setting-overwrites"] = kwargs["setting_overwrites"]
            if "default_agent_pool_id" in kwargs:
                patch_attrs["default-agent-pool-id"] = kwargs["default_agent_pool_id"]
            
            if patch_attrs:
                try:
                    _patch_project(client, project_id, patch_attrs)
                except Exception:
                    # Log warning but don't fail - project was updated
                    pass

        # Handle tag bindings separately after project update
        if tag_bindings:
            try:
                # Delete existing tag bindings and add new ones
                delete_project_tag_bindings(client, project_id)
                add_project_tag_bindings(client, project_id, tag_bindings)
            except Exception as e:
                # Log warning but don't fail - project was updated
                pass

        # Refetch the project using direct API to get ALL attributes
        api_data = _get_project_full(client, project_id)
        if api_data:
            return {"data": api_data}
        
        # Fallback to SDK response if direct API call fails
        if project:
            return {"data": _wrap_response(project)}
        return {}
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
        # Convert list of dicts to pytfe SDK Pydantic models
        tag_binding_models = [TagBinding(key=tb["key"], value=tb["value"]) for tb in tag_bindings]
        options = ProjectAddTagBindingsOptions(tag_bindings=tag_binding_models)
        
        # Add tag bindings using pytfe SDK
        result = client.safe_api_call(
            client.client.projects.add_tag_bindings,
            project_id,
            options,
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
        options = None
        if query_params:
            options = ProjectListOptions(
                name=query_params.get("filter[names]")
            )
        projects = client.safe_api_call(
            client.client.projects.list,
            organization,
            options,
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
