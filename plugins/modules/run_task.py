#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: run_task
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise run tasks (create, update, delete).
author: "Sivaselvan I (@isivaselvan)"
description:
  - Manages organization-scoped run tasks on Terraform Cloud and Terraform Enterprise.
  - A run task lets Terraform Cloud call an external service during the run lifecycle
    (for example a security or policy scan) and act on the result.
  - Identify a run task either directly by C(run_task_id), or by the combination of
    C(organization) and C(name).
  - The C(present) state creates the run task if it does not exist, or updates it when the
    desired configuration drifts.
  - The C(absent) state deletes the run task if it exists.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  run_task_id:
    description:
      - The unique identifier of the run task (e.g. C(task-...)).
      - Provide for unambiguous update or delete operations.
      - When given together with C(name), the run task is looked up by ID and C(name) is
        treated as the desired (possibly new) name.
    type: str
  organization:
    description:
      - The name of the organization that owns the run task.
      - Required unless C(run_task_id) is provided.
    type: str
  name:
    description:
      - Human-readable name of the run task.
      - Required when identifying the run task by (organization, name), and when creating a
        new run task.
    type: str
  url:
    description:
      - The URL that Terraform Cloud calls to invoke the run task.
      - Required when creating a new run task.
    type: str
  category:
    description:
      - The type of run task. Only C(task) is currently supported by the API.
    type: str
    choices: ["task"]
    default: "task"
  description:
    description:
      - An optional human-readable description of the run task.
    type: str
  enabled:
    description:
      - Whether the run task is enabled. New run tasks default to enabled on the server.
    type: bool
  hmac_key:
    description:
      - An optional HMAC key used to verify the run task request signature.
      - This value is write-only; the API never returns it, so it is not used for drift
        detection. Re-runs remain idempotent on the other run task fields.
    type: str
  agent_pool_id:
    description:
      - The ID of an agent pool to run this task on (e.g. C(apool-...)), for private run tasks.
    type: str
  global_configuration:
    description:
      - Global run task settings that apply the task to every workspace in the organization.
    type: dict
    suboptions:
      enabled:
        description:
          - Whether the run task is applied globally to all workspaces.
        type: bool
      stages:
        description:
          - The run stages at which the task is enforced when applied globally.
        type: list
        elements: str
        choices: ["pre_plan", "post_plan", "pre_apply", "post_apply"]
      enforcement_level:
        description:
          - The enforcement level for the global run task.
          - C(advisory) surfaces results without blocking; C(mandatory) blocks the run on failure.
        type: str
        choices: ["advisory", "mandatory"]
  state:
    description:
      - Desired state of the run task.
      - C(present) creates or updates; C(absent) deletes.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a run task
  hashicorp.terraform.run_task:
    organization: "my-org"
    name: "security-scan"
    url: "https://example.com/run-task"
    description: "External security scan"
    enabled: true
    state: present
  register: task

- name: Idempotent re-run with the same configuration
  hashicorp.terraform.run_task:
    organization: "my-org"
    name: "security-scan"
    url: "https://example.com/run-task"
    enabled: true
    state: present

- name: Apply a run task globally at the pre-plan stage
  hashicorp.terraform.run_task:
    organization: "my-org"
    name: "security-scan"
    url: "https://example.com/run-task"
    global_configuration:
      enabled: true
      stages:
        - pre_plan
      enforcement_level: mandatory
    state: present

- name: Rename a run task by ID
  hashicorp.terraform.run_task:
    run_task_id: "task-abc123"
    name: "security-scan-renamed"
    state: present

- name: Delete a run task by name
  hashicorp.terraform.run_task:
    organization: "my-org"
    name: "security-scan-renamed"
    state: absent

- name: Delete a run task by ID
  hashicorp.terraform.run_task:
    run_task_id: "task-abc123"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The run task identifier.
  returned: when state is present
  type: str
  sample: "task-abc123"
name:
  description: The run task name.
  returned: when state is present
  type: str
  sample: "security-scan"
url:
  description: The URL Terraform Cloud calls to invoke the run task.
  returned: when state is present
  type: str
  sample: "https://example.com/run-task"
category:
  description: The run task category.
  returned: when state is present
  type: str
  sample: "task"
description:
  description: The run task description.
  returned: when state is present
  type: str
  sample: "External security scan"
enabled:
  description: Whether the run task is enabled.
  returned: when state is present
  type: bool
  sample: true
global_configuration:
  description: Global run task configuration, when set.
  returned: when state is present and global configuration is set
  type: dict
  contains:
    enabled:
      description: Whether the run task is applied globally.
      type: bool
    stages:
      description: The run stages at which the global task is enforced.
      type: list
      elements: str
    enforcement_level:
      description: The enforcement level for the global run task.
      type: str
