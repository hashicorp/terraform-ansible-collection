from typing import Any, Optional, Union

from ansible.module_utils.common.text.converters import to_text

from .exceptions import TerraformError

def create_project(client, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Create a new project with the given parameters.
    Args:
        **kwargs: Keyword arguments to create a new project.
    Returns:
        The created project in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 201 status code.
    """
    response = client.post("/projects", data=data)
    if response.get("status") != 201:
        raise TerraformError(to_text(response))
    return response.get("data")


def get_project(client, project_id: str) -> Optional[dict[str, Any]]:
    """
    Get a project with the given project_id.
    Args:
        project_id(str): The ID of the project to get.
    Returns:
        The project.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    response = client.get(f"/projects/{project_id}")
    if response.get("status") == 200:
        return response.get("data")
    elif response.get("status") == 404:
        return {}
    else:
        raise TerraformError(to_text(response))


def update_project(client, project_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Update a project with the given project_id.
    Args:
        project_id(str): The ID of the project to update.
        **kwargs: Keyword arguments to update the project.
    Returns:
        The updated project in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    response = client.patch(f"/projects/{project_id}", data=data)
    if response.get("status") != 200:
        raise TerraformError(to_text(response))
    return response.get("data")

def delete_project(client, project_id: str) -> Optional[dict[str, Any]]:
    """
    Delete a project with the given project_id.
    Args:
        project_id(str): The ID of the project to delete.
    Returns:
        The deleted project in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    response = client.delete(f"/projects/{project_id}")
    if response.get("status") != 200:
        raise TerraformError(to_text(response))
    return response.get("data")

def get_project_tag_bindings(client, project_id: str) -> Optional[dict[str, Any]]:
    """
    Get the tag bindings for a project with the given project_id.
    Args:
        project_id(str): The ID of the project to get the tag bindings for.
    Returns:
        The tag bindings for the project.
    """
    response = client.get(f"/projects/{project_id}/tag-bindings")
    if response.get("status") == 200:
        return response.get("data")
    elif response.get("status") == 404:
        return {}
    else:
        raise TerraformError(to_text(response))

def update_project_tag_bindings(client, project_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Update the tag bindings for a project with the given project_id.
    Args:
        project_id(str): The ID of the project to update the tag bindings for.
        **kwargs: Keyword arguments to update the tag bindings.
    Returns:
        The updated tag bindings for the project.
    """
    response = client.patch(f"/projects/{project_id}/tag-bindings", data=data)
    if response.get("status") != 200:
        raise TerraformError(to_text(response))
    return response.get("data")
