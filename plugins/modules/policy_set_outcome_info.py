#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: policy_set_outcome_info
version_added: "2.2.0"
short_description: Retrieve OPA policy set outcomes for a Terraform Cloud/Enterprise policy evaluation.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves a policy set outcome by its unique ID.
  - Lists policy set outcomes for a policy evaluation when O(policy_evaluation_id) is provided,
    optionally filtered by O(status) and/or O(enforcement_level).
  - Documented by HashiCorp for OPA policy evaluations.
  - Fails if a requested outcome does not exist.
extends_documentation_fragment: hashicorp.terraform.common
options:
  policy_set_outcome_id:
    description:
      - The unique identifier of the policy set outcome to retrieve.
      - Mutually exclusive with O(policy_evaluation_id).
    type: str
  policy_evaluation_id:
    description:
      - The policy evaluation ID to list policy set outcomes for.
      - Mutually exclusive with O(policy_set_outcome_id).
    type: str
  status:
    description:
      - Only return outcomes with at least one result matching this status.
      - Requires O(policy_evaluation_id).
    type: str
    choices: ["passed", "failed", "errored"]
  enforcement_level:
    description:
      - Only return outcomes with at least one result matching this enforcement level.
      - Requires O(policy_evaluation_id).
    type: str
    choices: ["advisory", "mandatory"]
"""

EXAMPLES = r"""
- name: Retrieve a policy set outcome by ID
  hashicorp.terraform.policy_set_outcome_info:
    policy_set_outcome_id: "pso-EavQ1LztoRTQHSNT"
  register: outcome_info

- name: List all outcomes for a policy evaluation
  hashicorp.terraform.policy_set_outcome_info:
    policy_evaluation_id: "poleval-EavQ1LztoRTQHSNT"
  register: outcomes

- name: List only failed, mandatory outcomes
  hashicorp.terraform.policy_set_outcome_info:
    policy_evaluation_id: "poleval-EavQ1LztoRTQHSNT"
    status: failed
    enforcement_level: mandatory
  register: failed_outcomes
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
policy_set_outcome:
  description: A dictionary containing the policy set outcome information.
  returned: when O(policy_set_outcome_id) is provided
  type: dict
  contains:
    id:
      description: The unique identifier of the policy set outcome.
      type: str
      sample: "pso-EavQ1LztoRTQHSNT"
    policy_set_name:
      description: Name of the policy set this outcome belongs to.
      type: str
    overridable:
      description: Whether a mandatory failure in this outcome can be overridden.
      type: bool
    outcomes:
      description: Individual policy results within this outcome.
      type: list
      elements: dict
policy_set_outcomes:
  description: A list of policy set outcomes matching the query.
  returned: when O(policy_evaluation_id) is provided
  type: list
  elements: dict
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set_outcome import get_policy_set_outcome, list_policy_set_outcomes


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "policy_set_outcome_id": {"type": "str"},
            "policy_evaluation_id": {"type": "str"},
            "status": {"type": "str", "choices": ["passed", "failed", "errored"]},
            "enforcement_level": {"type": "str", "choices": ["advisory", "mandatory"]},
        },
        required_one_of=[("policy_set_outcome_id", "policy_evaluation_id")],
        mutually_exclusive=[("policy_set_outcome_id", "policy_evaluation_id")],
        required_by={"status": ("policy_evaluation_id",), "enforcement_level": ("policy_evaluation_id",)},
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("policy_set_outcome_id"):
                outcome = get_policy_set_outcome(adapter, params["policy_set_outcome_id"])
                if not outcome:
                    raise ValueError(f"Policy set outcome with ID {params['policy_set_outcome_id']} not found")
                result["policy_set_outcome"] = outcome
            else:
                result["policy_set_outcomes"] = list_policy_set_outcomes(
                    adapter, params["policy_evaluation_id"], status=params.get("status"), enforcement_level=params.get("enforcement_level")
                )

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
