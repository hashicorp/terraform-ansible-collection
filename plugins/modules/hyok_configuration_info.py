#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: hyok_configuration_info
version_added: "2.2.0"
short_description: Retrieve information about HCP Terraform HYOK (Hold Your Own Key) configurations.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves a HYOK configuration by its unique ID.
  - Lists HYOK configurations in an organization when O(organization) is provided without O(name).
  - Searches for a HYOK configuration by name when O(organization) and O(name) are provided.
  - Fails if a requested configuration does not exist.
extends_documentation_fragment: hashicorp.terraform.common
options:
  hyok_configuration_id:
    description:
      - The unique identifier of the HYOK configuration to retrieve.
      - Mutually exclusive with O(organization) and O(name).
    type: str
  organization:
    description:
      - The organization whose HYOK configurations should be listed or searched.
      - Required when O(hyok_configuration_id) is not provided.
      - Mutually exclusive with O(hyok_configuration_id).
    type: str
  name:
    description:
      - HYOK configuration name to search for within O(organization).
      - Requires O(organization).
      - Mutually exclusive with O(hyok_configuration_id).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve a HYOK configuration by ID
  hashicorp.terraform.hyok_configuration_info:
    hyok_configuration_id: "hyokc-L4CxAJEEn8vEUEkj"
  register: hyok_config

- name: Search for a HYOK configuration by organization and name
  hashicorp.terraform.hyok_configuration_info:
    organization: "my-org"
    name: "prod-key"
  register: hyok_config

- name: List HYOK configurations in an organization
  hashicorp.terraform.hyok_configuration_info:
    organization: "my-org"
  register: hyok_configs
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
hyok_configuration:
  description: A dictionary containing the HYOK configuration information.
  returned: when O(hyok_configuration_id) or O(name) is provided
  type: dict
  contains:
    id:
      description: The unique identifier of the HYOK configuration.
      type: str
      sample: "hyokc-L4CxAJEEn8vEUEkj"
    name:
      description: The HYOK configuration name.
      type: str
      sample: "prod-key"
    kek_id:
      description: The key-encryption-key ID in the customer's KMS.
      type: str
    status:
      description: Current lifecycle status.
      type: str
      sample: "available"
    primary:
      description: Whether this is the organization's primary HYOK configuration.
      type: bool
    organization_id:
      description: The owning organization's ID.
      type: str
    agent_pool_id:
      description: The agent pool ID used to reach the KMS.
      type: str
    oidc_configuration_id:
      description: The OIDC configuration ID used to authenticate to the KMS.
      type: str
hyok_configurations:
  description: A list of HYOK configurations matching the query.
  returned: when O(organization) is provided
  type: list
  elements: dict
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.hyok_configuration import (
    get_hyok_configuration,
    get_hyok_configuration_by_name,
    list_hyok_configurations,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "hyok_configuration_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
        },
        required_one_of=[("hyok_configuration_id", "organization")],
        required_by={"name": ("organization",)},
        mutually_exclusive=[("hyok_configuration_id", "organization"), ("hyok_configuration_id", "name")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("hyok_configuration_id"):
                config = get_hyok_configuration(adapter, params["hyok_configuration_id"])
                if not config:
                    raise ValueError(f"HYOK configuration with ID {params['hyok_configuration_id']} not found")
                result["hyok_configuration"] = config
            elif params.get("name"):
                config = get_hyok_configuration_by_name(adapter, params["organization"], params["name"])
                if not config:
                    raise ValueError(f"HYOK configuration {params['name']!r} was not found in organization {params['organization']!r}")
                result["hyok_configuration"] = config
                result["hyok_configurations"] = [config]
            else:
                result["hyok_configurations"] = list_hyok_configurations(adapter, params["organization"])

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
