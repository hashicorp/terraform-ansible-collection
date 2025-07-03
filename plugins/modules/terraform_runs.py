#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: plan_info
version_added: "1.0.0"
short_description: This module supports Create, Update, and Delete operations for Terraform Cloud/Enterprise runs.
description:
  - The module supports operations such as creating a new run, updating an existing run, and deleting a run.
  - It allows you to manage Terraform runs by specifying the workspace, plan, and other parameters.
  - It can also be used to trigger a plan or apply operation on a specified workspace.
  - The module provides options to manage run parameters, such as message, variables, and auto-apply settings.
  - It can be used to check plan status, resource changes, and execution details.
  - Supports both Terraform Cloud and Terraform Enterprise environments.
options:
    workspace:
        description: The ID of the workspace where the run will be created or managed.
        type: str
        required: true
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
    variables:
        description: A dictionary of variables to pass to the run.
        type: dict
        required: false
    plan_only:
        description: Whether to only create a plan without applying it.
        type: bool
        required: false
        default: false
    is_destroy:
        description: Whether to create a destroy plan
        type: bool
        required: false
        default: false
    run:
        description: The ID of the run to apply/cancel.
        type: str
        required: false
    apply:
        description: Whether to apply the run after planning.
        type: bool
        required: false
        default: false
    state:
        description: The state of the run to manage.
        type: str
        choices: ['present', 'absent']
        default: 'present'
        required: false
"""

Examples =  r"""
    - name: Create a new Terraform run
      hashicorp.terraform.terraform_runs:
        workspace: "ws-12345678"
        message: "Creating a new run"
        auto_apply: true
        variables:
          var1: "value1"
          var2: "value2"
        state: "present"

    - name: Update an existing Terraform run
      hashicorp.terraform.terraform_runs:
        workspace: "ws-12345678"
        run: "run-12345678"
        message: "Updating the run message"
        state: "present"

    - name: Apply a Terraform run
      hashicorp.terraform.terraform_runs:
        workspace: "ws-12345678"
        run: "run-12345678"
        apply: true
        state: "present"
"""
