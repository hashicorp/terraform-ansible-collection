# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

try:
    from pytfe.errors import NotFound
    from pytfe.models import ConfigurationVersionCreateOptions
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class ConfigurationVersionCreateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def create_config(adapter: TerraformClient, workspace_id: str, attributes: dict):
    """
    Creates a new configuration version for a specified Terraform Cloud workspace.

    Sends a POST request to the Terraform Cloud API to create a configuration version
    associated with the given workspace. If the operation is successful, returns the
    configuration version data with the response status code included.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud API.
        workspace_id (str): The ID of the workspace to associate with the new
            configuration version.
        attributes (dict): A dictionary of attributes to include in the configuration
            version payload (e.g., auto-queue, speculative, etc.).

    Returns:
        dict: The response data from Terraform Cloud, including the created
        configuration version details and a `status` field with HTTP status code.

    Raises:
        TerraformError: If the request fails (i.e., non-201 status code is returned).
    """
    create_options = ConfigurationVersionCreateOptions(**attributes)
    config_version = safe_api_call(
        adapter.client.configuration_versions.create,
        workspace_id,
        create_options,
        error_context=f"Failed to create configuration version for workspace {workspace_id}",
    )
    return format_response(config_version)


def archive_config(adapter: TerraformClient, config_version_id: str):
    """
    Archives a specified configuration version in Terraform Cloud.

    Sends a POST request to initiate the archive action for a given configuration
    version. If the configuration version does not exist or the user lacks
    authorization, returns an empty dictionary. If the archive action is
    successfully initiated, returns the response data. Raises an HTTPError if the
    request fails for any reason other than a 404 Not Found.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud API.
        config_version_id (str): The ID of the configuration version to archive.

    Returns:
        dict: Response data if the archive request is successfully initiated,
        or an empty dictionary if the configuration version is not found or access
        is denied.

    Raises:
        TerraformError: If the archive request fails with a non-404 or non-202 status code.
    """
    try:
        safe_api_call(
            adapter.client.configuration_versions.archive,
            config_version_id,
            error_context=f"Failed to archive configuration version {config_version_id}",
        )
        return {"status": 202}
    except NotFound:
        # Configuration version was not found
        # This should not raise an exception
        return {}


def upload_config(adapter: TerraformClient, upload_url: str, configuration_files_path: str):
    """
    Uploads a Terraform configuration `.tar.gz` archive to the specified upload URL.

    Opens the given file in binary mode and performs a PUT request to upload it.
    If the `upload_url` is a fully-qualified URL and contains `/object`, the function
    uploads directly to it. Otherwise, it assumes a relative path and prefixes it with `/object/`.

    Args:
        client (ArchivistClient): An API client capable of issuing PUT requests.
        upload_url (str): The upload destination URL (absolute or relative).
        configuration_files_path (str): Path to the `.tar.gz` archive to upload.

    Raises:
        TerraformError: If the upload fails (non-200 HTTP status code).
    """
    with open(configuration_files_path, "rb") as archive:
        safe_api_call(
            adapter.client.configuration_versions.upload_tar_gzip,
            upload_url,
            archive,
            error_context=f"Failed to upload configuration archive to {upload_url}",
        )


def get_config(adapter: TerraformClient, config_version_id: str):
    """
    Retrieves a specified configuration version from Terraform Cloud.

    Sends a GET request for the given configuration version. If the configuration
    version does not exist, returns an empty dictionary without raising an error.
    If the configuration is found, returns the full response. For any other
    non-success status, raises an HTTPError with the response.

    Args:
        adapter (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud API.
        config_version_id (str): The ID of the configuration version to retrieve.

    Returns:
        dict: The full response data if the configuration version is found (status 200),
        or an empty dictionary if not found (status 404).

    Raises:
        TerraformError: If the request fails with a non-404 or non-200 status code.
    """
    try:
        config_version = adapter.client.configuration_versions.read(config_version_id)
        return format_response(config_version)
    except NotFound:
        # Configuration version was not found
        # This should not raise an exception
        return {}
