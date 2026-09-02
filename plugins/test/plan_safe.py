# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
  name: plan_safe
  short_description: Test whether a plan_analyze result is safe to refresh under allow/deny drift rules
  version_added: "2.2.0"
  author: "Sivaselvan I (@isivaselvan)"
  description:
    - Ergonomic boolean wrapper around P(hashicorp.terraform.plan_guard#filter), for use directly in
      C(when:) without an intermediate C(set_fact).
    - Returns the same C(safe_to_refresh) verdict the P(hashicorp.terraform.plan_guard#filter) filter
      would return for the same inputs.
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
- name: Confirm the run only when the drift is safe to accept
  hashicorp.terraform.promote_run:
    run_id: "{{ refresh_run.id }}"
    action: apply
  when: drift_analysis is hashicorp.terraform.plan_safe(allow=allow_rules, deny=deny_rules)
"""

RETURN = r"""
  _value:
    description: Whether the detected drift is safe to accept via a refresh-only apply.
    type: bool
"""

from ansible_collections.hashicorp.terraform.plugins.module_utils.drift_policy import (
    evaluate,
)


def plan_safe(analysis, allow=None, deny=None, mode="strict"):
    """Return whether a plan_analyze result is safe to refresh under allow/deny drift rules."""
    return evaluate(analysis or {}, allow=allow, deny=deny, mode=mode)["safe_to_refresh"]


class TestModule:
    def tests(self):
        return {"plan_safe": plan_safe}
