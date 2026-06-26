#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: team_project_access
version_added: "2.1.0"
short_description: Manage team access grants on a Terraform Cloud/Enterprise project.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Grant, update, or revoke a team's access to a Terraform Cloud or Terraform Enterprise project.
  - When I(state=present) and no grant exists, the module creates one.
  - When I(state=present) and a grant already exists, the module updates it if any permission
    field differs; otherwise it is a no-op.
  - When I(state=absent), the module removes the grant if it exists; otherwise it is a no-op.
  - Identify the grant by I(team_project_access_id) or by the combination of
    I(team_id) and I(project_id).
  - The C(custom) access type allows fine-grained control over project-level and workspace-level
    permissions. These fields are only meaningful when I(access=custom); supplying them with any
    other access type will cause the module to fail.
extends_documentation_fragment: hashicorp.terraform.common
options:
  state:
    description:
      - Desired state of the team-project access grant.
      - C(present) creates or updates the grant.
      - C(absent) removes the grant if it exists.
    type: str
    choices: ["present", "absent"]
    default: present
  team_project_access_id:
    description:
      - The unique identifier of an existing team-project access grant (e.g. C(tpa-...)).
      - When provided, the module reads or deletes the grant directly without resolving
        I(team_id) and I(project_id).
      - Required for C(state=absent) when I(team_id)/I(project_id) are not given.
    type: str
  team_id:
    description:
      - The ID of the team whose access grant is being managed (e.g. C(team-...)).
      - Required for C(state=present) unless I(team_project_access_id) is given.
    type: str
  project_id:
    description:
      - The ID of the project the access grant belongs to (e.g. C(prj-...)).
      - Required for C(state=present) unless I(team_project_access_id) is given.
    type: str
  access:
    description:
      - The access level to grant.
      - C(read) — read-only access to the project.
      - C(write) — can create and manage workspaces in the project.
      - C(maintain) — can manage project settings (not delete).
      - C(admin) — full project administration including deletion.
      - C(custom) — fine-grained permissions via the C(project_*) and C(workspace_*) options.
      - Required for C(state=present).
    type: str
    choices: ["read", "write", "maintain", "admin", "custom"]
  project_settings:
    description:
      - Permission for project settings. Only meaningful when I(access=custom).
    type: str
    choices: ["read", "update", "delete"]
  project_teams:
    description:
      - Permission for managing teams on the project. Only meaningful when I(access=custom).
    type: str
    choices: ["none", "read", "manage"]
  project_variable_sets:
    description:
      - Permission for project-level variable sets. Only meaningful when I(access=custom).
    type: str
    choices: ["none", "read", "write"]
  workspace_runs:
    description:
      - Permission for managing runs in project workspaces. Only meaningful when I(access=custom).
    type: str
    choices: ["read", "plan", "apply"]
  workspace_sentinel_mocks:
    description:
      - Permission to download Sentinel mock data. Only meaningful when I(access=custom).
    type: str
    choices: ["none", "read"]
  workspace_state_versions:
    description:
      - Permission for state versions in project workspaces. Only meaningful when I(access=custom).
    type: str
    choices: ["none", "read-outputs", "read", "write"]
  workspace_variables:
    description:
      - Permission for variables in project workspaces. Only meaningful when I(access=custom).
    type: str
    choices: ["none", "read", "write"]
  workspace_create:
    description:
      - Whether the team can create workspaces in the project. Only meaningful when I(access=custom).
    type: bool
  workspace_delete:
    description:
      - Whether the team can delete workspaces in the project. Only meaningful when I(access=custom).
    type: bool
  workspace_locking:
    description:
      - Whether the team can manually lock and unlock workspaces. Only meaningful when I(access=custom).
    type: bool
  workspace_move:
    description:
      - Whether the team can move workspaces between projects. Only meaningful when I(access=custom).
    type: bool
  workspace_run_tasks:
    description:
      - Whether the team can manage run tasks. Only meaningful when I(access=custom).
    type: bool
"""

EXAMPLES = r"""
- name: Grant a team read access to a project
  hashicorp.terraform.team_project_access:
    team_id: "team-abc123"
    project_id: "prj-xyz789"
    access: read
    state: present
  register: result

