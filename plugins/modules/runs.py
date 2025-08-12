#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: runs
version_added: "1.0.0"
short_description: This module supports Create, for Terraform Cloud/Enterprise runs.
author: "Siddarth Sharma (@siddasha)"
description:
  - The module supports run operations such as creating, applying, cancelling and discarding.
  - It allows the user to manage Terraform runs by specifying the workspace, plan, and other parameters.
  - It can also be used to trigger a plan or apply operation on a specified workspace.
  - The module provides options to manage run attributes such as message, variables, and auto-apply settings.
  - Supports both Terraform Cloud and Terraform Enterprise environments.
  - The present state supports planned, planned and saved, planned and finished and applied states;
    defaults to planned state
  - The applied state corresponds to applying a run with it's run_id
  - The discarded state corresponds to discarding a run without applying it
  - The cancelled state corresponds to cancelling a run which is in progress
options:
    workspace_id:
        description: The ID of the workspace where the run will be created or managed.
        type: str
        required: false
    workspace:
        description: The desired workspace name where the run is to be created
        type: str
        required: false
    organization:
        description: The desired organization to which the workspace belongs to
        type: str
        required: false
    configuration_version:
        description: The configuration version for the run present in the workspace, defaults to the latest version in the workspace if not specified.
        type: str
        required: false
    message:
        description: A message to attach to the run.
        type: str
        required: false
    auto_apply:
        description: Whether to automatically apply the run after planning.
        type: bool
        required: false
    save_plan:
        description: Wheather to run plans and check the configuration without becoming the worspace's current run
        type: bool
        required: false
    variables:
        description: A list of dictionary of variables to pass to the run.
        type: list
        elements: dict
        required: false
    plan_only:
        description: Whether to only create a plan without applying it.
        type: bool
        required: false
    run_id:
        description: The ID of the run to apply/cancel.
        type: str
        required: false
    is_destroy:
        description: Wheather to destroy all the provisoned resources.
        type: bool
        required: false
    target_addrs:
        description: A list of target addresses to apply the run to.
        type: list
        elements: str
        required: false
    state:
        description: The state of the run to manage.
        type: str
        choices: ['present', 'applied', 'discarded', 'canceled']
        default: 'present'
        required: false
    poll:
        description: Whether to poll the run status.
        type: bool
        default: true
        required: false
    poll_interval:
        description:
            - Configures the interval (in seconds) to wait between retries of inspecting the `run` status.
            - This works in conjunction with the I(poll_timeout) parameter.
        type: int
        default: 5
    poll_timeout:
        description:
            - Configures the timeout (in seconds) for polling while inspecting the `run` status.
            - This works in conjunction with the I(poll_interval) parameter.
            - This would factor in the time in case of errors leading to exponential backoff.
        type: int
        default: 25
"""

EXAMPLES = r"""
    - name: Create a new Terraform run
      hashicorp.terraform.run:
        workspace: "ws-12345678"
        message: "Creating a new run"
        auto_apply: true
        variables:
          var1: "value1"
          var2: "value2"
        state: "present"

    - name: Apply a Terraform run
      hashicorp.terraform.run:
        run_id: "run-12345678"
        state: "applied"

    - name: Cancel a Terraform run
      hashicorp.terraform.run:
        run_id: "run-12345678"
        state: "canceled"

    - name: Discard a Terraform run
      hashicorp.terraform.run:
        run_id: "run-12345678"
        state: "discarded"
