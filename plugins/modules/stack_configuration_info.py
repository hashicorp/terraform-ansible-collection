#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: stack_configuration_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform stack configuration.
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Retrieves information about a single stack configuration on HCP Terraform or
    Terraform Enterprise by its ID.
  - This module only reads information and never changes state.
  - Compatible with both HCP Terraform and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  stack_configuration_id:
    description:
      - The unique identifier of the stack configuration (e.g. C(stc-abc123)).
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve a stack configuration by ID
  hashicorp.terraform.stack_configuration_info:
    stack_configuration_id: "stc-abc123"
  register: stack_configuration_info

- name: Print the status
  ansible.builtin.debug:
    msg: "Status: {{ stack_configuration_info.stack_configuration.status }}"
"""

RETURN = r"""
stack_configuration:
  description: The stack configuration matching the given ID.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the stack configuration.
      returned: always
      type: str
      sample: "stc-abc123"
    status:
      description: The current status of the stack configuration.
      returned: always
      type: str
      sample: "completed"
    sequence_number:
      description: The sequential number of this configuration for the stack.
      returned: always
      type: int
      sample: 3
    speculative:
      description: Whether this is a speculative (plan-only) configuration.
      returned: always
      type: bool
      sample: false
    created_at:
      description: ISO-8601 timestamp when the configuration was created.
      returned: always
      type: str
      sample: "2025-01-01T00:00:00+00:00"
    updated_at:
      description: ISO-8601 timestamp when the configuration was last updated.
      returned: always
      type: str
      sample: "2025-01-01T00:00:01+00:00"
"""

from copy import deepcopy
from typing import Any, Dict, List

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_configuration import (
    get_stack_configuration,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "stack_configuration_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: List[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            stack_configuration = get_stack_configuration(adapter, params["stack_configuration_id"])
            if not stack_configuration:
                raise ValueError(f"Stack configuration with ID {params['stack_configuration_id']!r} not found.")
            result["stack_configuration"] = stack_configuration
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
