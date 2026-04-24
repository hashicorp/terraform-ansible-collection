#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: variable
version_added: "2.0.0"
short_description: Manage Terraform Cloud/Enterprise workspace variables (create, update, delete).
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Manages workspace-scoped variables on Terraform Cloud and Terraform Enterprise.
  - Supports both Terraform input variables (C(category=terraform)) and environment variables (C(category=env)).
  - Variables may be looked up either directly by their C(variable_id), or by the combination of
    workspace (C(workspace_id) or C(workspace)+C(organization)) and the variable's C(key).
  - The C(present) state creates the variable if it does not exist, or updates it in place on drift.
  - The C(absent) state deletes the variable if it exists.
  - Note that the value of sensitive variables is never returned by the API; see the C(sensitive) option
    for the idempotency consequences.
extends_documentation_fragment: hashicorp.terraform.common
options:
  variable_id:
    description:
      - The unique identifier of the variable (e.g. C(var-...)).
      - Provide for unambiguous update or delete operations.
      - Mutually exclusive with C(key).
    type: str
  workspace_id:
    description:
      - The workspace that owns the variable.
      - One of C(workspace_id) or (C(workspace) and C(organization)) is required unless C(variable_id) is provided
        together with one of those identifiers.
    type: str
  workspace:
    description:
      - The workspace name, used together with C(organization) to locate the workspace.
    type: str
  organization:
    description:
      - The name of the organization that owns the workspace.
    type: str
  key:
    description:
      - The variable key.
      - Required when identifying a variable by C(workspace)+C(key) (i.e. when C(variable_id) is not provided).
      - Mutually exclusive with C(variable_id).
    type: str
  value:
    description:
      - The variable value.
      - For C(sensitive=true) variables, the stored value is never returned by the API,
        so specifying C(value) alone cannot be diffed — see C(sensitive) for details.
    type: str
  description:
    description:
      - Optional human-readable description for the variable.
    type: str
  category:
    description:
      - Whether the variable is a Terraform input variable or an environment variable.
      - Required when creating a variable.
      - Cannot be changed after creation.
    type: str
    choices: ["terraform", "env"]
  hcl:
    description:
      - Whether the variable value is to be evaluated as HCL.
      - Only applicable to C(category=terraform) variables.
    type: bool
  sensitive:
    description:
      - Whether the variable value is sensitive.
      - Once a variable is marked sensitive, the stored value is write-only; the API will not
        return it. When C(sensitive=true), the module cannot detect drift on C(value) alone
        and will treat re-runs with the same input as idempotent.
      - To rotate a sensitive value, change another field (for example, C(description)) alongside
        C(value), or pass C(variable_id) and rely on the update explicitly.
    type: bool
  state:
    description:
      - Desired state of the variable.
      - C(present) creates or updates; C(absent) deletes.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a Terraform input variable
  hashicorp.terraform.variable:
    organization: "my-org"
    workspace: "my-workspace"
    key: "region"
    value: "us-east-1"
    category: "terraform"
    description: "Default AWS region"
    state: present

- name: Idempotent re-run with identical input
  hashicorp.terraform.variable:
    organization: "my-org"
    workspace: "my-workspace"
    key: "region"
    value: "us-east-1"
    category: "terraform"
    description: "Default AWS region"
    state: present

# Re-running with the same inputs yields:
# "changed": false

- name: Update an environment variable's value
  hashicorp.terraform.variable:
    organization: "my-org"
    workspace: "my-workspace"
    key: "AWS_ACCESS_KEY_ID"
    value: "AKIA...updated..."
    category: "env"
    state: present

- name: Create a sensitive environment variable (write-only value)
  hashicorp.terraform.variable:
    organization: "my-org"
    workspace: "my-workspace"
    key: "AWS_SECRET_ACCESS_KEY"
    value: "{{ aws_secret }}"
    category: "env"
    sensitive: true
    state: present

- name: Delete a variable by ID
  hashicorp.terraform.variable:
    workspace_id: "ws-abc123"
    variable_id: "var-xyz789"
    state: absent

- name: Delete a variable by (workspace, key)
  hashicorp.terraform.variable:
    organization: "my-org"
    workspace: "my-workspace"
    key: "region"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The variable identifier.
  returned: when state is present
  type: str
  sample: "var-EavQ1LztoRTQHSNT"
key:
  description: The variable key.
  returned: when state is present
  type: str
  sample: "region"
value:
  description:
    - The variable value.
    - Empty string when the variable is sensitive.
  returned: when state is present
  type: str
  sample: "us-east-1"
description:
  description: The variable description.
  returned: when set
  type: str
  sample: "Default AWS region"
category:
  description: The variable category.
  returned: when state is present
  type: str
  sample: "terraform"
hcl:
  description: Whether the variable is evaluated as HCL.
  returned: when state is present
  type: bool
  sample: false
