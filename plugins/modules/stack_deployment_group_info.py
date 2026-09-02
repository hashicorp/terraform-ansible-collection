#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: stack_deployment_group_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise stack deployment group.
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Retrieves information about a stack deployment group on Terraform Cloud and Terraform Enterprise.
  - A stack deployment group represents a group of deployment runs for a single deployment within
    a stack configuration.
  - Look up a single deployment group by C(stack_deployment_group_id), or by
    C(stack_configuration_id) and C(name).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  stack_deployment_group_id:
    description:
      - The unique identifier of the stack deployment group (e.g. C(sdg-...)).
      - Provide this to look up a deployment group by ID.
      - Mutually exclusive with C(stack_configuration_id) and C(name).
    type: str
  stack_configuration_id:
    description:
      - The unique identifier of the stack configuration that owns the deployment group
        (e.g. C(stc-...)).
      - Must be provided together with C(name) to look up a deployment group by name.
      - Mutually exclusive with C(stack_deployment_group_id).
    type: str
  name:
    description:
      - The deployment name of a specific deployment group within C(stack_configuration_id)
        (e.g. C(dev), C(prod)).
      - Must be provided together with C(stack_configuration_id) to look up a deployment group by name.
      - Mutually exclusive with C(stack_deployment_group_id).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve a deployment group by ID
  hashicorp.terraform.stack_deployment_group_info:
    stack_deployment_group_id: "sdg-abc123"
  register: group

- name: Retrieve a deployment group by name within a stack configuration
  hashicorp.terraform.stack_deployment_group_info:
    stack_configuration_id: "stc-abc123"
    name: "dev"
  register: group
"""

RETURN = r"""
stack_deployment_group:
  description: A single deployment group, returned for all successful lookups (by C(stack_deployment_group_id) or by C(stack_configuration_id) and C(name)).
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the deployment group.
      returned: always
      type: str
      sample: "sdg-xyz789"
    name:
      description: The deployment name.
      returned: always
      type: str
      sample: "dev"
    status:
      description: >
        The current status of the deployment group.
        One of C(pending), C(deploying), C(succeeded), C(failed), C(abandoned).
      returned: always
      type: str
      sample: "deploying"
    created_at:
      description: Timestamp when the deployment group was created (ISO 8601).
      returned: always
      type: str
      sample: "2026-07-02T09:40:00+00:00"
    updated_at:
      description: Timestamp when the deployment group was last updated (ISO 8601).
      returned: always
      type: str
      sample: "2026-07-02T09:41:00+00:00"
    stack_configuration:
      description: The parent stack configuration, included when the API response contains relationship data.
      returned: when present
      type: dict
      contains:
        id:
          description: The stack configuration identifier.
          returned: always
          type: str
          sample: "stc-abc123"
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_deployment_group import (
    get_stack_deployment_group,
    get_stack_deployment_group_by_name,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "stack_deployment_group_id": {"type": "str"},
            "stack_configuration_id": {"type": "str"},
            "name": {"type": "str"},
        },
        required_one_of=[("stack_deployment_group_id", "name")],
        required_by={"name": ("stack_configuration_id",)},
        mutually_exclusive=[
            ("stack_deployment_group_id", "stack_configuration_id"),
            ("stack_deployment_group_id", "name"),
        ],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("stack_deployment_group_id"):
                group = get_stack_deployment_group(adapter, params["stack_deployment_group_id"])
                if not group:
                    raise ValueError(f"Stack deployment group with ID {params['stack_deployment_group_id']!r} not found")
                result["stack_deployment_group"] = group

            else:
                group = get_stack_deployment_group_by_name(
                    adapter,
                    params["stack_configuration_id"],
                    params["name"],
                )
                if not group:
                    raise ValueError(f"Stack deployment group {params['name']!r} was not found in" f" stack configuration {params['stack_configuration_id']!r}")
                result["stack_deployment_group"] = group

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
