#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: registry_provider_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise registry provider.
author: "Nimisha Shrivastava (@nimisha-shrivastava)"
description:
  - Retrieves information about a registry provider in Terraform Cloud and Terraform Enterprise.
  - The target provider is identified by organization, namespace, and provider name.
  - This module only reads information and never changes state.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - The name of the organization that owns the registry provider.
    type: str
    required: true
  namespace:
    description:
      - The registry namespace that contains the provider.
    type: str
    required: true
  name:
    description:
      - The provider name in the registry.
    type: str
    required: true
  registry_name:
    description:
      - The registry name, either C(private) or C(public).
      - Defaults to C(private).
    type: str
    default: "private"
    choices: ["private", "public"]
"""

EXAMPLES = r"""
- name: Retrieve registry provider information
  hashicorp.terraform.registry_provider_info:
    organization: "my-org"
    namespace: "my-org"
    name: "aws"
  register: provider_info

- name: Retrieve a public registry provider
  hashicorp.terraform.registry_provider_info:
    organization: "my-org"
    namespace: "my-org"
    name: "aws"
    registry_name: "public"
  register: provider_info
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
registry_provider:
  description: A dictionary containing the registry provider information.
  returned: always
  type: dict
  contains:
    id:
      description: The registry provider identifier.
      returned: always
      type: str
      sample: "regprov-abc123"
    name:
      description: The provider name.
      returned: always
      type: str
      sample: "aws"
    namespace:
      description: The registry namespace.
      returned: always
      type: str
      sample: "my-org"
    registry_name:
      description: The registry name.
      returned: always
      type: str
      sample: "private"
    created_at:
      description: Timestamp of when the registry provider was created.
      returned: always
      type: str
      sample: "2026-07-21T07:06:30.510000Z"
    updated_at:
      description: Timestamp of when the registry provider was last updated.
      returned: always
      type: str
      sample: "2026-07-21T07:06:30.510000Z"
    permissions:
      description: The permissions the caller has on the registry provider.
      returned: always
      type: dict
    registry_provider_versions:
      description: The versions published for the registry provider.
      returned: always
      type: list
      elements: dict
    organization:
      description: The owning organization.
      returned: always
      type: dict
    links:
      description: Links related to the registry provider.
      returned: when present
      type: dict
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider import get_registry_provider


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "organization": {"type": "str", "required": True},
            "namespace": {"type": "str", "required": True},
            "name": {"type": "str", "required": True},
            "registry_name": {"type": "str", "default": "private", "choices": ["private", "public"]},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            provider = get_registry_provider(
                adapter,
                params["organization"],
                params["registry_name"],
                params["namespace"],
                params["name"],
            )
            if not provider:
                raise ValueError(
                    f"Registry provider '{params['name']}' in namespace '{params['namespace']}' for organization '{params['organization']}' was not found"
                )
            result["registry_provider"] = provider
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
