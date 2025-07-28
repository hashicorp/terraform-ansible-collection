# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import re


try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    ArchivistClient,
    TerraformClient,
)


def create_config(client: TerraformClient, workspace_id: str, attributes: dict):
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
        requests.HTTPError: If the request fails (i.e., non-201 status code is returned).
    """
    payload = {
        "data": {
            "type": "configuration-versions",
            "attributes": attributes,
        },
    }
    response = client.post(f"/workspaces/{workspace_id}/configuration-versions", data=payload)
    response_data = response.get("data", {})
    response_status = response["status"]
    if response_status == 201:
        # configuration version was created successfully
        response_data.update({"status": response_status})
        return response_data
    else:
        # A non-201 status code was received when attempting to create specified configuration version
        # there can be several reasons for this so we raise an exception with the response
        raise requests.HTTPError(response)


def archive_config(client: TerraformClient, config_version_id: str):
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
        requests.HTTPError: If the archive request fails with a non-404 or non-202 status code.
    """
    response = client.post(f"/configuration-versions/{config_version_id}/actions/archive")
    response_status = response["status"]

    if response["status"] == 404:
        # Configuration version was not found
        # This should not raise an exception
        return {}
    elif response["status"] == 202:
        # Archive process initiated successfully
        # returns the response payload
        return {"status": response_status}
    else:
        # Archive process was not initiated successfully
        # there can be several reasons for this so we raise an exception with the response
        raise requests.HTTPError(response)


def upload_config(client: ArchivistClient, upload_url: str, configuration_files_path: str):
    """
    Uploads a Terraform configuration `.tar.gz` archive to the specified upload URL.

    Opens the given file in binary mode and performs a PUT request to upload it.
    If the `upload_url` is a fully-qualified URL and contains `/object`, the function
    uploads directly to it. Otherwise, it assumes a relative path and prefixes it with `/object/`.

    Args:
        client (ArchivistClient): An API client capable of issuing PUT requests.
        upload_url (str): The upload destination URL (absolute or relative).
        configuration_files_path (str): Path to the `.tar.gz` archive to upload.

    Returns:
        dict: The HTTP response returned from the PUT request.

    Raises:
        requests.HTTPError: If the upload fails (non-200 HTTP status code).
    """
    response = {}
    with open(configuration_files_path, "rb") as f:
        if re.match(r"^https?://", client.base_url) and "/object" in upload_url:
            response = client.put(f"{upload_url}", f)
        else:
            response = client.put(f"/object/{upload_url}", f)

    if response["status"] != 200:
        raise requests.HTTPError(response)
    return response


def get_config(client: TerraformClient, config_version_id: str):
    """
    Retrieves a specified configuration version from Terraform Cloud.

    Sends a GET request for the given configuration version. If the configuration
    version does not exist, returns an empty dictionary without raising an error.
    If the configuration is found, returns the full response. For any other
    non-success status, raises an HTTPError with the response.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud API.
        config_version_id (str): The ID of the configuration version to retrieve.

    Returns:
        dict: The full response data if the configuration version is found (status 200),
        or an empty dictionary if not found (status 404).

    Raises:
        requests.HTTPError: If the request fails with a non-404 or non-200 status code.
    """
    response = client.get(f"/configuration-versions/{config_version_id}")
    response_data = response.get("data", {})
    response_status = response["status"]

    if response_status == 404:
        # Configuration version was not found
        # This should not raise an exception
        return {}
    elif response_status == 200:
        # configuration version was fetched successfully
        response_data.update({"status": response_status})
        return response_data
    else:
        # A failure status code was received when attempting to fetch the specified configuration version
        # there can be several reasons for this so we raise an exception with the response
        raise requests.HTTPError(response)
