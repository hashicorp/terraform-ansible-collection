#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: hyok_configuration
version_added: "2.2.0"
short_description: Manage HCP Terraform HYOK (Hold Your Own Key) configurations.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Manages a HYOK (Hold Your Own Key) configuration, which lets an organization encrypt
    workspace state and plan data with a customer-controlled KMS key. Requires the HYOK
    entitlement on the organization.
  - Every attribute is immutable once created - the underlying API has no update endpoint.
    If C(state=present) targets an existing configuration whose supplied options differ from
    the current ones, the module fails rather than silently ignoring the drift or replacing
    the configuration. To change any attribute, explicitly run with C(state=absent) first,
    then C(state=present) again with the new values.
  - C(state=absent) must revoke the configuration before it can be deleted - the API rejects
    deleting a configuration that is not already C(revoked). This module does that
    automatically - if the target isn't already revoked, it calls the revoke action and polls
    until the status reaches C(revoked) (bounded by C(timeout)/C(poll_interval)) before deleting.
    Set C(wait=false) to only trigger the revoke and stop - the module will not attempt delete
    in that case, since the API would reject it.
  - Setting C(test=true) invokes the async key-access test action against the (existing or
    just-created) configuration and, by default, waits for a terminal result
    (C(available)/C(active) or C(test_failed)), failing the task if the result is
    C(test_failed).
  - Identify a configuration either directly by C(hyok_configuration_id), or by the combination
    of C(organization) and C(name).
extends_documentation_fragment: hashicorp.terraform.common
options:
  hyok_configuration_id:
    description:
      - The unique identifier of the HYOK configuration (e.g. C(hyokc-...)).
      - Provide for unambiguous update-drift-check or delete operations.
    type: str
  organization:
    description:
      - The name of the organization that owns the HYOK configuration.
      - Required unless C(hyok_configuration_id) is provided.
    type: str
  name:
    description:
      - Human-readable label for the HYOK configuration.
      - Required when creating, or when identifying the configuration by (organization, name).
    type: str
  kek_id:
    description:
      - The name/ID of the key-encryption-key in your KMS.
      - Required when creating a new configuration.
    type: str
  agent_pool_id:
    description:
      - The ID of the agent pool used to reach your KMS.
      - Required when creating a new configuration.
    type: str
  oidc_configuration_id:
    description:
      - The ID of the OIDC configuration HCP Terraform authenticates to your KMS with.
      - Required when creating a new configuration.
    type: str
  oidc_configuration_type:
    description:
      - The cloud provider of the OIDC configuration referenced by C(oidc_configuration_id).
      - Required when creating a new configuration.
    type: str
    choices: ["aws", "azure", "gcp", "vault"]
  primary:
    description:
      - Whether this is the organization's primary HYOK configuration.
    type: bool
  kms_options:
    description:
      - Optional KMS-specific options.
    type: dict
    suboptions:
      key_region:
        description: Cloud region of the key, for KMS providers that require it.
        type: str
      key_location:
        description: Cloud location of the key, for KMS providers that require it.
        type: str
      key_ring_id:
        description: Key ring identifier, for KMS providers that require it (e.g. GCP).
        type: str
  test:
    description:
      - When C(true), invokes the key-access test action against the configuration after
        ensuring it exists.
    type: bool
    default: false
  wait:
    description:
      - When C(true), block until the C(revoke) (on C(state=absent)) or C(test) action reaches
        a terminal status, subject to C(timeout)/C(poll_interval).
      - When C(false) on C(state=absent), the module triggers revoke and returns without
        attempting delete (which the API would reject pre-revoke).
      - When C(false) with C(test=true), the module triggers the test action and returns
        immediately without checking the result.
    type: bool
    default: true
  timeout:
    description:
      - Maximum seconds to wait for an async action to reach a terminal status when C(wait=true).
    type: int
    default: 300
  poll_interval:
    description:
      - Seconds to sleep between status polls when C(wait=true).
    type: int
    default: 5
  state:
    description:
      - Desired state of the HYOK configuration.
      - C(present) creates the configuration if missing, or validates an existing one has no
        drifted attributes.
      - C(absent) revokes (if needed) and deletes the configuration.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a HYOK configuration
  hashicorp.terraform.hyok_configuration:
    organization: "my-org"
    name: "prod-key"
    kek_id: "arn:aws:kms:us-east-1:123456789012:key/abcd-1234"
    agent_pool_id: "apool-x"
    oidc_configuration_id: "aoidc-x"
    oidc_configuration_type: "aws"
    state: present

