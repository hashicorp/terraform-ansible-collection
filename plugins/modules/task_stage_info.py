#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: task_stage_info
version_added: "2.2.0"
short_description: Retrieve information about Terraform Cloud/Enterprise task stages.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves information about run task stages on Terraform Cloud and Terraform Enterprise.
  - A task stage represents the run tasks and policy evaluations that execute at a particular
    point (stage) of a run, such as C(pre_plan) or C(post_plan).
  - Look up a single task stage by C(task_stage_id), or list every task stage for a run with C(run_id).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  task_stage_id:
    description:
      - The unique identifier of the task stage (e.g. C(ts-...)).
      - Mutually exclusive with C(run_id).
    type: str
  run_id:
    description:
      - The unique identifier of the run (e.g. C(run-...)) whose task stages should be listed.
      - Mutually exclusive with C(task_stage_id).
    type: str
  include:
    description:
      - Related resources to sideload when reading a single task stage by C(task_stage_id).
      - Has no effect when listing task stages by C(run_id).
    type: list
    elements: str
    choices:
      - run
      - run.workspace
      - task_results
      - policy_evaluations
"""

EXAMPLES = r"""
- name: List all task stages for a run
  hashicorp.terraform.task_stage_info:
    run_id: "run-abc123"
  register: stages

- name: Get a single task stage by ID
  hashicorp.terraform.task_stage_info:
    task_stage_id: "ts-abc123"
  register: stage

- name: Get a task stage and sideload its task results
  hashicorp.terraform.task_stage_info:
    task_stage_id: "ts-abc123"
    include:
      - task_results
  register: stage_with_results
"""

RETURN = r"""
task_stage:
  description: A single task stage, returned when C(task_stage_id) is provided.
  returned: when O(task_stage_id) is provided
  type: dict
  contains:
    id:
      description: The task stage identifier.
      type: str
      sample: "ts-abc123"
    stage:
      description: The run stage this task stage belongs to.
      type: str
      sample: "post_plan"
    status:
      description: The current status of the task stage.
      type: str
      sample: "passed"
    task_results:
      description: The task results in this stage (populated when included or available).
      type: list
      elements: dict
    policy_evaluations:
      description: The policy evaluations in this stage.
      type: list
      elements: dict
task_stages:
  description: The list of task stages for the run, returned when C(run_id) is provided.
  returned: when O(run_id) is provided
  type: list
  elements: dict
"""

from copy import deepcopy
from typing import Any, Dict, List

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.task_stage import (
    get_task_stage,
    list_task_stages,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "task_stage_id": {"type": "str"},
            "run_id": {"type": "str"},
            "include": {
                "type": "list",
                "elements": "str",
                "choices": ["run", "run.workspace", "task_results", "policy_evaluations"],
            },
        },
        required_one_of=[("task_stage_id", "run_id")],
        mutually_exclusive=[("task_stage_id", "run_id")],
        supports_check_mode=True,
    )

    warnings: List[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("task_stage_id"):
                stage = get_task_stage(adapter, params["task_stage_id"], params.get("include"))
                if not stage:
                    raise ValueError(f"Task stage with ID {params['task_stage_id']} not found")
                result["task_stage"] = stage
            else:
                result["task_stages"] = list_task_stages(adapter, params["run_id"])

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
