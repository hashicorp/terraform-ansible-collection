#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: tf_policy_evaluation_info
version_added: "2.2.0"
short_description: Read Terraform policy (tf-policy) evaluations and set outcomes for a run.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves tf-policy compliance results, either every evaluation for a C(run_id), or a
    single evaluation by C(evaluation_id).
  - tf-policy is HCP Terraform's native policy-as-code engine, evaluated during a run's Init,
    Plan, and Apply stages. This is distinct from the Sentinel/OPA policy-check flow surfaced by
    M(hashicorp.terraform.policy_check_info) and M(hashicorp.terraform.policy_evaluation_info).
  - This module only reads information and never changes state - it is designed to be used as a
    pre-flight compliance gate before Day 2 automation runs against infrastructure that may have
    failed or unresolved tf-policy findings.
  - HCP Terraform only - tf-policy has no Terraform Enterprise (self-hosted) equivalent.
extends_documentation_fragment: hashicorp.terraform.common
options:
  run_id:
    description:
      - The run ID to list tf-policy evaluations for (e.g. C(run-...)).
      - Mutually exclusive with C(evaluation_id).
    type: str
  evaluation_id:
    description:
      - The ID of a single tf-policy evaluation to read directly (e.g. C(tfpeval-...)).
      - Mutually exclusive with C(run_id).
    type: str
  include_outcomes:
    description:
      - When C(true), also fetches each evaluation's policy-set outcomes and attaches them as
        C(set_outcomes). This issues one additional API call per evaluation.
    type: bool
    default: false
  filter:
    description:
      - Narrows the C(set_outcomes) fetched when C(include_outcomes=true). Has no effect
        otherwise.
    type: dict
    suboptions:
      status:
        description: Only include outcomes with this status (e.g. C(failed)).
        type: str
      enforcement_level:
        description: Only include outcomes at this enforcement level (e.g. C(mandatory_overridable)).
        type: str
"""

EXAMPLES = r"""
- name: Gate on tf-policy compliance before Day 2 automation
  hashicorp.terraform.tf_policy_evaluation_info:
    run_id: "{{ tfc_run_id }}"
    include_outcomes: true
  register: posture

- name: Fail the play if the run is non-compliant
  ansible.builtin.assert:
    that:
      - posture.evaluations
        | selectattr('status', 'in', ['failed', 'errored'])
        | list | length == 0
    fail_msg: "Run {{ tfc_run_id }} has failed tf-policy evaluation(s)."

- name: Read one evaluation directly
  hashicorp.terraform.tf_policy_evaluation_info:
    evaluation_id: "tfpeval-EavQ1LztoRTQHSNT"
  register: evaluation

- name: List only mandatory-overridable failures for a run
  hashicorp.terraform.tf_policy_evaluation_info:
    run_id: "{{ tfc_run_id }}"
    include_outcomes: true
    filter:
      status: failed
      enforcement_level: mandatory_overridable
  register: posture
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
evaluations:
  description: The run's tf-policy evaluations, one per applicable stage.
  returned: when O(run_id) is provided
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the evaluation.
      type: str
      sample: "tfpeval-EavQ1LztoRTQHSNT"
    status:
      description: The evaluation's status.
      type: str
      sample: "awaiting_override"
    stage_type:
      description: The run stage this evaluation covers (C(Init), C(Plan), or C(Apply)).
      type: str
      sample: "Plan"
    result_count:
      description: Counts of passed/mandatory_failed/advisory_failed/errored/unknown outcomes.
      type: dict
    actions:
      description: Available actions on this evaluation.
      type: dict
      contains:
        is_overridable:
          description: Whether this evaluation can be overridden. Only true for Plan-stage evaluations.
          type: bool
    permissions:
      description: The caller's permissions on this evaluation.
      type: dict
      contains:
        can_override:
          description: Whether the caller has permission to override.
          type: bool
    created_at:
      description: When the evaluation was created.
      type: str
      sample: "2026-08-21T09:56:47.602000Z"
    updated_at:
      description: When the evaluation was last updated.
      type: str
      sample: "2026-08-21T09:57:13.711000Z"
    status_timestamps:
      description: Timestamps for each status transition the evaluation has gone through.
      type: dict
      sample:
        queued_at: "2026-08-21T09:56:48Z"
        running_at: "2026-08-21T09:56:51Z"
        awaiting_override_at: "2026-08-21T09:57:13Z"
    set_outcomes:
      description: Policy-set outcomes for this evaluation. Present only when C(include_outcomes=true).
      returned: when O(include_outcomes=true)
      type: list
      elements: dict
      contains:
        id:
          description: The unique identifier of the set outcome.
          type: str
          sample: "tfpsout-EavQ1LztoRTQHSNT"
        policy_set_name:
          description: The name of the policy set this outcome belongs to.
          type: str
        overridable:
          description: Whether this policy set's failures can be overridden.
          type: bool
        result_count:
          description: Counts of passed/mandatory_failed/advisory_failed/errored/unknown outcomes for this set.
          type: dict
        outcomes:
          description: The result of each individual policy in the set.
          type: list
          elements: dict
          contains:
            policy_name:
              description: The evaluated policy's name.
              type: str
            enforcement_level:
              description: The policy's enforcement level.
              type: str
              sample: "mandatory_overridable"
            status:
              description: The policy's result status.
              type: str
              sample: "failed"
            diagnostics:
              description: Diagnostic messages explaining why the policy failed, one per violating resource.
              type: list
              elements: dict
            passed_resources:
              description: Resources that satisfied the policy.
              type: list
              elements: dict
evaluation:
  description: A single tf-policy evaluation. Same shape as one element of C(evaluations) above.
  returned: when O(evaluation_id) is provided
  type: dict
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.tf_policy_evaluation import (
    get_evaluation,
    list_evaluations,
    list_set_outcomes,
)


def _attach_set_outcomes(adapter, evaluation: Dict[str, Any], filter_status, filter_enforcement_level) -> Dict[str, Any]:
    evaluation["set_outcomes"] = list_set_outcomes(
        adapter,
        evaluation["id"],
        filter_status=filter_status,
        filter_enforcement_level=filter_enforcement_level,
    )
    return evaluation


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "run_id": {"type": "str"},
            "evaluation_id": {"type": "str"},
            "include_outcomes": {"type": "bool", "default": False},
            "filter": {
                "type": "dict",
                "options": {
                    "status": {"type": "str"},
                    "enforcement_level": {"type": "str"},
                },
            },
        },
        required_one_of=[("run_id", "evaluation_id")],
        mutually_exclusive=[("run_id", "evaluation_id")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)
    filter_params = params.get("filter") or {}
    filter_status = filter_params.get("status")
    filter_enforcement_level = filter_params.get("enforcement_level")

    try:
        with module.client() as adapter:
            if params.get("run_id"):
                evaluations = list_evaluations(adapter, params["run_id"])
                if params["include_outcomes"]:
                    evaluations = [_attach_set_outcomes(adapter, e, filter_status, filter_enforcement_level) for e in evaluations]
                result["evaluations"] = evaluations
            else:
                evaluation = get_evaluation(adapter, params["evaluation_id"], include_outcomes=params["include_outcomes"])
                if evaluation is None:
                    raise ValueError(f"tf-policy evaluation with ID {params['evaluation_id']} not found")
                if params["include_outcomes"]:
                    evaluation = _attach_set_outcomes(adapter, evaluation, filter_status, filter_enforcement_level)
                result["evaluation"] = evaluation

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
