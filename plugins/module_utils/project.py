# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

from typing import Any, Dict

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)


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
