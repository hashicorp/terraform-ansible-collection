#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: team_workspace_access
version_added: "2.1.0"
short_description: Manage team access grants on a Terraform Cloud/Enterprise workspace.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Grant, update, or revoke a team's access to a Terraform Cloud or Terraform Enterprise workspace.
  - When I(state=present) and no grant exists, the module creates one.
  - When I(state=present) and a grant already exists, the module updates it if any permission
    field differs; otherwise it is a no-op.
  - When I(state=absent), the module removes the grant if it exists; otherwise it is a no-op.
  - Identify the grant by I(team_workspace_access_id) or by the combination of
    I(team_id) and I(workspace_id).
  - The C(custom) access type allows fine-grained control over individual permission fields
    (I(runs), I(variables), I(state_versions), I(sentinel_mocks), I(workspace_locking),
    I(run_tasks), I(policy_overrides)).  These fields are only meaningful when
    I(access=custom); supplying them with any other access type will cause the module to fail.
extends_documentation_fragment: hashicorp.terraform.common
options:
  state:
    description:
      - Desired state of the team-workspace access grant.
      - C(present) creates or updates the grant.
      - C(absent) removes the grant if it exists.
    type: str
    choices: ["present", "absent"]
    default: present
  team_workspace_access_id:
    description:
      - The unique identifier of an existing team-workspace access grant (e.g. C(tws-...)).
      - When provided, the module reads or deletes the grant directly without resolving
        I(team_id) and I(workspace_id).
      - Required for C(state=absent) when I(team_id)/I(workspace_id) are not given.
    type: str
  team_id:
    description:
      - The ID of the team whose access grant is being managed (e.g. C(team-...)).
      - Required for C(state=present) unless I(team_workspace_access_id) is given.
      - Used together with I(workspace_id) to locate an existing grant.
    type: str
  workspace_id:
    description:
      - The ID of the workspace the access grant belongs to (e.g. C(ws-...)).
      - Required for C(state=present) unless I(team_workspace_access_id) is given.
      - Used together with I(team_id) to locate an existing grant.
    type: str
  access:
    description:
      - The access level to grant.
      - C(read) — read-only access to the workspace.
      - C(plan) — can queue plans but not apply.
      - C(write) — can apply runs.
      - C(admin) — full workspace administration.
      - C(custom) — fine-grained permissions set via I(runs), I(variables),
        I(state_versions), I(sentinel_mocks), I(workspace_locking), I(run_tasks),
        and I(policy_overrides).
      - Required for C(state=present).
    type: str
    choices: ["read", "plan", "write", "admin", "custom"]
  runs:
    description:
      - Permission for managing runs. Only meaningful when I(access=custom).
      - C(read) — can view runs.
      - C(plan) — can queue plans.
      - C(apply) — can apply runs.
    type: str
    choices: ["read", "plan", "apply"]
  variables:
    description:
      - Permission for workspace variables. Only meaningful when I(access=custom).
    type: str
    choices: ["none", "read", "write"]
  state_versions:
    description:
      - Permission for state versions. Only meaningful when I(access=custom).
    type: str
    choices: ["none", "read-outputs", "read", "write"]
  sentinel_mocks:
    description:
      - Permission to download Sentinel mock data. Only meaningful when I(access=custom).
    type: str
    choices: ["none", "read"]
  workspace_locking:
    description:
      - Whether the team can manually lock and unlock the workspace.
      - Only meaningful when I(access=custom).
    type: bool
  run_tasks:
    description:
      - Whether the team can manage run tasks. Only meaningful when I(access=custom).
    type: bool
  policy_overrides:
    description:
      - Whether the team can override Sentinel policy failures. Only meaningful when I(access=custom).
    type: bool
"""

EXAMPLES = r"""
- name: Grant a team read access to a workspace
  hashicorp.terraform.team_workspace_access:
    team_id: "team-abc123"
    workspace_id: "ws-xyz789"
    access: read
    state: present
  register: result

# Task output:
# {
#   "changed": true,
#   "id": "tws-abc123",
#   "access": "read",
#   "team_id": "team-abc123",
#   "workspace_id": "ws-xyz789"
# }

