#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: policy_set_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise policy set.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves a policy set by its unique ID.
  - Lists policy sets in an organization when O(organization) is provided without O(name).
  - Searches for a policy set by name when O(organization) and O(name) are provided.
  - Fails if a requested policy set does not exist.
extends_documentation_fragment: hashicorp.terraform.common
options:
  policy_set_id:
    description:
      - The unique identifier of the policy set to retrieve.
      - Mutually exclusive with O(organization) and O(name).
    type: str
  organization:
    description:
      - The organization whose policy sets should be listed or searched.
      - Required when O(policy_set_id) is not provided.
      - Mutually exclusive with O(policy_set_id).
    type: str
  name:
    description:
      - Policy set name to search for within O(organization).
      - Requires O(organization).
      - Mutually exclusive with O(policy_set_id).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve a policy set by ID
  hashicorp.terraform.policy_set_info:
    policy_set_id: "polset-EavQ1LztoRTQHSNT"
  register: policy_set_info

- name: Search for a policy set by organization and name
  hashicorp.terraform.policy_set_info:
    organization: "my-org"
    name: "baseline-policies"
  register: policy_set_info

- name: List policy sets in an organization
  hashicorp.terraform.policy_set_info:
    organization: "my-org"
  register: policy_set_list
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
policy_set:
  description: A dictionary containing the policy set information.
  returned: when O(policy_set_id) or O(name) is provided
  type: dict
  contains:
    id:
      description: The unique identifier of the policy set.
      type: str
      sample: "polset-EavQ1LztoRTQHSNT"
    name:
      description: The policy set name.
      type: str
    kind:
      description: The policy engine for policies in this set.
      type: str
    global:
      description: Whether this policy set applies to every workspace in the organization.
      type: bool
    policies:
      description: Policies belonging to this set.
      type: list
      elements: dict
    workspaces:
      description: Workspaces this policy set applies to.
      type: list
      elements: dict
policy_sets:
  description: A list of policy sets matching the query.
  returned: when O(organization) is provided
  type: list
  elements: dict
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set import get_policy_set, get_policy_set_by_name, list_policy_sets


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "policy_set_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
        },
        required_one_of=[("policy_set_id", "organization")],
        required_by={"name": ("organization",)},
        mutually_exclusive=[("policy_set_id", "organization"), ("policy_set_id", "name")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("policy_set_id"):
                policy_set = get_policy_set(adapter, params["policy_set_id"])
                if not policy_set:
                    raise ValueError(f"Policy set with ID {params['policy_set_id']} not found")
                result["policy_set"] = policy_set
            elif params.get("name"):
                policy_set = get_policy_set_by_name(adapter, params["organization"], params["name"])
                if not policy_set:
                    raise ValueError(f"Policy set {params['name']!r} was not found in organization {params['organization']!r}")
                result["policy_set"] = policy_set
                result["policy_sets"] = [policy_set]
            else:
                result["policy_sets"] = list_policy_sets(adapter, params["organization"])

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
