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
  - The C(present) state creates a new run with the specified parameters.
  - The C(applied) state applies an existing run using its run ID.
  - The C(discarded) state discards a run without applying it.
  - The C(canceled) state cancels a run that is currently in progress.
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
        description:
        - Whether to automatically apply the run after the planning phase completes successfully.
        - Mutually exclusive with I(plan_only) and I(save_plan).
        type: bool
        required: false
    save_plan:
        description:
        - Whether to save the plan and check the configuration without making it the workspace's current run.
        - Mutually exclusive with I(auto_apply) and I(plan_only).
        type: bool
        required: false
    variables:
        description: A list of variables to pass to the run for configuration.
        type: list
        elements: dict
        required: false
    plan_only:
        description:
        - Whether to only create a plan without applying any changes.
        - Mutually exclusive with I(auto_apply) and I(save_plan).
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
        description:
        - The desired state of the run to manage.
        - The applied, discarded, and canceled states require the I(run_id) while the other parameters do not have any effect on the run.
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
        default: 120
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

# Task output:
# ------------
# "result": {
#     "changed": true,
#     "failed": false,
#     "id": "run-abc123def456",
#     "auto_apply": true,
#     "created_at": "2025-01-15T10:30:00.000Z",,
#     "has_changes": true,
#     "is_destroy": false,
#     "message": "Deploy new application version",
#     "plan_only": false,
#     "source": "tfe-api",
#     "status": "applied",
#     "status_timestamps": {
#         "applied_at": "2025-01-15T10:35:00.000Z",
#         "plan_queueable_at": "2025-01-15T10:30:05.000Z",
#         "planning_at": "2025-01-15T10:30:10.000Z",
#         "planned_at": "2025-01-15T10:32:00.000Z",
#         "apply_queueable_at": "2025-01-15T10:32:05.000Z",
#         "applying_at": "2025-01-15T10:33:00.000Z"
#     },
#     "actions": {
#         "is_cancelable": false,
#         "is_confirmable": false,
#         "is_discardable": false,
#         "is_force_cancelable": false
#     },
# }

- name: Create a plan-only run for review (with polling)
  hashicorp.terraform.run:
    workspace_id: "ws-abc123def456"
    run_message: "Review infrastructure changes"
    plan_only: true
    poll: true
    state: "present"

# Task output (with poll: true - default interval and timeout):
# ------------
# "result": {
#     "changed": true,
#     "id": "run-def456ghi789",
#     "auto_apply": false,
#     "created_at": "2025-02-20T14:00:00.000Z",
#     "has_changes": true,
#     "is_destroy": false,
#     "message": "Review infrastructure changes",
#     "source": "tfe-api",
#     "status": "planned",
#     "plan_only": true,
#     "status_timestamps": {
#         "plan_queueable_at": "2025-01-15T11:00:05.000Z",
#         "planning_at": "2025-01-15T11:00:10.000Z",
#         "planned_at": "2025-01-15T11:02:00.000Z"
#     },
#     "actions": {
#         "is_cancelable": false,
#         "is_confirmable": true,
#         "is_discardable": true,
#         "is_force_cancelable": false
#     },
#     "variables": []
# }

- name: Create a plan-only run without polling
  hashicorp.terraform.run:
    workspace_id: "ws-abc123def456"
    run_message: "Quick plan check"
    plan_only: true
    poll: false
    state: "present"

# Task output (with poll: false):
# ------------
# "result": {
#     "changed": true,
#     "id": "run-jkl012mno345",
#     "actions": {
#         "is_cancelable": true,
#         "is_confirmable": false,
#         "is_discardable": false,
#         "is_force_cancelable": false
#     },
#     "auto_apply": false,
#     "created_at": "2025-01-15T11:30:00.000Z",
#     "has_changes": null,
#     "is_destroy": false,
#     "message": "Quick plan check",
#     "plan_only": true,
#     "source": "tfe-api",
#     "status": "pending",
#     "status_timestamps": {
#         "queuing_at": "2025-01-15T11:30:00.000Z"
#     },
# }

- name: Create a destroy run to remove resources
  hashicorp.terraform.run:
    workspace: "staging-workspace"
    organization: "my-org"
    run_message: "Clean up staging environment"
    is_destroy: true
    auto_apply: false
    state: "present"

# Task output:
# ------------
# "result": {
#     "changed": true,
#     "id": "run-ghi789jkl012hi",
#     "actions": {
#         "is_cancelable": false,
#         "is_confirmable": false,
#         "is_discardable": false,
#         "is_force_cancelable": false
#     },
#     "auto_apply": true,
#     "created_at": "2026-03-26T10:15:05.813000Z",
#     "has_changes": true,
#     "is_destroy": true,
#     "message": "Clean up staging environment",
#     "plan_only": false,
#     "source": "tfe-api",
#     "status": "planned",
#     "status_timestamps": {
#         "plan_queueable_at": "2026-03-26T10:15:05Z",
#         "planning_at": "2026-03-26T10:15:08Z",
#         "planned_at": "2026-03-26T10:15:12Z",
#     },
# }

