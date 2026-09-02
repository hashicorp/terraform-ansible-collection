#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: workspace_run_task
version_added: "2.2.0"
short_description: Associate and manage run tasks on a Terraform Cloud/Enterprise workspace.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Associates an organization-scoped run task with a specific workspace, updates the
    association, or removes it, on Terraform Cloud and Terraform Enterprise.
  - A workspace run task is the link between an existing run task (see M(hashicorp.terraform.run_task))
    and a workspace, together with the enforcement level and run stages that apply.
  - Identify the target workspace by C(workspace_id) or by C(organization) plus C(workspace).
  - Identify the run task to associate by C(run_task_id) or by C(run_task_name) (with C(organization)).
    An existing association can also be targeted directly by C(workspace_run_task_id).
  - The C(present) state creates the association if it does not exist, or updates it when the
    enforcement level or stages drift.
  - The C(absent) state removes the association if it exists.
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
      - Required when identifying the workspace by name, or the run task by name.
    type: str
  workspace:
    description:
      - The name of the workspace. Resolved to a workspace ID within C(organization).
      - Requires C(organization).
    type: str
  run_task_id:
    description:
      - The ID of the run task to associate (e.g. C(task-...)).
      - Required to create a new association unless C(run_task_name) is provided.
    type: str
  run_task_name:
    description:
      - The name of the run task to associate, resolved to an ID within C(organization).
      - Requires C(organization). Mutually exclusive with C(run_task_id).
    type: str
  workspace_run_task_id:
    description:
      - The ID of an existing workspace run task association (e.g. C(wstask-...)).
      - Provide for unambiguous update or delete of a specific association.
    type: str
  enforcement_level:
    description:
      - The enforcement level of the run task on this workspace.
      - C(advisory) surfaces results without blocking the run; C(mandatory) blocks the run on failure.
      - Required when creating a new association.
    type: str
    choices: ["advisory", "mandatory"]
  stages:
    description:
      - The run stages at which the run task runs on this workspace.
      - When omitted on create, the server default (C(post_plan)) applies.
    type: list
    elements: str
    choices: ["pre_plan", "post_plan", "pre_apply", "post_apply"]
  state:
    description:
      - Desired state of the workspace run task association.
      - C(present) creates or updates; C(absent) removes.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Associate a run task with a workspace (advisory, post-plan)
  hashicorp.terraform.workspace_run_task:
    organization: "my-org"
    workspace: "my-workspace"
    run_task_name: "security-scan"
    enforcement_level: advisory
    stages:
      - post_plan
    state: present
  register: association

- name: Idempotent re-run with the same configuration
  hashicorp.terraform.workspace_run_task:
    organization: "my-org"
    workspace: "my-workspace"
    run_task_name: "security-scan"
    enforcement_level: advisory
    stages:
      - post_plan
    state: present

- name: Make the run task mandatory using IDs
  hashicorp.terraform.workspace_run_task:
    workspace_id: "ws-abc123"
    run_task_id: "task-abc123"
    enforcement_level: mandatory
    state: present

- name: Remove a run task association by name
  hashicorp.terraform.workspace_run_task:
    organization: "my-org"
    workspace: "my-workspace"
    run_task_name: "security-scan"
    state: absent

- name: Remove a run task association by its ID
  hashicorp.terraform.workspace_run_task:
    workspace_id: "ws-abc123"
    workspace_run_task_id: "wstask-abc123"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The workspace run task association identifier.
  returned: when state is present
  type: str
  sample: "wstask-abc123"
enforcement_level:
  description: The enforcement level of the run task on this workspace.
  returned: when state is present
  type: str
  sample: "advisory"
stages:
  description: The run stages at which the run task runs.
  returned: when state is present
  type: list
  elements: str
  sample: ["post_plan"]
run_task:
  description: The associated run task.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The run task identifier.
      type: str
      sample: "task-abc123"
workspace:
  description: The workspace the run task is associated with.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The workspace identifier.
      type: str
      sample: "ws-abc123"
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Workspace run task wstask-abc123 has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.run_task import get_run_task_by_name
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace_run_task import (
    create_workspace_run_task,
    delete_workspace_run_task,
    get_workspace_run_task,
    get_workspace_run_task_by_run_task,
    update_workspace_run_task,
)


