#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: policy_check
version_added: "2.2.0"
short_description: Override a soft-mandatory Terraform Cloud/Enterprise policy check.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Overrides a soft-mandatory or warning Sentinel policy check on a run, allowing it to
    proceed despite a policy failure.
  - Idempotent - the check is read first; if it is already C(overridden), the module reports
    C(changed=false) without calling the API again.
  - Policy checks support Sentinel versions up to 0.40.x only. HashiCorp's own docs recommend
    policy evaluations (tf_policy_evaluation) instead for newer Sentinel versions and OPA -
    this module only applies to the legacy policy-checks surface.
extends_documentation_fragment: hashicorp.terraform.common
options:
  policy_check_id:
    description:
      - The ID of the policy check to override.
    type: str
    required: true
  override:
    description:
      - Must be C(true) for the module to call the API. Set to C(false) to make the task a
        documented no-op (for example, to gate the override behind a variable without adding a
        separate C(when) clause).
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Override a soft-mandatory policy check
  hashicorp.terraform.policy_check:
    policy_check_id: "polchk-EasPB4Srx5NAiWAU"
    override: true

- name: Gate the override behind a variable without a separate when clause
  hashicorp.terraform.policy_check:
    policy_check_id: "polchk-EasPB4Srx5NAiWAU"
    override: "{{ should_override | default(false) }}"
"""

RETURN = r"""
changed:
  description: Whether the override was invoked against the API.
  returned: always
  type: bool
  sample: true
id:
  description: The policy check identifier.
  returned: always
  type: str
  sample: "polchk-EasPB4Srx5NAiWAU"
status:
  description: The policy check's status after the operation.
  returned: always
  type: str
  sample: "overridden"
msg:
  description: Informational message, primarily for the override=false no-op, already-overridden no-op, and check mode.
  returned: when relevant
  type: str
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_check import get_policy_check, override_policy_check


def do_override(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Override the given policy check, honoring the override gate, idempotency, and check mode."""
    policy_check_id = params["policy_check_id"]

    if not params.get("override", True):
        return {"changed": False, "id": policy_check_id, "msg": f"override is false; no action taken for policy check {policy_check_id}."}

    current = get_policy_check(adapter, policy_check_id)
    if current is None:
        raise ValueError(f"Policy check {policy_check_id} not found")

    if current.get("status") == "overridden":
        return {"changed": False, **current}

    if check_mode:
        return {"changed": True, "id": policy_check_id, "msg": f"Policy check {policy_check_id} would be overridden. Skipped due to check mode."}

    overridden = override_policy_check(adapter, policy_check_id)
    return {"changed": True, **overridden}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "policy_check_id": {"type": "str", "required": True},
            "override": {"type": "bool", "default": True},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            action_result = do_override(adapter, params, params["check_mode"])
            result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
