# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


from ansible_collections.hashicorp.terraform.plugins.module_utils.common import TerraformClient


def get_workspace(client: TerraformClient, organization: str, workspace_name: str):
    """
    Retrieves a specified workspace from Terraform Cloud.

    Sends a GET request to fetch details of a workspace identified by its name
    within a given organization. If the workspace is not found, returns an empty
    dictionary. If successful, returns the workspace data with an added "status" field.
    For any other error status, raises an HTTPError.

    Args:
        client (TerraformClient): An authenticated client used to interact with
            the Terraform Cloud API.
        organization (str): The name of the Terraform Cloud organization.
        workspace_name (str): The name of the workspace to retrieve.

    Returns:
        dict: A dictionary containing the workspace data (with an added "status" field)
        if found, or an empty dictionary if the workspace is not found (status 404).

    Raises:
        requests.HTTPError: If the request fails with a non-404 status code.
    """
    response = client.get(f"/organizations/{organization}/workspaces/{workspace_name}")
    response_data = response.get("data", {})
    response_status = response["status"]

    if response_status == 404:
        # workspace was not found
        # This should not raise an exception
        return {}
    elif response_status == 200:
        # workspace was fetched successfully
        response_data.update({"status": response_status})
        return response_data
    else:
        # A failure status code was received when attempting to fetch the specified configuration version
        # there can be several reasons for this so we raise an exception with the response
        raise requests.HTTPError(response)