def _resolve_workspace_id(adapter: TerraformClient, params: Dict[str, Any]) -> str:
    """Return the workspace ID from workspace_id or (organization, workspace)."""
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


def _resolve_run_task_id(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[str]:
    """Return the run task ID from run_task_id or (organization, run_task_name)."""
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


def _fetch_workspace_run_task(adapter: TerraformClient, workspace_id: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the association by its ID or by the linked run task."""
    workspace_run_task_id = params.get("workspace_run_task_id")
    if workspace_run_task_id:
        return get_workspace_run_task(adapter, workspace_id, workspace_run_task_id)
    run_task_id = _resolve_run_task_id(adapter, params)
    if run_task_id:
        return get_workspace_run_task_by_run_task(adapter, workspace_id, run_task_id)
    return None


def _desired_payload(params: Dict[str, Any], run_task_id: Optional[str] = None) -> Dict[str, Any]:
    """Build the create/update payload from the user-supplied (non-None) params."""
    data: Dict[str, Any] = {}
    if params.get("enforcement_level") is not None:
        data["enforcement_level"] = params["enforcement_level"]
    if params.get("stages") is not None:
        data["stages"] = params["stages"]
    if run_task_id is not None:
        data["run_task"] = {"id": run_task_id}
    return data


def _has_drift(params: Dict[str, Any], current: Dict[str, Any]) -> bool:
    """Return True if the enforcement level or stages differ from the current association."""
    if params.get("enforcement_level") is not None and params["enforcement_level"] != current.get("enforcement_level"):
        return True
    if params.get("stages") is not None and sorted(params["stages"]) != sorted(current.get("stages") or []):
        return True
    return False


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update a workspace run task association to match the desired state."""
    workspace_id = _resolve_workspace_id(adapter, params)
    current = _fetch_workspace_run_task(adapter, workspace_id, params)

    if current is None:
        run_task_id = _resolve_run_task_id(adapter, params)
        if not run_task_id:
            raise ValueError("'run_task_id' or 'run_task_name' is required when creating a workspace run task.")
        if not params.get("enforcement_level"):
            raise ValueError("'enforcement_level' is required when creating a workspace run task.")
        if check_mode:
            return {
                "changed": True,
                "msg": "Workspace run task would be created. Skipped creation due to check mode.",
            }
        created = create_workspace_run_task(adapter, workspace_id, _desired_payload(params, run_task_id))
        return {"changed": True, **created}

    if _has_drift(params, current):
        if check_mode:
            return {
                "changed": True,
                "msg": f"Workspace run task {current.get('id')} would be updated. Skipped update due to check mode.",
            }
        updated = update_workspace_run_task(adapter, workspace_id, current["id"], _desired_payload(params))
        return {"changed": True, **updated}

    return {"changed": False, **current}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Remove the workspace run task association if present; no-op otherwise."""
    workspace_id = _resolve_workspace_id(adapter, params)
    current = _fetch_workspace_run_task(adapter, workspace_id, params)
    if current is None:
        return {"changed": False, "msg": "Workspace run task is already absent."}

    workspace_run_task_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"Workspace run task {workspace_run_task_id} would be deleted. Skipped deletion due to check mode."}

    delete_workspace_run_task(adapter, workspace_id, workspace_run_task_id)
    return {"changed": True, "msg": f"Workspace run task {workspace_run_task_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "workspace_id": {"type": "str"},
            "organization": {"type": "str"},
            "workspace": {"type": "str"},
            "run_task_id": {"type": "str"},
            "run_task_name": {"type": "str"},
            "workspace_run_task_id": {"type": "str"},
            "enforcement_level": {"type": "str", "choices": ["advisory", "mandatory"]},
            "stages": {
                "type": "list",
                "elements": "str",
                "choices": ["pre_plan", "post_plan", "pre_apply", "post_apply"],
            },
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_one_of=[("workspace_id", "workspace")],
        required_by={
            "workspace": ("organization",),
            "run_task_name": ("organization",),
        },
        mutually_exclusive=[("run_task_id", "run_task_name")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    action_result: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            match params["state"]:
                case "present":
                    action_result = state_present(adapter, params, params["check_mode"])
                case "absent":
                    action_result = state_absent(adapter, params, params["check_mode"])

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