- name: Idempotent re-run with identical input
  hashicorp.terraform.hyok_configuration:
    organization: "my-org"
    name: "prod-key"
    kek_id: "arn:aws:kms:us-east-1:123456789012:key/abcd-1234"
    agent_pool_id: "apool-x"
    oidc_configuration_id: "aoidc-x"
    oidc_configuration_type: "aws"
    state: present

- name: Create and immediately validate key access, failing the task if the test fails
  hashicorp.terraform.hyok_configuration:
    organization: "my-org"
    name: "prod-key"
    kek_id: "arn:aws:kms:us-east-1:123456789012:key/abcd-1234"
    agent_pool_id: "apool-x"
    oidc_configuration_id: "aoidc-x"
    oidc_configuration_type: "aws"
    test: true
    timeout: 120
    state: present

- name: Revoke and delete a HYOK configuration, waiting for revocation to complete
  hashicorp.terraform.hyok_configuration:
    hyok_configuration_id: "hyokc-L4CxAJEEn8vEUEkj"
    state: absent

- name: Only trigger revocation without waiting or deleting
  hashicorp.terraform.hyok_configuration:
    hyok_configuration_id: "hyokc-L4CxAJEEn8vEUEkj"
    wait: false
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The HYOK configuration identifier.
  returned: when state is present
  type: str
  sample: "hyokc-L4CxAJEEn8vEUEkj"
name:
  description: The HYOK configuration name.
  returned: when state is present
  type: str
  sample: "prod-key"
status:
  description: Current lifecycle status.
  returned: when state is present
  type: str
  sample: "available"
error:
  description: Error detail when status is errored or test_failed.
  returned: when relevant
  type: str
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "HYOK configuration hyokc-L4CxAJEEn8vEUEkj has been deleted successfully"
"""

import time
from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.hyok_configuration import (
    OIDC_CONFIGURATION_TYPE_MAP,
    create_hyok_configuration,
    delete_hyok_configuration,
    get_hyok_configuration,
    get_hyok_configuration_by_name,
    revoke_hyok_configuration,
    run_hyok_configuration_test,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff

# Argspec keys that are plumbing, not HYOK configuration attributes, and must
# be filtered out before diffing / sending to pytfe.
_NON_SDK_KEYS = {"hyok_configuration_id", "organization", "state", "check_mode", "test", "wait", "timeout", "poll_interval"}

_REVOKE_STALL_STATUSES = {"revoking"}
_TEST_STALL_STATUSES = {"testing"}


def _fetch_hyok_configuration(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target HYOK configuration by ID or by (organization, name)."""
    hyok_configuration_id = params.get("hyok_configuration_id")
    if hyok_configuration_id:
        return get_hyok_configuration(adapter, hyok_configuration_id)
    organization = params.get("organization")
    name = params.get("name")
    if organization and name:
        return get_hyok_configuration_by_name(adapter, organization, name)
    return None


