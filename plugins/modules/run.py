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
#     "attributes": {
#         "actions": {
#             "is-cancelable": false,
#             "is-confirmable": false,
#             "is-discardable": false,
#             "is-force-cancelable": false
#         },
#         "auto-apply": true,
#         "created-at": "2025-01-15T10:30:00.000Z",
#         "has-changes": true,
#         "is-destroy": false,
#         "message": "Deploy new application version",
#         "plan-only": false,
#         "source": "tfe-api",
#         "status": "applied",
#         "status-timestamps": {
#             "applied-at": "2025-01-15T10:35:00.000Z",
#             "plan-queueable-at": "2025-01-15T10:30:05.000Z",
#             "planning-at": "2025-01-15T10:30:10.000Z",
#             "planned-at": "2025-01-15T10:32:00.000Z",
#             "apply-queueable-at": "2025-01-15T10:32:05.000Z",
#             "applying-at": "2025-01-15T10:33:00.000Z"
#         }
#     },
#     "changed": true,
#     "failed": false,
#     "id": "run-abc123def456",
#     "links": {
#         "self": "/api/v2/runs/run-abc123def456"
#     },
#     "relationships": {
#         "workspace": {
#             "data": {
#                 "id": "ws-xyz789abc123",
#                 "type": "workspaces"
#             }
#         }
#     },
#     "type": "runs"
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
#     "attributes": {
#         "actions": {
#             "is-cancelable": true,
#             "is-confirmable": true,
#             "is-discardable": true,
#             "is-force-cancelable": false
#         },
#         "auto-apply": false,
#         "created-at": "2025-01-15T11:00:00.000Z",
#         "has-changes": true,
#         "is-destroy": false,
#         "message": "Review infrastructure changes",
#         "plan-only": true,
#         "source": "tfe-api",
#         "status": "planned",
#         "status-timestamps": {
#             "plan-queueable-at": "2025-01-15T11:00:05.000Z",
#             "planning-at": "2025-01-15T11:00:10.000Z",
#             "planned-at": "2025-01-15T11:02:00.000Z"
#         }
#     },
#     "changed": true,
#     "id": "run-def456ghi789",
#     "links": {
#         "self": "/api/v2/runs/run-def456ghi789"
#     },
#     "relationships": {
#         "workspace": {
#             "data": {
#                 "id": "ws-abc123def456",
#                 "type": "workspaces"
#             }
#         }
#     },
#     "type": "runs"
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
#     "attributes": {
#         "actions": {
#             "is-cancelable": true,
#             "is-confirmable": false,
#             "is-discardable": false,
#             "is-force-cancelable": false
#         },
#         "auto-apply": false,
#         "created-at": "2025-01-15T11:30:00.000Z",
#         "has-changes": null,
#         "is-destroy": false,
#         "message": "Quick plan check",
#         "plan-only": true,
#         "source": "tfe-api",
#         "status": "pending",
#         "status-timestamps": {
#             "queuing-at": "2025-01-15T11:30:00.000Z"
#         }
#     },
#     "changed": true,
#     "id": "run-jkl012mno345",
#     "links": {
#         "self": "/api/v2/runs/run-jkl012mno345"
#     },
#     "relationships": {
#         "workspace": {
#             "data": {
#                 "id": "ws-abc123def456",
#                 "type": "workspaces"
#             }
#         }
#     },
#     "type": "runs"
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
#     "attributes": {
#         "actions": {
#             "is-cancelable": true,
#             "is-confirmable": true,
#             "is-discardable": true,
#             "is-force-cancelable": false
#         },
#         "auto-apply": false,
#         "created-at": "2025-01-15T12:00:00.000Z",
#         "has-changes": true,
#         "is-destroy": true,
#         "message": "Clean up staging environment",
#         "plan-only": false,
#         "source": "tfe-api",
#         "status": "planned",
#         "status-timestamps": {
#             "plan-queueable-at": "2025-01-15T12:00:05.000Z",
#             "planning-at": "2025-01-15T12:00:10.000Z",
#             "planned-at": "2025-01-15T12:01:30.000Z"
#         }
#     },
#     "changed": true,
#     "id": "run-ghi789jkl012",
#     "links": {
#         "self": "/api/v2/runs/run-ghi789jkl012"
#     },
#     "relationships": {
#         "workspace": {
#             "data": {
#                 "id": "ws-staging123",
#                 "type": "workspaces"
#             }
#         }
#     },
#     "type": "runs"
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
#     "attributes": {
#         "actions": {
#             "is-cancelable": false,
#             "is-confirmable": false,
#             "is-discardable": false,
#             "is-force-cancelable": false
#         },
#         "auto-apply": false,
#         "created-at": "2025-01-15T10:30:00.000Z",
#         "has-changes": true,
#         "is-destroy": false,
#         "message": "Deploy new application version",
#         "plan-only": false,
#         "source": "tfe-api",
#         "status": "applied",
#         "status-timestamps": {
#             "applied-at": "2025-01-15T13:15:00.000Z",
#             "plan-queueable-at": "2025-01-15T10:30:05.000Z",
#             "planning-at": "2025-01-15T10:30:10.000Z",
#             "planned-at": "2025-01-15T10:32:00.000Z",
#             "apply-queueable-at": "2025-01-15T13:10:00.000Z",
#             "applying-at": "2025-01-15T13:12:00.000Z"
#         }
#     },
#     "changed": true,
#     "failed": false,
#     "id": "run-abc123def456",
#     "links": {
#         "self": "/api/v2/runs/run-abc123def456"
#     },
#     "relationships": {
#         "workspace": {
#             "data": {
#                 "id": "ws-xyz789abc123",
#                 "type": "workspaces"
#             }
#         }
#     },
#     "type": "runs"
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
#     "attributes": {
#         "actions": {
#             "is-cancelable": false,
#             "is-confirmable": false,
#             "is-discardable": false,
#             "is-force-cancelable": false
#         },
#         "auto-apply": false,
#         "created-at": "2025-01-15T10:30:00.000Z",
#         "has-changes": true,
#         "is-destroy": false,
#         "message": "Deploy new application version",
#         "plan-only": false,
#         "source": "tfe-api",
#         "status": "canceled",
#         "status-timestamps": {
#             "canceled-at": "2025-01-15T13:20:00.000Z",
#             "plan-queueable-at": "2025-01-15T10:30:05.000Z",
#             "planning-at": "2025-01-15T10:30:10.000Z",
#             "planned-at": "2025-01-15T10:32:00.000Z"
#         }
#     },
#     "changed": true,
#     "failed": false,
#     "id": "run-abc123def456",
#     "links": {
#         "self": "/api/v2/runs/run-abc123def456"
#     },
#     "relationships": {
#         "workspace": {
#             "data": {
#                 "id": "ws-xyz789abc123",
#                 "type": "workspaces"
#             }
#         }
#     },
#     "type": "runs"
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
#     "attributes": {
#         "actions": {
#             "is-cancelable": false,
#             "is-confirmable": false,
#             "is-discardable": false,
#             "is-force-cancelable": false
#         },
#         "auto-apply": false,
#         "created-at": "2025-01-15T10:30:00.000Z",
#         "has-changes": true,
#         "is-destroy": false,
#         "message": "Deploy new application version",
#         "plan-only": false,
#         "source": "tfe-api",
#         "status": "discarded",
#         "status-timestamps": {
#             "discarded-at": "2025-01-15T13:25:00.000Z",
#             "plan-queueable-at": "2025-01-15T10:30:05.000Z",
#             "planning-at": "2025-01-15T10:30:10.000Z",
#             "planned-at": "2025-01-15T10:32:00.000Z"
#         }
#     },
#     "changed": true,
#     "failed": false,
#     "id": "run-abc123def456",
#     "links": {
#         "self": "/api/v2/runs/run-abc123def456"
#     },
#     "relationships": {
#         "workspace": {
#             "data": {
#                 "id": "ws-xyz789abc123",
#                 "type": "workspaces"
#             }
#         }
#     },
#     "type": "runs"
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
"""

import time

from copy import deepcopy
from typing import Any, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.run import RunRequest, RunStates
from ansible_collections.hashicorp.terraform.plugins.module_utils.run import apply_run, cancel_run, create_run, discard_run, get_run
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace


def wait_for_state(client: TerraformClient, run_id: str, timeout: int = 120, polling_interval: int = 5) -> tuple[str, Optional[dict[str, Any]]]:
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
    while True:
        run = get_run(client, run_id)
        # Check for empty dict (404 case) or missing data
        if not run or not run.get("data"):
            return "failure", {"error": f"Run {run_id} not found"}
        state = run.get("data").get("attributes", {}).get("status")
        if run and RunStates.is_success_state(state):
            return "success", run
        elif run and RunStates.is_failure_state(state):
            return "failure", run

        if time.time() - start_time > timeout:
            break

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
        status, poll_response = wait_for_state(client, target_run_id, kwargs.get("poll_timeout", 120), kwargs.get("poll_interval", 5))
        if status == "success" and poll_response:
            poll_data = poll_response.get("data") or {}
            action_result.update({"changed": True, **poll_data})
        else:
            action_result.update({"failed": True, "msg": f"Run reached status '{status}' instead of expected success state"})
    else:
        data = response.get("data") or {}
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
            if not run or not run.get("data"):
                return {"failed": True, "msg": f"Run {run_id} not found"}
            elif run.get("data").get("attributes", {}).get("status") == func.__name__.split("_")[1]:
                return {"changed": False, "run": run.get("data")}
        return func(*args, **kwargs)

    return wrapper


@check_mode
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
    # Filter out Terraform client params (tf_*), polling params (poll_*), and Ansible-specific params
    excluded_params = {"check_mode", "state", "organization", "workspace"}
    run_params = {key: value for key, value in kwargs.items() if not key.startswith(("tf_", "poll_")) and key not in excluded_params}

    workspace_id = run_params.pop("workspace_id")
    configuration_version_id = run_params.pop("configuration_version", None)

    run_request = RunRequest.create(workspace_id=workspace_id, configuration_version_id=configuration_version_id, **run_params)

    run_payload = run_request.model_dump(by_alias=True, exclude_unset=False, exclude_none=True)
    response = create_run(client, run_payload)
    return handle_polling_and_result(client, response, **kwargs)


@check_mode
@idempotency_check
def state_applied(client: TerraformClient, **kwargs: Any) -> Optional[dict[str, Any]]:
    """
    Apply a run with the given parameters.
    Args:
        **kwargs: Keyword arguments to apply a run.
    Returns:
        The applied run in the form of a dictionary.
    """
    run_id = kwargs.pop("run_id", None)
    poll = kwargs.pop("poll", True)
    response = apply_run(client, run_id)
    return handle_polling_and_result(client, response, poll, run_id, **kwargs)


@check_mode
@idempotency_check
def state_discarded(client: TerraformClient, **kwargs: Any) -> Optional[dict[str, Any]]:
    """
    Discard a run with the given parameters.
    Args:
        **kwargs: Keyword arguments to discard a run.
    Returns:
        The discarded run in the form of a dictionary.
    """
    run_id = kwargs.pop("run_id", None)
    poll = kwargs.pop("poll", True)
    response = discard_run(client, run_id)
    return handle_polling_and_result(client, response, poll, run_id, **kwargs)


@check_mode
@idempotency_check
def state_canceled(client: TerraformClient, **kwargs: Any) -> Optional[dict[str, Any]]:
    """
    Cancel a run with the given parameters.
    Args:
        **kwargs: Keyword arguments to cancel a run.
    Returns:
        The canceled run in the form of a dictionary.
    """
    run_id = kwargs.pop("run_id", None)
    poll = kwargs.pop("poll", True)
    response = cancel_run(client, run_id)
    return handle_polling_and_result(client, response, poll, run_id, **kwargs)


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
        argument_spec={
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
            "poll": {"type": "bool", "default": True},
            "poll_interval": {"type": "int", "default": 5},
            "poll_timeout": {"type": "int", "default": 120},
            "configuration_version": {"type": "str"},
            "run_message": {"type": "str"},
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

    try:
        tf_client = TerraformClient(**module.params)

        # Get workspace_id if not provided and state is present
        if not params.get("workspace_id") and params.get("state") == "present":
            params["workspace_id"] = get_workspace_id(tf_client, params["workspace"], params["organization"])

        match params.get("state"):
            case "present":
                action_result = state_present(tf_client, **params)
            case "applied":
                action_result = state_applied(tf_client, **params)
            case "discarded":
                action_result = state_discarded(tf_client, **params)
            case "canceled":
                action_result = state_canceled(tf_client, **params)

        result.update(action_result)
        module.exit_json(**result)

    except Exception as e:
        module.fail_from_exception(e)


if __name__ == "__main__":
    main()
