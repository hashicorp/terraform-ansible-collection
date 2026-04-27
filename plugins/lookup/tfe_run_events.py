# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
name: tfe_run_events
short_description: Retrieve the timeline of events for a Terraform Cloud/Enterprise run
version_added: "2.0.0"
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Returns the ordered list of run events (state transitions, comments, etc.) for a run.
  - Supports filtering by action name and by creation-time window (UTC ISO-8601 strings).
options:
  run_id:
    description: The unique identifier of the run (e.g. C(run-...)).
    type: str
    required: true
  action:
    description:
      - Optional filter - return only events whose C(action) matches this value
        (e.g. C(created), C(applied), C(canceled)).
    type: str
  since:
    description:
      - Optional lower bound on C(created_at), ISO-8601 string (UTC).
    type: str
  until:
    description:
      - Optional upper bound on C(created_at), ISO-8601 string (UTC).
    type: str
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
- name: Get all events for a run
  ansible.builtin.debug:
    msg: "{{ lookup('hashicorp.terraform.tfe_run_events', run_id='run-abc123') }}"

- name: Get only applied events since a timestamp
  ansible.builtin.set_fact:
    applied_events: "{{ lookup('hashicorp.terraform.tfe_run_events',
                              run_id='run-abc123',
                              action='applied',
                              since='2026-01-01T00:00:00Z') }}"
"""

RETURN = r"""
_raw:
  description: Ordered list of event payloads (id, action, created_at, description, actor, comment).
  type: list
  elements: dict
"""

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.run_event import filter_events, list_run_events


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        run_id = kwargs.get("run_id")
        if not run_id:
            raise AnsibleError("run_id is required.")
        action = kwargs.get("action")
        since = kwargs.get("since")
        until = kwargs.get("until")

        try:
            with TerraformClient.from_mapping(kwargs) as adapter:
                events = list_run_events(adapter, run_id)
        except Exception as e:
            raise AnsibleError(f"tfe_run_events lookup failed: {e}")

        return filter_events(events, action=action, since=since, until=until)
