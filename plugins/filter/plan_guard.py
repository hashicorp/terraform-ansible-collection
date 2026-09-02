# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
  name: plan_guard
  short_description: Evaluate a plan_analyze result against allow/deny drift rules
  version_added: "2.2.0"
  author: "Sivaselvan I (@isivaselvan)"
  description:
    - Evaluate the result of M(hashicorp.terraform.plan_analyze) against C(allow) / C(deny) glob rules and
      return a single, auditable decision about whether the detected drift is safe to absorb into
      Terraform state via a refresh-only apply.
    - This is a pure, offline decision layer - it performs no API calls. Use it inline in a play (for
      example piped into C(set_fact)) rather than as a module, since it never needs to fork a Python
      interpreter and can be composed directly with C(when:).
    - Pair with the P(hashicorp.terraform.plan_safe#test) test plugin for a boolean, ergonomic C(when:)
      condition.
    - Each rule is matched against a canonical target string built as
      C(<module_path>.<type>.<name>.<attribute.path>) (list indices stripped), or
      C(output.<name>) for output changes. C(*) in a rule spans dots, and a rule on a parent path (for
      example C(*.tags)) also matches child paths (C(tags.role)).
    - Precedence is C(blocked > deny > allow). A resource that M(hashicorp.terraform.plan_analyze) already
      classified C(blocked) is escalated unconditionally and cannot be overridden by an C(allow) rule. A
      target matching both C(allow) and C(deny) is denied.
    - This is a client-side, attribute-path gate for approving refresh-only applies. It is not a
      replacement for TFE-native Sentinel/OPA policy checks.
  positional: allow, deny, mode
  options:
    _input:
      description: The registered result of a M(hashicorp.terraform.plan_analyze) task.
      type: dict
      required: true
    allow:
      description: Rules for attribute targets that are acceptable to absorb into state.
      type: list
      elements: str
      default: []
    deny:
      description: Rules for attribute targets that must never be absorbed. Always wins over O(allow).
      type: list
      elements: str
      default: []
    mode:
      description:
        - C(strict) is default-deny - an attribute matched by neither O(allow) nor O(deny), or any
          computed/unknown attribute, makes the drift unsafe.
        - C(permissive) is default-allow - only O(deny) matches (or a C(blocked) classification) block.
      type: str
      choices: ['strict', 'permissive']
      default: strict
"""

EXAMPLES = r"""
- name: Gate a refresh-only apply on the plan_guard decision
  ansible.builtin.set_fact:
    guard: "{{ drift_analysis | hashicorp.terraform.plan_guard(allow=allow_rules, deny=deny_rules, mode='strict') }}"

- name: Fail loudly on any denied drift
  ansible.builtin.assert:
    that: "guard.safe_to_refresh"
    fail_msg: "Denied drift: {{ guard.denied }}"
"""

RETURN = r"""
  _value:
    description: The plan_guard decision.
    type: dict
    contains:
      safe_to_refresh:
        description: Whether the detected drift is safe to accept via a refresh-only apply.
        type: bool
      mode:
        description: The mode that was applied.
        type: str
      summary:
        description: Count of attribute changes per bucket.
        type: dict
      allowed:
        description: Attribute changes permitted to be absorbed.
        type: list
        elements: dict
      denied:
        description: Attribute changes blocked by a deny rule or left unmatched in strict mode.
        type: list
        elements: dict
      blocked:
        description: Attribute changes on resources plan_analyze classified as blocked.
        type: list
        elements: dict
      unknown:
        description: Computed (unknown-until-apply) attribute changes.
        type: list
        elements: dict
      reasons:
        description: Human-readable reasons behind the decision.
        type: list
        elements: str
"""

from ansible_collections.hashicorp.terraform.plugins.module_utils.drift_policy import (
    evaluate,
)


def plan_guard(analysis, allow=None, deny=None, mode="strict"):
    """Evaluate a plan_analyze result against allow/deny drift rules."""
    return evaluate(analysis or {}, allow=allow, deny=deny, mode=mode)


class FilterModule:
    def filters(self):
        return {"plan_guard": plan_guard}
