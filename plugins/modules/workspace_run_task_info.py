#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: workspace_run_task_info
version_added: "2.2.0"
short_description: Retrieve information about run tasks associated with a workspace.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves information about run tasks associated with a workspace on Terraform Cloud and
    Terraform Enterprise.
  - Identify the workspace by C(workspace_id) or by C(organization) plus C(workspace).
  - Look up a single association by C(workspace_run_task_id), or by the associated run task
    (C(run_task_id) or C(run_task_name)), or list every run task associated with the workspace.
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  workspace_id:
    description:
      - The ID of the workspace (e.g. C(ws-...)).
      - Required unless C(organization) and C(workspace) are provided.
    type: str
  organization:
    description:
      - The name of the organization that owns the workspace and run task.
      - Required when identifying the workspace or run task by name.
    type: str
  workspace:
    description:
      - The name of the workspace. Resolved to a workspace ID within C(organization).
      - Requires C(organization).
    type: str
  workspace_run_task_id:
    description:
      - The ID of a specific workspace run task association to look up (e.g. C(wstask-...)).
    type: str
  run_task_id:
    description:
      - The ID of an associated run task to look up (e.g. C(task-...)).
      - Mutually exclusive with C(run_task_name).
    type: str
  run_task_name:
    description:
      - The name of an associated run task to look up, resolved within C(organization).
      - Requires C(organization). Mutually exclusive with C(run_task_id).
    type: str
"""

EXAMPLES = r"""
- name: List all run tasks associated with a workspace
  hashicorp.terraform.workspace_run_task_info:
    organization: "my-org"
    workspace: "my-workspace"
  register: associations

- name: Get a specific association by run task name
  hashicorp.terraform.workspace_run_task_info:
    organization: "my-org"
    workspace: "my-workspace"
    run_task_name: "security-scan"
  register: association

- name: Get a specific association by its ID
  hashicorp.terraform.workspace_run_task_info:
    workspace_id: "ws-abc123"
    workspace_run_task_id: "wstask-abc123"
  register: association
"""

RETURN = r"""
workspace_run_task:
  description: A single association, returned when looking up by ID or by run task.
  returned: when O(workspace_run_task_id), O(run_task_id), or O(run_task_name) is provided
  type: dict
  contains:
    id:
      description: The workspace run task association identifier.
      type: str
      sample: "wstask-abc123"
    enforcement_level:
      description: The enforcement level of the run task on this workspace.
      type: str
      sample: "advisory"
    stages:
      description: The run stages at which the run task runs.
      type: list
      elements: str
workspace_run_tasks:
  description: The list of associations on the workspace, returned when no specific association is requested.
  returned: when neither a specific association nor a run task is requested
  type: list
  elements: dict
"""

from copy import deepcopy
from typing import Any, Dict, List

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.run_task import get_run_task_by_name
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace_run_task import (
    get_workspace_run_task,
    get_workspace_run_task_by_run_task,
    list_workspace_run_tasks,
)


def _resolve_workspace_id(adapter, params: Dict[str, Any]) -> str:
    workspace_id = params.get("workspace_id")
    if workspace_id:
        return workspace_id
    organization = params.get("organization")
    workspace = params.get("workspace")
    if not (organization and workspace):
        raise ValueError("Either 'workspace_id' or both 'organization' and 'workspace' are required.")
    ws = get_workspace(adapter, organization, workspace)
    if not ws:
        raise ValueError(f"Workspace '{workspace}' was not found in organization '{organization}'.")
    return ws["id"]


def _resolve_run_task_id(adapter, params: Dict[str, Any]):
    run_task_id = params.get("run_task_id")
    if run_task_id:
        return run_task_id
    run_task_name = params.get("run_task_name")
    organization = params.get("organization")
    if run_task_name:
        if not organization:
            raise ValueError("'organization' is required to resolve 'run_task_name'.")
        task = get_run_task_by_name(adapter, organization, run_task_name)
        if not task:
            raise ValueError(f"Run task '{run_task_name}' was not found in organization '{organization}'.")
        return task["id"]
    return None


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "workspace_id": {"type": "str"},
            "organization": {"type": "str"},
            "workspace": {"type": "str"},
            "workspace_run_task_id": {"type": "str"},
            "run_task_id": {"type": "str"},
            "run_task_name": {"type": "str"},
        },
        required_one_of=[("workspace_id", "workspace")],
        required_by={
            "workspace": ("organization",),
            "run_task_name": ("organization",),
        },
        mutually_exclusive=[("run_task_id", "run_task_name")],
        supports_check_mode=True,
    )

    warnings: List[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            workspace_id = _resolve_workspace_id(adapter, params)

            if params.get("workspace_run_task_id"):
                task = get_workspace_run_task(adapter, workspace_id, params["workspace_run_task_id"])
                if not task:
                    raise ValueError(f"Workspace run task with ID {params['workspace_run_task_id']} not found")
                result["workspace_run_task"] = task
            elif params.get("run_task_id") or params.get("run_task_name"):
                run_task_id = _resolve_run_task_id(adapter, params)
                task = get_workspace_run_task_by_run_task(adapter, workspace_id, run_task_id)
                if not task:
                    raise ValueError(f"Run task {run_task_id} is not associated with workspace {workspace_id}")
                result["workspace_run_task"] = task
                result["workspace_run_tasks"] = [task]
            else:
                result["workspace_run_tasks"] = list_workspace_run_tasks(adapter, workspace_id)

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
