#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: policy_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise policy.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves a policy by its unique ID.
  - Lists policies in an organization when O(organization) is provided without O(name).
  - Searches for a policy by name when O(organization) and O(name) are provided.
  - Fails if a requested policy does not exist.
extends_documentation_fragment: hashicorp.terraform.common
options:
  policy_id:
    description:
      - The unique identifier of the policy to retrieve.
      - Mutually exclusive with O(organization) and O(name).
    type: str
  organization:
    description:
      - The organization whose policies should be listed or searched.
      - Required when O(policy_id) is not provided.
      - Mutually exclusive with O(policy_id).
    type: str
  name:
    description:
      - Policy name to search for within O(organization).
      - Requires O(organization).
      - Mutually exclusive with O(policy_id).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve a policy by ID
  hashicorp.terraform.policy_info:
    policy_id: "pol-EavQ1LztoRTQHSNT"
  register: policy_info

- name: Search for a policy by organization and name
  hashicorp.terraform.policy_info:
    organization: "my-org"
    name: "restrict-instance-type"
  register: policy_info

- name: List policies in an organization
  hashicorp.terraform.policy_info:
    organization: "my-org"
  register: policy_list
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
policy:
  description: A dictionary containing the policy information.
  returned: when O(policy_id) or O(name) is provided
  type: dict
  contains:
    id:
      description: The unique identifier of the policy.
      type: str
      sample: "pol-EavQ1LztoRTQHSNT"
    name:
      description: The policy name.
      type: str
    kind:
      description: The policy engine.
      type: str
    enforcement_level:
      description: The policy's enforcement level.
      type: str
    policy_set_count:
      description: The number of policy sets this policy belongs to.
      type: int
policies:
  description: A list of policies matching the query.
  returned: when O(organization) is provided
  type: list
  elements: dict
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy import get_policy, get_policy_by_name, list_policies


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "policy_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
        },
        required_one_of=[("policy_id", "organization")],
        required_by={"name": ("organization",)},
        mutually_exclusive=[("policy_id", "organization"), ("policy_id", "name")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("policy_id"):
                policy = get_policy(adapter, params["policy_id"])
                if not policy:
                    raise ValueError(f"Policy with ID {params['policy_id']} not found")
                result["policy"] = policy
            elif params.get("name"):
                policy = get_policy_by_name(adapter, params["organization"], params["name"])
                if not policy:
                    raise ValueError(f"Policy {params['name']!r} was not found in organization {params['organization']!r}")
                result["policy"] = policy
                result["policies"] = [policy]
            else:
                result["policies"] = list_policies(adapter, params["organization"])

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
