from typing import Any, Optional

from ansible.module_utils.common.text.converters import to_text

from .exceptions import TerraformError


def create_project(client, organization: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Create a new project with the given parameters.
    Args:
        client: The Terraform client instance.
        organization (str): The name of the Terraform Cloud organization.
        data (dict): The project data to create.
    Returns:
        The created project in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 201 status code.
    """
    response = client.post(f"/organizations/{organization}/projects", data=data)
    if response.get("status") != 201:
        raise TerraformError(to_text(response))
    return response.get("data")


def get_project_by_id(client: TerraformClient, project_id: str) -> Dict[str, Any]:
    """
    Retrieves a specified project from Terraform Cloud by its ID.

    Sends a GET request to fetch details of a project identified by its unique ID.
    If the project is not found, returns an empty dictionary. If successful,
    returns the project data with an added "status" field. For any other error
    status, raises a TerraformError.

    Args:
        client (TerraformClient): An authenticated client used to interact with
            the Terraform Cloud API.
        project_id (str): The unique ID of the project to retrieve.

    Returns:
        dict: A dictionary containing the project data (with an added "status" field)
        if found, or an empty dictionary if the project is not found (status 404).

    Raises:
        TerraformError: If the request fails with a non-404 status code.
    """
    response = client.get(f"/projects/{project_id}")
    response_data = response.get("data", {})
    response_status = response["status"]

    if response_status == 404:
        # project was not found
        # This should not raise an exception
        return {}
    elif response_status == 200:
        # project was fetched successfully
        response_data.update({"status": response_status})
        return response_data
    else:
        # A failure status code was received when attempting to fetch the specified project
        # there can be several reasons for this so we raise an exception with the response
        raise TerraformError(response)


def update_project(client, project_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Update a project with the given project_id.
    Args:
        client: The Terraform client instance.
        project_id (str): The ID of the project to update.
        data (dict): The project data to update.
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
        client: The Terraform client instance.
        project_id (str): The ID of the project to delete.
    Returns:
        The deleted project in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    response = client.delete(f"/projects/{project_id}")
    if response.get("status") != 204:
        raise TerraformError(to_text(response))
    return response.get("data")


def get_project_tag_bindings(client, project_id: str) -> Optional[dict[str, Any]]:
    """
    Get the tag bindings for a project with the given project_id.
    Args:
        client: The Terraform client instance.
        project_id (str): The ID of the project to get the tag bindings for.
    Returns:
        The tag bindings for the project.
    Raises:
        TerraformError: If the response does not return a 200 status code.
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
        client: The Terraform client instance.
        project_id (str): The ID of the project to update the tag bindings for.
        data (dict): The tag bindings data to update.
    Returns:
        The updated tag bindings for the project.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    response = client.patch(f"/projects/{project_id}/tag-bindings", data=data)
    if response.get("status") != 200:
        raise TerraformError(to_text(response))
    return response.get("data")


def list_projects(client, organization: str, query_params: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    """
    List all projects for an organization.
    Args:
        client: The Terraform client instance.
        organization (str): The name of the organization to list projects for.
    Returns:
        The list of projects.
    """
    response = client.get(f"/organizations/{organization}/projects", query_params=query_params)
    if response.get("status") == 200:
        return response.get("data")
    elif response.get("status") == 404:
        return {}
    else:
        raise TerraformError(to_text(response))