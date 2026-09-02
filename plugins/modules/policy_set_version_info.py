#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: policy_set_version_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise policy set version.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves a policy set version by its unique ID.
  - There is no C(list) endpoint for this resource, so lookup is only possible by
    O(policy_set_version_id) - typically the C(id) returned by a prior
    M(hashicorp.terraform.policy_set_version) task.
  - Fails if the requested version does not exist.
extends_documentation_fragment: hashicorp.terraform.common
options:
  policy_set_version_id:
    description:
      - The unique identifier of the policy set version to retrieve.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve a policy set version by ID
  hashicorp.terraform.policy_set_version_info:
    policy_set_version_id: "polsetver-EavQ1LztoRTQHSNT"
  register: version_info
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
policy_set_version:
  description: A dictionary containing the policy set version information.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the policy set version.
      type: str
      sample: "polsetver-EavQ1LztoRTQHSNT"
    status:
      description: The version's status.
      type: str
      sample: "ready"
    error:
      description: Error detail when status is errored.
      type: str
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set_version import get_policy_set_version


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "policy_set_version_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            version = get_policy_set_version(adapter, params["policy_set_version_id"])
            if version is None:
                raise ValueError(f"Policy set version {params['policy_set_version_id']} not found")
            result["policy_set_version"] = version
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
