#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: policy_set_parameter_info
version_added: "2.2.0"
short_description: Retrieve information about Terraform Cloud/Enterprise policy set parameters.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves a policy set parameter by its unique ID.
  - Searches for a parameter by key within O(policy_set_id) when O(key) is provided.
  - Lists all parameters on O(policy_set_id) when neither O(parameter_id) nor O(key) is provided.
  - Fails if a requested parameter does not exist.
  - Note that sensitive parameter values are never returned by the API.
extends_documentation_fragment: hashicorp.terraform.common
options:
  policy_set_id:
    description:
      - The ID of the policy set the parameter(s) belong to.
    type: str
    required: true
  parameter_id:
    description:
      - The unique identifier of the parameter to retrieve.
      - Mutually exclusive with O(key).
    type: str
  key:
    description:
      - Parameter key to search for within O(policy_set_id).
      - Mutually exclusive with O(parameter_id).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve a policy set parameter by ID
  hashicorp.terraform.policy_set_parameter_info:
    policy_set_id: "polset-EavQ1LztoRTQHSNT"
    parameter_id: "var-EavQ1LztoRTQHSNT"
  register: parameter_info

- name: Search for a policy set parameter by key
  hashicorp.terraform.policy_set_parameter_info:
    policy_set_id: "polset-EavQ1LztoRTQHSNT"
    key: "environment"
  register: parameter_info

- name: List all parameters on a policy set
  hashicorp.terraform.policy_set_parameter_info:
    policy_set_id: "polset-EavQ1LztoRTQHSNT"
  register: parameter_list
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
parameter:
  description: A dictionary containing the parameter information.
  returned: when O(parameter_id) or O(key) is provided
  type: dict
  contains:
    id:
      description: The unique identifier of the parameter.
      type: str
      sample: "var-EavQ1LztoRTQHSNT"
    key:
      description: The parameter key.
      type: str
    value:
      description: The parameter value (omitted when sensitive).
      type: str
    sensitive:
      description: Whether the parameter value is sensitive.
      type: bool
parameters:
  description: A list of parameters matching the query.
  returned: when neither O(parameter_id) nor O(key) is provided
  type: list
  elements: dict
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set_parameter import (
    get_policy_set_parameter,
    get_policy_set_parameter_by_key,
    list_policy_set_parameters,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "policy_set_id": {"type": "str", "required": True},
            "parameter_id": {"type": "str"},
            "key": {"type": "str", "no_log": False},
        },
        mutually_exclusive=[("parameter_id", "key")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            policy_set_id = params["policy_set_id"]
            if params.get("parameter_id"):
                parameter = get_policy_set_parameter(adapter, policy_set_id, params["parameter_id"])
                if not parameter:
                    raise ValueError(f"Policy set parameter with ID {params['parameter_id']} not found")
                result["parameter"] = parameter
            elif params.get("key"):
                parameter = get_policy_set_parameter_by_key(adapter, policy_set_id, params["key"])
                if not parameter:
                    raise ValueError(f"Policy set parameter {params['key']!r} was not found on policy set {policy_set_id!r}")
                result["parameter"] = parameter
            else:
                result["parameters"] = list_policy_set_parameters(adapter, policy_set_id)

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
