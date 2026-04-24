#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: variable_sets
version_added: "2.0.0"
short_description: Manage Terraform Cloud/Enterprise variable sets (create, update, delete, attach).
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Manages variable sets on Terraform Cloud and Terraform Enterprise.
  - Supports creating, updating, and deleting the variable set itself and reconciling its
    attachments to workspaces and projects.
  - The C(present) state creates the variable set if missing, or updates it in place on drift,
    and converges the set of attached workspaces and projects to match the provided lists.
  - The C(absent) state deletes the variable set if it exists.
  - Variable sets declared as C(global) cannot be scoped to individual workspaces or projects;
    attempting to pass C(workspace_ids) or C(project_ids) alongside C(global=true) is rejected.
  - The contents of a variable set (the variables it holds) are managed out of band and are not
    touched by this module.
extends_documentation_fragment: hashicorp.terraform.common
options:
  variable_set_id:
    description:
      - The unique identifier of the variable set (e.g. C(varset-...)).
      - Used for unambiguous update or delete operations.
      - Mutually exclusive with C(name).
    type: str
  name:
    description:
      - Name of the variable set.
      - Required when identifying the variable set by C(organization) + C(name).
      - Mutually exclusive with C(variable_set_id).
    type: str
  organization:
    description:
      - Organization that owns the variable set.
      - Required when C(variable_set_id) is not provided, or when creating a new set.
    type: str
  description:
    description:
      - Human-readable description.
    type: str
  global:
    description:
      - Whether the variable set applies globally to every workspace in the organization.
      - A global variable set cannot be attached to individual workspaces or projects.
    type: bool
  priority:
    description:
      - Whether values in this set override values defined on the workspace or by other
        (non-priority) variable sets.
    type: bool
  workspace_ids:
    description:
      - List of workspace IDs the variable set should be attached to.
      - When provided, the module converges attachments to exactly this list. Any workspaces
        currently attached but not listed will be detached, and any listed but not attached
        will be attached.
      - Pass an empty list C([]) to detach from all workspaces. Omit to leave attachments untouched.
      - Only valid when C(global=false).
    type: list
    elements: str
  project_ids:
    description:
      - List of project IDs the variable set should be attached to.
      - When provided, the module converges attachments to exactly this list.
      - Pass an empty list C([]) to detach from all projects. Omit to leave attachments untouched.
      - Only valid when C(global=false).
    type: list
    elements: str
  state:
    description:
      - Desired state of the variable set.
      - C(present) creates or updates; C(absent) deletes.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a non-global variable set
  hashicorp.terraform.variable_sets:
    organization: "my-org"
    name: "shared-aws-creds"
    description: "Shared AWS credentials for platform workspaces"
    global: false
    priority: false
    state: present

- name: Idempotent re-run with identical input
  hashicorp.terraform.variable_sets:
    organization: "my-org"
    name: "shared-aws-creds"
    description: "Shared AWS credentials for platform workspaces"
    global: false
    priority: false
    state: present

# Re-running with the same inputs yields:
# "changed": false

- name: Attach the variable set to two workspaces
  hashicorp.terraform.variable_sets:
    organization: "my-org"
    name: "shared-aws-creds"
    workspace_ids:
      - "ws-abc123"
      - "ws-def456"
    state: present

- name: Update description and raise priority
  hashicorp.terraform.variable_sets:
    organization: "my-org"
    name: "shared-aws-creds"
    description: "Shared AWS credentials (authoritative)"
    priority: true
    state: present

- name: Detach from every workspace and project
  hashicorp.terraform.variable_sets:
    organization: "my-org"
    name: "shared-aws-creds"
    workspace_ids: []
    project_ids: []
    state: present

- name: Delete a variable set by ID
  hashicorp.terraform.variable_sets:
    variable_set_id: "varset-7tRVyqGbvrF1RmWQ"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: Variable set identifier.
  returned: when state is present
  type: str
  sample: "varset-7tRVyqGbvrF1RmWQ"
name:
  description: Variable set name.
  returned: when state is present
  type: str
  sample: "shared-aws-creds"
description:
  description: Variable set description.
  returned: when set
  type: str
  sample: "Shared AWS credentials for platform workspaces"
