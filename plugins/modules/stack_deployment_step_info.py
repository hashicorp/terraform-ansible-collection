#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: stack_deployment_step_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise stack deployment step.
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Retrieves information about a stack deployment step on Terraform Cloud and Terraform Enterprise.
  - A stack deployment step represents a single unit of work within a deployment run for a stack
    configuration.
  - Look up a single deployment step by its C(stack_deployment_step_id), or list all steps in a
    deployment run by supplying C(stack_deployment_run_id) alone.
  - To list diagnostics produced by a step, supply C(stack_deployment_step_id) together with
    C(list_diagnostics=true).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  stack_deployment_step_id:
    description:
      - The unique identifier of the stack deployment step (e.g. C(sds-...)).
      - Provide this to look up a deployment step by ID, or combine with
        C(list_diagnostics=true) to list all diagnostics for that step.
      - Mutually exclusive with C(stack_deployment_run_id).
    type: str
  stack_deployment_run_id:
    description:
      - The unique identifier of the deployment run (e.g. C(sdr-...)).
      - When provided, lists all deployment steps in that run.
      - Mutually exclusive with C(stack_deployment_step_id).
    type: str
  list_diagnostics:
    description:
      - When C(true), lists all diagnostics for the step identified by
        C(stack_deployment_step_id) instead of returning the step itself.
      - Must be combined with C(stack_deployment_step_id); an error is raised otherwise.
      - Diagnostics are produced by the pytfe C(stack_deployment_steps.list_diagnostics)
        relationship; an empty list is returned when the step produced none.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Retrieve a deployment step by ID
  hashicorp.terraform.stack_deployment_step_info:
    stack_deployment_step_id: "sds-abc123"
  register: step

- name: List all deployment steps for a deployment run
  hashicorp.terraform.stack_deployment_step_info:
    stack_deployment_run_id: "sdr-xyz789"
  register: steps

- name: List all diagnostics for a deployment step
  hashicorp.terraform.stack_deployment_step_info:
    stack_deployment_step_id: "sds-abc123"
    list_diagnostics: true
  register: diags
"""

RETURN = r"""
stack_deployment_step:
  description: A single deployment step, returned when looking up by C(stack_deployment_step_id).
  returned: when O(stack_deployment_step_id) is provided and O(list_diagnostics) is false
  type: dict
  contains:
    id:
      description: The unique identifier of the deployment step.
      returned: always
      type: str
      sample: "sds-abc123"
    status:
      description: >
        The current status of the deployment step.
        One of C(blocked), C(abandoned), C(queued), C(running),
        C(pending-operator), C(completed), C(failed).
      returned: always
      type: str
      sample: "running"
    operation_type:
      description: The type of operation performed by this step (e.g. C(plan), C(apply)).
      returned: when present
      type: str
      sample: "plan"
    created_at:
      description: Timestamp when the deployment step was created (ISO 8601).
      returned: always
      type: str
      sample: "2026-07-02T09:40:37+00:00"
    updated_at:
      description: Timestamp when the deployment step was last updated (ISO 8601).
      returned: always
      type: str
      sample: "2026-07-02T09:40:38+00:00"
    stack_deployment_run:
      description: The parent deployment run, included when the API response contains relationship data.
      returned: when present
      type: dict
      contains:
        id:
          description: The deployment run identifier.
          returned: always
          type: str
          sample: "sdr-xyz789"
stack_deployment_steps:
  description: All deployment steps belonging to the deployment run.
  returned: when O(stack_deployment_run_id) is provided
  type: list
  elements: dict
stack_diagnostics:
  description: >
    All diagnostics belonging to the deployment step.
    The list is empty when the step produced no diagnostics.
  returned: when O(list_diagnostics) is true
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the diagnostic.
      returned: always
      type: str
      sample: "std-abc123"
    severity:
      description: Diagnostic severity (e.g. C(error), C(warning)).
      returned: always
      type: str
      sample: "error"
    summary:
      description: Short summary of the diagnostic.
      returned: always
      type: str
      sample: "Invalid configuration"
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_deployment_step import (
    get_stack_deployment_step,
    list_stack_deployment_steps,
    list_stack_diagnostics,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "stack_deployment_step_id": {"type": "str"},
            "stack_deployment_run_id": {"type": "str"},
            "list_diagnostics": {"type": "bool", "default": False},
        },
        required_one_of=[("stack_deployment_step_id", "stack_deployment_run_id")],
        mutually_exclusive=[("stack_deployment_step_id", "stack_deployment_run_id")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("list_diagnostics") and not params.get("stack_deployment_step_id"):
                raise ValueError("list_diagnostics requires stack_deployment_step_id")
            if params.get("stack_deployment_step_id"):
                if params.get("list_diagnostics"):
                    result["stack_diagnostics"] = list_stack_diagnostics(adapter, params["stack_deployment_step_id"])
                else:
                    step = get_stack_deployment_step(adapter, params["stack_deployment_step_id"])
                    if not step:
                        raise ValueError(f"Stack deployment step with ID {params['stack_deployment_step_id']!r} not found")
                    result["stack_deployment_step"] = step
            else:
                result["stack_deployment_steps"] = list_stack_deployment_steps(adapter, params["stack_deployment_run_id"])
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
