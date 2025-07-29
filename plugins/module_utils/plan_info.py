# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    TerraformClient,
)


def get_plan_metadata(client: TerraformClient, identifier: str, use_plan_id: bool):
    """
    Retrieve plan metadata from Terraform Cloud/Enterprise API.

    Sends a GET request to retrieve the metadata for a specified plan.
    The request can be made using either a plan ID directly or through a run ID.
    If the plan does not exist, returns an empty dictionary without raising an error.
    If the plan is found, returns the full response. For any other non-success
    status, raises an HTTPError with the response.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud/Enterprise API.
        identifier (str): Either the plan ID or run ID depending on use_plan_id flag.
        use_plan_id (bool): True if identifier is plan_id, False if it's run_id.

    Returns:
        dict: The full response data if the plan is found (status 200),
        or an empty dictionary if not found (status 404).

    Raises:
        requests.HTTPError: If the request fails with a non-404 or non-200 status code.
    """
    if use_plan_id:
        path = f"/plans/{identifier}"
    else:
        path = f"/runs/{identifier}/plan"

    response = client.get(path)
    response_status = response["status"]

    if response_status == 404:
        # Plan was not found
        # This should not raise an exception
        return {}
    elif response_status == 200:
        # Plan metadata was fetched successfully
        return response
    else:
        # A failure status code was received when attempting to fetch the specified plan
        # there can be several reasons for this so we raise an exception with the response
        raise requests.HTTPError(response)


def get_plan_json_output(client: TerraformClient, identifier: str, use_plan_id: bool):
    """
    Retrieve plan JSON output from Terraform Cloud/Enterprise API.

    Sends a GET request to retrieve the JSON output for a specified plan.
    The request can be made using either a plan ID directly or through a run ID.
    If the plan JSON output does not exist, returns an empty dictionary without
    raising an error. If the JSON output is found, returns the full response.
    For any other non-success status, raises an HTTPError with the response.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud/Enterprise API.
        identifier (str): Either the plan ID or run ID depending on use_plan_id flag.
        use_plan_id (bool): True if identifier is plan_id, False if it's run_id.

    Returns:
        dict: The full response data if the plan JSON output is found (status 200),
        or an empty dictionary if not found (status 404).

    Raises:
        requests.HTTPError: If the request fails with a non-404 or non-200 status code.
    """
    if use_plan_id:
        path = f"/plans/{identifier}/json-output"
    else:
        path = f"/runs/{identifier}/plan/json-output"

    response = client.get(path)
    response_status = response["status"]

    if response_status == 404:
        # Plan JSON output was not found
        # This should not raise an exception
        return {}
    elif response_status == 200:
        # Plan JSON output was fetched successfully
        return response
    else:
        # A failure status code was received when attempting to fetch the specified plan JSON output
        # there can be several reasons for this so we raise an exception with the response
        raise requests.HTTPError(response)
