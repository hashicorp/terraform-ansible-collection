#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: policy_set
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise policy sets and their memberships.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Manages a policy set - a group of policies attached to workspaces/projects, either
    populated by individual M(hashicorp.terraform.policy) resources or by a VCS repository.
  - Identify a policy set either directly by C(policy_set_id), or by the combination of
    C(organization) and C(name).
  - C(kind) is immutable after creation - the update API does not accept it. If
    C(state=present) targets an existing policy set with a different C(kind) than supplied,
    the module fails with a clear message rather than silently ignoring the drift.
  - The 5 relationship options (C(policy_ids), C(workspace_ids), C(workspace_exclusion_ids),
    C(project_ids), C(project_exclusion_ids)) are each independently diffed against the policy
    set's current membership and synced via add/remove calls - only relationships you actually
    pass a value for are touched; omit an option to leave that membership untouched.
extends_documentation_fragment: hashicorp.terraform.common
options:
  policy_set_id:
    description:
      - The unique identifier of the policy set (e.g. C(polset-...)).
      - Provide for unambiguous update or delete operations.
    type: str
  organization:
    description:
      - The name of the organization that owns the policy set.
      - Required unless C(policy_set_id) is provided.
    type: str
  name:
    description:
      - Human-readable name of the policy set.
      - Required when identifying the set by (organization, name), and when creating.
    type: str
  description:
    description:
      - Human-readable description of the policy set.
    type: str
  kind:
    description:
      - The policy engine for policies in this set. Immutable after creation.
      - Defaults to C(sentinel) when creating a new policy set if omitted. Leave unset on
        updates to avoid a spurious drift error against an existing set of a different kind.
    type: str
    choices: ["sentinel", "opa", "tfpolicy"]
  global:
    description:
      - Whether this policy set applies to every workspace in the organization.
    type: bool
  overridable:
    description:
      - Whether soft-mandatory policy failures from this set can be overridden.
    type: bool
  agent_enabled:
    description:
      - Whether this policy set runs via an agent (required for OPA policies using custom
        Rego builtins, or self-hosted policy tooling).
    type: bool
  policy_tool_version:
    description:
      - The version of the policy tool (OPA/Sentinel) to run this set's policies with.
    type: str
  policies_path:
    description:
      - Subdirectory within the VCS repository where policy files live. Only meaningful for
        VCS-backed policy sets (C(vcs_repo) set).
    type: str
  vcs_repo:
    description:
      - VCS repository backing this policy set. Omit to manage policies individually via
        M(hashicorp.terraform.policy) and C(policy_ids) instead.
    type: dict
    suboptions:
      identifier:
        description: The VCS repository identifier, in the format C(org/repo).
        type: str
      branch:
        description: The VCS branch to track. Defaults to the repository's default branch.
        type: str
      ingress_submodules:
        description: Whether to fetch Git submodules when cloning.
        type: bool
      oauth_token_id:
        description: The VCS OAuth token ID to use.
        type: str
      tags_regex:
        description: A regular expression matching Git tags that trigger new policy set versions.
        type: str
      gha_installation_id:
        description: The GitHub App installation ID, for GitHub App VCS connections.
        type: str
  policy_ids:
    description:
      - IDs of individual M(hashicorp.terraform.policy) resources belonging to this set.
      - Only meaningful for non-VCS-backed policy sets. Omit to leave membership untouched.
    type: list
    elements: str
  workspace_ids:
    description:
      - Workspace IDs this policy set applies to (when C(global=false)). Omit to leave
        membership untouched.
    type: list
    elements: str
  workspace_exclusion_ids:
    description:
      - Workspace IDs explicitly excluded from this policy set. Omit to leave membership
        untouched.
    type: list
    elements: str
  project_ids:
    description:
      - Project IDs this policy set applies to. Omit to leave membership untouched.
    type: list
    elements: str
  project_exclusion_ids:
    description:
      - Project IDs explicitly excluded from this policy set. Omit to leave membership
        untouched.
    type: list
    elements: str
  state:
    description:
      - Desired state of the policy set.
      - C(present) creates or updates the policy set and syncs any supplied relationships.
      - C(absent) deletes the policy set if it exists.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a policy set with individual policies
  hashicorp.terraform.policy_set:
    organization: "my-org"
    name: "baseline-policies"
    kind: sentinel
    global: true
    policy_ids:
      - "pol-abc123"
      - "pol-def456"
    state: present
  register: result

