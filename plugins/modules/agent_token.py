#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: agent_token
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise agent pool tokens.
author: "Nimisha Shrivastava (@NimishaShrivastava-dev)"
description:
  - Manages authentication tokens for agent pools on Terraform Cloud and Terraform Enterprise.
  - Agent tokens are used by agents to authenticate with Terraform Cloud/Enterprise.
  - Supports creating and deleting agent tokens.
  - The C(present) state creates a new token. When C(agent_token_id) is provided,
    the module verifies the token already exists and returns it unchanged (idempotent).
  - The C(absent) state deletes the token identified by C(agent_token_id).
  - The secret token value is returned only on creation and is not available on subsequent reads.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  agent_token_id:
    description:
      - The unique identifier of the agent token (e.g. C(at-...)).
      - When provided with C(state=present), the module checks whether the token
        exists and returns it unchanged if found (idempotent).
      - Required when C(state=absent).
    type: str
  agent_pool_id:
    description:
      - The unique identifier of the agent pool to create the token in (e.g. C(apool-...)).
      - Required when creating a new agent token (i.e. C(state=present) without C(agent_token_id)).
    type: str
  description:
    description:
      - A human-readable description for the agent token.
      - Required when creating a new agent token (i.e. C(state=present) without C(agent_token_id)).
    type: str
  state:
    description:
      - Desired state of the agent token.
      - C(present) creates the token or verifies it exists.
      - C(absent) deletes the token.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create an agent token
  hashicorp.terraform.agent_token:
    agent_pool_id: "apool-abc123"
    description: "ci-runner"
    state: present
  register: token_result

- name: Store the token value (only available on creation)
  ansible.builtin.debug:
    msg: "Token value: {{ token_result.token }}"

- name: Verify an existing agent token (idempotent)
  hashicorp.terraform.agent_token:
    agent_token_id: "at-abc123"
    state: present
  register: existing_token

- name: Delete an agent token
  hashicorp.terraform.agent_token:
    agent_token_id: "at-abc123"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The agent token identifier.
  returned: when state is present and token exists or is created
  type: str
  sample: "at-EavQ1LztoRTQHSNT"
description:
  description: The agent token description.
  returned: when state is present and token exists or is created
  type: str
  sample: "ci-runner"
created_at:
  description: The timestamp when the token was created.
  returned: when state is present and token exists or is created
  type: str
  sample: "2024-01-01T00:00:00Z"
last_used_at:
  description: The timestamp when the token was last used.
  returned: when the token has been used at least once
  type: str
  sample: "2024-06-01T00:00:00Z"
token:
  description: >
    The secret authentication token value.
    Only returned on creation; never returned by subsequent reads.
    Store this value securely immediately after creation.
  returned: when the token is first created
  type: str
  sample: "REDACTED"
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Agent token at-EavQ1LztoRTQHSNT has been deleted successfully"
warnings:
  description: List of non-fatal warning messages generated during execution.
  returned: always
  type: list
  elements: str
  sample: []
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.agent_token import (
    create_agent_token,
    delete_agent_token,
    get_agent_token,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient


def _fetch_agent_token(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target agent token by ID, or return None if no ID is provided."""
    agent_token_id = params.get("agent_token_id")
    if agent_token_id:
        return get_agent_token(adapter, agent_token_id)
    return None


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create a new agent token, or verify an existing one is present."""
    current = _fetch_agent_token(adapter, params)
    if current is not None:
        return {"changed": False, **current}

    agent_pool_id = params.get("agent_pool_id")
    description = params.get("description")

    if not agent_pool_id:
        raise ValueError("'agent_pool_id' is required when creating a new agent token.")
    if not description:
        raise ValueError("'description' is required when creating a new agent token.")

    if check_mode:
        return {
            "changed": True,
            "msg": f"Agent token would be created in pool {agent_pool_id}. Skipped creation due to check mode.",
            "description": description,
        }

    created = create_agent_token(adapter, agent_pool_id, {"description": description})
    return {"changed": True, **created}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the agent token if present; no-op otherwise."""
    agent_token_id = params["agent_token_id"]
    current = get_agent_token(adapter, agent_token_id)
    if current is None:
        return {"changed": False, "msg": "Agent token is already absent."}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Agent token {agent_token_id} would be deleted. Skipped deletion due to check mode.",
        }

    delete_agent_token(adapter, agent_token_id)
    return {"changed": True, "msg": f"Agent token {agent_token_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "agent_token_id": {"type": "str"},
            "agent_pool_id": {"type": "str"},
            "description": {"type": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_if=[("state", "absent", ["agent_token_id"])],
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
