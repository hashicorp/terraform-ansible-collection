#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: run
version_added: "1.0.0"
short_description: Manage Terraform Cloud/Enterprise runs (create, apply, cancel, discard).
author: "Siddarth Sharma (@siddasha)"
description:
  - Manages Terraform Cloud and Terraform Enterprise runs with support for creating, applying, canceling, and discarding operations.
  - Allows users to manage Terraform runs by specifying workspace, plan configuration, and other run parameters.
  - Can trigger plan or apply operations on specified workspaces with customizable settings.
  - Provides comprehensive options for managing run attributes including messages, variables, and auto-apply settings.
  - Compatible with both Terraform Cloud and Terraform Enterprise environments.
  - The I(present) state creates a new run with the specified parameters.
  - The I(applied) state applies an existing run using its run ID.
  - The I(discarded) state discards a run without applying it.
  - The I(canceled) state cancels a run that is currently in progress.
extends_documentation_fragment: hashicorp.terraform.common
options:
    workspace_id:
        description: The unique identifier of the workspace where the run will be created or managed.
        type: str
        required: false
    workspace:
        description: The name of the workspace where the run will be created.
        type: str
        required: false
    organization:
        description: The name of the organization that owns the workspace.
        type: str
        required: false
    configuration_version:
        description:
          - The configuration version ID to use for the run.
          - If not specified, defaults to the latest configuration version available in the workspace.
        type: str
        required: false
    run_message:
        description: An optional message to attach to the run for documentation purposes.
        type: str
        required: false
    auto_apply:
        description: Whether to automatically apply the run after the planning phase completes successfully.
        type: bool
        required: false
    save_plan:
        description: Whether to save the plan and check the configuration without making it the workspace's current run.
        type: bool
        required: false
    variables:
        description: A list of variables to pass to the run for configuration.
        type: list
        elements: dict
        required: false
    plan_only:
        description: Whether to only create a plan without applying any changes.
        type: bool
        required: false
    run_id:
        description: The unique identifier of the run to apply, cancel, or discard.
        type: str
        required: false
    is_destroy:
        description: Whether to destroy all provisioned resources managed by this configuration.
        type: bool
        required: false
    target_addrs:
        description: A list of resource addresses to target for this run operation.
        type: list
        elements: str
        required: false
    state:
        description: The desired state of the run to manage.
        type: str
        choices: ['present', 'applied', 'discarded', 'canceled']
        default: 'present'
        required: false
    poll:
        description: Whether to poll and wait for the run to reach a terminal state.
        type: bool
        default: true
        required: false
    poll_interval:
        description:
            - The interval in seconds to wait between status checks when polling.
            - Used in conjunction with the C(poll_timeout) parameter.
        type: int
        default: 5
    poll_timeout:
        description:
            - The maximum time in seconds to wait for the run to reach a terminal state.
            - Used in conjunction with the C(poll_interval) parameter.
            - Includes time for exponential backoff in case of transient errors.
        type: int
        default: 25
"""

EXAMPLES = r"""
- name: Create a new Terraform run with auto-apply
  hashicorp.terraform.run:
    workspace: "my-app-workspace"
    organization: "my-org"
    run_message: "Deploy new application version"
    auto_apply: true
    variables:
      - key: "environment"
        value: "production"
      - key: "app_version"
        value: "v1.2.3"
    state: "present"

- name: Create a plan-only run for review
  hashicorp.terraform.run:
    workspace_id: "ws-abc123def456"
    run_message: "Review infrastructure changes"
    plan_only: true
    state: "present"

- name: Create a destroy run to remove resources
  hashicorp.terraform.run:
    workspace: "staging-workspace"
    organization: "my-org"
    run_message: "Clean up staging environment"
    is_destroy: true
    auto_apply: false
    state: "present"

- name: Apply an existing run
  hashicorp.terraform.run:
    run_id: "run-abc123def456"
    state: "applied"
    poll: true
    poll_timeout: 300

- name: Cancel a running Terraform operation
  hashicorp.terraform.run:
    run_id: "run-abc123def456"
    state: "canceled"

- name: Discard a planned run without applying
  hashicorp.terraform.run:
    run_id: "run-abc123def456"
    state: "discarded"
