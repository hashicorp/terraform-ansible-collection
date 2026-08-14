#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: stack_state_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise stack state.
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Retrieves information about a specific stack state on Terraform Cloud and
    Terraform Enterprise by its unique ID.
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  stack_state_id:
    description:
      - The unique identifier of the stack state (e.g. C(sts-...)).
      - Provide this to retrieve a single stack state by ID.
      - Mutually exclusive with C(stack_id).
    type: str
  stack_id:
    description:
      - The unique identifier of the parent stack (e.g. C(st-...)).
      - When provided, lists all stack states for that stack.
      - Mutually exclusive with C(stack_state_id).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve stack state by ID
  hashicorp.terraform.stack_state_info:
    stack_state_id: "sts-abc123"
  register: state

- name: List all stack states for a stack
  hashicorp.terraform.stack_state_info:
    stack_id: "st-xyz789"
  register: states

# Task output:
# ------------
# "state": {
#     "changed": false,
#     "failed": false,
#     "stack_state": {
#         "id": "sts-abc123",
#         "generation": 3,
#         "status": "completed",
#         "deployment": "dev",
#         "is_current": true,
#         "resource_instance_count": 7,
#         "components": [
#             {
#                 "address": "component.ns",
#                 "component_address": "component.ns",
#                 "instance_correlator": "abc123==",
#                 "component_correlator": "xyz789==",
#                 "resource_instance_count": 1
#             }
#         ]
#     }
# }

- name: Handle case when stack state does not exist
  hashicorp.terraform.stack_state_info:
    stack_state_id: "sts-doesnotexist"
  register: state
  ignore_errors: true

# Task output:
# ------------
# FAILED! => {
#     "changed": false,
#     "failed": true,
#     "msg": "Stack state with ID 'sts-doesnotexist' not found"
# }
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
stack_states:
  description: All stack states belonging to the stack.
  returned: when O(stack_id) is provided
  type: list
  elements: dict
stack_state:
  description: A dictionary containing the stack state information.
  returned: on success
  type: dict
  contains:
    id:
      description: The unique identifier of the stack state.
      returned: always
      type: str
      sample: "ss-abc123"
    generation:
      description: The sequential generation number of this state capture.
      returned: when present
      type: int
      sample: 3
    status:
      description: The status of the stack state (e.g. C(completed), C(superseded)).
      returned: when present
      type: str
      sample: "completed"
    deployment:
      description: The deployment name this state belongs to.
      returned: when present
      type: str
      sample: "dev"
    is_current:
      description: Whether this is the current active state for the deployment.
      returned: when present
      type: bool
      sample: true
    resource_instance_count:
      description: Total number of managed resource instances in this state.
      returned: when present
      type: int
      sample: 7
    components:
      description: List of component entries within the stack state.
      returned: when present
      type: list
      elements: dict
      contains:
        address:
          description: The component address within the stack.
          returned: when present
          type: str
          sample: "component.ns"
        component_address:
          description: The full component address.
          returned: when present
          type: str
          sample: "component.ns"
        instance_correlator:
          description: Unique correlator for tracking the component instance.
          returned: when present
          type: str
          sample: "abc123=="
        component_correlator:
          description: Unique correlator for tracking the component.
          returned: when present
          type: str
          sample: "xyz789=="
        resource_instance_count:
          description: Number of resource instances managed by this component.
          returned: when present
          type: int
          sample: 1
    stack:
      description: The parent stack associated with this state.
      returned: when present
      type: dict
      contains:
        id:
          description: The unique identifier of the stack.
          returned: always
          type: str
          sample: "st-xyz789"
    stack_deployment_run:
      description: The stack deployment run that produced this state.
      returned: when present
      type: dict
      contains:
        id:
          description: The unique identifier of the stack deployment run.
          returned: always
          type: str
          sample: "sdr-run001"
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_state import (
    get_stack_state,
    list_stack_states,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "stack_state_id": {"type": "str"},
            "stack_id": {"type": "str"},
        },
        required_one_of=[("stack_state_id", "stack_id")],
        mutually_exclusive=[("stack_state_id", "stack_id")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("stack_state_id"):
                stack_state = get_stack_state(adapter, params["stack_state_id"])
                if stack_state is None:
                    raise ValueError(f"Stack state with ID '{params['stack_state_id']}' not found")
                result["stack_state"] = stack_state
            else:
                result["stack_states"] = list_stack_states(adapter, params["stack_id"])
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
