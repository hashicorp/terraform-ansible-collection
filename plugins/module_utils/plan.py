# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.run import (
    get_run,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import (
    format_response,
)


def get_plan_data(
    adapter: TerraformClient,
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
        adapter: An authenticated client instance used to interact
            with the Terraform Cloud/Enterprise API.
        identifier: Either the plan ID or run ID depending on use_plan_id flag.
        use_plan_id: True if identifier is plan_id, False if it's run_id.
        include_json_output: If True, retrieves JSON output; if False, retrieves
            plan metadata. Defaults to False.

    Returns:
        The full response data.

    Examples:
        # Get plan metadata
        metadata = get_plan_data(client, "plan-123", True)

        # Get plan JSON output
        json_output = get_plan_data(client, "run-456", False, include_json_output=True)
    """
    if not use_plan_id:
        run_response = get_run(adapter, identifier)
        if run_response:
            plan = run_response.get("plan")
            if plan and plan.get("id"):
                identifier = plan["id"]
            else:
                raise TerraformError(f"Run with ID {identifier} does not have an associated plan, cannot retrieve plan data.")
        else:
            raise TerraformError(f"Run with ID {identifier} not found, cannot retrieve plan data.")

    try:
        if include_json_output:
            response = adapter.client.plans.read_json_output(identifier)
        else:
            response = adapter.client.plans.read(identifier)
    except NotFound:
        return {}

    if isinstance(response, dict):
        return response

    return format_response(response)