def _build_desired_state(params: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the SDK-relevant, non-None attributes the user asked for."""
    return {key: value for key, value in params.items() if not key.startswith(("tf_", "tfe_")) and key not in _NON_SDK_KEYS and value is not None}


def _wait_while(adapter: TerraformClient, hyok_configuration_id: str, stall_statuses: set, timeout: int, poll_interval: int) -> Optional[Dict[str, Any]]:
    """Poll until status leaves stall_statuses or the timeout elapses.

    Always sleeps once before the first read, since the async action was just
    triggered and the first read otherwise risks observing a stale pre-action
    status.
    """
    deadline = time.time() + timeout
    time.sleep(poll_interval)
    current = get_hyok_configuration(adapter, hyok_configuration_id)
    while current and current.get("status") in stall_statuses and time.time() < deadline:
        time.sleep(poll_interval)
        current = get_hyok_configuration(adapter, hyok_configuration_id)
    return current


def _run_test_action(adapter: TerraformClient, config: Dict[str, Any], params: Dict[str, Any], check_mode: bool) -> Dict[str, Any]:
    """Invoke the test action against config, honoring wait/timeout/poll_interval."""
    hyok_configuration_id = config["id"]
    if check_mode:
        return {**config, "changed": True, "msg": f"HYOK configuration {hyok_configuration_id} would be tested. Skipped due to check mode."}

    run_hyok_configuration_test(adapter, hyok_configuration_id)

    if not params.get("wait", True):
        return {**config, "changed": True, "msg": f"Test triggered for HYOK configuration {hyok_configuration_id} (wait=false, result not checked)."}

    final = _wait_while(adapter, hyok_configuration_id, _TEST_STALL_STATUSES, params.get("timeout", 300), params.get("poll_interval", 5))
    final = final or config
    if final.get("status") == "test_failed":
        raise ValueError(f"HYOK configuration {hyok_configuration_id} test failed: {final.get('error') or 'no error detail returned'}")
    return {**final, "changed": True}


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create a HYOK configuration, or validate an existing one has no drift."""
    current = _fetch_hyok_configuration(adapter, params)
    want = _build_desired_state(params)

    if current is None:
        organization = params.get("organization")
        name = params.get("name")
        if not organization:
            raise ValueError("'organization' is required when creating a new HYOK configuration.")
        for required in ("name", "kek_id", "agent_pool_id", "oidc_configuration_id", "oidc_configuration_type"):
            if not want.get(required):
                raise ValueError(f"{required!r} is required when creating a new HYOK configuration.")

        if check_mode:
            result: Dict[str, Any] = {
                "changed": True,
                "msg": f"HYOK configuration {name} would be created. Skipped creation due to check mode.",
                "name": name,
            }
        else:
            create_data = dict(want)
            create_data["oidc_configuration_type"] = OIDC_CONFIGURATION_TYPE_MAP[create_data["oidc_configuration_type"]]
            created = create_hyok_configuration(adapter, organization, create_data)
            result = {"changed": True, **created}
    else:
        comparable = {key: value for key, value in want.items() if key != "name"}
        if "oidc_configuration_type" in comparable:
            # `want` carries the short argspec value (e.g. "vault"); the API
            # always reports the wire-level JSON:API type (e.g.
            # "vault-oidc-configurations") on read. Compare like-for-like or
            # every re-run would falsely detect drift on this field.
            mapped = OIDC_CONFIGURATION_TYPE_MAP[comparable["oidc_configuration_type"]]
            comparable["oidc_configuration_type"] = getattr(mapped, "value", mapped)
        have = {key: current.get(key) for key in comparable.keys()}
        diff = dict_diff(have, comparable)
        if diff:
            raise ValueError(
                f"HYOK configuration {current['id']} has drifted from the supplied options ({sorted(diff.keys())}), "
                "but every attribute is immutable server-side (no update endpoint exists). "
                "Run with state=absent then state=present again to replace it."
            )
        result = {"changed": False, **current}

    if params.get("test"):
        config_for_test = result if result.get("id") else _fetch_hyok_configuration(adapter, params)
        if config_for_test is None:
            # Only reachable in check_mode create, where nothing was actually created.
            return {**result, "msg": result.get("msg", "") + " Test skipped: configuration does not exist yet (check mode)."}
        test_result = _run_test_action(adapter, config_for_test, params, check_mode)
        result = {**result, **test_result, "changed": result.get("changed", False) or test_result.get("changed", False)}

    return result


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Revoke (if needed) and delete the HYOK configuration; no-op if already absent."""
    current = _fetch_hyok_configuration(adapter, params)
    if current is None:
        return {"changed": False, "msg": "HYOK configuration is already absent."}

    hyok_configuration_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"HYOK configuration {hyok_configuration_id} would be revoked (if needed) and deleted. Skipped due to check mode."}

    status = current.get("status")
    if status != "revoked":
        revoke_hyok_configuration(adapter, hyok_configuration_id)
        if not params.get("wait", True):
            return {
                "changed": True,
                "msg": f"Revoke triggered for HYOK configuration {hyok_configuration_id} (wait=false); delete was not attempted.",
            }
        final = _wait_while(adapter, hyok_configuration_id, _REVOKE_STALL_STATUSES, params.get("timeout", 300), params.get("poll_interval", 5))
        if not final or final.get("status") != "revoked":
            raise ValueError(
                f"Timed out waiting for HYOK configuration {hyok_configuration_id} to reach status=revoked "
                f"(last observed: {(final or {}).get('status')!r})."
            )

    delete_hyok_configuration(adapter, hyok_configuration_id)
    return {"changed": True, "msg": f"HYOK configuration {hyok_configuration_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "hyok_configuration_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
            "kek_id": {"type": "str"},
            "agent_pool_id": {"type": "str"},
            "oidc_configuration_id": {"type": "str"},
            "oidc_configuration_type": {"type": "str", "choices": ["aws", "azure", "gcp", "vault"]},
            "primary": {"type": "bool"},
            "kms_options": {
                "type": "dict",
                "options": {
                    "key_region": {"type": "str", "no_log": False},
                    "key_location": {"type": "str", "no_log": False},
                    "key_ring_id": {"type": "str"},
                },
            },
            "test": {"type": "bool", "default": False},
            "wait": {"type": "bool", "default": True},
            "timeout": {"type": "int", "default": 300},
            "poll_interval": {"type": "int", "default": 5},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_one_of=[("hyok_configuration_id", "name")],
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
                    action_result = state_present(adapter, params, params["check_mode"])
                case "absent":
                    action_result = state_absent(adapter, params, params["check_mode"])

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
