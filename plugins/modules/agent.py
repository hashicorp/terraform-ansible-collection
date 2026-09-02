#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: agent
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise agents (delete).
author: "Nimisha Shrivastava (@NimishaShrivastava-dev)"
description:
  - Manages individual Terraform Cloud and Terraform Enterprise agents.
  - Identify an agent by C(agent_id).
  - The C(absent) state deletes the agent if it exists.
  - The PyTFE SDK exposes only a delete (and read) operation for the Agent
    resource. Create and update are not supported by the API.
  - B(API constraint) -- The Terraform Cloud API only permits deletion of agents
    whose status is C(unknown) (i.e. agents that have disconnected from the
    pool). Attempting to delete an agent with status C(idle) or C(busy) will
    fail with an error from the API (C(Agent with status 'idle' may not be
    deleted)). This module surfaces that error faithfully; it is not a bug in
    the module.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  agent_id:
    description:
      - The unique identifier of the agent (e.g. C(agent-...)).
    type: str
    required: true
  state:
    description:
      - Desired state of the agent.
      - C(absent) deletes the agent.
    type: str
    choices: ["absent"]
    default: "absent"
"""

EXAMPLES = r"""
# NOTE: The Terraform Cloud API only allows deletion of agents whose status is
# 'unknown' (i.e. the agent process has disconnected). Attempting to delete an
# 'idle' or 'busy' agent will return an API error.

- name: Delete a disconnected (unknown-status) agent by ID
  hashicorp.terraform.agent:
    agent_id: "agent-abc123"
    state: absent
  register: result

- name: Check-mode delete (no API call is made, works regardless of agent status)
  hashicorp.terraform.agent:
    agent_id: "agent-abc123"
    state: absent
  check_mode: true
  register: result_check

- name: Conditionally delete only if the agent has disconnected
  hashicorp.terraform.agent_info:
    agent_id: "agent-abc123"
  register: agent_info

- name: Delete the agent when it is no longer connected
  hashicorp.terraform.agent:
    agent_id: "agent-abc123"
    state: absent
  when: agent_info.agent.status == "unknown"
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
msg:
  description: Informational message for delete, no-op, and check-mode operations.
  returned: always
  type: str
  sample: "Agent agent-abc123 has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.agent import (
    delete_agent,
    get_agent,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient


def _fetch_agent(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target agent by ID."""
    agent_id = params.get("agent_id")
    if agent_id:
        return get_agent(adapter, agent_id)
    return None


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the agent if present; no-op otherwise."""
    current = _fetch_agent(adapter, params)
    if current is None:
        return {"changed": False, "msg": "Agent is already absent."}

    agent_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"Agent {agent_id} would be deleted. Skipped deletion due to check mode."}

    delete_agent(adapter, agent_id)
    return {"changed": True, "msg": f"Agent {agent_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "agent_id": {"type": "str", "required": True},
            "state": {"type": "str", "default": "absent", "choices": ["absent"]},
        },
        supports_check_mode=True,
    )

    warnings: List[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    action_result: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            match params["state"]:
                case "absent":
                    action_result = state_absent(adapter, params, params["check_mode"])

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