agent_pool:
  description: The agent pool associated with the run task, when configured.
  returned: when state is present and an agent pool is configured
  type: dict
  contains:
    id:
      description: The agent pool identifier.
      type: str
      sample: "apool-abc123"
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Run task task-abc123 has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.run_task import (
    create_run_task,
    delete_run_task,
    get_run_task,
    get_run_task_by_name,
    update_run_task,
)

# Scalar fields compared for drift detection. hmac_key is intentionally excluded
# because the API never returns it (write-only)
_SCALAR_DRIFT_KEYS = ("name", "url", "category", "description", "enabled")


def _fetch_run_task(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target run task by ID or by (organization, name)."""
    run_task_id = params.get("run_task_id")
    if run_task_id:
        return get_run_task(adapter, run_task_id)
    organization = params.get("organization")
    name = params.get("name")
    if organization and name:
        return get_run_task_by_name(adapter, organization, name)
    return None


def _desired_payload(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build the create/update payload from the user-supplied (non-None) params."""
    data: Dict[str, Any] = {}
    for key in _SCALAR_DRIFT_KEYS:
        if params.get(key) is not None:
            data[key] = params[key]
    if params.get("hmac_key") is not None:
        data["hmac_key"] = params["hmac_key"]
    if params.get("global_configuration") is not None:
        data["global_configuration"] = params["global_configuration"]
    if params.get("agent_pool_id") is not None:
        data["agent_pool"] = {"id": params["agent_pool_id"]}
    return data


def _global_config_drift(desired: Dict[str, Any], current: Dict[str, Any]) -> bool:
    """Return True if the desired global_configuration differs from the current one."""
    current_gc = current.get("global_configuration") or {}
    if not isinstance(current_gc, dict):
        current_gc = {}
    if desired.get("enabled") is not None and desired["enabled"] != current_gc.get("enabled"):
        return True
    if desired.get("stages") is not None and sorted(desired["stages"]) != sorted(current_gc.get("stages") or []):
        return True
    if desired.get("enforcement_level") is not None and desired["enforcement_level"] != current_gc.get("enforcement_level"):
        return True
    return False


def _has_drift(params: Dict[str, Any], current: Dict[str, Any]) -> bool:
    """Return True if any user-specified field differs from the current run task."""
    for key in _SCALAR_DRIFT_KEYS:
        if params.get(key) is not None and params[key] != current.get(key):
            return True
    if params.get("global_configuration") is not None and _global_config_drift(params["global_configuration"], current):
        return True
    if params.get("agent_pool_id") is not None:
        current_pool = current.get("agent_pool") or {}
        current_pool_id = current_pool.get("id") if isinstance(current_pool, dict) else getattr(current_pool, "id", None)
        if params["agent_pool_id"] != current_pool_id:
            return True
    return False


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update a run task to match the desired state."""
    current = _fetch_run_task(adapter, params)
    name = params.get("name")

    if current is None:
        if not params.get("organization"):
            raise ValueError("'organization' is required when creating a new run task.")
        if not name:
            raise ValueError("'name' is required when creating a new run task.")
        if not params.get("url"):
            raise ValueError("'url' is required when creating a new run task.")
        if check_mode:
            return {
                "changed": True,
                "msg": f"Run task {name!r} would be created. Skipped creation due to check mode.",
                "name": name,
            }
        created = create_run_task(adapter, params["organization"], _desired_payload(params))
        return {"changed": True, **created}

    if _has_drift(params, current):
        if check_mode:
            return {
                "changed": True,
                "msg": f"Run task {current.get('id')} would be updated. Skipped update due to check mode.",
                "name": name or current.get("name"),
            }
        updated = update_run_task(adapter, current["id"], _desired_payload(params))
        return {"changed": True, **updated}

    return {"changed": False, **current}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the run task if present; no-op otherwise."""
    current = _fetch_run_task(adapter, params)
    if current is None:
        return {"changed": False, "msg": "Run task is already absent."}

    run_task_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"Run task {run_task_id} would be deleted. Skipped deletion due to check mode."}

    delete_run_task(adapter, run_task_id)
    return {"changed": True, "msg": f"Run task {run_task_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "run_task_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
            "url": {"type": "str"},
            "category": {"type": "str", "default": "task", "choices": ["task"]},
            "description": {"type": "str"},
            "enabled": {"type": "bool"},
            "hmac_key": {"type": "str", "no_log": True},
            "agent_pool_id": {"type": "str"},
            "global_configuration": {
                "type": "dict",
                "options": {
                    "enabled": {"type": "bool"},
                    "stages": {
                        "type": "list",
                        "elements": "str",
                        "choices": ["pre_plan", "post_plan", "pre_apply", "post_apply"],
                    },
                    "enforcement_level": {"type": "str", "choices": ["advisory", "mandatory"]},
                },
            },
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_one_of=[("run_task_id", "name")],
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