- name: Upgrade to maintain access
  hashicorp.terraform.team_project_access:
    team_id: "team-abc123"
    project_id: "prj-xyz789"
    access: maintain
    state: present

- name: Grant custom fine-grained access
  hashicorp.terraform.team_project_access:
    team_id: "team-abc123"
    project_id: "prj-xyz789"
    access: custom
    project_settings: read
    project_teams: none
    project_variable_sets: read
    workspace_runs: apply
    workspace_variables: write
    workspace_state_versions: read-outputs
    workspace_sentinel_mocks: none
    workspace_locking: true
    workspace_create: false
    workspace_delete: false
    workspace_move: false
    workspace_run_tasks: false
    state: present

- name: Revoke team access by grant ID
  hashicorp.terraform.team_project_access:
    team_project_access_id: "tpa-abc123"
    state: absent

- name: Revoke team access by team and project IDs
  hashicorp.terraform.team_project_access:
    team_id: "team-abc123"
    project_id: "prj-xyz789"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The team-project access grant identifier.
  returned: when state is present and not check mode
  type: str
  sample: "tpa-EavQ1LztoRTQHSNT"
access:
  description: The effective access level of the grant.
  returned: when state is present and not check mode
  type: str
  sample: "maintain"
team_id:
  description: The team identifier.
  returned: when state is present and not check mode
  type: str
  sample: "team-abc123"
project_id:
  description: The project identifier.
  returned: when state is present and not check mode
  type: str
  sample: "prj-xyz789"
project_settings:
  description: Project settings permission (custom access only).
  returned: when access is custom and state is present
  type: str
  sample: "read"
project_teams:
  description: Project teams permission (custom access only).
  returned: when access is custom and state is present
  type: str
  sample: "none"
project_variable_sets:
  description: Project variable sets permission (custom access only).
  returned: when access is custom and state is present
  type: str
  sample: "read"
workspace_runs:
  description: Workspace runs permission (custom access only).
  returned: when access is custom and state is present
  type: str
  sample: "apply"
workspace_sentinel_mocks:
  description: Workspace Sentinel mocks permission (custom access only).
  returned: when access is custom and state is present
  type: str
  sample: "none"
workspace_state_versions:
  description: Workspace state versions permission (custom access only).
  returned: when access is custom and state is present
  type: str
  sample: "read-outputs"
workspace_variables:
  description: Workspace variables permission (custom access only).
  returned: when access is custom and state is present
  type: str
  sample: "write"
workspace_create:
  description: Whether the team can create workspaces (custom access only).
  returned: when access is custom and state is present
  type: bool
  sample: false
workspace_delete:
  description: Whether the team can delete workspaces (custom access only).
  returned: when access is custom and state is present
  type: bool
  sample: false
workspace_locking:
  description: Whether the team can lock workspaces (custom access only).
  returned: when access is custom and state is present
  type: bool
  sample: true
workspace_move:
  description: Whether the team can move workspaces (custom access only).
  returned: when access is custom and state is present
  type: bool
  sample: false
workspace_run_tasks:
  description: Whether the team can manage run tasks (custom access only).
  returned: when access is custom and state is present
  type: bool
  sample: false
