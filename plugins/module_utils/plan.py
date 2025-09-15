# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)


def _handle_api_response(response: dict) -> dict:
    """
    Handle common API response patterns for Terraform Cloud/Enterprise requests.
    Args:
        response: The response dictionary from the API call
    Returns:
        dict: The response if successful, empty dict if not found
    Raises:
        TerraformError: If the request fails with a non-404 or non-200 status code
    """
    response_status = response.get("status")

    if response_status == 404:
        # Resource was not found - return empty dict without raising exception
        return {}
    elif response_status == 200:
        # Request was successful
        return response
    else:
        # A failure status code was received - raise exception with response
        raise TerraformError(response)


def get_plan_data(
    client: TerraformClient,
    identifier: str,
    use_plan_id: bool,
    include_json_output: bool = False,
) -> dict:
    """
    Retrieve plan data from Terraform Cloud/Enterprise API.

    Sends a GET request to retrieve either plan metadata or JSON output for a
    specified plan. The request can be made using either a plan ID directly or
    through a run ID. If the plan does not exist, returns an empty dictionary
    without raising an error. If the plan is found, returns the full response.
    For any other non-success status, raises a TerraformError with the response.

    Args:
        client: An authenticated client instance used to interact
            with the Terraform Cloud/Enterprise API.
        identifier: Either the plan ID or run ID depending on use_plan_id flag.
        use_plan_id: True if identifier is plan_id, False if it's run_id.
        include_json_output: If True, retrieves JSON output; if False, retrieves
            plan metadata. Defaults to False.

    Returns:
        The full response data if the plan is found (status 200),
        or an empty dictionary if not found (status 404).

    Raises:
        TerraformError: If the request fails with a non-404 or non-200 status code.

    Examples:
        # Get plan metadata
        metadata = get_plan_data(client, "plan-123", True)

        # Get plan JSON output
        json_output = get_plan_data(client, "run-456", False, include_json_output=True)
    """
    endpoint_suffix = "/json-output" if include_json_output else ""

    if use_plan_id:
        path = f"/plans/{identifier}{endpoint_suffix}"
    else:
        path = f"/runs/{identifier}/plan{endpoint_suffix}"

    response = client.get(path)
    return _handle_api_response(response)
