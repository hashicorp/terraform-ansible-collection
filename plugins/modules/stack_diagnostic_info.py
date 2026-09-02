#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: stack_diagnostic_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise stack diagnostic.
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Retrieves information about a single stack diagnostic on Terraform Cloud and Terraform Enterprise.
  - Look up a stack diagnostic by C(stack_diagnostic_id).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  stack_diagnostic_id:
    description:
      - The unique identifier of the stack diagnostic (e.g. C(std-...)).
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve stack diagnostic
  hashicorp.terraform.stack_diagnostic_info:
    stack_diagnostic_id: "std-abc123"
  register: diagnostic
"""

RETURN = r"""
stack_diagnostic:
  description: The requested stack diagnostic.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the stack diagnostic.
      returned: always
      type: str
      sample: "std-abc123"
    severity:
      description: Diagnostic severity.
      returned: always
      type: str
      sample: "error"
    summary:
      description: Short summary of the diagnostic.
      returned: always
      type: str
      sample: "Invalid configuration"
    detail:
      description: Detailed diagnostic message.
      returned: when present
      type: str
      sample: "The stack configuration failed validation."
    diags:
      description: Additional diagnostic details.
      returned: when present
      type: raw
    acknowledged:
      description: Whether the diagnostic has been acknowledged.
      returned: when present
      type: bool
      sample: false
    acknowledged_at:
      description: Timestamp when the diagnostic was acknowledged.
      returned: when present
      type: str
      sample: "2026-07-03T10:05:00.000Z"
    created_at:
      description: Timestamp when the diagnostic was created.
      returned: when present
      type: str
      sample: "2026-07-03T10:00:00.000Z"
"""

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_diagnostic import (
    get_stack_diagnostic,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "stack_diagnostic_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    result = {"changed": False}

    try:
        with module.client() as adapter:
            stack_diagnostic = get_stack_diagnostic(adapter, module.params["stack_diagnostic_id"])
            if stack_diagnostic is None:
                module.fail_json(msg=("Stack diagnostic with ID " f"{module.params['stack_diagnostic_id']!r} not found"))

            result["stack_diagnostic"] = stack_diagnostic
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