msg:
  description: Human-readable status message for no-op, absent, and check mode results.
  returned: when relevant
  type: str
  sample: "Team access grant tpa-abc123 removed successfully."
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.team_project_access import (
    add_team_project_access,
    get_team_project_access,
    get_team_project_access_by_id,
    remove_team_project_access,
    update_team_project_access,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff

# Fields only valid when access=custom.
_PROJECT_CUSTOM_FIELDS = frozenset(["project_settings", "project_teams", "project_variable_sets"])
_WORKSPACE_CUSTOM_FIELDS = frozenset(
    [
        "workspace_runs",
        "workspace_sentinel_mocks",
        "workspace_state_versions",
        "workspace_variables",
        "workspace_create",
        "workspace_delete",
        "workspace_locking",
        "workspace_move",
        "workspace_run_tasks",
    ]
)
_CUSTOM_FIELDS = _PROJECT_CUSTOM_FIELDS | _WORKSPACE_CUSTOM_FIELDS


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
    """Create or update the team-project access grant.

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
        if not (params.get("team_id") and params.get("project_id")):
            raise ValueError(
                f"Team-project access grant '{params.get('team_project_access_id')}' was not found. "
                "To create a new grant, provide both 'team_id' and 'project_id'."
            )
        if check_mode:
            return {
                "changed": True,
                "msg": (f"Team access for team {params.get('team_id')} on project {params.get('project_id')} would be created. Skipped due to check mode."),
            }
        add_options = dict(desired)
        add_options["team_id"] = params["team_id"]
        add_options["project_id"] = params["project_id"]
        created = add_team_project_access(adapter, add_options)
        return {"changed": True, **created}

    if not _has_diff(existing, desired):
        return {"changed": False, **existing}

    if check_mode:
        return {
            "changed": True,
            "msg": (f"Team access grant {existing['id']} would be updated. Skipped due to check mode."),
        }

    updated = update_team_project_access(adapter, existing["id"], desired)
    return {"changed": True, **updated}


def state_absent(
    adapter: TerraformClient,
    params: Dict[str, Any],
    existing: Optional[Dict[str, Any]],
    check_mode: bool = False,
) -> Dict[str, Any]:
    """Remove the team-project access grant if it exists.

    Args:
        adapter: Authenticated TerraformClient.
        params: Module params dict.
        existing: Current grant dict, or None if absent.
        check_mode: When True, skip API mutations.

    Returns:
        Module result dict with ``changed`` key.
    """
    if existing is None:
        tpa_id = params.get("team_project_access_id", "unknown")
        return {"changed": False, "msg": f"Team access grant {tpa_id} was not found."}

    tpa_id = existing["id"]

    if check_mode:
        return {"changed": True, "msg": f"Team access grant {tpa_id} would be removed. Skipped due to check mode."}

    remove_team_project_access(adapter, tpa_id)
    return {"changed": True, "msg": f"Team access grant {tpa_id} removed successfully."}


def _resolve_existing(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Locate the current grant from either a direct ID or team+project IDs."""
    tpa_id = params.get("team_project_access_id")
    if tpa_id:
        return get_team_project_access_by_id(adapter, tpa_id)
    return get_team_project_access(adapter, params["project_id"], params["team_id"])


def main() -> None:
    argument_spec = {
        "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        "team_project_access_id": {"type": "str"},
        "team_id": {"type": "str"},
        "project_id": {"type": "str"},
        "access": {
            "type": "str",
            "choices": ["read", "write", "maintain", "admin", "custom"],
        },
        # Project-level custom fields
        "project_settings": {"type": "str", "choices": ["read", "update", "delete"]},
        "project_teams": {"type": "str", "choices": ["none", "read", "manage"]},
        "project_variable_sets": {"type": "str", "choices": ["none", "read", "write"]},
        # Workspace-level custom fields
        "workspace_runs": {"type": "str", "choices": ["read", "plan", "apply"]},
        "workspace_sentinel_mocks": {"type": "str", "choices": ["none", "read"]},
        "workspace_state_versions": {"type": "str", "choices": ["none", "read-outputs", "read", "write"]},
        "workspace_variables": {"type": "str", "choices": ["none", "read", "write"]},
        "workspace_create": {"type": "bool"},
        "workspace_delete": {"type": "bool"},
        "workspace_locking": {"type": "bool"},
        "workspace_move": {"type": "bool"},
        "workspace_run_tasks": {"type": "bool"},
    }

    module = AnsibleTerraformModule(
        argument_spec=argument_spec,
        required_if=[
            ("state", "present", ("team_project_access_id", "team_id"), True),
            ("state", "present", ("team_project_access_id", "project_id"), True),
            ("state", "present", ("access",)),
        ],
        supports_check_mode=True,
    )

    params: Dict[str, Any] = deepcopy(module.params)

    # Validate: custom-only fields must not be set when access != custom
    if params.get("access") and params["access"] != "custom":
        for field in _CUSTOM_FIELDS:
            if params.get(field) is not None:
                module.fail_json(msg=(f"Parameter '{field}' is only valid when access='custom'. Current access='{params['access']}'."))

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