global:
  description: Whether the variable set applies to all workspaces in the organization.
  returned: when state is present
  type: bool
  sample: false
priority:
  description: Whether values in this set override workspace-level values.
  returned: when state is present
  type: bool
  sample: false
workspace_ids:
  description: Final set of workspace IDs the variable set is attached to (when reconciled).
  returned: when workspace_ids was provided
  type: list
  elements: str
  sample: ["ws-abc123", "ws-def456"]
project_ids:
  description: Final set of project IDs the variable set is attached to (when reconciled).
  returned: when project_ids was provided
  type: list
  elements: str
  sample: ["prj-abc123"]
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Variable set varset-7tRVyqGbvrF1RmWQ has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Tuple

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff
from ansible_collections.hashicorp.terraform.plugins.module_utils.variable_sets import (
    apply_to_projects,
    apply_to_workspaces,
    create_variable_set,
    delete_variable_set,
    get_variable_set,
    get_variable_set_by_name,
    remove_from_projects,
    remove_from_workspaces,
    update_variable_set,
)

# Attribute keys that participate in create/update payloads and drift detection.
_ATTR_KEYS = {"name", "description", "global", "priority"}


def _resolve_variable_set(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Locate the variable set by ID or by (organization, name), with relations included."""
    variable_set_id = params.get("variable_set_id")
    if variable_set_id:
        return get_variable_set(adapter, variable_set_id, include_relations=True)
    name = params.get("name")
    organization = params.get("organization")
    if name and organization:
        summary = get_variable_set_by_name(adapter, organization, name)
        if summary and summary.get("id"):
            return get_variable_set(adapter, summary["id"], include_relations=True)
    return None


def _build_desired_attrs(params: Dict[str, Any]) -> Dict[str, Any]:
    """Pick the variable-set scalar attributes from params, dropping Nones."""
    return {k: v for k, v in params.items() if k in _ATTR_KEYS and v is not None}


def _filter_current_attrs(have: Dict[str, Any], want: Dict[str, Any]) -> Dict[str, Any]:
    """Project the server view down to the keys the user specified."""
    return {k: have.get(k) for k in want.keys() if k in have}


def _extract_ids(items: Any) -> List[str]:
    """Extract a list of ids from a list of dicts/models (or empty on anything else)."""
    if not isinstance(items, list):
        return []
    return [item["id"] for item in items if isinstance(item, dict) and item.get("id")]


def _reconcile_attachments(
    desired: Optional[List[str]],
    current: List[str],
) -> Tuple[Set[str], Set[str], List[str]]:
    """Compute (to_add, to_remove, final) for an attachment set.

    Returns ``(set(), set(), current)`` when ``desired`` is ``None`` (user omitted
    the field and wants attachments left untouched).
    """
    if desired is None:
        return set(), set(), current
    desired_set = set(desired)
    current_set = set(current)
    to_add = desired_set - current_set
    to_remove = current_set - desired_set
    return to_add, to_remove, sorted(desired_set)


def _validate_attachment_scope(params: Dict[str, Any], current_global: Optional[bool]) -> None:
    """Reject workspace/project attachments against a global variable set."""
    desired_global = params.get("global")
    # Use desired global if set, otherwise fall back to current server value.
    effective_global = desired_global if desired_global is not None else current_global
    if not effective_global:
        return
    if params.get("workspace_ids") is not None or params.get("project_ids") is not None:
        raise ValueError(
            "A global variable set cannot be attached to specific workspaces or projects. " + "Set 'global: false' or omit 'workspace_ids'/'project_ids'."
        )


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update the variable set and reconcile its attachments."""
    current = _resolve_variable_set(adapter, params)
    want_attrs = _build_desired_attrs(params)

    _validate_attachment_scope(params, current_global=current.get("global") if current else None)

    if current is None:
        if not params.get("name"):
            raise ValueError("'name' is required when creating a new variable set.")
        if not params.get("organization"):
            raise ValueError("'organization' is required when creating a new variable set.")
        # pytfe requires `global` on create — default to False if the user didn't specify.
        create_payload = {"global": False, **want_attrs}
        if check_mode:
            return {
                "changed": True,
                "msg": f"Variable set {params['name']} would be created. Skipped creation due to check mode.",
                **create_payload,
            }
        created = create_variable_set(adapter, params["organization"], create_payload)
        variable_set_id = created["id"]
        # After create, reconcile attachments if the user provided them.
        attach_result = _apply_attachments(adapter, variable_set_id, params, current_attached={"workspaces": [], "projects": []}, check_mode=False)
        return {"changed": True, **created, **attach_result}

    variable_set_id = current["id"]
    have_attrs = _filter_current_attrs(current, want_attrs)
    attr_diff = dict_diff(have_attrs, want_attrs)

    # Attachments
    current_ws = _extract_ids(current.get("workspaces"))
    current_pr = _extract_ids(current.get("projects"))
    ws_add, ws_remove, ws_final = _reconcile_attachments(params.get("workspace_ids"), current_ws)
    pr_add, pr_remove, pr_final = _reconcile_attachments(params.get("project_ids"), current_pr)

    attachment_changes = bool(ws_add or ws_remove or pr_add or pr_remove)

    if not attr_diff and not attachment_changes:
        return {"changed": False, **current}

    if check_mode:
        msg_parts = []
        if attr_diff:
            msg_parts.append(f"attrs {sorted(attr_diff.keys())}")
        if ws_add or ws_remove:
            msg_parts.append(f"workspaces +{sorted(ws_add)} -{sorted(ws_remove)}")
        if pr_add or pr_remove:
            msg_parts.append(f"projects +{sorted(pr_add)} -{sorted(pr_remove)}")
        return {
            "changed": True,
            "msg": f"Variable set {variable_set_id} would be updated ({'; '.join(msg_parts)}). Skipped due to check mode.",
            **want_attrs,
        }

    updated = current
    if attr_diff:
        updated = update_variable_set(adapter, variable_set_id, want_attrs)

    attach_result = _apply_attachments(
        adapter,
        variable_set_id,
        params,
        current_attached={"workspaces": current_ws, "projects": current_pr},
        check_mode=False,
    )
    return {"changed": True, **updated, **attach_result}


def _apply_attachments(
    adapter: TerraformClient,
    variable_set_id: str,
    params: Dict[str, Any],
    current_attached: Dict[str, List[str]],
    check_mode: bool,
) -> Dict[str, Any]:
    """Converge workspace/project attachments to the user's desired set.

    Returns a dict with ``workspace_ids`` / ``project_ids`` keys when the user
    provided those inputs, so the caller can surface the final state.
    """
    out: Dict[str, Any] = {}

    ws_desired = params.get("workspace_ids")
    if ws_desired is not None:
        to_add, to_remove, final = _reconcile_attachments(ws_desired, current_attached.get("workspaces", []))
        if not check_mode:
            if to_remove:
                remove_from_workspaces(adapter, variable_set_id, sorted(to_remove))
            if to_add:
                apply_to_workspaces(adapter, variable_set_id, sorted(to_add))
        out["workspace_ids"] = final

    pr_desired = params.get("project_ids")
    if pr_desired is not None:
        to_add, to_remove, final = _reconcile_attachments(pr_desired, current_attached.get("projects", []))
        if not check_mode:
            if to_remove:
                remove_from_projects(adapter, variable_set_id, sorted(to_remove))
            if to_add:
                apply_to_projects(adapter, variable_set_id, sorted(to_add))
        out["project_ids"] = final

    return out


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the variable set if present; no-op otherwise."""
    current = _resolve_variable_set(adapter, params)
    if current is None:
        return {"changed": False, "msg": "Variable set is already absent."}

    variable_set_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"Variable set {variable_set_id} would be deleted. Skipped deletion due to check mode."}

    delete_variable_set(adapter, variable_set_id)
    return {"changed": True, "msg": f"Variable set {variable_set_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "variable_set_id": {"type": "str"},
            "name": {"type": "str"},
            "organization": {"type": "str"},
            "description": {"type": "str"},
            "global": {"type": "bool"},
            "priority": {"type": "bool"},
            "workspace_ids": {"type": "list", "elements": "str"},
            "project_ids": {"type": "list", "elements": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        mutually_exclusive=[("variable_set_id", "name")],
        required_one_of=[("variable_set_id", "name")],
        required_by={"name": ("organization",)},
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