- name: Idempotent re-run — no change when access is already read
  hashicorp.terraform.team_workspace_access:
    team_id: "team-abc123"
    workspace_id: "ws-xyz789"
    access: read
    state: present
  register: result_idem
# result_idem.changed == false AND result_idem.id is defined

- name: Upgrade the team to write access
  hashicorp.terraform.team_workspace_access:
    team_id: "team-abc123"
    workspace_id: "ws-xyz789"
    access: write
    state: present

- name: Grant custom access with fine-grained permissions
  hashicorp.terraform.team_workspace_access:
    team_id: "team-abc123"
    workspace_id: "ws-xyz789"
    access: custom
    runs: apply
    variables: write
    state_versions: read-outputs
    sentinel_mocks: none
    workspace_locking: true
    run_tasks: false
    policy_overrides: false
    state: present

- name: Revoke team access by team and workspace IDs
  hashicorp.terraform.team_workspace_access:
    team_id: "team-abc123"
    workspace_id: "ws-xyz789"
    state: absent

- name: Revoke team access directly by grant ID
  hashicorp.terraform.team_workspace_access:
    team_workspace_access_id: "tws-abc123"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The team-workspace access grant identifier.
  returned: when state is present and not check mode
  type: str
  sample: "tws-EavQ1LztoRTQHSNT"
access:
  description: The effective access level of the grant.
  returned: when state is present and not check mode
  type: str
  sample: "write"
runs:
  description: Runs permission (custom access only).
  returned: when access is custom and state is present
  type: str
  sample: "apply"
variables:
  description: Variables permission (custom access only).
  returned: when access is custom and state is present
  type: str
  sample: "write"
state_versions:
  description: State versions permission (custom access only).
  returned: when access is custom and state is present
  type: str
  sample: "read-outputs"
sentinel_mocks:
  description: Sentinel mocks permission (custom access only).
  returned: when access is custom and state is present
  type: str
  sample: "none"
workspace_locking:
  description: Whether the team can manually lock and unlock the workspace (custom access only).
  returned: when access is custom and state is present
  type: bool
  sample: true
run_tasks:
  description: Whether the team can manage run tasks (custom access only).
  returned: when access is custom and state is present
  type: bool
  sample: false
policy_overrides:
  description: Whether the team can override Sentinel policy failures (custom access only).
  returned: when access is custom and state is present
  type: bool
  sample: false
team_id:
  description: The team identifier.
  returned: when state is present and not check mode
  type: str
  sample: "team-abc123"
workspace_id:
  description: The workspace identifier.
  returned: when state is present and not check mode
  type: str
  sample: "ws-xyz789"
