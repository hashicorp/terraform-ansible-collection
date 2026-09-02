#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: policy
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise policies (Sentinel, OPA, or tf-policy).
author: "Sivaselvan I (@isivaselvan)"
description:
  - Manages a standalone policy (as opposed to a VCS-backed policy set) on Terraform
    Cloud/Enterprise, including its Sentinel/OPA/tf-policy source content.
  - Identify a policy either directly by C(policy_id), or by the combination of C(organization)
    and C(name).
  - C(kind) and C(name) are immutable after creation - the update API accepts neither. If
    C(state=present) targets an existing policy with a different C(kind) or C(name) than
    supplied, the module fails with a clear message rather than silently ignoring the drift.
  - C(policy_content) is round-trippable - unlike some write-only resources in this collection,
    the API's C(download) endpoint returns the previously uploaded content, so drift on
    C(policy_content) is genuinely detected and re-uploaded, not just written once.
  - Attach the policy to workspaces by adding it to a M(hashicorp.terraform.policy_set).
extends_documentation_fragment: hashicorp.terraform.common
options:
  policy_id:
    description:
      - The unique identifier of the policy (e.g. C(pol-...)).
      - Provide for unambiguous update or delete operations.
    type: str
  organization:
    description:
      - The name of the organization that owns the policy.
      - Required unless C(policy_id) is provided.
    type: str
  name:
    description:
      - Human-readable name of the policy. Immutable after creation.
      - Required when identifying the policy by (organization, name), and when creating.
    type: str
  kind:
    description:
      - The policy engine. Immutable after creation.
      - Defaults to C(sentinel) when creating a new policy if omitted. Leave unset on updates
        to avoid a spurious drift error against an existing policy of a different kind.
    type: str
    choices: ["sentinel", "opa", "tfpolicy"]
  query:
    description:
      - The OPA query to run (e.g. C(terraform.main)). Required when C(kind=opa).
    type: str
  description:
    description:
      - Human-readable description of the policy.
    type: str
  enforcement_level:
    description:
      - Enforcement level for the policy.
      - Required when creating a new policy.
    type: str
    choices: ["advisory", "mandatory", "hard-mandatory", "soft-mandatory"]
  policy_content:
    description:
      - The policy source code (Sentinel/Rego/tf-policy) to upload.
      - Omit to manage only the policy's metadata and leave any existing content untouched.
    type: str
  state:
    description:
      - Desired state of the policy.
      - C(present) creates or updates the policy (and its content, if C(policy_content) is given).
      - C(absent) deletes the policy if it exists.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a Sentinel policy with content
  hashicorp.terraform.policy:
    organization: "my-org"
    name: "restrict-instance-type"
    kind: sentinel
    enforcement_level: hard-mandatory
    policy_content: "main = rule { true }"
    state: present
  register: result

- name: Idempotent re-run with identical content
  hashicorp.terraform.policy:
    organization: "my-org"
    name: "restrict-instance-type"
    enforcement_level: hard-mandatory
    policy_content: "main = rule { true }"
    state: present
# "changed": false

- name: Update enforcement level and content by ID
  hashicorp.terraform.policy:
    policy_id: "{{ result.id }}"
    enforcement_level: soft-mandatory
    policy_content: "main = rule { false }"
    state: present

- name: Create an OPA policy
  hashicorp.terraform.policy:
    organization: "my-org"
    name: "deny-all"
    kind: opa
    query: "terraform.main"
    enforcement_level: mandatory
    policy_content: "package terraform.main\n\ndeny := []\n"
    state: present

- name: Delete a policy
  hashicorp.terraform.policy:
    policy_id: "{{ result.id }}"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The policy identifier.
  returned: when state is present
  type: str
  sample: "pol-EavQ1LztoRTQHSNT"
name:
  description: The policy name.
  returned: when state is present
  type: str
kind:
  description: The policy engine.
  returned: when state is present
  type: str
enforcement_level:
  description: The policy's enforcement level.
  returned: when state is present
  type: str
policy_set_count:
  description: The number of policy sets this policy belongs to.
  returned: when state is present
  type: int
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Policy pol-EavQ1LztoRTQHSNT has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy import (
    create_policy,
    delete_policy,
    download_policy_content,
    get_policy,
    get_policy_by_name,
    update_policy,
    upload_policy_content,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff

_IMMUTABLE_KEYS = ("name", "kind")
_UPDATABLE_KEYS = ("query", "description", "enforcement_level")


def _fetch_policy(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target policy by ID or by (organization, name)."""
    policy_id = params.get("policy_id")
    if policy_id:
        return get_policy(adapter, policy_id)
    organization = params.get("organization")
    name = params.get("name")
    if organization and name:
        return get_policy_by_name(adapter, organization, name)
    return None


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update a policy (and its content) to match the desired state."""
    current = _fetch_policy(adapter, params)
    name = params.get("name")
    policy_content = params.get("policy_content")

    if current is None:
        if not params.get("organization"):
            raise ValueError("'organization' is required when creating a new policy.")
        if not name:
            raise ValueError("'name' is required when creating a new policy.")
        if not params.get("enforcement_level"):
            raise ValueError("'enforcement_level' is required when creating a new policy.")
        if params.get("kind") == "opa" and not params.get("query"):
            raise ValueError("'query' is required when creating a new policy with kind=opa.")

        if check_mode:
            return {"changed": True, "msg": f"Policy {name} would be created. Skipped creation due to check mode.", "name": name}

        create_data = {key: params[key] for key in ("name", "kind", "query", "description", "enforcement_level") if params.get(key) is not None}
        create_data.setdefault("kind", "sentinel")
        created = create_policy(adapter, params["organization"], create_data)
        if policy_content is not None:
            upload_policy_content(adapter, created["id"], policy_content)
        return {"changed": True, **created}

    for key in _IMMUTABLE_KEYS:
        if params.get(key) is not None and params[key] != current.get(key):
            raise ValueError(
                f"Policy {current['id']} has drifted on immutable field {key!r} ('{current.get(key)}' -> '{params[key]}'). "
                "kind and name cannot be changed after creation - delete and recreate to change them."
            )

    want = {key: params[key] for key in _UPDATABLE_KEYS if params.get(key) is not None}
    have = {key: current.get(key) for key in want.keys()}
    attr_diff = dict_diff(have, want)

    content_diff = False
    if policy_content is not None:
        current_content = download_policy_content(adapter, current["id"])
        content_diff = current_content != policy_content

    if not attr_diff and not content_diff:
        return {"changed": False, **current}

    if check_mode:
        return {"changed": True, "msg": f"Policy {current['id']} would be updated. Skipped update due to check mode.", **want}

    result = current
    if attr_diff:
        result = update_policy(adapter, current["id"], want)
    if content_diff:
        upload_policy_content(adapter, current["id"], policy_content)
        result = {**result, "id": current["id"]}

    return {"changed": True, **result}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the policy if present; no-op otherwise."""
    current = _fetch_policy(adapter, params)
    if current is None:
        return {"changed": False, "msg": "Policy is already absent."}

    policy_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"Policy {policy_id} would be deleted. Skipped deletion due to check mode."}

    delete_policy(adapter, policy_id)
    return {"changed": True, "msg": f"Policy {policy_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "policy_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
            "kind": {"type": "str", "choices": ["sentinel", "opa", "tfpolicy"]},
            "query": {"type": "str"},
            "description": {"type": "str"},
            "enforcement_level": {"type": "str", "choices": ["advisory", "mandatory", "hard-mandatory", "soft-mandatory"]},
            "policy_content": {"type": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_one_of=[("policy_id", "name")],
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
