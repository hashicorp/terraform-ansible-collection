#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: stack_deployment_run_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise stack deployment run.
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Retrieves information about a stack deployment run on Terraform Cloud and Terraform Enterprise.
  - A stack deployment run represents a single execution within a deployment group for a stack
    configuration.
  - Look up a single deployment run by its C(stack_deployment_run_id).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  stack_deployment_run_id:
    description:
      - The unique identifier of the stack deployment run (e.g. C(sdr-...)).
      - Required to look up a deployment run by ID.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve a deployment run by ID
  hashicorp.terraform.stack_deployment_run_info:
    stack_deployment_run_id: "sdr-abc123"
  register: run
"""

RETURN = r"""
stack_deployment_run:
  description: A single deployment run, returned for all successful lookups.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the deployment run.
      returned: always
      type: str
      sample: "sdr-abc123"
    status:
      description: >
        The current status of the deployment run.
        One of C(pending), C(pre-deploying), C(pre-deploying-pending-operator),
        C(acquiring-lock), C(deploying), C(deploying-pending-operator),
        C(succeeded), C(failed), C(abandoned).
      returned: always
      type: str
      sample: "deploying"
    deployment:
      description: The deployment identifier associated with this run.
      returned: when present
      type: str
      sample: "dep-xyz456"
    created_at:
      description: Timestamp when the deployment run was created (ISO 8601).
      returned: always
      type: str
      sample: "2026-07-02T09:40:37+00:00"
    updated_at:
      description: Timestamp when the deployment run was last updated (ISO 8601).
      returned: always
      type: str
      sample: "2026-07-02T09:40:38+00:00"
    stack_deployment_group:
      description: The parent deployment group, included when the API response contains relationship data.
      returned: when present
      type: dict
      contains:
        id:
          description: The deployment group identifier.
          returned: always
          type: str
          sample: "sdg-xyz789"
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_deployment_run import (
    get_stack_deployment_run,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "stack_deployment_run_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            run = get_stack_deployment_run(adapter, params["stack_deployment_run_id"])
            if not run:
                raise ValueError(f"Stack deployment run with ID {params['stack_deployment_run_id']!r} not found")
            result["stack_deployment_run"] = run
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
