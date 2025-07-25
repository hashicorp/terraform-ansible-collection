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
        description: The desired workspace name when the run is to be created
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
        default: false
    save_plan:
        description: Wheather to run plans and check the configuration without becoming the worspace's current run
        type: bool
        required: false
        default: false
    variables:
        description: A list of dictionary of variables to pass to the run.
        type: list
        required: false
    plan_only:
        description: Whether to only create a plan without applying it.
        type: bool
        required: false
        default: false
    run_id:
        description: The ID of the run to apply/cancel.
        type: str
        required: false
    is_destroy:
        description: Wheather to destroy all the provisoned resources.
        type: bool
        required: false
        default: false
    target-addrs:
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
"""

Examples =  r"""
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
