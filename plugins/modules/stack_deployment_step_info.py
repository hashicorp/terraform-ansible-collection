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
  - Look up a single deployment step by its C(stack_deployment_step_id).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  stack_deployment_step_id:
    description:
      - The unique identifier of the stack deployment step (e.g. C(sds-...)).
      - Required to look up a deployment step by ID.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve a deployment step by ID
  hashicorp.terraform.stack_deployment_step_info:
    stack_deployment_step_id: "sds-abc123"
  register: step
"""

RETURN = r"""
stack_deployment_step:
  description: A single deployment step, returned for all successful lookups.
  returned: always
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
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_deployment_step import (
    get_stack_deployment_step,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "stack_deployment_step_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            step = get_stack_deployment_step(adapter, params["stack_deployment_step_id"])
            if not step:
                raise ValueError(f"Stack deployment step with ID" f" {params['stack_deployment_step_id']!r} not found")
            result["stack_deployment_step"] = step
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
