#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: stack
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise stacks (create, update, delete).
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Manages organization-scoped stacks on Terraform Cloud and Terraform Enterprise.
  - A stack is a deployable unit of infrastructure backed by a VCS repository and
    associated with a project.
  - Identify existing stacks by C(stack_id) or by C(organization) and C(name).
  - The C(present) state creates the stack if it does not exist, or updates it when
    the desired configuration drifts.
  - The C(absent) state deletes the stack if it exists.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  stack_id:
    description:
      - The unique identifier of the stack (e.g. C(st-...)).
      - Provide this for unambiguous update, delete, or read operations.
      - Mutually exclusive with C(organization) and C(name).
    type: str
  organization:
    description:
      - The name of the organization that owns the stack.
      - Required when creating a new stack, or when using C(name) to identify an existing stack.
      - Must be provided together with C(name) if stack_id is not provided.
    type: str
  name:
    description:
      - Human-readable name of the stack.
      - Required when creating a new stack, or when using C(organization) to identify an existing stack.
      - Must be provided together with C(organization) if stack_id is not provided.
    type: str
  project_id:
    description:
      - The ID of the project this stack belongs to (e.g. C(prj-...)).
      - Required when creating a new stack.
    type: str
  description:
    description:
      - An optional description of the stack.
    type: str
  vcs_repo:
    description:
      - VCS repository settings for the stack.
    type: dict
    suboptions:
      identifier:
        description:
          - The repository identifier (e.g. C(org/repo)).
        type: str
        required: true
      branch:
        description:
          - The repository branch to use.
        type: str
      oauth_token_id:
        description:
          - The OAuth token ID for VCS authentication.
        type: str
      gha_installation_id:
        description:
          - The GitHub App installation ID.
        type: str
  agent_pool_id:
    description:
      - The ID of the agent pool to use for this stack (e.g. C(apool-...)).
    type: str
  state:
    description:
      - Desired state of the stack.
      - C(present) creates or updates; C(absent) deletes.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a stack linked to a VCS repository
  hashicorp.terraform.stack:
    organization: "my-org"
    name: "app-stack"
    project_id: "prj-abc123"
    description: "Production application stack"
    vcs_repo:
      identifier: "my-org/my-repo"
      branch: "main"
      oauth_token_id: "ot-abc123"
    state: present
  register: stack

- name: Idempotent re-run with the same configuration
  hashicorp.terraform.stack:
    organization: "my-org"
    name: "app-stack"
    project_id: "prj-abc123"
    state: present
# "changed": false

- name: Update stack description
  hashicorp.terraform.stack:
    stack_id: "st-abc123"
    description: "Updated description"
    state: present

- name: Delete a stack by ID
  hashicorp.terraform.stack:
    stack_id: "st-abc123"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The stack identifier.
  returned: when state is present
  type: str
  sample: "st-yoGmEFwGwL31Gee1"
name:
  description: The stack name.
  returned: when state is present
  type: str
  sample: "app-stack"
description:
  description: The stack description.
  returned: when state is present
  type: str
  sample: "Production application stack"
vcs_repo:
  description: VCS repository configuration for the stack.
  returned: when state is present and vcs_repo is configured
  type: dict
  contains:
    identifier:
      description: The repository identifier.
      type: str
      sample: "my-org/my-repo"
    branch:
      description: The repository branch.
      type: str
      sample: "main"
    oauth_token_id:
      description: The OAuth token ID.
      type: str
      sample: "ot-abc123"
project:
  description: The project associated with this stack.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The project identifier.
      type: str
      sample: "prj-abc123"
agent_pool:
  description: The agent pool associated with this stack.
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
  sample: "Stack st-yoGmEFwGwL31Gee1 has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.stack import (
    create_stack,
    delete_stack,
    get_stack,
    get_stack_by_name,
    update_stack,
)

# Fields that are compared for drift detection (scalar)
_SCALAR_DRIFT_KEYS = ("name", "description")


