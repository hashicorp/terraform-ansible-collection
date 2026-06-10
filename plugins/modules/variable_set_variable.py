#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: variable_set_variable
version_added: "2.0.0"
short_description: Manage variables within a Terraform Cloud/Enterprise variable set (create, update, delete).
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Manages the individual variables contained in a variable set on Terraform Cloud and Terraform Enterprise.
  - These variables are scoped to the variable set itself and are distinct from workspace-scoped variables.
  - Supports both Terraform input variables (C(category=terraform)) and environment variables (C(category=env)).
  - The variable set may be identified directly by C(variable_set_id), or by the combination of
    C(organization) and C(variable_set_name).
  - A variable within the set may be looked up either directly by its C(variable_id), or by its C(key).
  - The C(present) state creates the variable if it does not exist, or updates it in place on drift.
  - The C(absent) state deletes the variable if it exists.
  - Note that the value of sensitive variables is never returned by the API; see the C(sensitive) option
    for the idempotency consequences.
extends_documentation_fragment: hashicorp.terraform.common
options:
  variable_set_id:
    description:
      - The unique identifier of the variable set (e.g. C(varset-...)).
      - Mutually exclusive with C(variable_set_name).
    type: str
  variable_set_name:
    description:
      - The name of the variable set, used together with C(organization) to locate the set.
      - Mutually exclusive with C(variable_set_id).
    type: str
  organization:
    description:
      - The name of the organization that owns the variable set.
      - Required when identifying the variable set by C(variable_set_name).
    type: str
  variable_id:
    description:
      - The unique identifier of the variable (e.g. C(var-...)).
      - Provide for unambiguous update or delete operations.
      - Mutually exclusive with C(key).
    type: str
  key:
    description:
      - The variable key.
      - Required when identifying a variable by C(key) (i.e. when C(variable_id) is not provided).
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
- name: Create a Terraform input variable in a variable set
  hashicorp.terraform.variable_set_variable:
    organization: "my-org"
    variable_set_name: "shared-platform-defaults"
    key: "region"
    value: "us-east-1"
    category: "terraform"
    description: "Default application region"
    state: present

- name: Idempotent re-run with identical input
  hashicorp.terraform.variable_set_variable:
    organization: "my-org"
    variable_set_name: "shared-platform-defaults"
    key: "region"
    value: "us-east-1"
    category: "terraform"
    description: "Default application region"
    state: present

# Re-running with the same inputs yields:
# "changed": false

- name: Create a sensitive environment variable (write-only value)
  hashicorp.terraform.variable_set_variable:
    variable_set_id: "varset-7tRVyqGbvrF1RmWQ"
    key: "APP_API_TOKEN"
    value: "{{ app_api_token }}"
    category: "env"
    sensitive: true
    state: present

- name: Update a variable's value
  hashicorp.terraform.variable_set_variable:
    variable_set_id: "varset-7tRVyqGbvrF1RmWQ"
    key: "region"
    value: "eu-west-1"
    category: "terraform"
    state: present

- name: Delete a variable by ID
  hashicorp.terraform.variable_set_variable:
    variable_set_id: "varset-7tRVyqGbvrF1RmWQ"
    variable_id: "var-xyz789"
    state: absent

- name: Delete a variable by key
  hashicorp.terraform.variable_set_variable:
    organization: "my-org"
    variable_set_name: "shared-platform-defaults"
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
    - Empty or absent when the variable is sensitive.
  returned: when state is present
  type: str
  sample: "us-east-1"
description:
  description: The variable description.
  returned: when set
  type: str
  sample: "Default application region"
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
from ansible_collections.hashicorp.terraform.plugins.module_utils.variable_set_variable import (
    create_variable_set_variable,
    delete_variable_set_variable,
    get_variable_set_variable,
    get_variable_set_variable_by_key,
    update_variable_set_variable,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.variable_sets import get_variable_set_by_name

# Keys that belong to the SDK option models and participate in drift detection.
_SDK_KEYS = {"key", "value", "description", "category", "hcl", "sensitive"}


def _resolve_variable_set_id(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[str]:
    """Return the variable_set_id, resolving by name+organization when necessary."""
    if params.get("variable_set_id"):
        return params["variable_set_id"]
    name = params.get("variable_set_name")
    organization = params.get("organization")
    if name and organization:
        variable_set = get_variable_set_by_name(adapter, organization, name)
        if variable_set:
            return variable_set.get("id")
    return None


def _fetch_variable(adapter: TerraformClient, variable_set_id: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target variable by ID or by key within the variable set."""
    variable_id = params.get("variable_id")
    if variable_id:
        return get_variable_set_variable(adapter, variable_set_id, variable_id)
    key = params.get("key")
    if key:
        return get_variable_set_variable_by_key(adapter, variable_set_id, key)
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
    """Create or update a variable-set variable to match the desired state."""
    variable_set_id = _resolve_variable_set_id(adapter, params)
    if not variable_set_id:
        raise ValueError("Unable to resolve variable set: provide 'variable_set_id' or both 'variable_set_name' and 'organization'.")

    current = _fetch_variable(adapter, variable_set_id, params)
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
        created = create_variable_set_variable(adapter, variable_set_id, want)
        return {"changed": True, **created}

    # Category cannot be mutated in place; flag it rather than silently drifting.
    if want.get("category") and current.get("category") and want["category"] != current["category"]:
        raise ValueError(f"Cannot change variable category from {current['category']!r} to {want['category']!r}; " "delete and recreate the variable instead.")

    # category is not part of the update payload; drop it before diffing/updating.
    update_payload = {k: v for k, v in want.items() if k != "category"}

    have = _filter_current_state(current, update_payload)
    _strip_unverifiable_sensitive_value(have, update_payload)
    diff = dict_diff(have, update_payload)
    if not diff:
        return {"changed": False, **current}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Variable {current.get('id')} would be updated with the given options. Skipped update due to check mode.",
            **update_payload,
        }
    updated = update_variable_set_variable(adapter, variable_set_id, current["id"], update_payload)
    return {"changed": True, **updated}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the variable if present; no-op otherwise."""
    variable_set_id = _resolve_variable_set_id(adapter, params)
    if not variable_set_id:
        return {"changed": False, "msg": "Variable set not found; variable is already absent."}

    current = _fetch_variable(adapter, variable_set_id, params)
    if current is None:
        return {"changed": False, "msg": "Variable is already absent."}

    variable_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"Variable {variable_id} would be deleted. Skipped deletion due to check mode."}

    delete_variable_set_variable(adapter, variable_set_id, variable_id)
    return {"changed": True, "msg": f"Variable {variable_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "variable_set_id": {"type": "str"},
            "variable_set_name": {"type": "str"},
            "organization": {"type": "str"},
            "variable_id": {"type": "str"},
            "key": {"type": "str", "no_log": False},
            "value": {"type": "str", "no_log": True},
            "description": {"type": "str"},
            "category": {"type": "str", "choices": ["terraform", "env"]},
            "hcl": {"type": "bool"},
            "sensitive": {"type": "bool"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_by={"variable_set_name": ("organization",)},
        mutually_exclusive=[("variable_set_id", "variable_set_name"), ("variable_id", "key")],
        required_one_of=[("variable_set_id", "variable_set_name"), ("variable_id", "key")],
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
