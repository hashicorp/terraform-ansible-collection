#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: agent_pool_info
version_added: "2.1.0"
short_description: Retrieve information about Terraform Cloud/Enterprise agent pools.
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Retrieves information about agent pools on Terraform Cloud and Terraform Enterprise.
  - Look up a single agent pool by C(agent_pool_id), look one up by C(organization) plus C(name),
    or list every agent pool in an C(organization).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  agent_pool_id:
    description:
      - The unique identifier of the agent pool (e.g. C(apool-...)).
      - Mutually exclusive with C(organization) and C(name).
    type: str
  organization:
    description:
      - The name of the organization whose agent pools should be queried.
      - Required unless C(agent_pool_id) is provided.
    type: str
  name:
    description:
      - Name of a specific agent pool to look up within C(organization).
      - Requires C(organization).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve an agent pool by ID
  hashicorp.terraform.agent_pool_info:
    agent_pool_id: "apool-abc123"
  register: pool

- name: Retrieve an agent pool by name
  hashicorp.terraform.agent_pool_info:
    organization: "my-org"
    name: "builders"
  register: pool

- name: List all agent pools in an organization
  hashicorp.terraform.agent_pool_info:
    organization: "my-org"
  register: all_pools
"""

RETURN = r"""
agent_pool:
  description: A single agent pool, returned when looking up by C(agent_pool_id) or by (organization, name).
  returned: when O(agent_pool_id) or O(name) is provided
  type: dict
  contains:
    id:
      description: The unique identifier of the agent pool.
      returned: always
      type: str
      sample: "apool-yoGmEFwGwL31Gee1"
    name:
      description: The name of the agent pool.
      returned: always
      type: str
      sample: "builders"
    organization_scoped:
      description: Whether the pool is available to every workspace in the organization.
      returned: always
      type: bool
      sample: true
    agent_count:
      description: The number of agents currently registered with the pool.
      returned: always
      type: int
      sample: 0
agent_pools:
  description: A list of agent pools matching the query.
  returned: when O(organization) is provided
  type: list
  elements: dict
"""


from copy import deepcopy
from typing import Any, Dict, List

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.agent_pool import (
    get_agent_pool,
    get_agent_pool_by_name,
    list_agent_pools,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "agent_pool_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
        },
        required_one_of=[("agent_pool_id", "organization")],
        required_by={"name": ("organization",)},
        mutually_exclusive=[("agent_pool_id", "organization"), ("agent_pool_id", "name")],
        supports_check_mode=True,
    )

    warnings: List[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("agent_pool_id"):
                pool = get_agent_pool(adapter, params["agent_pool_id"])
                if not pool:
                    raise ValueError(f"Agent pool with ID {params['agent_pool_id']} not found")
                result["agent_pool"] = pool
            elif params.get("name"):
                pool = get_agent_pool_by_name(adapter, params["organization"], params["name"])
                if not pool:
                    raise ValueError(f"Agent pool '{params['name']}' was not found in organization '{params['organization']}'")
                result["agent_pool"] = pool
                result["agent_pools"] = [pool]
            else:
                result["agent_pools"] = list_agent_pools(adapter, params["organization"])

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
