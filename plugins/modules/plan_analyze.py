# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: plan_analyze
version_added: "2.2.0"
short_description: Analyze a Terraform plan for drift and change classification
author: "Sivaselvan I (@isivaselvan)"
description:
  - Parse a Terraform execution plan JSON document and return Ansible-friendly drift and change facts.
  - Complements M(hashicorp.terraform.view_plan), which renders a human-readable diff. This module instead
    returns machine-consumable facts - which resources are affected, which attribute paths changed, and a
    per-resource safety classification.
  - The plan JSON can be fetched from HashiCorp Terraform Cloud or Terraform Enterprise using a C(run_id) or
    C(plan_id), or supplied inline via C(plan_json) (useful for offline analysis or testing).
  - This is a read-only module. It never modifies infrastructure and always reports C(changed=false).
  - Targets Terraform 1.x plan JSON. An unrecognized C(format_version) major version does not fail the
    task; the module warns and proceeds best-effort.
  - Classification (O(safe_attributes)/O(risky_attributes)/O(blocked_attributes)) is descriptive only and
    defaults to empty, fail-closed rule sets - it does not ship AWS-specific opinions, since this module
    targets HCP Terraform/TFE generically. Pair this module with the
    P(hashicorp.terraform.plan_guard#filter) filter and
    P(hashicorp.terraform.plan_safe#test) test plugins for an authoritative accept/deny decision.
options:
  run_id:
    description:
      - The ID of a run whose plan JSON should be analyzed.
      - The module resolves the run's associated plan and fetches its JSON output.
      - Mutually exclusive with O(plan_id) and O(plan_json).
    type: str
  plan_id:
    description:
      - The ID of a plan whose JSON output should be analyzed.
      - Mutually exclusive with O(run_id) and O(plan_json).
    type: str
    aliases: ['id']
  plan_json:
    description:
      - A Terraform plan JSON document supplied inline, bypassing any API call.
      - Useful for analyzing a previously captured plan or for offline testing.
      - Mutually exclusive with O(run_id) and O(plan_id).
    type: dict
  detect_drift:
    description:
      - Walk the C(resource_drift) array of the plan JSON to surface out-of-band drift.
    type: bool
    default: true
  include_resource_changes:
    description:
      - Walk the C(resource_changes) array of the plan JSON to surface planned changes.
    type: bool
    default: true
  include_output_changes:
    description:
      - Analyze the C(output_changes) section of the plan JSON.
    type: bool
    default: true
  include_values:
    description:
      - When C(true), include the masked C(before) and C(after) values for each analyzed entry.
      - Values flagged in C(before_sensitive) / C(after_sensitive) are always masked, even when this is C(true).
    type: bool
    default: false
  safe_attributes:
    description:
      - Glob-style rules (see the collection's drift matching grammar) for attribute targets classified as
        C(safe). A changed attribute matching none of the classification lists also defaults to C(safe).
      - Defaults to an empty list. This module ships no built-in (e.g. AWS-specific) defaults; see EXAMPLES
        for an illustrative rule set.
    type: list
    elements: str
    default: []
  risky_attributes:
    description:
      - Glob-style rules for attribute targets classified as C(risky). Defaults to an empty list.
    type: list
    elements: str
    default: []
  blocked_attributes:
    description:
      - Glob-style rules for attribute targets classified as C(blocked). Classification precedence is
        C(blocked > risky > safe > unknown). Defaults to an empty list.
    type: list
    elements: str
    default: []
extends_documentation_fragment:
  - hashicorp.terraform.common
"""

EXAMPLES = r"""
- name: Analyze drift on a workspace's latest run
  hashicorp.terraform.plan_analyze:
    run_id: run-FDuANSTFnnDowa3C
    detect_drift: true
    include_resource_changes: true
  register: analysis

- name: Print drift and change summary
  ansible.builtin.debug:
    msg:
      - "Drift: {{ analysis.has_drift }} ({{ analysis.drift_count }})"
      - "Changes: {{ analysis.has_changes }} ({{ analysis.change_count }})"
      - "Risky: {{ analysis.summary.risky }}"
      - "Blocked: {{ analysis.summary.blocked }}"

- name: Analyze a plan by plan ID with a custom classification (illustrative AWS ruleset)
  hashicorp.terraform.plan_analyze:
    plan_id: plan-ZRJZNANFgoYhx3Ch
    blocked_attributes:
      - "aws_instance.*.ami"
      - "aws_iam_policy.*"
      - "aws_instance.*.subnet_id"
    risky_attributes:
      - "aws_instance.*.instance_type"
  register: analysis

- name: Fail the play when any blocked change is detected
  ansible.builtin.fail:
    msg: "Plan contains {{ analysis.summary.blocked }} blocked change(s)."
  when: analysis.summary.blocked > 0

- name: Analyze a captured plan JSON offline
  hashicorp.terraform.plan_analyze:
    plan_json: "{{ lookup('file', 'plan.json') | from_json }}"
    include_values: true
  register: analysis
"""

RETURN = r"""
changed:
  description: Always C(false); this module is read-only.
  returned: always
  type: bool
has_drift:
  description: Whether any out-of-band drift was detected.
  returned: always
  type: bool
drift_count:
  description: Number of drifted resources detected.
  returned: always
  type: int
has_changes:
  description: Whether the plan contains any resource changes.
  returned: always
  type: bool
change_count:
  description: Number of changed resources in the plan.
  returned: always
  type: int
resource_changes:
  description: Per-resource analysis entries, drawn from both drift and change sources.
  returned: always
  type: list
  elements: dict
  contains:
    address:
      description: Absolute resource address.
      type: str
    type:
      description: Resource type.
      type: str
    name:
      description: Resource name.
      type: str
    provider_name:
      description: Provider that manages the resource.
      type: str
    module_address:
      description: Address of the module containing the resource, if any.
      type: str
    mode:
      description: Resource mode (C(managed) or C(data)).
      type: str
    actions:
      description: The planned actions for the resource.
      type: list
      elements: str
    action_reason:
      description: The reason for the action, when Terraform provides one.
      type: str
    source:
      description: Which section the entry came from, C(resource_drift) or C(resource_changes).
      type: str
    changed_attributes:
      description: Concrete attribute paths that changed.
      type: list
      elements: str
    unknown_attributes:
      description: Attribute paths that are computed (unknown until apply).
      type: list
      elements: str
    classification:
      description:
        - Descriptive resource-level verdict, one of C(safe), C(risky), C(blocked), C(unknown), based on
          O(safe_attributes)/O(risky_attributes)/O(blocked_attributes).
        - This is descriptive only, not an authoritative accept/deny decision; use
          P(hashicorp.terraform.plan_guard#filter) for that.
      type: str
    change_summary:
      description: Human-readable count of attribute categories, e.g. C(1 risky, 1 safe).
      type: str
    before:
      description: Masked prior values (only when O(include_values=true)).
      type: raw
    after:
      description: Masked planned values (only when O(include_values=true)).
      type: raw
output_changes:
  description: Per-output analysis entries.
  returned: always
  type: list
  elements: dict
summary:
  description: Count of resources per classification.
  returned: always
  type: dict
  contains:
    safe:
      description: Number of resources classified C(safe).
      type: int
    risky:
      description: Number of resources classified C(risky).
      type: int
    blocked:
      description: Number of resources classified C(blocked).
      type: int
    unknown:
      description: Number of resources classified C(unknown).
      type: int
"""

from copy import deepcopy

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.plan import (
    get_plan_data,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.plan_analyze import (
    analyze_plan,
)


def _resolve_plan_json(module: AnsibleTerraformModule, params: dict) -> dict:
    """Return the plan JSON document to analyze.

    Uses inline ``plan_json`` when supplied; otherwise fetches it from the API
    using ``plan_id`` or ``run_id``.
    """
    plan_json = params.get("plan_json")
    if plan_json is not None:
        return plan_json

    plan_id = params.get("plan_id")
    run_id = params.get("run_id")
    identifier = plan_id if plan_id else run_id
    use_plan_id = plan_id is not None

    with module.client() as adapter:
        json_output = get_plan_data(adapter, identifier, use_plan_id, include_json_output=True)

    if not json_output:
        id_type = "Plan" if use_plan_id else "Plan for run"
        raise ValueError(f"{id_type} with ID '{identifier}' has no JSON output available.")

    return json_output


def main() -> None:
    """Main module execution function."""
    module = AnsibleTerraformModule(
        argument_spec={
            "run_id": {"type": "str"},
            "plan_id": {"type": "str", "aliases": ["id"]},
            "plan_json": {"type": "dict"},
            "detect_drift": {"type": "bool", "default": True},
            "include_resource_changes": {"type": "bool", "default": True},
            "include_output_changes": {"type": "bool", "default": True},
            "include_values": {"type": "bool", "default": False},
            "safe_attributes": {"type": "list", "elements": "str", "default": []},
            "risky_attributes": {"type": "list", "elements": "str", "default": []},
            "blocked_attributes": {"type": "list", "elements": "str", "default": []},
        },
        required_one_of=[["run_id", "plan_id", "plan_json"]],
        mutually_exclusive=[
            ["run_id", "plan_id"],
            ["run_id", "plan_json"],
            ["plan_id", "plan_json"],
        ],
        supports_check_mode=True,
    )

    params = deepcopy(module.params)

    try:
        plan_json = _resolve_plan_json(module, params)

        result = analyze_plan(
            plan_json,
            detect_drift=params.get("detect_drift"),
            include_resource_changes=params.get("include_resource_changes"),
            include_output_changes=params.get("include_output_changes"),
            include_values=params.get("include_values"),
            safe_attributes=params.get("safe_attributes"),
            risky_attributes=params.get("risky_attributes"),
            blocked_attributes=params.get("blocked_attributes"),
        )

        warning = result.pop("warning", None)
        if warning:
            module.warn(warning)

        module.exit_json(changed=False, **result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