def _fetch_stack(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target stack by ID or by organization/name."""
    stack_id = params.get("stack_id")
    if stack_id:
        return get_stack(adapter, stack_id)

    organization = params.get("organization")
    name = params.get("name")
    if organization and name:
        return get_stack_by_name(adapter, organization, name)

    return None


def _desired_payload(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build the create/update payload from the user-supplied (non-None) params."""
    data: Dict[str, Any] = {}
    for key in _SCALAR_DRIFT_KEYS:
        if params.get(key) is not None:
            data[key] = params[key]
    if params.get("vcs_repo") is not None:
        data["vcs_repo"] = params["vcs_repo"]
    if params.get("project_id") is not None:
        data["project"] = {"id": params["project_id"]}
    if params.get("agent_pool_id") is not None:
        data["agent_pool"] = {"id": params["agent_pool_id"]}
    return data


def _has_drift(params: Dict[str, Any], current: Dict[str, Any]) -> bool:
    """Return True if any user-specified field differs from the current stack."""
    for key in _SCALAR_DRIFT_KEYS:
        if params.get(key) is not None and params[key] != current.get(key):
            return True
    if params.get("vcs_repo") is not None:
        current_vcs = current.get("vcs_repo") or {}
        desired_vcs = params["vcs_repo"]
        if isinstance(current_vcs, dict):
            current_id = current_vcs.get("identifier")
            current_branch = current_vcs.get("branch")
        else:
            current_id = getattr(current_vcs, "identifier", None)
            current_branch = getattr(current_vcs, "branch", None)
        if desired_vcs.get("identifier") != current_id:
            return True
        if desired_vcs.get("branch") is not None and desired_vcs["branch"] != current_branch:
            return True
    if params.get("project_id") is not None:
        current_project = current.get("project") or {}
        current_prj_id = current_project.get("id") if isinstance(current_project, dict) else getattr(current_project, "id", None)
        if params["project_id"] != current_prj_id:
            return True
    if params.get("agent_pool_id") is not None:
        current_pool = current.get("agent_pool") or {}
        current_pool_id = current_pool.get("id") if isinstance(current_pool, dict) else getattr(current_pool, "id", None)
        if params["agent_pool_id"] != current_pool_id:
            return True
    return False


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update a stack to match the desired state."""
    current = _fetch_stack(adapter, params)
    name = params.get("name")

    if current is None:
        if not params.get("organization"):
            raise ValueError("'organization' is required when creating a new stack.")
        if not name:
            raise ValueError("'name' is required when creating a new stack.")
        if not params.get("project_id"):
            raise ValueError("'project_id' is required when creating a new stack.")
        if check_mode:
            return {
                "changed": True,
                "msg": f"Stack {name!r} would be created. Skipped creation due to check mode.",
                "name": name,
            }
        created = create_stack(adapter, _desired_payload(params))
        return {"changed": True, **created}

    if _has_drift(params, current):
        if check_mode:
            return {
                "changed": True,
                "msg": f"Stack {current.get('id')} would be updated. Skipped update due to check mode.",
                "name": name or current.get("name"),
            }
        updated = update_stack(adapter, current["id"], _desired_payload(params))
        return {"changed": True, **updated}

    return {"changed": False, **current}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the stack if present; no-op otherwise."""
    current = _fetch_stack(adapter, params)
    if current is None:
        return {"changed": False, "msg": "Stack is already absent."}

    stack_id = current["id"]
    if check_mode:
        return {
            "changed": True,
            "msg": f"Stack {stack_id} would be deleted. Skipped deletion due to check mode.",
        }

    delete_stack(adapter, stack_id)
    return {"changed": True, "msg": f"Stack {stack_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "stack_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
            "project_id": {"type": "str"},
            "description": {"type": "str"},
            "vcs_repo": {
                "type": "dict",
                "options": {
                    "identifier": {"type": "str", "required": True},
                    "branch": {"type": "str"},
                    "oauth_token_id": {"type": "str"},
                    "gha_installation_id": {"type": "str"},
                },
            },
            "agent_pool_id": {"type": "str"},
            "state": {
                "type": "str",
                "default": "present",
                "choices": ["present", "absent"],
            },
        },
        required_one_of=[("stack_id", "name")],
        required_together=[["organization", "name"]],
        mutually_exclusive=[("stack_id", "organization"), ("stack_id", "name")],
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