- name: Idempotent re-run with the same membership
  hashicorp.terraform.policy_set:
    policy_set_id: "{{ result.id }}"
    policy_ids:
      - "pol-abc123"
      - "pol-def456"
    state: present
# "changed": false

- name: Restrict a policy set to specific workspaces and drop a policy
  hashicorp.terraform.policy_set:
    policy_set_id: "{{ result.id }}"
    global: false
    workspace_ids:
      - "ws-abc123"
    policy_ids:
      - "pol-abc123"
    state: present

- name: Create a VCS-backed OPA policy set
  hashicorp.terraform.policy_set:
    organization: "my-org"
    name: "vcs-policies"
    kind: opa
    policies_path: "policies/"
    vcs_repo:
      identifier: "my-org/policy-repo"
      branch: "main"
      oauth_token_id: "ot-abc123"
    state: present

- name: Delete a policy set
  hashicorp.terraform.policy_set:
    policy_set_id: "{{ result.id }}"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The policy set identifier.
  returned: when state is present
  type: str
  sample: "polset-EavQ1LztoRTQHSNT"
name:
  description: The policy set name.
  returned: when state is present
  type: str
kind:
  description: The policy engine for policies in this set.
  returned: when state is present
  type: str
global:
  description: Whether this policy set applies to every workspace in the organization.
  returned: when state is present
  type: bool
policies:
  description: Policies belonging to this set (id-only unless read with includes).
  returned: when state is present
  type: list
  elements: dict