"""
# todo add task outputs above
RETURN = r"""
data:
    description: The main data object containing run information.
    returned: always
    type: complex
    contains:
        id:
            description: The unique identifier of the run.
            returned: always
            type: str
            sample: "run-7TwrwCoRQ3FXbFtP"
        type:
            description: The resource type, always 'runs'.
            returned: always
            type: str
            sample: "runs"
        attributes:
            description: The run's attributes and configuration.
            returned: always
            type: dict
            sample: {
                "actions": {
                    "is-cancelable": true,
                    "is-confirmable": false,
                    "is-discardable": false,
                    "is-force-cancelable": false
                },
                "allow-config-generation": false,
                "allow-empty-apply": false,
                "auto-apply": false,
                "canceled-at": null,
                "created-at": "2025-07-03T08:10:20.479Z",
                "has-changes": false,
                "is-destroy": false,
                "message": "Custom message2",
                "plan-only": true,
                "status": "pending",
                "terraform-version": "1.10.5",
                "updated-at": "2025-07-03T08:10:20.651Z",
                "permissions": {
                    "can-apply": true,
                    "can-cancel": true,
                    "can-discard": true,
                    "can-force-cancel": true
                },
                "variables": []
            }
        relationships:
            description: Related resources linked to the run.
            returned: always
            type: dict
            sample: {
                "workspace": {
                    "data": {
                        "id": "ws-82Qk88p7boaHK2BT",
                        "type": "workspaces"
                    }
                },
                "apply": {
                    "data": {
                        "id": "apply-qki4X5daDtNzNjpw",
                        "type": "applies"
                    }
                },
                "configuration-version": {
                    "data": {
                        "id": "cv-h2u3XnkPasTHbgyv",
                        "type": "configuration-versions"
                    }
                },
                "plan": {
                    "data": {
                        "id": "plan-YDyzmtnwadKwjVSn",
                        "type": "plans"
                    }
                },
                "created-by": {
                    "data": {
                        "id": "user-YYhuc7w4AJxv5RVp",
                        "type": "users"
                    }
                }
            }
        links:
            description: API links for the run.
            returned: always
            type: dict
            sample: {
                "self": "/api/v2/runs/run-7TwrwCoRQ3FXbFtP"
            }
changed:
    description: Whether any changes were made.
    returned: always
    type: bool
    sample: true
failed:
    description: Whether the operation failed.
    returned: when operation fails
    type: bool
    sample: false
msg:
    description: Human readable message describing the result.
    returned: when operation fails or during polling timeout
    type: str
    sample: "Run reached status 'timeout' instead of expected success state"
"""

import time

from typing import Any, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.run import RunRequest, RunStates
from ansible_collections.hashicorp.terraform.plugins.module_utils.run import apply_run, cancel_run, create_run, discard_run, get_run
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace


def wait_for_state(client: TerraformClient, run_id: str, timeout: int = 25, polling_interval: int = 5) -> tuple[str, Optional[dict[str, Any]]]:
    """
    Wait for a run to reach a terminal state (success or failure).
    Args:
        client: TerraformClient instance
        run_id: The ID of the run to wait for.
        timeout: The timeout for the wait in seconds.
        polling_interval: The polling interval in seconds.
    Returns:
        A tuple of (status, run_data) where status is "success", "failure", or "timeout"
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


def handle_polling_and_result(client: TerraformClient, response: dict, poll: bool, run_id: Optional[str] = None, **kwargs: Any) -> dict[str, Any]:
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
        status, poll_response = wait_for_state(client, target_run_id, kwargs.get("poll_timeout", 25), kwargs.get("poll_interval", 5))
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
    return handle_polling_and_result(client, response, **kwargs)


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
        The canceled run in the form of a dictionary.
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
            run_message=dict(type="str"),
            auto_apply=dict(type="bool"),
            save_plan=dict(type="bool"),
            variables=dict(type="list", elements="dict"),
            plan_only=dict(type="bool"),
            is_destroy=dict(type="bool"),
            target_addrs=dict(type="list", elements="str"),
            state=dict(type="str", choices=["present", "applied", "discarded", "canceled"], default="present"),
            run_id=dict(type="str"),
        ),
        required_together=[["workspace", "organization"]],
        required_if=[
            ("state", "present", ("workspace_id", "workspace"), True),
            ("state", "applied", ("run_id",), True),
            ("state", "discarded", ("run_id",), True),
            ("state", "canceled", ("run_id",), True),
        ],
        supports_check_mode=True,
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