msg:
  description: Human-readable status message for no-op, absent, and check mode results.
  returned: when relevant
  type: str
  sample: "Team access grant tws-abc123 removed successfully."
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.team_workspace_access import (
    add_team_workspace_access,
    get_team_workspace_access,
    get_team_workspace_access_by_id,
    remove_team_workspace_access,
    update_team_workspace_access,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff

# Permission fields that are only valid when access=custom.
_CUSTOM_FIELDS = frozenset(["runs", "variables", "state_versions", "sentinel_mocks", "workspace_locking", "run_tasks", "policy_overrides"])


def _build_desired(params: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only the permission fields that were explicitly set by the user."""
    desired: Dict[str, Any] = {"access": params["access"]}
    for field in _CUSTOM_FIELDS:
        if params.get(field) is not None:
            desired[field] = params[field]
    return desired


def _has_diff(existing: Dict[str, Any], desired: Dict[str, Any]) -> bool:
    """Return True if any desired field differs from the current grant."""
    existing_subset = {k: existing.get(k) for k in desired}
    return bool(dict_diff(existing_subset, desired))


def state_present(
    adapter: TerraformClient,
    params: Dict[str, Any],
    existing: Optional[Dict[str, Any]],
    check_mode: bool = False,
) -> Dict[str, Any]:
    """Create or update the team-workspace access grant.

    Args:
        adapter: Authenticated TerraformClient.
        params: Module params dict.
        existing: Current grant dict, or None if absent.
        check_mode: When True, skip API mutations.

    Returns:
        Module result dict with ``changed`` key.
    """
    desired = _build_desired(params)

    if existing is None:
        # Grant does not exist — create it.
        if not (params.get("team_id") and params.get("workspace_id")):
            raise ValueError(
                f"Team-workspace access grant '{params.get('team_workspace_access_id')}' was not found. "
                "To create a new grant, provide both 'team_id' and 'workspace_id'."
            )
        if check_mode:
            return {
                "changed": True,
                "msg": (
                    f"Team access for team {params.get('team_id')} on workspace " f"{params.get('workspace_id')} would be created. Skipped due to check mode."
                ),
            }
        add_options = dict(desired)
        add_options["team_id"] = params["team_id"]
        add_options["workspace_id"] = params["workspace_id"]
        created = add_team_workspace_access(adapter, add_options)
        return {"changed": True, **created}

    # Grant exists — update if there is a diff.
    if not _has_diff(existing, desired):
        return {"changed": False, **existing}

    if check_mode:
        return {
            "changed": True,
            "msg": (f"Team access grant {existing['id']} would be updated. Skipped due to check mode."),
        }

    updated = update_team_workspace_access(adapter, existing["id"], desired)
    return {"changed": True, **updated}


def state_absent(
    adapter: TerraformClient,
    params: Dict[str, Any],
    existing: Optional[Dict[str, Any]],
    check_mode: bool = False,
) -> Dict[str, Any]:
    """Remove the team-workspace access grant if it exists.

    Args:
        adapter: Authenticated TerraformClient.
        params: Module params dict.
        existing: Current grant dict, or None if absent.
        check_mode: When True, skip API mutations.

    Returns:
        Module result dict with ``changed`` key.
    """
    if existing is None:
        twa_id = params.get("team_workspace_access_id", "unknown")
        return {"changed": False, "msg": f"Team access grant {twa_id} was not found."}

    twa_id = existing["id"]

    if check_mode:
        return {"changed": True, "msg": f"Team access grant {twa_id} would be removed. Skipped due to check mode."}

    remove_team_workspace_access(adapter, twa_id)
    return {"changed": True, "msg": f"Team access grant {twa_id} removed successfully."}


def _resolve_existing(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Locate the current grant from either a direct ID or team+workspace IDs."""
    twa_id = params.get("team_workspace_access_id")
    if twa_id:
        return get_team_workspace_access_by_id(adapter, twa_id)
    return get_team_workspace_access(adapter, params["workspace_id"], params["team_id"])


def main() -> None:
    argument_spec = {
        "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        "team_workspace_access_id": {"type": "str"},
        "team_id": {"type": "str"},
        "workspace_id": {"type": "str"},
        "access": {
            "type": "str",
            "choices": ["read", "plan", "write", "admin", "custom"],
        },
        "runs": {"type": "str", "choices": ["read", "plan", "apply"]},
        "variables": {"type": "str", "choices": ["none", "read", "write"]},
        "state_versions": {"type": "str", "choices": ["none", "read-outputs", "read", "write"]},
        "sentinel_mocks": {"type": "str", "choices": ["none", "read"]},
        "workspace_locking": {"type": "bool"},
        "run_tasks": {"type": "bool"},
        "policy_overrides": {"type": "bool"},
    }

    module = AnsibleTerraformModule(
        argument_spec=argument_spec,
        required_if=[
            # For present, user must provide access + identification
            ("state", "present", ("team_workspace_access_id", "team_id"), True),
            ("state", "present", ("team_workspace_access_id", "workspace_id"), True),
            ("state", "present", ("access",)),
        ],
        supports_check_mode=True,
    )

    params: Dict[str, Any] = deepcopy(module.params)

    # Validate: custom-only fields must not be set when access != custom
    if params.get("access") and params["access"] != "custom":
        for field in _CUSTOM_FIELDS:
            if params.get(field) is not None:
                module.fail_json(msg=(f"Parameter '{field}' is only valid when access='custom'. " f"Current access='{params['access']}'."))

    result: Dict[str, Any] = {"changed": False}

    try:
        with module.client() as adapter:
            existing = _resolve_existing(adapter, params)

            if params["state"] == "present":
                action_result = state_present(adapter, params, existing, check_mode=module.check_mode)
            else:
                action_result = state_absent(adapter, params, existing, check_mode=module.check_mode)

            result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