- name: Apply an existing run
  hashicorp.terraform.run:
    run_id: "run-abc123def456"
    state: "applied"
    poll: true
    poll_timeout: 300
    poll_interval: 10

# Task output (with poll: true, poll_timeout: 300, poll_interval: 10):
# ------------
# "result": {
#     "changed": true,
#     "failed": false,
#     "id": "run-abc123def456",
#     "actions": {
#         "is_cancelable": false,
#         "is_confirmable": false,
#         "is_discardable": false,
#         "is_force_cancelable": false
#     },
#     "auto_apply": false,
#     "created_at": "2026-03-26T10:14:34.631000Z",
#     "has_changes": true,
#     "is_destroy": false,
#     "message": "Deploy new application version",
#     "plan_only": false,
#     "source": "tfe-api",
#     "status": "applied",
#     "status_timestamps": {
#         "applied_at": "2025-01-15T10:35:00.000Z",
#         "plan_queueable_at": "2025-01-15T10:30:05.000Z",
#         "planning_at": "2025-01-15T10:30:10.000Z",
#         "planned_at": "2025-01-15T10:32:00.000Z",
#         "apply_queueable_at": "2025-01-15T10:32:05.000Z",
#         "applying_at": "2025-01-15T10:33:00.000Z",
#     },
# }
#
# Task output (with poll: false):
# ------------
# "result": {
#     "changed": true,
#     "failed": false
# }

- name: Cancel a running Terraform operation
  hashicorp.terraform.run:
    run_id: "run-abc123def456"
    state: "canceled"

# Task output (with poll: true - default):
# ------------
# "result": {
#     "changed": true,
#     "failed": false,
#     "id": "run-abc123def456",
#     "actions": {
#         "is_cancelable": false,
#         "is_confirmable": false,
#         "is_discardable": false,
#         "is_force_cancelable": false
#     },
#     "auto_apply": true,
#     "created_at": "2025-01-15T10:14:34.631000Z",
#     "has_changes": true,
#     "is_destroy": false,
#     "message": "Deploy new application version",
#     "plan_only": false,
#     "source": "tfe-api",
#     "status": "canceled",
#     "status_timestamps": {
#         "canceled_at": "2025-01-15T10:20:00.000Z",
#         "plan_queueable_at": "2025-01-15T10:30:05.000Z",
#         "planning_at": "2025-01-15T10:30:10.000Z",
#         "planned_at": "2025-01-15T10:32:00.000Z",
#     },

# }
#
# Task output (with poll: false):
# ------------
# "result": {
#     "changed": true,
#     "failed": false
# }

- name: Discard a planned run without applying
  hashicorp.terraform.run:
    run_id: "run-abc123def456"
    state: "discarded"

# Task output (with poll: true - default interval and timeout):
# ------------
# "result": {
#     "changed": true,
#     "failed": false,
#     "id": "run-abc123def456",
#     "actions": {
#         "is_cancelable": false,
#         "is_confirmable": false,
#         "is_discardable": false,
#         "is_force_cancelable": false
#     },
#     "auto_apply": false,
#     "created_at": "2025-01-15T10:14:34.631000Z",
#     "has_changes": true,
#     "is_destroy": false,
#     "message": "Deploy new application version",
#     "plan_only": false,
#     "source": "tfe-api",
#     "status": "discarded",
#     "status_timestamps": {
#         "planned_at": "2025-01-15T10:32:00.000Z",
#         "discarded_at": "2025-01-15T10:36:10.000Z",
#         "plan_queueable_at": "2025-01-15T10:30:05.000Z",
#         "planning_at": "2025-01-15T10:30:10.000Z",
#     },
# }
#
# Task output (with poll: false):
# ------------
# "result": {
#     "changed": true,
#     "failed": false
# }
"""

RETURN = r"""
id:
    description: The unique identifier of the run.
    returned: always
    type: str
    sample: run-uYpZSm96CYWWk5gJ
status:
    description: Current status of the run.
    returned: when run data is returned
    type: str
    sample: applied
actions:
    description: Action capability flags for the run.
    returned: when run data is returned
    type: dict
    sample:
        is_cancelable: false
        is_confirmable: false
        is_discardable: false
        is_force_cancelable: false
auto_apply:
    description: Whether auto-apply is enabled for the run.
    returned: when run data is returned
    type: bool
    sample: false
