#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: agent_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise agent.
author: "Nimisha Shrivastava (@NimishaShrivastava-dev)"
description:
  - Retrieves information about an agent on Terraform Cloud and Terraform Enterprise.
  - Look up a single agent by C(agent_id).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  agent_id:
    description:
      - The unique identifier of the agent (e.g. C(agent-...)).
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve an agent by ID
  hashicorp.terraform.agent_info:
    agent_id: "agent-abc123"
  register: result

- name: Print agent status
  ansible.builtin.debug:
    msg: "Agent {{ result.agent.id }} is {{ result.agent.status }}"
"""

RETURN = r"""
agent:
  description: The agent matching the provided C(agent_id).
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the agent.
      returned: always
      type: str
      sample: "agent-yoGmEFwGwL31Gee1"
    name:
      description: The name of the agent.
      returned: when available
      type: str
      sample: "my-agent"
    status:
      description: The current status of the agent.
      returned: when available
      type: str
      sample: "idle"
    version:
      description: The agent software version.
      returned: when available
      type: str
      sample: "1.12.0"
    ip_address:
      description: The IP address of the agent.
      returned: when available
      type: str
      sample: "203.0.113.42"
    last_ping_at:
      description: The timestamp of the agent's last ping.
      returned: when available
      type: str
      sample: "2024-01-15T10:30:00Z"
"""


from copy import deepcopy
from typing import Any, Dict, List

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.agent import (
    get_agent,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "agent_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: List[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            agent = get_agent(adapter, params["agent_id"])
            if not agent:
                raise ValueError(f"Agent with ID {params['agent_id']} not found")
            result["agent"] = agent
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