workspaces:
  description: Workspaces this policy set applies to (id-only unless read with includes).
  returned: when state is present
  type: list
  elements: dict
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Policy set polset-EavQ1LztoRTQHSNT has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set import (
    create_policy_set,
    delete_policy_set,
    get_policy_set,
    get_policy_set_by_name,
    sync_relationship,
    update_policy_set,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff

_ATTR_KEYS = ("name", "description", "global", "overridable", "agent_enabled", "policy_tool_version", "policies_path", "vcs_repo")
_RELATIONSHIP_PARAM_MAP = {
    "policy_ids": "policies",
    "workspace_ids": "workspaces",
    "workspace_exclusion_ids": "workspace_exclusions",
    "project_ids": "projects",
    "project_exclusion_ids": "project_exclusions",
}


def _fetch_policy_set(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target policy set by ID or by (organization, name)."""
    policy_set_id = params.get("policy_set_id")
    if policy_set_id:
        return get_policy_set(adapter, policy_set_id)
    organization = params.get("organization")
    name = params.get("name")
    if organization and name:
        return get_policy_set_by_name(adapter, organization, name)
    return None


def _current_ids(current: Dict[str, Any], relationship: str) -> List[str]:
    """Extract the sorted list of member IDs from a read-model relationship list."""
    return sorted(item.get("id") for item in current.get(relationship, []) if item.get("id"))


def _plan_relationship_syncs(params: Dict[str, Any], current: Dict[str, Any]) -> List[Tuple[str, List[str], List[str]]]:
    """Diff each supplied relationship param against current membership.

    Returns a list of (relationship, add_ids, remove_ids) tuples - only for
    relationships the caller actually supplied and that have drift.
    """
    plans = []
    for param_key, relationship in _RELATIONSHIP_PARAM_MAP.items():
        desired = params.get(param_key)
        if desired is None:
            continue
        desired_ids = sorted(desired)
        current_ids = _current_ids(current, relationship)
        if desired_ids == current_ids:
            continue
        add_ids = sorted(set(desired_ids) - set(current_ids))
        remove_ids = sorted(set(current_ids) - set(desired_ids))
        plans.append((relationship, add_ids, remove_ids))
    return plans


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update a policy set, syncing any supplied relationships."""
    current = _fetch_policy_set(adapter, params)
    name = params.get("name")
    want_attrs = {key: params[key] for key in _ATTR_KEYS if params.get(key) is not None}

    if current is None:
        if not params.get("organization"):
            raise ValueError("'organization' is required when creating a new policy set.")
        if not name:
            raise ValueError("'name' is required when creating a new policy set.")

        if check_mode:
            return {"changed": True, "msg": f"Policy set {name} would be created. Skipped creation due to check mode.", "name": name}

        create_data = dict(want_attrs)
        create_data["kind"] = params.get("kind") or "sentinel"
        # Every relationship, all 5 types, is synced via add_* calls after create -
        # pytfe's create() cannot accept relationships directly, see create_policy_set().
        created = create_policy_set(adapter, params["organization"], create_data)

        any_relationship_supplied = False
        for param_key, relationship in _RELATIONSHIP_PARAM_MAP.items():
            add_ids = params.get(param_key)
            if add_ids:
                sync_relationship(adapter, created["id"], relationship, add_ids=add_ids, remove_ids=[])
                any_relationship_supplied = True
        if any_relationship_supplied:
            created = get_policy_set(adapter, created["id"])

        return {"changed": True, **created}

    if params.get("kind") is not None and params["kind"] != current.get("kind"):
        raise ValueError(
            f"Policy set {current['id']} has drifted on immutable field 'kind' ('{current.get('kind')}' -> '{params['kind']}'). "
            "kind cannot be changed after creation - delete and recreate to change it."
        )

    have_attrs = {key: current.get(key) for key in want_attrs.keys()}
    attr_diff = dict_diff(have_attrs, want_attrs)
    relationship_syncs = _plan_relationship_syncs(params, current)

    if not attr_diff and not relationship_syncs:
        return {"changed": False, **current}

    if check_mode:
        summary = list(attr_diff.keys()) + [relationship for relationship, _add_ids, _remove_ids in relationship_syncs]
        return {"changed": True, "msg": f"Policy set {current['id']} would be updated ({', '.join(summary)}). Skipped update due to check mode."}

    if attr_diff:
        update_policy_set(adapter, current["id"], attr_diff)
    for relationship, add_ids, remove_ids in relationship_syncs:
        sync_relationship(adapter, current["id"], relationship, add_ids, remove_ids)

    final = get_policy_set(adapter, current["id"])
    return {"changed": True, **final}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the policy set if present; no-op otherwise."""
    current = _fetch_policy_set(adapter, params)
    if current is None:
        return {"changed": False, "msg": "Policy set is already absent."}

    policy_set_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"Policy set {policy_set_id} would be deleted. Skipped deletion due to check mode."}

    delete_policy_set(adapter, policy_set_id)
    return {"changed": True, "msg": f"Policy set {policy_set_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "policy_set_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
            "description": {"type": "str"},
            "kind": {"type": "str", "choices": ["sentinel", "opa", "tfpolicy"]},
            "global": {"type": "bool"},
            "overridable": {"type": "bool"},
            "agent_enabled": {"type": "bool"},
            "policy_tool_version": {"type": "str"},
            "policies_path": {"type": "str"},
            "vcs_repo": {
                "type": "dict",
                "options": {
                    "identifier": {"type": "str"},
                    "branch": {"type": "str"},
                    "ingress_submodules": {"type": "bool"},
                    "oauth_token_id": {"type": "str"},
                    "tags_regex": {"type": "str"},
                    "gha_installation_id": {"type": "str"},
                },
            },
            "policy_ids": {"type": "list", "elements": "str"},
            "workspace_ids": {"type": "list", "elements": "str"},
            "workspace_exclusion_ids": {"type": "list", "elements": "str"},
            "project_ids": {"type": "list", "elements": "str"},
            "project_exclusion_ids": {"type": "list", "elements": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_one_of=[("policy_set_id", "name")],
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
