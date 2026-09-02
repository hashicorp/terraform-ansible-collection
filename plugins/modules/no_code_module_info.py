#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: no_code_module_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise no-code module.
author: "Nimisha Shrivastava (@nimisha-shrivastava)"
description:
  - Retrieves information about a specific no-code module on Terraform Cloud and
    Terraform Enterprise.
  - Look up a no-code module by its C(no_code_module_id).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  no_code_module_id:
    description:
      - The unique identifier of the no-code module (e.g., C(nocode-xxxxxxxx)).
      - Required.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve a no-code module
  hashicorp.terraform.no_code_module_info:
    no_code_module_id: "nocode-abc123"
  register: result

- name: Display no-code module information
  ansible.builtin.debug:
    msg: "No-code module {{ result.no_code_module.id }} enabled: {{ result.no_code_module.enabled }}"
"""

RETURN = r"""
no_code_module:
  description: The no-code module information.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the no-code module.
      returned: always
      type: str
      sample: "nocode-abc123"
    enabled:
      description: Whether no-code provisioning is enabled.
      returned: always
      type: bool
      sample: true
    version_pin:
      description: The version the no-code module is pinned to.
      returned: when set
      type: str
      sample: "1.2.3"
"""


from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.no_code_module import get_no_code_module


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "no_code_module_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            no_code_module = get_no_code_module(adapter, params["no_code_module_id"])
            if not no_code_module:
                raise ValueError(f"No-code module '{params['no_code_module_id']}' was not found")
            result["no_code_module"] = no_code_module
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
