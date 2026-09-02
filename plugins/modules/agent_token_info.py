#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: agent_token_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise agent token.
author: "Nimisha Shrivastava (@NimishaShrivastava-dev)"
description:
  - Retrieves information about an agent pool authentication token on Terraform Cloud
    and Terraform Enterprise.
  - Look up a single agent token by C(agent_token_id).
  - This module only reads information and never changes state.
  - Note - the secret token value is never returned by read operations; it is only
    available immediately after creation via the C(agent_token) module.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  agent_token_id:
    description:
      - The unique identifier of the agent token (e.g. C(at-...)).
      - Required.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve an agent token by ID
  hashicorp.terraform.agent_token_info:
    agent_token_id: "at-abc123"
  register: token_info

- name: Display token description
  ansible.builtin.debug:
    msg: "Token description: {{ token_info.agent_token.description }}"
"""

RETURN = r"""
agent_token:
  description: The agent token information.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the agent token.
      returned: always
      type: str
      sample: "at-EavQ1LztoRTQHSNT"
    description:
      description: The agent token description.
      returned: always
      type: str
      sample: "ci-runner"
    created_at:
      description: The timestamp when the token was created.
      returned: always
      type: str
      sample: "2024-01-01T00:00:00Z"
    last_used_at:
      description: The timestamp when the token was last used.
      returned: when the token has been used
      type: str
      sample: "2024-06-01T00:00:00Z"
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.agent_token import get_agent_token
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "agent_token_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            token = get_agent_token(adapter, params["agent_token_id"])
            if not token:
                raise ValueError(f"Agent token with ID {params['agent_token_id']!r} was not found.")
            result["agent_token"] = token
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
