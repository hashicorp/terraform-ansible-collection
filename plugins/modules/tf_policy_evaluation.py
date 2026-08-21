#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: tf_policy_evaluation
version_added: "2.2.0"
short_description: Override a Terraform policy (tf-policy) evaluation.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Overrides a tf-policy evaluation that is C(awaiting_override), unblocking the run.
  - tf-policy evaluations are produced by Terraform runs and are never created, updated, or
    deleted directly by this module - C(state=overridden) is the only supported transition.
  - Override only succeeds for Plan-stage evaluations with at least one C(mandatory_overridable)
    failure and no non-overridable C(mandatory) failures. Init and Apply stage evaluations are
    never overridable regardless of enforcement level.
  - HCP Terraform only - tf-policy has no Terraform Enterprise (self-hosted) equivalent.
extends_documentation_fragment: hashicorp.terraform.common
options:
  evaluation_id:
    description:
      - The ID of the tf-policy evaluation to override (e.g. C(tfpeval-...)).
    type: str
    required: true
  comment:
    description:
      - An optional comment recorded with the override, for audit purposes.
    type: str
  state:
    description:
      - The only supported value is C(overridden). Kept explicit, rather than implied, to leave
        room for future evaluation actions without a breaking change.
    type: str
    choices: ["overridden"]
    default: "overridden"
"""

EXAMPLES = r"""
- name: Override a mandatory_overridable failure
  hashicorp.terraform.tf_policy_evaluation:
    evaluation_id: "{{ item.id }}"
    comment: "Ops approved - ticket OPS-123"
  loop: >-
    {{ posture.evaluations
       | selectattr('status', 'eq', 'awaiting_override')
       | selectattr('actions.is_overridable', 'eq', true)
       | list }}

- name: Override without a comment
  hashicorp.terraform.tf_policy_evaluation:
    evaluation_id: "tfpeval-EavQ1LztoRTQHSNT"
"""

RETURN = r"""
changed:
  description: Whether the evaluation was transitioned to C(overridden) by this run.
  returned: always
  type: bool
  sample: true
id:
  description: The tf-policy evaluation identifier.
  returned: always
  type: str
  sample: "tfpeval-EavQ1LztoRTQHSNT"
status:
  description: The evaluation's status after the operation.
  returned: always
  type: str
  sample: "overridden"
stage_type:
  description: The run stage this evaluation covers. Always C(Plan) - the only stage that can be overridden.
  returned: when the override was actually performed
  type: str
  sample: "Plan"
result_count:
  description: Counts of passed/mandatory_failed/advisory_failed/errored/unknown outcomes.
  returned: when the override was actually performed
  type: dict
actions:
  description: Available actions on this evaluation after the operation.
  returned: when the override was actually performed
  type: dict
permissions:
  description: The caller's permissions on this evaluation.
  returned: when the override was actually performed
  type: dict
msg:
  description: Informational message, primarily for no-op and check mode outcomes.
  returned: when relevant
  type: str
  sample: "tf-policy evaluation tfpeval-EavQ1LztoRTQHSNT is already in status 'overridden'"
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.tf_policy_evaluation import (
    get_evaluation,
    override_evaluation,
)


def state_overridden(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Override the evaluation if it is awaiting_override; no-op otherwise."""
    evaluation_id = params["evaluation_id"]
    current = get_evaluation(adapter, evaluation_id)
    if current is None:
        raise ValueError(f"tf-policy evaluation with ID {evaluation_id} not found")

    if current.get("status") != "awaiting_override":
        return {
            "changed": False,
            "id": evaluation_id,
            "status": current.get("status"),
            "msg": f"tf-policy evaluation {evaluation_id} is already in status '{current.get('status')}'",
        }

    if check_mode:
        return {
            "changed": True,
            "id": evaluation_id,
            "status": current.get("status"),
            "msg": f"tf-policy evaluation {evaluation_id} would be overridden. Skipped due to check mode.",
        }

    updated = override_evaluation(adapter, evaluation_id, comment=params.get("comment"))
    return {"changed": True, **updated}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "evaluation_id": {"type": "str", "required": True},
            "comment": {"type": "str"},
            "state": {"type": "str", "default": "overridden", "choices": ["overridden"]},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            action_result = state_overridden(adapter, params, module.check_mode)
            result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
