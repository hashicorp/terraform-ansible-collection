#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: policy_set_parameter
version_added: "2.2.0"
short_description: Manage parameters on a Terraform Cloud/Enterprise policy set.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Manages a key/value parameter available to policies in a M(hashicorp.terraform.policy_set)
    at evaluation time (Sentinel's C(tfe.parameters), OPA's input data, etc.).
  - Identify a parameter either directly by C(parameter_id), or by C(key) within the given
    C(policy_set_id).
  - Note that the value of sensitive parameters is never returned by the API; see O(sensitive)
    for details on how that affects idempotency.
extends_documentation_fragment: hashicorp.terraform.common
options:
  policy_set_id:
    description:
      - The ID of the policy set this parameter belongs to.
    type: str
    required: true
  parameter_id:
    description:
      - The unique identifier of the parameter (e.g. C(var-...)).
      - Provide for unambiguous update or delete operations.
    type: str
  key:
    description:
      - The parameter key/name.
      - Required when identifying the parameter by key, and when creating a new parameter.
    type: str
  value:
    description:
      - The parameter value.
      - For C(sensitive=true) parameters, the stored value is never returned by the API,
        so specifying C(value) alone cannot be diffed - see O(sensitive) for details.
    type: str
  sensitive:
    description:
      - Whether the parameter value is sensitive.
      - Once a parameter is marked sensitive, the stored value is write-only; the API will not
        return it. When C(sensitive=true), the module cannot detect drift on C(value) alone -
        a re-run with the same inputs is reported as C(changed=false), regardless of whether
        the stored value actually matches. To rotate a sensitive value, delete and recreate
        the parameter, or change O(sensitive) itself back to C(false) first.
    type: bool
  state:
    description:
      - Desired state of the parameter.
      - C(present) creates or updates the parameter.
      - C(absent) deletes the parameter if it exists.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a policy set parameter
  hashicorp.terraform.policy_set_parameter:
    policy_set_id: "polset-EavQ1LztoRTQHSNT"
    key: "environment"
    value: "prod"
    state: present
  register: result

- name: Idempotent re-run with identical input
  hashicorp.terraform.policy_set_parameter:
    policy_set_id: "polset-EavQ1LztoRTQHSNT"
    key: "environment"
    value: "prod"
    state: present
# "changed": false

- name: Create a sensitive parameter (write-only value)
  hashicorp.terraform.policy_set_parameter:
    policy_set_id: "polset-EavQ1LztoRTQHSNT"
    key: "api_key"
    value: "s3cr3t"
    sensitive: true
    state: present

- name: Delete a policy set parameter
  hashicorp.terraform.policy_set_parameter:
    policy_set_id: "polset-EavQ1LztoRTQHSNT"
    parameter_id: "{{ result.id }}"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The parameter identifier.
  returned: when state is present
  type: str
  sample: "var-EavQ1LztoRTQHSNT"
key:
  description: The parameter key.
  returned: when state is present
  type: str
value:
  description: The parameter value.
  returned: when state is present and not sensitive
  type: str
sensitive:
  description: Whether the parameter value is sensitive.
  returned: when state is present
  type: bool
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Policy set parameter var-EavQ1LztoRTQHSNT has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set_parameter import (
    create_policy_set_parameter,
    delete_policy_set_parameter,
    get_policy_set_parameter,
    get_policy_set_parameter_by_key,
    update_policy_set_parameter,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff

_SDK_KEYS = ("key", "value", "sensitive")


def _fetch_parameter(adapter: TerraformClient, policy_set_id: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target parameter by ID or by key within the policy set."""
    parameter_id = params.get("parameter_id")
    if parameter_id:
        return get_policy_set_parameter(adapter, policy_set_id, parameter_id)
    key = params.get("key")
    if key:
        return get_policy_set_parameter_by_key(adapter, policy_set_id, key)
    return None


def _strip_unverifiable_sensitive_value(have: Dict[str, Any], want: Dict[str, Any]) -> None:
    """Drop ``value`` from both sides when the parameter is sensitive.

    The API never returns the stored value of a sensitive parameter, so drift
    on it alone is unverifiable - dropping it from both sides keeps
    re-runs idempotent; rotation must happen via delete+recreate.
    """
    if have.get("sensitive") or want.get("sensitive"):
        have.pop("value", None)
        want.pop("value", None)


def state_present(adapter: TerraformClient, policy_set_id: str, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update a policy set parameter to match the desired state."""
    current = _fetch_parameter(adapter, policy_set_id, params)
    key = params.get("key")
    want = {sdk_key: params[sdk_key] for sdk_key in _SDK_KEYS if params.get(sdk_key) is not None}

    if current is None:
        if not key:
            raise ValueError("'key' is required when creating a new policy set parameter.")
        if check_mode:
            return {"changed": True, "msg": f"Policy set parameter {key} would be created. Skipped creation due to check mode.", "key": key}
        created = create_policy_set_parameter(adapter, policy_set_id, want)
        return {"changed": True, **created}

    have = {sdk_key: current.get(sdk_key) for sdk_key in want.keys()}
    _strip_unverifiable_sensitive_value(have, want)
    diff = dict_diff(have, want)
    if not diff:
        return {"changed": False, **current}

    if check_mode:
        return {"changed": True, "msg": f"Policy set parameter {current['id']} would be updated. Skipped update due to check mode.", **want}

    updated = update_policy_set_parameter(adapter, policy_set_id, current["id"], want)
    return {"changed": True, **updated}


def state_absent(adapter: TerraformClient, policy_set_id: str, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the policy set parameter if present; no-op otherwise."""
    current = _fetch_parameter(adapter, policy_set_id, params)
    if current is None:
        return {"changed": False, "msg": "Policy set parameter is already absent."}

    parameter_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"Policy set parameter {parameter_id} would be deleted. Skipped deletion due to check mode."}

    delete_policy_set_parameter(adapter, policy_set_id, parameter_id)
    return {"changed": True, "msg": f"Policy set parameter {parameter_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "policy_set_id": {"type": "str", "required": True},
            "parameter_id": {"type": "str"},
            "key": {"type": "str", "no_log": False},
            "value": {"type": "str", "no_log": True},
            "sensitive": {"type": "bool"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_one_of=[("parameter_id", "key")],
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
                    action_result = state_present(adapter, params["policy_set_id"], params, params["check_mode"])
                case "absent":
                    action_result = state_absent(adapter, params["policy_set_id"], params, params["check_mode"])

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
