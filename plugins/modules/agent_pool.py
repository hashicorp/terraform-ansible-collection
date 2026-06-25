#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: agent_pool
version_added: "2.1.0"
short_description: Manage Terraform Cloud/Enterprise agent pools (create, update, delete).
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Manages organization-scoped agent pools on Terraform Cloud and Terraform Enterprise.
  - Agent pools group Terraform Cloud Agents so that C(execution_mode=agent) workspaces and projects
    can run plans and applies on private, self-hosted infrastructure.
  - Identify a pool either directly by C(agent_pool_id), or by the combination of C(organization) and C(name).
  - The C(present) state creates the pool if it does not exist, or updates it when the desired
    configuration drifts.
  - The C(absent) state deletes the pool if it exists.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  agent_pool_id:
    description:
      - The unique identifier of the agent pool (e.g. C(apool-...)).
      - Provide for unambiguous update or delete operations.
      - When given together with C(name), the pool is looked up by ID and C(name) is treated as the desired (possibly new) name.
    type: str
  organization:
    description:
      - The name of the organization that owns the agent pool.
      - Required unless C(agent_pool_id) is provided.
    type: str
  name:
    description:
      - Human-readable name of the agent pool.
      - Required when identifying the pool by (organization, name), and when creating a new pool.
    type: str
  organization_scoped:
    description:
      - Whether the agent pool is available to every workspace in the organization.
      - When C(false), restrict access using O(allowed_workspace_ids) and/or O(allowed_project_ids).
    type: bool
  allowed_workspace_ids:
    description:
      - Workspace IDs allowed to use this agent pool when O(organization_scoped=false).
    type: list
    elements: str
  excluded_workspace_ids:
    description:
      - Workspace IDs explicitly excluded from using this agent pool.
    type: list
    elements: str
  allowed_project_ids:
    description:
      - Project IDs allowed to use this agent pool when O(organization_scoped=false).
    type: list
    elements: str
  state:
    description:
      - Desired state of the agent pool.
      - C(present) creates or updates; C(absent) deletes.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create an organization-scoped agent pool
  hashicorp.terraform.agent_pool:
    organization: "my-org"
    name: "builders"
    organization_scoped: true
    state: present
  register: pool

- name: Idempotent re-run with the same configuration
  hashicorp.terraform.agent_pool:
    organization: "my-org"
    name: "builders"
    organization_scoped: true
    state: present
# "changed": false

- name: Restrict an agent pool to specific workspaces
  hashicorp.terraform.agent_pool:
    organization: "my-org"
    name: "builders"
    organization_scoped: false
    allowed_workspace_ids:
      - "ws-abc123"
      - "ws-def456"
    state: present

- name: Rename an agent pool by ID
  hashicorp.terraform.agent_pool:
    agent_pool_id: "apool-abc123"
    name: "builders-renamed"
    state: present

- name: Delete an agent pool by name
  hashicorp.terraform.agent_pool:
    organization: "my-org"
    name: "builders-renamed"
    state: absent

- name: Delete an agent pool by ID
  hashicorp.terraform.agent_pool:
    agent_pool_id: "apool-abc123"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The agent pool identifier.
  returned: when state is present
  type: str
  sample: "apool-yoGmEFwGwL31Gee1"
name:
  description: The agent pool name.
  returned: when state is present
  type: str
  sample: "builders"
organization_scoped:
  description: Whether the pool is available to every workspace in the organization.
  returned: when state is present
  type: bool
  sample: true
agent_count:
  description: The number of agents currently registered with the pool.
  returned: when state is present
  type: int
  sample: 0
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Agent pool apool-yoGmEFwGwL31Gee1 has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.agent_pool import (
    create_agent_pool,
    delete_agent_pool,
    get_agent_pool,
    get_agent_pool_by_name,
    update_agent_pool,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient

_SCOPING_KEYS = ("allowed_workspace_ids", "excluded_workspace_ids", "allowed_project_ids")
# Maps a desired scoping option to the corresponding list of objects returned by the read model.
_SCOPING_READ_KEYS = {
    "allowed_workspace_ids": "allowed_workspaces",
    "excluded_workspace_ids": "excluded_workspaces",
    "allowed_project_ids": "allowed_projects",
}


def _fetch_agent_pool(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target agent pool by ID or by (organization, name)."""
    agent_pool_id = params.get("agent_pool_id")
    if agent_pool_id:
        return get_agent_pool(adapter, agent_pool_id)
    organization = params.get("organization")
    name = params.get("name")
    if organization and name:
        return get_agent_pool_by_name(adapter, organization, name)
    return None


def _desired_payload(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build the create/update payload from the user-supplied (non-None) params."""
    data: Dict[str, Any] = {}
    if params.get("name") is not None:
        data["name"] = params["name"]
    if params.get("organization_scoped") is not None:
        data["organization_scoped"] = params["organization_scoped"]
    for key in _SCOPING_KEYS:
        if params.get(key) is not None:
            data[key] = params[key]
    return data


def _current_ids(current: Dict[str, Any], read_key: str) -> List[str]:
    """Extract the list of IDs from a read-model relationship list (e.g. allowed_workspaces)."""
    return sorted(item.get("id") for item in current.get(read_key, []) if item.get("id"))


def _has_drift(params: Dict[str, Any], current: Dict[str, Any]) -> bool:
    """Return True if any user-specified field differs from the current pool."""
    if params.get("name") is not None and params["name"] != current.get("name"):
        return True
    if params.get("organization_scoped") is not None and params["organization_scoped"] != current.get("organization_scoped"):
        return True
    for key in _SCOPING_KEYS:
        if params.get(key) is not None and sorted(params[key]) != _current_ids(current, _SCOPING_READ_KEYS[key]):
            return True
    return False


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update an agent pool to match the desired state."""
    current = _fetch_agent_pool(adapter, params)
    name = params.get("name")

    if current is None:
        if not params.get("organization"):
            raise ValueError("'organization' is required when creating a new agent pool.")
        if not name:
            raise ValueError("'name' is required when creating a new agent pool.")
        if check_mode:
            return {
                "changed": True,
                "msg": f"Agent pool {name} would be created. Skipped creation due to check mode.",
                "name": name,
            }
        created = create_agent_pool(adapter, params["organization"], _desired_payload(params))
        return {"changed": True, **created}

    if _has_drift(params, current):
        if check_mode:
            return {
                "changed": True,
                "msg": f"Agent pool {current.get('id')} would be updated. Skipped update due to check mode.",
                "name": name or current.get("name"),
            }
        updated = update_agent_pool(adapter, current["id"], _desired_payload(params))
        return {"changed": True, **updated}

    return {"changed": False, **current}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the agent pool if present; no-op otherwise."""
    current = _fetch_agent_pool(adapter, params)
    if current is None:
        return {"changed": False, "msg": "Agent pool is already absent."}

    agent_pool_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"Agent pool {agent_pool_id} would be deleted. Skipped deletion due to check mode."}

    delete_agent_pool(adapter, agent_pool_id)
    return {"changed": True, "msg": f"Agent pool {agent_pool_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "agent_pool_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
            "organization_scoped": {"type": "bool"},
            "allowed_workspace_ids": {"type": "list", "elements": "str"},
            "excluded_workspace_ids": {"type": "list", "elements": "str"},
            "allowed_project_ids": {"type": "list", "elements": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_one_of=[("agent_pool_id", "name")],
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
