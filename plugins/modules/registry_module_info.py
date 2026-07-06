#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: registry_module_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise private registry module.
author: "Nimisha Shrivastava (@nimisha-shrivastava)"
description:
  - Retrieves information about a specific private registry module on Terraform Cloud and Terraform Enterprise.
  - Look up a single registry module by C(organization), C(name), and C(provider).
  - Optionally retrieve a specific version by providing C(version).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - The name of the organization that owns the registry module.
      - Required for all operations.
    type: str
    required: true
  name:
    description:
      - Name of the registry module to look up.
      - Required.
    type: str
    required: true
  provider:
    description:
      - Provider name for the registry module (e.g., C(aws), C(azurerm)).
      - Required.
    type: str
    required: true
  namespace:
    description:
      - The namespace for the registry module.
      - For private modules, defaults to the organization name.
    type: str
  registry_name:
    description:
      - The registry name (C(private) or C(public)).
      - Defaults to C(private).
    type: str
    choices: ["private", "public"]
    default: "private"
  version:
    description:
      - Specific version to retrieve.
      - If not provided, retrieves the module metadata.
      - If provided, retrieves the specific version information.
    type: str
"""

EXAMPLES = r"""
- name: Retrieve a registry module
  hashicorp.terraform.registry_module_info:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
  register: module

- name: Retrieve a specific version of a registry module
  hashicorp.terraform.registry_module_info:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    version: "1.0.0"
  register: module_version

- name: Display module information
  ansible.builtin.debug:
    msg: "Module {{ module.registry_module.name }} status: {{ module.registry_module.status }}"
"""

RETURN = r"""
registry_module:
  description: The registry module information.
  returned: when O(version) is not provided
  type: dict
  contains:
    id:
      description: The unique identifier of the registry module.
      returned: always
      type: str
      sample: "mod-abc123"
    name:
      description: The name of the registry module.
      returned: always
      type: str
      sample: "vpc"
    provider:
      description: The provider name.
      returned: always
      type: str
      sample: "aws"
    registry_name:
      description: The registry name (private or public).
      returned: always
      type: str
      sample: "private"
    namespace:
      description: The namespace for the module.
      returned: always
      type: str
      sample: "my-org"
    status:
      description: The module status.
      returned: always
      type: str
      sample: "setup_complete"
    no_code:
      description: Whether this is a no-code module.
      returned: always
      type: bool
      sample: false
    version_statuses:
      description: List of version statuses for the module.
      returned: always
      type: list
      elements: dict
registry_module_version:
  description: The registry module version information.
  returned: when O(version) is provided
  type: dict
  contains:
    id:
      description: The unique identifier of the version.
      returned: always
      type: str
      sample: "modver-abc123"
    version:
      description: The version string.
      returned: always
      type: str
      sample: "1.0.0"
    status:
      description: The version status.
      returned: always
      type: str
      sample: "ok"
    links:
      description: Links related to the version.
      returned: always
      type: dict
      sample: {"upload": "https://archivist.terraform.io/v1/object/..."}
"""


from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_module import (
    get_registry_module,
    get_registry_module_version,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "organization": {"type": "str", "required": True},
            "name": {"type": "str", "required": True},
            "provider": {"type": "str", "required": True},
            "namespace": {"type": "str"},
            "registry_name": {"type": "str", "default": "private", "choices": ["private", "public"]},
            "version": {"type": "str"},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            module_id = {
                "organization": params["organization"],
                "name": params["name"],
                "provider": params["provider"],
                "namespace": params.get("namespace"),
                "registry_name": params.get("registry_name", "private"),
            }
            
            if params.get("version"):
                # Retrieve specific version
                registry_module_version = get_registry_module_version(
                    adapter, module_id, params["version"]
                )
                if not registry_module_version:
                    raise ValueError(
                        f"Registry module version '{params['version']}' for '{params['name']}/{params['provider']}' "
                        f"was not found in organization '{params['organization']}'"
                    )
                result["registry_module_version"] = registry_module_version
            else:
                # Retrieve module metadata
                registry_module = get_registry_module(adapter, module_id)
                if not registry_module:
                    raise ValueError(
                        f"Registry module '{params['name']}/{params['provider']}' was not found "
                        f"in organization '{params['organization']}'"
                    )
                result["registry_module"] = registry_module

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()

# Made with Bob
