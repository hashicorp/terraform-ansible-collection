# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
name: tfe_policy_checks
short_description: Retrieve Sentinel policy check outcomes for a run
version_added: "2.0.0"
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Returns Sentinel policy check outcomes for a run, or a single policy check by ID.
  - Supports optional filtering to return only hard-failed or soft-failed checks for gating logic.
options:
  run_id:
    description:
      - The unique identifier of the run (e.g. C(run-...)).
      - Mutually exclusive with I(policy_check_id).
    type: str
  policy_check_id:
    description:
      - The unique identifier of a single policy check (e.g. C(polchk-...)).
      - Mutually exclusive with I(run_id).
    type: str
  only_failures:
    description: When I(true), return only policy checks whose status indicates failure.
    type: bool
    default: false
  tfe_address:
    description:
      - Terraform Cloud/Enterprise API address.
      - Falls back to the C(TFE_ADDRESS) environment variable when not set.
    type: str
    default: https://app.terraform.io
  tfe_token:
    description:
      - Terraform Cloud/Enterprise API token.
      - Falls back to the C(TFE_TOKEN) environment variable when not set.
      - The C(tf_token) alias is kept for compatibility with older collection releases.
    type: str
    required: true
    aliases: ['tf_token']
  tfe_timeout:
    description:
      - HTTP request timeout in seconds used by the underlying pytfe SDK.
      - Falls back to the C(TFE_TIMEOUT) environment variable when not set.
    type: float
    default: 30.0
  tfe_verify_tls:
    description:
      - Whether to verify TLS certificates when talking to the Terraform Cloud/Enterprise API.
      - Falls back to the C(TFE_VERIFY_TLS) environment variable when not set.
    type: bool
    default: true
  tfe_max_retries:
    description:
      - Maximum number of automatic retries the pytfe SDK performs for transient HTTP failures.
      - Falls back to the C(TFE_MAX_RETRIES) environment variable when not set.
    type: int
    default: 5
  tfe_ca_bundle:
    description:
      - Path to a CA bundle file used to verify TLS certificates.
      - Falls back to the C(SSL_CERT_FILE) environment variable when not set.
    type: path
  tfe_proxies:
    description:
      - HTTP/HTTPS proxy URL passed through to the pytfe SDK.
    type: str
"""

EXAMPLES = r"""
- name: Get all policy checks for a run
  ansible.builtin.debug:
    msg: "{{ lookup('hashicorp.terraform.tfe_policy_checks', run_id='run-abc123') }}"

- name: Fail if any hard-mandatory policy check failed
  ansible.builtin.fail:
    msg: "Mandatory policy checks failed on run {{ run_id }}"
  when: lookup('hashicorp.terraform.tfe_policy_checks',
               run_id=run_id, only_failures=true)
        | selectattr('status', 'equalto', 'hard_failed') | list | length > 0
"""

RETURN = r"""
_raw:
  description: List of policy check payloads (id, status, scope, result, permissions, actions).
  type: list
  elements: dict
"""

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_check import (
    HARD_FAIL_STATUSES,
    SOFT_FAIL_STATUSES,
    get_policy_check,
    list_policy_checks,
)


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        run_id = kwargs.get("run_id")
        policy_check_id = kwargs.get("policy_check_id")
        only_failures = bool(kwargs.get("only_failures", False))

        if run_id and policy_check_id:
            raise AnsibleError("run_id and policy_check_id are mutually exclusive.")
        if not run_id and not policy_check_id:
            raise AnsibleError("Either run_id or policy_check_id is required.")

        try:
            with TerraformClient.from_mapping(kwargs) as adapter:
                if policy_check_id:
                    single = get_policy_check(adapter, policy_check_id)
                    if not single:
                        raise AnsibleError(f"Policy check {policy_check_id} not found.")
                    checks = [single]
                else:
                    checks = list_policy_checks(adapter, run_id)
        except AnsibleError:
            raise
        except Exception as e:
            raise AnsibleError(f"tfe_policy_checks lookup failed: {e}")

        if only_failures:
            failing = HARD_FAIL_STATUSES | SOFT_FAIL_STATUSES
            checks = [c for c in checks if c.get("status") in failing]
        return checks
