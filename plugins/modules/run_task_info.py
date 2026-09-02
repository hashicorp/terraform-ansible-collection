#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: run_task_info
version_added: "2.2.0"
short_description: Retrieve information about Terraform Cloud/Enterprise run tasks.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves information about run tasks on Terraform Cloud and Terraform Enterprise.
  - Look up a single run task by C(run_task_id), look one up by C(organization) plus C(name),
    or list every run task in an C(organization).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  run_task_id:
    description:
      - The unique identifier of the run task (e.g. C(task-...)).
      - Mutually exclusive with C(organization) and C(name).
    type: str
  organization:
    description:
      - The name of the organization whose run tasks should be queried.
      - Required unless C(run_task_id) is provided.
    type: str
  name:
    description:
      - Name of a specific run task to look up within C(organization).
      - Requires C(organization).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve a run task by ID
  hashicorp.terraform.run_task_info:
    run_task_id: "task-abc123"
  register: task

- name: Retrieve a run task by name
  hashicorp.terraform.run_task_info:
    organization: "my-org"
    name: "security-scan"
  register: task

- name: List all run tasks in an organization
  hashicorp.terraform.run_task_info:
    organization: "my-org"
  register: all_tasks
"""

RETURN = r"""
run_task:
  description: A single run task, returned when looking up by C(run_task_id) or by (organization, name).
  returned: when O(run_task_id) or O(name) is provided
  type: dict
  contains:
    id:
      description: The unique identifier of the run task.
      type: str
      sample: "task-abc123"
    name:
      description: The name of the run task.
      type: str
      sample: "security-scan"
    url:
      description: The URL Terraform Cloud calls to invoke the run task.
      type: str
      sample: "https://example.com/run-task"
    category:
      description: The run task category.
      type: str
      sample: "task"
    enabled:
      description: Whether the run task is enabled.
      type: bool
      sample: true
run_tasks:
  description: The list of run tasks, returned when only C(organization) is provided (or the single match by name).
  returned: when O(organization) is provided without O(run_task_id)
  type: list
  elements: dict
"""

from copy import deepcopy
from typing import Any, Dict, List

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.run_task import (
    get_run_task,
    get_run_task_by_name,
    list_run_tasks,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "run_task_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
        },
        required_one_of=[("run_task_id", "organization")],
        required_by={"name": ("organization",)},
        mutually_exclusive=[("run_task_id", "organization"), ("run_task_id", "name")],
        supports_check_mode=True,
    )

    warnings: List[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("run_task_id"):
                task = get_run_task(adapter, params["run_task_id"])
                if not task:
                    raise ValueError(f"Run task with ID {params['run_task_id']} not found")
                result["run_task"] = task
            elif params.get("name"):
                task = get_run_task_by_name(adapter, params["organization"], params["name"])
                if not task:
                    raise ValueError(f"Run task '{params['name']}' was not found in organization '{params['organization']}'")
                result["run_task"] = task
                result["run_tasks"] = [task]
            else:
                result["run_tasks"] = list_run_tasks(adapter, params["organization"])

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
