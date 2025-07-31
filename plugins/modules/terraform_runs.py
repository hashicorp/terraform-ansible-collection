#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: run
version_added: "1.0.0"
short_description: This module supports Create,  for Terraform Cloud/Enterprise runs.
author: "Siddarth Sharma (@siddasha)"
description:
  - The module supports run operations such as creating, applying, cancelling and discarding.
  - It allows the user to manage Terraform runs by specifying the workspace, plan, and other parameters.
  - It can also be used to trigger a plan or apply operation on a specified workspace.
  - The module provides options to manage run attributes such as message, variables, and auto-apply settings.
  - Supports both Terraform Cloud and Terraform Enterprise environments.
  - The present state supports planned, planned and saved, planned and finished and applied states; defaults to planned state
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
        choices: ['present', 'applied', 'discarded', 'cancelled']
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

Examples = r"""
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
        state: "cancelled"

    - name: Discard a Terraform run
      hashicorp.terraform.run:
        run_id: "run-12345678"
        state: "discarded"
"""

from plugins.module_utils.common import TerraformClient, TerraformModule
from plugins.module_utils.run import TerraformRun


def main():
    module = TerraformModule(
        argument_spec=dict(
            workspace_id=dict(type="str", required=False),
            workspace=dict(type="str", required=False),
            organization=dict(type="str", required=False),
            poll=dict(type="bool", required=False, default=True),
            poll_interval=dict(type="int", required=False, default=5),
            poll_timeout=dict(type="int", required=False, default=25),
            configuration_version=dict(type="str", required=False),
            message=dict(type="str", required=False),
            auto_apply=dict(type="bool", required=False),
            save_plan=dict(type="bool", required=False),
            variables=dict(type="list", required=False),
            plan_only=dict(type="bool", required=False),
            is_destroy=dict(type="bool", required=False),
            target_addrs=dict(type="list", required=False),
            state=dict(type="str", required=False, choices=["present", "applied", "discarded", "cancelled"], default="present"),
            run_id=dict(type="str", required=False),
        ),
        required_together=[["workspace", "organization"]],
        required_if=[
            ("state", "present", ("workspace_id", "workspace"), True),
            ("state", "applied", ("run_id"), True),
            ("state", "discarded", ("run_id"), True),
            ("state", "cancelled", ("run_id"), True),
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

    tf_client = TerraformClient(**module.params)
    tf_run = TerraformRun(client=tf_client)


if __name__ == "__main__":
    main()