created_at:
    description: Run creation timestamp.
    returned: when run data is returned
    type: str
    sample: "2026-03-26T10:14:34.631000Z"
has_changes:
    description: Whether the run contains infrastructure changes.
    returned: when run data is returned
    type: bool
    sample: true
is_destroy:
    description: Whether the run is a destroy run.
    returned: when run data is returned
    type: bool
    sample: false
message:
    description: Message associated with the run.
    returned: when run data is returned
    type: str
    sample: Triggered via API
plan_only:
    description: Whether the run is plan-only.
    returned: when run data is returned
    type: bool
    sample: false
source:
    description: Source of the run trigger.
    returned: when run data is returned
    type: str
    sample: tfe-api
status_timestamps:
    description: Lifecycle timestamps keyed by event name.
    returned: when run data is returned
    type: dict
    sample:
        planned_at: "2026-03-26T10:14:40Z"
        applied_at: "2026-03-26T10:14:55Z"
variables:
    description: Variables passed to the run.
    returned: when run data is returned
    type: list
    elements: dict
    sample:
        - key: env
          value: production
"""

import time
from copy import deepcopy
from typing import Any, Optional

from ansible.module_utils.common.text.converters import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.run import apply_run, cancel_run, create_run, discard_run, get_run
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace

SUCCESS_STATES = [
    "planned",
    "planned_and_finished",
    "planned_and_saved",
    "applied",
    "discarded",
    "canceled",
    "force_canceled",
    "policy_override",
    "post_plan_completed",
    "post_plan_awaiting_decision",
]

FAILURE_STATES = ["errored", "policy_soft_failed"]


def wait_for_state(adapter: TerraformClient, run_id: str, timeout: int = 120, polling_interval: int = 5) -> tuple[str, Optional[dict[str, Any]]]:
    """
    Wait for a run to reach a terminal state (success or failure).
    Args:
        adapter: TerraformClient instance
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
    while True:
        run = get_run(adapter, run_id)
        # Check for empty dict (404 case) or missing data
        if not run:
            return "failure", {"error": f"Run {run_id} not found"}
        state = run.get("status")
        if run and state in SUCCESS_STATES:
            return "success", run
        elif run and state in FAILURE_STATES:
            return "failure", run

        if time.time() - start_time > timeout:
            break

        time.sleep(polling_interval)
    return "timeout", run


def handle_polling_and_result(adapter: TerraformClient, response: dict, poll: bool, run_id: Optional[str] = None, **kwargs: Any) -> dict[str, Any]:
    """
    Handle polling and return appropriate action result.
    Args:
        adapter: TerraformClient instance
        response: The API response
        poll: Whether to poll for status
        run_id: Run ID to poll (defaults to response data id)
    Returns:
        Action result dictionary
    """
    action_result = {}
    target_run_id = run_id or response.get("id")
    if poll and target_run_id:
        status, poll_response = wait_for_state(adapter, target_run_id, kwargs.get("poll_timeout", 120), kwargs.get("poll_interval", 5))
        if status == "success" and poll_response:
            poll_data = poll_response or {}
            action_result.update({"changed": True, **poll_data})
        else:
            action_result.update({"failed": True, "msg": f"Run reached status '{status}' instead of expected success state"})
    else:
        data = response or {}
        action_result.update({"changed": True, **data})

    return action_result


def check_mode(func):
    """
    Decorator to handle check mode and check if the run exists.
    Args:
        func: The function to decorate.
    Returns:
        The decorated function.
    """

    def wrapper(*args, **kwargs):
        # Check if check_mode is enabled
        check_mode_enabled = kwargs.get("check_mode", False)
        if not check_mode_enabled:
            return func(*args, **kwargs)

        default_return = {"changed": True, "msg": "Check mode is enabled, no changes will be made"}

        # Handle present state functions directly
        if func.__name__.endswith("_present"):
            return default_return

        # For discarded, canceled, and applied states, check if run exists first
        run_id = kwargs.get("run_id")
        client = args[0]
        run = get_run(client, run_id)
        if not run:
            return {"failed": True, "msg": f"Run {run_id} not found in the Terraform Cloud/Enterprise workspace"}
        return {"changed": True, "msg": f"Run {run_id} found, check mode is enabled, no changes will be made"}

    return wrapper


def idempotency_check(func):
    """
    Decorator to check if the run is idempotent.
    Args:
        func: The function to decorate.
    Returns:
        The decorated function.
    """

    def wrapper(*args, **kwargs):
        run_id = kwargs.get("run_id")
        if run_id:
            run = get_run(args[0], run_id)
            if not run:
                return {"failed": True, "msg": f"Run {run_id} not found"}
            elif run.get("status") == func.__name__.split("_")[1]:
                return {"changed": False, "run": run}
        return func(*args, **kwargs)

    return wrapper


