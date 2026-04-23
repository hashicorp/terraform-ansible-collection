#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: run_trigger
version_added: "2.0.0"
short_description: Manage Terraform Cloud/Enterprise run triggers (create, delete).
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Manages run triggers on Terraform Cloud and Terraform Enterprise.
  - A run trigger causes a run in the target workspace (C(workspace_id)/C(workspace)) whenever
    a run completes successfully in the source workspace (C(sourceable_id)/C(sourceable_workspace)).
  - Identify a trigger either directly by C(run_trigger_id), or by the combination of
    target workspace and source workspace.
  - The C(present) state creates the trigger if it does not already exist between the two workspaces.
  - The C(absent) state deletes the trigger if it exists.
  - Run triggers are immutable relationships, so there is no update path — drift is a no-op as
    long as the same source/target pair exists.
extends_documentation_fragment: hashicorp.terraform.common
options:
  run_trigger_id:
    description:
      - The unique identifier of the run trigger (e.g. C(rt-...)).
      - Use this for unambiguous delete operations.
    type: str
  workspace_id:
    description:
      - The target workspace ID (the workspace that will be triggered).
      - One of C(workspace_id) or (C(workspace) and C(organization)) is required unless
        C(run_trigger_id) is provided for delete.
    type: str
  workspace:
    description:
      - The target workspace name, used together with C(organization) to locate the workspace.
    type: str
  organization:
    description:
      - The name of the organization that owns the target (and source) workspace.
    type: str
  sourceable_id:
    description:
      - The source workspace ID. A successful run here will trigger a run in the target workspace.
      - Required when creating a trigger if C(sourceable_workspace) is not given.
    type: str
  sourceable_workspace:
    description:
      - The source workspace name, resolved within C(organization).
      - Mutually exclusive with C(sourceable_id).
    type: str
  state:
    description:
      - Desired state of the run trigger.
      - C(present) creates the trigger if missing.
      - C(absent) deletes the trigger if it exists.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a run trigger from 'networking' into 'app'
  hashicorp.terraform.run_trigger:
    organization: "my-org"
    workspace: "app"
    sourceable_workspace: "networking"
    state: present

- name: Idempotent re-run with the same source/target pair
  hashicorp.terraform.run_trigger:
    organization: "my-org"
    workspace: "app"
    sourceable_workspace: "networking"
    state: present
# "changed": false

- name: Create a run trigger via workspace IDs
  hashicorp.terraform.run_trigger:
    workspace_id: "ws-app123"
    sourceable_id: "ws-net456"
    state: present

- name: Delete a run trigger by ID
  hashicorp.terraform.run_trigger:
    run_trigger_id: "rt-abc123"
    state: absent

- name: Delete a run trigger by source/target pair
  hashicorp.terraform.run_trigger:
    organization: "my-org"
    workspace: "app"
    sourceable_workspace: "networking"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The run trigger identifier.
  returned: when state is present
  type: str
  sample: "rt-EavQ1LztoRTQHSNT"
workspace:
  description: The target workspace reference (the workspace that will be triggered).
  returned: when state is present
  type: dict
  sample: {"id": "ws-app123"}
sourceable:
  description: The source workspace reference (the workspace whose runs cause the trigger).
  returned: when state is present
  type: dict
  sample: {"id": "ws-net456"}
sourceable_name:
  description: Name of the source workspace.
  returned: when state is present
  type: str
  sample: "networking"
workspace_name:
  description: Name of the target workspace.
  returned: when state is present
  type: str
  sample: "app"
created_at:
  description: Timestamp when the run trigger was created.
  returned: when state is present
  type: str
  sample: "2025-07-03T08:10:20.479Z"
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Run trigger rt-EavQ1LztoRTQHSNT has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.run_trigger import (
    create_run_trigger,
    delete_run_trigger,
    find_run_trigger,
    get_run_trigger,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace


def _resolve_workspace_id(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[str]:
    """Return the target workspace_id, resolving by (workspace, organization) if needed."""
    if params.get("workspace_id"):
        return params["workspace_id"]
    name = params.get("workspace")
    organization = params.get("organization")
    if name and organization:
        ws = get_workspace(adapter, organization, name)
        if ws:
            return ws.get("id")
    return None


def _resolve_sourceable_id(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[str]:
    """Return the source workspace_id, resolving by name within organization if needed."""
    if params.get("sourceable_id"):
        return params["sourceable_id"]
    name = params.get("sourceable_workspace")
    organization = params.get("organization")
    if name and organization:
        ws = get_workspace(adapter, organization, name)
        if ws:
            return ws.get("id")
    return None


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create the run trigger if it does not already exist."""
    workspace_id = _resolve_workspace_id(adapter, params)
    if not workspace_id:
        raise ValueError("Unable to resolve target workspace: provide 'workspace_id' or both 'workspace' and 'organization'.")

    sourceable_id = _resolve_sourceable_id(adapter, params)
    if not sourceable_id:
        raise ValueError("Unable to resolve source workspace: provide 'sourceable_id' or both 'sourceable_workspace' and 'organization'.")

    existing = find_run_trigger(adapter, workspace_id, sourceable_id)
    if existing is not None:
        return {"changed": False, **existing}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Run trigger from {sourceable_id} to {workspace_id} would be created. Skipped creation due to check mode.",
        }

    created = create_run_trigger(adapter, workspace_id, sourceable_id)
    return {"changed": True, **created}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the run trigger if it exists; no-op otherwise."""
    run_trigger_id = params.get("run_trigger_id")

    if not run_trigger_id:
        workspace_id = _resolve_workspace_id(adapter, params)
        if not workspace_id:
            return {"changed": False, "msg": "Target workspace not found; run trigger is already absent."}
        sourceable_id = _resolve_sourceable_id(adapter, params)
        if not sourceable_id:
            return {"changed": False, "msg": "Source workspace not found; run trigger is already absent."}
        existing = find_run_trigger(adapter, workspace_id, sourceable_id)
        if existing is None:
            return {"changed": False, "msg": "Run trigger is already absent."}
        run_trigger_id = existing["id"]
    else:
        if get_run_trigger(adapter, run_trigger_id) is None:
            return {"changed": False, "msg": "Run trigger is already absent."}

    if check_mode:
        return {"changed": True, "msg": f"Run trigger {run_trigger_id} would be deleted. Skipped deletion due to check mode."}

    delete_run_trigger(adapter, run_trigger_id)
    return {"changed": True, "msg": f"Run trigger {run_trigger_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "run_trigger_id": {"type": "str"},
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
            "sourceable_id": {"type": "str"},
            "sourceable_workspace": {"type": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_together=[["workspace", "organization"]],
        mutually_exclusive=[
            ("workspace_id", "workspace"),
            ("sourceable_id", "sourceable_workspace"),
        ],
        required_if=[
            ("state", "present", ("workspace_id", "workspace"), True),
            ("state", "present", ("sourceable_id", "sourceable_workspace"), True),
        ],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    action_result: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            if params["state"] == "present":
                action_result = state_present(adapter, params, params["check_mode"])
            elif params["state"] == "absent":
                action_result = state_absent(adapter, params, params["check_mode"])

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
