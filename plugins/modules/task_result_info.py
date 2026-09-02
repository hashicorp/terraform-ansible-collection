#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: task_result_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise task result.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves information about a single run task result on Terraform Cloud and Terraform Enterprise.
  - A task result is the outcome recorded for a run task within a task stage of a run.
  - Look up a task result by C(task_result_id). Task result IDs can be discovered via
    M(hashicorp.terraform.task_stage_info) with C(include=task_results).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  task_result_id:
    description:
      - The unique identifier of the task result (e.g. C(taskrs-...)).
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Get a task result by ID
  hashicorp.terraform.task_result_info:
    task_result_id: "taskrs-abc123"
  register: task_result
"""

RETURN = r"""
task_result:
  description: The task result.
  returned: on success
  type: dict
  contains:
    id:
      description: The task result identifier.
      type: str
      sample: "taskrs-abc123"
    status:
      description: The current status of the task result.
      type: str
      sample: "passed"
    message:
      description: A short message describing the status of the task result.
      type: str
      sample: "4 passed, 0 skipped, 0 failed"
    url:
      description: A URL where users can obtain more information about the task result.
      type: str
    task_name:
      description: The name of the run task that produced the result.
      type: str
    workspace_task_enforcement_level:
      description: The enforcement level of the run task on the workspace.
      type: str
      sample: "advisory"
"""

from copy import deepcopy
from typing import Any, Dict, List

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.task_result import get_task_result


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "task_result_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: List[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            task_result = get_task_result(adapter, params["task_result_id"])
            if not task_result:
                raise ValueError(f"Task result with ID {params['task_result_id']} not found")
            result["task_result"] = task_result

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