sensitive:
  description: Whether the variable value is sensitive.
  returned: when state is present
  type: bool
  sample: false
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Variable var-EavQ1LztoRTQHSNT has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff
from ansible_collections.hashicorp.terraform.plugins.module_utils.variable import (
    create_variable,
    delete_variable,
    get_variable,
    get_variable_by_key,
    update_variable,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace

# Keys that belong to the SDK option models and participate in drift detection.
_SDK_KEYS = {"key", "value", "description", "category", "hcl", "sensitive"}


def _resolve_workspace_id(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[str]:
    """Return the workspace_id, resolving by name+organization when necessary."""
    if params.get("workspace_id"):
        return params["workspace_id"]
    workspace_name = params.get("workspace")
    organization = params.get("organization")
    if workspace_name and organization:
        workspace = get_workspace(adapter, organization, workspace_name)
        if workspace:
            return workspace.get("id")
    return None


def _fetch_variable(adapter: TerraformClient, workspace_id: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target variable by ID or by (workspace_id, key[, category])."""
    variable_id = params.get("variable_id")
    if variable_id:
        return get_variable(adapter, workspace_id, variable_id)
    key = params.get("key")
    if key:
        return get_variable_by_key(adapter, workspace_id, key, category=params.get("category"))
    return None


def _build_desired_state(params: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only SDK-relevant, user-specified fields for drift/create payloads."""
    return {k: v for k, v in params.items() if k in _SDK_KEYS and v is not None}


def _filter_current_state(have: Dict[str, Any], want: Dict[str, Any]) -> Dict[str, Any]:
    """Project the server view down to keys the user explicitly managed."""
    return {k: have.get(k) for k in want.keys() if k in have}


def _strip_unverifiable_sensitive_value(have: Dict[str, Any], want: Dict[str, Any]) -> None:
    """Drop ``value`` from both sides when the variable is sensitive.

    TFE/C never returns the stored value of a sensitive variable, so drift on
    ``value`` alone cannot be detected. Stripping from both sides keeps
    re-runs idempotent; rotation must happen via an explicit non-sensitive
    signal (e.g. changing description) or by recreating the variable.
    Mutates both dicts in place.
    """
    if have.get("sensitive") or want.get("sensitive"):
        have.pop("value", None)
        want.pop("value", None)


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update a variable to match the desired state."""
    workspace_id = _resolve_workspace_id(adapter, params)
    if not workspace_id:
        raise ValueError("Unable to resolve workspace: provide 'workspace_id' or both 'workspace' and 'organization'.")

    current = _fetch_variable(adapter, workspace_id, params)
    want = _build_desired_state(params)

    if current is None:
        if not params.get("key"):
            raise ValueError("'key' is required when creating a new variable.")
        if not params.get("category"):
            raise ValueError("'category' is required when creating a new variable.")
        if check_mode:
            return {
                "changed": True,
                "msg": f"Variable {params['key']} would be created. Skipped creation due to check mode.",
                **want,
            }
        created = create_variable(adapter, workspace_id, want)
        return {"changed": True, **created}

    # Category cannot be mutated in place; flag it rather than silently drifting.
    if want.get("category") and current.get("category") and want["category"] != current["category"]:
        raise ValueError(f"Cannot change variable category from {current['category']!r} to {want['category']!r}; " "delete and recreate the variable instead.")

    have = _filter_current_state(current, want)
    _strip_unverifiable_sensitive_value(have, want)
    diff = dict_diff(have, want)
    if not diff:
        return {"changed": False, **current}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Variable {current.get('id')} would be updated with the given options. Skipped update due to check mode.",
            **want,
        }
    updated = update_variable(adapter, workspace_id, current["id"], want)
    return {"changed": True, **updated}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the variable if present; no-op otherwise."""
    workspace_id = _resolve_workspace_id(adapter, params)
    if not workspace_id:
        return {"changed": False, "msg": "Workspace not found; variable is already absent."}

    current = _fetch_variable(adapter, workspace_id, params)
    if current is None:
        return {"changed": False, "msg": "Variable is already absent."}

    variable_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"Variable {variable_id} would be deleted. Skipped deletion due to check mode."}

    delete_variable(adapter, workspace_id, variable_id)
    return {"changed": True, "msg": f"Variable {variable_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "variable_id": {"type": "str"},
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
            "key": {"type": "str", "no_log": False},
            "value": {"type": "str", "no_log": True},
            "description": {"type": "str"},
            "category": {"type": "str", "choices": ["terraform", "env"]},
            "hcl": {"type": "bool"},
            "sensitive": {"type": "bool"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_together=[["workspace", "organization"]],
        mutually_exclusive=[("variable_id", "key"), ("workspace_id", "workspace")],
        required_one_of=[("variable_id", "key")],
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
