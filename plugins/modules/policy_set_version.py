#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: policy_set_version
version_added: "2.2.0"
short_description: Create and upload a Terraform Cloud/Enterprise policy set version.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Creates a new version of a non-VCS-backed M(hashicorp.terraform.policy_set) and uploads a
    local directory of policy files to it, in one task - the same create-then-upload shape as
    M(hashicorp.terraform.configuration_version).
  - There is no update or delete/archive endpoint for policy set versions - they are immutable
    once created. B(Every successful run of this module creates a new version) - there is no
    way to check "does an equivalent version already exist" beforehand, so this module is not
    idempotent by nature. Guard repeated runs with C(when) if that matters to your workflow.
  - Waits for the version to leave C(pending) status (into C(ready) or C(errored)), bounded by
    C(poll_interval)/C(poll_timeout). If the timeout elapses first, the module reports
    C(changed=true) with the last observed status rather than failing the task - the version
    was created and uploaded either way.
extends_documentation_fragment: hashicorp.terraform.common
options:
  policy_set_id:
    description:
      - The ID of the (non-VCS-backed) policy set to create a new version for.
    type: str
    required: true
  policy_files_path:
    description:
      - Path to a local directory containing policy files (e.g. C(./policies)). Packed and
        uploaded the same way C(terraform login)-style CLI uploads work - no need to pre-tar it.
    type: str
    required: true
  poll_interval:
    description:
      - Seconds to wait between status polls.
    type: int
    default: 2
  poll_timeout:
    description:
      - Maximum seconds to wait for the version to leave C(pending) status.
    type: int
    default: 10
"""

EXAMPLES = r"""
- name: Create and upload a new policy set version
  hashicorp.terraform.policy_set_version:
    policy_set_id: "polset-EavQ1LztoRTQHSNT"
    policy_files_path: "./policies"
    poll_interval: 3
    poll_timeout: 30
  register: result

- name: Fail the play if the version didn't become ready
  ansible.builtin.fail:
    msg: "Policy set version {{ result.id }} ended in status {{ result.status }}"
  when: result.status != "ready"
"""

RETURN = r"""
changed:
  description: Always true - every successful run creates a new version.
  returned: always
  type: bool
  sample: true
id:
  description: The policy set version identifier.
  returned: always
  type: str
  sample: "polsetver-EavQ1LztoRTQHSNT"
status:
  description: The version's status after polling (C(ready), C(errored), or still C(pending)/C(ingressing) if polling timed out).
  returned: always
  type: str
  sample: "ready"
error:
  description: Error detail when status is errored.
  returned: when relevant
  type: str
msg:
  description: Informational message, set when polling times out before reaching a terminal status.
  returned: when relevant
  type: str
"""

import time
from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_set_version import (
    create_policy_set_version,
    get_policy_set_version,
    upload_policy_set_version,
)

_STALL_STATUSES = {"pending", "ingressing"}


def _poll_until_terminal(adapter: TerraformClient, policy_set_version_id: str, poll_interval: int, poll_timeout: int) -> Dict[str, Any]:
    """Poll until status leaves pending/ingressing or the timeout elapses."""
    deadline = time.time() + poll_timeout
    current = get_policy_set_version(adapter, policy_set_version_id)
    while current and current.get("status") in _STALL_STATUSES and time.time() < deadline:
        time.sleep(poll_interval)
        current = get_policy_set_version(adapter, policy_set_version_id)
    return current or {}


def create_and_upload(adapter: TerraformClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new policy set version and upload the given local directory to it."""
    created = create_policy_set_version(adapter, params["policy_set_id"])
    upload_policy_set_version(adapter, created["id"], params["policy_files_path"])

    final = _poll_until_terminal(adapter, created["id"], params["poll_interval"], params["poll_timeout"])
    final = final or created

    result = {"changed": True, **final}
    if final.get("status") in _STALL_STATUSES:
        result["msg"] = f"Policy set version {final.get('id')} was created and uploaded but did not reach a terminal status within poll_timeout."
    return result


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "policy_set_id": {"type": "str", "required": True},
            "policy_files_path": {"type": "str", "required": True},
            "poll_interval": {"type": "int", "default": 2},
            "poll_timeout": {"type": "int", "default": 10},
        },
        supports_check_mode=False,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            result.update(create_and_upload(adapter, params))
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
