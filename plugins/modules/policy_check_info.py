#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: policy_check_info
version_added: "2.2.0"
short_description: Retrieve Sentinel policy check outcomes for a Terraform Cloud/Enterprise run.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves a policy check by its unique ID.
  - Lists policy checks for a run when O(run_id) is provided.
  - Policy checks support Sentinel versions up to 0.40.x only. HashiCorp's own docs recommend
    M(hashicorp.terraform.policy_evaluation_info) instead for newer Sentinel versions and OPA.
  - Fails if a requested policy check does not exist.
extends_documentation_fragment: hashicorp.terraform.common
options:
  policy_check_id:
    description:
      - The unique identifier of the policy check to retrieve.
      - Mutually exclusive with O(run_id).
    type: str
  run_id:
    description:
      - The run ID to list policy checks for.
      - Mutually exclusive with O(policy_check_id).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve a policy check by ID
  hashicorp.terraform.policy_check_info:
    policy_check_id: "polchk-9VYRc9bpfJEsnwum"
  register: check_info

- name: List policy checks for a run
  hashicorp.terraform.policy_check_info:
    run_id: "run-veDoQbv6xh6TbnJD"
  register: checks
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
policy_check:
  description: A dictionary containing the policy check information.
  returned: when O(policy_check_id) is provided
  type: dict
  contains:
    id:
      description: The unique identifier of the policy check.
      type: str
      sample: "polchk-9VYRc9bpfJEsnwum"
    status:
      description: The policy check's status.
      type: str
      sample: "passed"
    scope:
      description: Whether the check ran at organization or workspace scope.
      type: str
policy_checks:
  description: A list of policy checks matching the query.
  returned: when O(run_id) is provided
  type: list
  elements: dict
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_check import get_policy_check, list_policy_checks


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "policy_check_id": {"type": "str"},
            "run_id": {"type": "str"},
        },
        required_one_of=[("policy_check_id", "run_id")],
        mutually_exclusive=[("policy_check_id", "run_id")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("policy_check_id"):
                policy_check = get_policy_check(adapter, params["policy_check_id"])
                if not policy_check:
                    raise ValueError(f"Policy check with ID {params['policy_check_id']} not found")
                result["policy_check"] = policy_check
            else:
                result["policy_checks"] = list_policy_checks(adapter, params["run_id"])

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