@check_mode
def state_present(adapter: TerraformClient, **kwargs: Any) -> Optional[dict[str, Any]]:
    """
    Create a new run with the given parameters.
    Args:
        **kwargs: Keyword arguments to create a new run.
    Returns:
        The created run in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 201 status code.
    """
    # Filter out Terraform client params (tf_*), polling params (poll_*), and Ansible-specific params
    excluded_params = {"check_mode", "state", "organization", "workspace"}
    run_params = {key: value for key, value in kwargs.items() if not key.startswith(("tf_", "tfe_", "poll_")) and key not in excluded_params}

    response = create_run(adapter, data=run_params)
    return handle_polling_and_result(adapter, response, **kwargs)


@check_mode
@idempotency_check
def state_applied(adapter: TerraformClient, **kwargs: Any) -> Optional[dict[str, Any]]:
    """
    Apply a run with the given parameters.
    Args:
        **kwargs: Keyword arguments to apply a run.
    Returns:
        The applied run in the form of a dictionary.
    """
    run_id = kwargs.pop("run_id", None)
    poll = kwargs.pop("poll", True)
    response = apply_run(adapter, run_id, comment=kwargs.get("run_message"))
    return handle_polling_and_result(adapter, response, poll, run_id, **kwargs)


@check_mode
@idempotency_check
def state_discarded(adapter: TerraformClient, **kwargs: Any) -> Optional[dict[str, Any]]:
    """
    Discard a run with the given parameters.
    Args:
        **kwargs: Keyword arguments to discard a run.
    Returns:
        The discarded run in the form of a dictionary.
    """
    run_id = kwargs.pop("run_id", None)
    poll = kwargs.pop("poll", True)
    response = discard_run(adapter, run_id, comment=kwargs.get("run_message"))
    return handle_polling_and_result(adapter, response, poll, run_id, **kwargs)


@check_mode
@idempotency_check
def state_canceled(adapter: TerraformClient, **kwargs: Any) -> Optional[dict[str, Any]]:
    """
    Cancel a run with the given parameters.
    Args:
        **kwargs: Keyword arguments to cancel a run.
    Returns:
        The canceled run in the form of a dictionary.
    """
    run_id = kwargs.pop("run_id", None)
    poll = kwargs.pop("poll", True)
    response = cancel_run(adapter, run_id, comment=kwargs.get("run_message"))
    return handle_polling_and_result(adapter, response, poll, run_id, **kwargs)


def get_workspace_id(adapter: TerraformClient, workspace: str, organization: str) -> str:
    """
    Get the workspace ID for the given workspace and organization.
    Args:
        workspace: The name of the workspace.
        organization: The name of the organization.
    Returns:
        workspace_id: The ID of the workspace.
    """
    response = get_workspace(adapter, organization, workspace)
    if not response:
        raise TerraformError(f"The Workspace {workspace} was not found in the organization {organization}")
    return response.get("id")


def main():
    module = AnsibleTerraformModule(
        argument_spec={
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
            "poll": {"type": "bool", "default": True},
            "poll_interval": {"type": "int", "default": 5},
            "poll_timeout": {"type": "int", "default": 120},
            "configuration_version": {"type": "str"},
            "run_message": {"type": "str", "default": None},
            "auto_apply": {"type": "bool"},
            "save_plan": {"type": "bool"},
            "variables": {"type": "list", "elements": "dict"},
            "plan_only": {"type": "bool"},
            "is_destroy": {"type": "bool"},
            "target_addrs": {"type": "list", "elements": "str"},
            "state": {"type": "str", "choices": ["present", "applied", "discarded", "canceled"], "default": "present"},
            "run_id": {"type": "str"},
        },
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
    params = deepcopy(module.params)
    params["check_mode"] = module.check_mode
    adapter = None

    try:
        adapter = TerraformClient(tfe_token=params.get("tfe_token"), tfe_address=params.get("tfe_address"))

        # Get workspace_id if not provided and state is present
        if not params.get("workspace_id") and params.get("state") == "present":
            params["workspace_id"] = get_workspace_id(adapter, params["workspace"], params["organization"])

        match params.get("state"):
            case "present":
                action_result = state_present(adapter, **params)
            case "applied":
                action_result = state_applied(adapter, **params)
            case "discarded":
                action_result = state_discarded(adapter, **params)
            case "canceled":
                action_result = state_canceled(adapter, **params)

        result.update(action_result)
        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))
    finally:
        if adapter:
            adapter.cleanup()


if __name__ == "__main__":
    main()
