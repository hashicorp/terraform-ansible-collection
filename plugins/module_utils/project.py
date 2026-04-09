from typing import Any, Dict, Optional

from pytfe.errors import NotFound
from pytfe.models import ProjectAddTagBindingsOptions, ProjectCreateOptions, ProjectListOptions, ProjectUpdateOptions, TagBinding

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def create_project(adapter: TerraformClient, organization: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Create a new project with the given parameters.
    Args:
        adapter: The Terraform client instance.
        organization (str): The name of the Terraform Cloud organization.
        data (dict): The project data to create.
    Returns:
        The created project in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 201 status code.
    """

    if data.get("tag_bindings") is not None:
        data["tag_bindings"] = [TagBinding.model_validate(tag) for tag in data["tag_bindings"]]
    if "setting_overwrites" in data:
        data["setting_overwrites"] = data["setting_overwrites"]
    options = ProjectCreateOptions.model_validate(data)
    project_response = safe_api_call(adapter.client.projects.create, organization, options)
    return format_response(project_response)


def get_project_by_id(adapter: TerraformClient, project_id: str) -> Dict[str, Any]:
    """
    Retrieves a specified project from Terraform Cloud by its ID.

    Sends a GET request to fetch details of a project identified by its unique ID.
    If the project is not found, returns an empty dictionary. If successful,
    returns the project data.

    Args:
        adapter (TerraformClient): An authenticated client used to interact with
            the Terraform Cloud API.
        project_id (str): The unique ID of the project to retrieve.

    Returns:
        dict: A dictionary containing the project data if found, or an empty dictionary if the project is not found (status 404).
    """
    try:
        project = adapter.client.projects.read(project_id)
        data = format_response(project)
        
        return data
    except NotFound:

        return {}


def update_project(adapter: TerraformClient, project_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Update a project with the given project_id.
    Args:
        adapter: The Terraform client instance.
        project_id (str): The ID of the project to update.
        data (dict): The project data to update.
    Returns:
        The updated project in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """

    if data.get("tag_bindings") is not None:
        data["tag_bindings"] = [TagBinding.model_validate(tag) for tag in data["tag_bindings"]]
    if "setting_overwrites" in data:
        data["setting_overwrites"] = data["setting_overwrites"]
    options = ProjectUpdateOptions.model_validate(data)
    project_response = safe_api_call(adapter.client.projects.update, project_id, options)
    return format_response(project_response)


def delete_project(adapter: TerraformClient, project_id: str) -> None:
    """
    Delete a project with the given project_id.
    Args:
        adapter: The Terraform client instance.
        project_id (str): The ID of the project to delete.
    Returns:
        None
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    safe_api_call(adapter.client.projects.delete, project_id, error_context=f"Failed to delete project with ID {project_id}")


def get_project_tag_bindings(adapter: TerraformClient, project_id: str) -> Optional[dict[str, Any]]:
    """
    Get the tag bindings for a project with the given project_id.
    Args:
        adapter: The Terraform client instance.
        project_id (str): The ID of the project to get the tag bindings for.
    Returns:
        The tag bindings for the project.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    try:
        response = adapter.client.projects.list_tag_bindings(project_id)
        if isinstance(response, list):
            return [format_response(tag_binding) for tag_binding in response]
        return format_response(response)
    except NotFound:
        return {}


def update_project_tag_bindings(adapter: TerraformClient, project_id: str, options: ProjectAddTagBindingsOptions) -> Optional[dict[str, Any]]:
    """
    Update the tag bindings for a project with the given project_id.
    Args:
        adapter: The Terraform client instance.
        project_id (str): The ID of the project to update the tag bindings for.
        options (ProjectAddTagBindingsOptions): The tag bindings options to update.
    Returns:
        The updated tag bindings for the project.
    """
    tag_bindings = adapter.client.projects.add_tag_bindings(project_id, options)
    return [format_response(tag_binding) for tag_binding in tag_bindings]


def list_projects(adapter: TerraformClient, organization: str, options: Optional[ProjectListOptions] = None) -> Optional[dict[str, Any]]:
    """
    List all projects for an organization.
    Args:
        adapter: The Terraform client instance.
        organization (str): The name of the organization to list projects for.
    Returns:
        The list of projects.
    """
    try:
        return adapter.client.projects.list(organization, options=options)
    except NotFound:
        # No projects found for the organization
        return {}


def get_project_by_name(adapter: TerraformClient, organization: str, name: str) -> Dict[str, Any]:
    """
    Get a project by name.
    Args:
        adapter: TerraformClient instance
        organization: The name of the organization
        name: The name of the project
    Returns:
        The project in the form of a dictionary, or empty dict if not found.
    """
    options = ProjectListOptions(name=name)
    response = list(list_projects(adapter, organization, options))
    if not response:
        return {}

    project = response[0]
    if isinstance(project, dict):
        return project
    return format_response(project)
