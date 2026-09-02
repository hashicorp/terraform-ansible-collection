#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: policy_evaluation_info
version_added: "2.2.0"
short_description: List OPA policy evaluations for a Terraform Cloud/Enterprise task stage.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Lists policy evaluations for a task stage. Documented by HashiCorp for OPA policies
    specifically (Sentinel results surface through
    M(hashicorp.terraform.policy_check_info) instead).
  - There is no C(list) filter and no single-evaluation read by ID in the underlying API - this
    module always returns every evaluation for the given task stage.
extends_documentation_fragment: hashicorp.terraform.common
options:
  task_stage_id:
    description:
      - The ID of the task stage to list policy evaluations for.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: List policy evaluations for a task stage
  hashicorp.terraform.policy_evaluation_info:
    task_stage_id: "ts-EavQ1LztoRTQHSNT"
  register: evaluations
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
policy_evaluations:
  description: The task stage's policy evaluations.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the policy evaluation.
      type: str
      sample: "poleval-EavQ1LztoRTQHSNT"
    status:
      description: The evaluation's status.
      type: str
      sample: "passed"
    policy_kind:
      description: The policy engine evaluated.
      type: str
      sample: "opa"
    result_count:
      description: Counts of passed/failed/errored/advisory results.
      type: dict
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_evaluation import list_policy_evaluations


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "task_stage_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            result["policy_evaluations"] = list_policy_evaluations(adapter, params["task_stage_id"])
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