"""
# todo: add task output to the examples above
import time

from typing import Any, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.runs import RunRequest, RunStates
from ansible_collections.hashicorp.terraform.plugins.module_utils.runs import apply_run, cancel_run, create_run, discard_run, get_run
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace


def wait_for_state(
    client: TerraformClient, run_id: str, expected_key: str, timeout: int = 50, polling_interval: int = 5
) -> tuple[str, Optional[dict[str, Any]]]:
    """
    Wait for a run to reach a specific state.
    Args:
        run_id: The ID of the run to wait for.
        expected_state: The expected state of the run.
        expected_key: The expected key of the run.
        timeout: The timeout for the wait.
        polling_interval: The polling interval.
    Returns:
        The run.
    Raises:
        TerraformError: If the run does not reach the expected state within the timeout.
    """
    start_time = time.time()
    run = None
    while time.time() - start_time <= timeout:
        run = get_run(client, run_id)
        state = run.get("data").get("attributes").get("status")
        if run and RunStates.is_success_state(state):
            return "success", run
        elif run and RunStates.is_failure_state(state):
            return "failure", run
        time.sleep(polling_interval)
    return "timeout", run


def handle_polling_and_result(client: TerraformClient, response: dict, poll: bool, run_id: Optional[str] = None) -> dict[str, Any]:
    """
    Handle polling and return appropriate action result.
    Args:
        client: TerraformClient instance
        response: The API response
        poll: Whether to poll for status
        run_id: Run ID to poll (defaults to response data id)
    Returns:
        Action result dictionary
    """
    action_result = {}
    target_run_id = run_id or response.get("data", {}).get("id")
    if poll and target_run_id:
        status, poll_response = wait_for_state(client, target_run_id, "status")
        if status == "success" and poll_response:
            action_result.update({"changed": True, **poll_response.get("data", {})})
        else:
            action_result.update({"failed": True, "msg": f"Run reached status '{status}' instead of expected success state"})
    else:
        action_result.update({"changed": True, **response.get("data", {})})

    return action_result


def idempotency_check(func):
    def wrapper(*args, **kwargs):
        run_id = kwargs.get("run_id")
        if run_id:
            run = get_run(args[0], run_id)
            if run.get("data").get("attributes").get("status") == func.__name__.split("_")[1]:
                return {"changed": False, "run": run.get("data")}
        return func(*args, **kwargs)

    return wrapper


def state_present(client: TerraformClient, **kwargs: Any) -> Optional[dict[str, Any]]:
    """
    Create a new run with the given parameters.
    Args:
        **kwargs: Keyword arguments to create a new run.
    Returns:
        The created run in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 201 status code.
    """
    ignore_list = ["tf_hostname", "tf_token", "tf_timeout", "tf_max_retries", "tf_validate_certs", "check_mode", "state", "organization", "workspace"]
    run_params = kwargs.copy()
    for value in ignore_list:
        run_params.pop(value, None)

    workspace_id = run_params.pop("workspace_id")
    configuration_version_id = run_params.pop("configuration_version", None)

    if configuration_version_id:
        run_request = RunRequest.create(workspace_id=workspace_id, configuration_version_id=configuration_version_id, **run_params)
    else:
        run_request = RunRequest.create(workspace_id=workspace_id, **run_params)

    run_payload = run_request.model_dump(by_alias=True, exclude_unset=False, exclude_none=True)
    response = create_run(client, run_payload)
    return handle_polling_and_result(client, response, kwargs.get("poll", True))


@idempotency_check
def state_applied(client: TerraformClient, **kwargs: Any) -> Optional[dict[str, Any]]:
    """
    Apply a run with the given parameters.
    Args:
        **kwargs: Keyword arguments to apply a run.
    Returns:
        The applied run in the form of a dictionary.
    """
    run_id = kwargs.get("run_id")
    response = apply_run(client, run_id)
    return handle_polling_and_result(client, response, kwargs.get("poll", True), run_id)


@idempotency_check
def state_discarded(client: TerraformClient, **kwargs: Any) -> Optional[dict[str, Any]]:
    """
    Discard a run with the given parameters.
    Args:
        **kwargs: Keyword arguments to discard a run.
    Returns:
        The discarded run in the form of a dictionary.
    """
    run_id = kwargs.get("run_id")
    response = discard_run(client, run_id)
    return handle_polling_and_result(client, response, kwargs.get("poll", True), run_id)


@idempotency_check
def state_canceled(client: TerraformClient, **kwargs: Any) -> Optional[dict[str, Any]]:
    """
    Cancel a run with the given parameters.
    Args:
        **kwargs: Keyword arguments to cancel a run.
    Returns:
        The cancelled run in the form of a dictionary.
    """
    run_id = kwargs.get("run_id")
    response = cancel_run(client, run_id)
    return handle_polling_and_result(client, response, kwargs.get("poll", False), run_id)


def get_workspace_id(client: TerraformClient, workspace: str, organization: str) -> str:
    """
    Get the workspace ID for the given workspace and organization.
    Args:
        workspace: The name of the workspace.
        organization: The name of the organization.
    Returns:
        workspace_id: The ID of the workspace.
    """
    response = get_workspace(client, organization, workspace)
    if not response:
        raise TerraformError(f"The Workspace {workspace} was not found in the organization {organization}")
    return response.get("data").get("id")


def main():
    module = AnsibleTerraformModule(
        argument_spec=dict(
            workspace_id=dict(type="str"),
            workspace=dict(type="str"),
            organization=dict(type="str"),
            poll=dict(type="bool", default=True),
            poll_interval=dict(type="int", default=5),
            poll_timeout=dict(type="int", default=25),
            configuration_version=dict(type="str"),
            message=dict(type="str"),
            auto_apply=dict(type="bool"),
            save_plan=dict(type="bool"),
            variables=dict(type="list"),
            plan_only=dict(type="bool"),
            is_destroy=dict(type="bool"),
            target_addrs=dict(type="list"),
            state=dict(type="str", choices=["present", "applied", "discarded", "canceled"], default="present"),
            run_id=dict(type="str"),
        ),
        required_together=[["workspace", "organization"]],
        required_if=[
            ("state", "present", ("workspace_id", "workspace"), True),
            ("state", "applied", ("run_id", "workspace_id", "workspace"), True),
            ("state", "discarded", ("run_id", "workspace_id", "workspace"), True),
            ("state", "canceled", ("run_id", "workspace_id", "workspace"), True),
        ],
        mutually_exclusive=[
            ("workspace", "workspace_id"),
            ("plan_only", "save_plan"),
            ("plan_only", "auto_apply"),
            ("save_plan", "auto_apply"),
        ],
    )
    warnings = []
    result = {"changed": False, "warnings": warnings}
    action_result = {}
    params = module.params
    params["check_mode"] = module.check_mode

    try:
        tf_client = TerraformClient(**module.params)
        if not params.get("workspace_id"):
            params["workspace_id"] = get_workspace_id(tf_client, params["organization"], params["workspace"])

        if module.check_mode:
            action_result = {"changed": True, "msg": "Check mode is enabled, no changes will be made"}
            module.exit_json(**action_result)
        else:
            match params.get("state"):
                case "present":
                    action_result = state_present(tf_client, **params)
                case "applied":
                    action_result = state_applied(tf_client, **params)
                case "discarded":
                    action_result = state_discarded(tf_client, **params)
                case "canceled":
                    action_result = state_canceled(tf_client, **params)
                case _:
                    raise TerraformError(f"Invalid state: {params.get('state')}")

            result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_from_exception(e)


if __name__ == "__main__":
    main()
