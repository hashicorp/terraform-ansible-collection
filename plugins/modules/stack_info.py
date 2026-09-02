#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: stack_info
version_added: "2.2.0"
short_description: Retrieve information about Terraform Cloud/Enterprise stacks.
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Retrieves information about stacks on Terraform Cloud and Terraform Enterprise.
  - Look up a single stack by C(stack_id) or by C(organization) and C(name).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  stack_id:
    description:
      - The unique identifier of the stack (e.g. C(st-...)).
      - Provide this to look up a stack by ID.
      - Mutually exclusive with C(name) and C(organization).
    type: str
  organization:
    description:
      - The name of the organization that owns the stack.
      - Must be provided together with C(name) to look up a stack by name.
      - Mutually exclusive with C(stack_id).
    type: str
  name:
    description:
      - Human-readable stack name.
      - Must be provided together with C(organization) to look up a stack by name.
      - Mutually exclusive with C(stack_id).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve a stack by ID
  hashicorp.terraform.stack_info:
    stack_id: "st-abc123"
  register: stack

- name: Retrieve a stack by organization and name
  hashicorp.terraform.stack_info:
    organization: "my-org"
    name: "app-stack"
  register: stack
"""

RETURN = r"""
stack:
  description: A single stack, returned for all successful lookups (by C(stack_id) or by C(organization) and C(name)).
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the stack.
      returned: always
      type: str
      sample: "st-yoGmEFwGwL31Gee1"
    name:
      description: The name of the stack.
      returned: always
      type: str
      sample: "app-stack"
    description:
      description: The stack description.
      returned: when present
      type: str
      sample: "Production application stack"
    vcs_repo:
      description: VCS repository configuration.
      returned: when configured
      type: dict
    project:
      description: The associated project.
      returned: when present
      type: dict
    agent_pool:
      description: The associated agent pool.
      returned: when configured
      type: dict
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.stack import (
    get_stack,
    get_stack_by_name,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "stack_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
        },
        required_one_of=[("stack_id", "name")],
        required_together=[["organization", "name"]],
        mutually_exclusive=[("stack_id", "organization"), ("stack_id", "name")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("stack_id"):
                stack = get_stack(adapter, params["stack_id"])
            else:
                stack = get_stack_by_name(adapter, params["organization"], params["name"])

            if not stack:
                if params.get("stack_id"):
                    raise ValueError(f"Stack with ID {params['stack_id']!r} not found")
                raise ValueError(f"Stack named {params['name']!r} in organization {params['organization']!r} not found")

            result["stack"] = stack
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
