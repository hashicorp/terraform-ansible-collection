#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: promote_run
version_added: "2.0.0"
short_description: Gate and apply a Terraform Cloud/Enterprise run based on policy outcomes.
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Evaluates policy-check outcomes for a Terraform run and, when eligible, applies it.
  - Implemented as an action plugin that wraps the collection's pytfe-backed helpers; it
    does not issue its own HTTP calls.
  - Returns a structured C(gates) dictionary describing the decision taken so callers can
    inspect why the run was or was not applied.
  - Idempotent: runs already in a final state (applied, errored, canceled, discarded,
    planned_and_finished) are reported as a no-op.
extends_documentation_fragment: hashicorp.terraform.common
options:
  run_id:
    description:
      - The ID of the run to evaluate and potentially apply.
    type: str
    required: true
  require_policy_pass:
    description:
      - When true, mandatory policy failures block the apply.
    type: bool
    default: true
  allow_advisory_failures:
    description:
      - When true, advisory (soft-mandatory) policy failures are ignored.
      - Only meaningful when C(require_policy_pass=true).
    type: bool
    default: true
  wait:
    description:
      - When true, wait for the run to become appliable before evaluating policies.
    type: bool
    default: false
  timeout:
    description:
      - Maximum seconds to wait for the run to become appliable when C(wait=true).
    type: int
    default: 600
  poll_interval:
    description:
      - Seconds to sleep between run-status polls when C(wait=true).
    type: int
    default: 10
  auto_apply_when_eligible:
    description:
      - When true, apply the run after all gates pass.
      - When false, the run is evaluated but not applied.
    type: bool
    default: true
  comment:
    description:
      - Optional comment attached to the apply action.
    type: str
"""

EXAMPLES = r"""
- name: Apply a run only if mandatory policies pass
  hashicorp.terraform.promote_run:
    run_id: run-ABC123
    require_policy_pass: true
    allow_advisory_failures: true
    wait: true
    timeout: 900
  register: promote

- name: Evaluate policies without applying
  hashicorp.terraform.promote_run:
    run_id: run-ABC123
    auto_apply_when_eligible: false
  register: evaluation
"""

RETURN = r"""
changed:
  description: Whether the run was applied.
  type: bool
  returned: always
gates:
  description: Details on the decision taken.
  type: dict
  returned: always
  contains:
    run_status_before:
      description: Run status observed before the decision.
      type: str
    run_status_after:
      description: Run status observed after the apply (if applied).
      type: str
    policy_summary:
      description: Counts of policy-check outcomes by enforcement level.
      type: dict
    applied:
      description: Whether an apply was issued.
      type: bool
    skipped_reason:
      description: Human-readable reason when no apply was performed.
      type: str
run:
  description: The run object at the end of the action.
  type: dict
  returned: when the run exists
policy_checks:
  description: Raw policy-check records evaluated.
  type: list
  returned: when policy evaluation occurred
"""
