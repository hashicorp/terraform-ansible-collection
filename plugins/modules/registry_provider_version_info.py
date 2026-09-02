#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: registry_provider_version_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise private registry provider version.
author: "Nimisha Shrivastava (@nimisha-shrivastava)"
description:
  - Retrieves information about a specific private registry provider version on Terraform Cloud
    and Terraform Enterprise.
  - Look up a single provider version by C(organization_name), C(namespace), C(name), and C(version).
  - This module only reads information and never changes state.
  - Only private registry providers are supported (C(registry_name) must be C(private)).
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization_name:
    description:
      - The name of the organization that owns the registry provider.
      - Required for all operations.
    type: str
    required: true
  namespace:
    description:
      - The namespace for the registry provider.
      - For private providers, this is typically the organization name.
      - Required for all operations.
    type: str
    required: true
  name:
    description:
      - The name of the registry provider (e.g., C(aws), C(azurerm)).
      - Required for all operations.
    type: str
    required: true
  version:
    description:
      - The semantic version string of the provider version to retrieve (e.g., C(1.0.0)).
      - Required for all operations.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve a registry provider version
  hashicorp.terraform.registry_provider_version_info:
    organization_name: "my-org"
    namespace: "my-org"
    name: "aws"
    version: "1.0.0"
  register: provider_version

- name: Display provider version information
  ansible.builtin.debug:
    msg: "Provider version {{ provider_version.registry_provider_version.version }}"
"""

RETURN = r"""
registry_provider_version:
  description: The registry provider version information.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the provider version.
      returned: always
      type: str
      sample: "provver-abc123"
    version:
      description: The version string.
      returned: always
      type: str
      sample: "1.0.0"
    key_id:
      description: The GPG key ID used to sign this provider version.
      returned: always
      type: str
      sample: "ABCDEF1234567890"
    protocols:
      description: The Terraform plugin protocols supported by this version.
      returned: always
      type: list
      elements: str
      sample: ["5.0"]
    shasums_uploaded:
      description: Whether the shasums file has been uploaded.
      returned: always
      type: bool
      sample: false
    shasums_sig_uploaded:
      description: Whether the shasums signature file has been uploaded.
      returned: always
      type: bool
      sample: false
    created_at:
      description: The timestamp when the provider version was created.
      returned: always
      type: str
      sample: "2025-01-01T00:00:00.000Z"
    updated_at:
      description: The timestamp when the provider version was last updated.
      returned: always
      type: str
      sample: "2025-01-01T00:00:00.000Z"
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider_version import (
    get_registry_provider_version,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "organization_name": {"type": "str", "required": True},
            "namespace": {"type": "str", "required": True},
            "name": {"type": "str", "required": True},
            "version": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            provider_id = {
                "organization_name": params["organization_name"],
                "registry_name": "private",
                "namespace": params["namespace"],
                "name": params["name"],
            }

            provider_version = get_registry_provider_version(
                adapter,
                provider_id,
                params["version"],
            )
            if not provider_version:
                raise ValueError(
                    f"Registry provider version {params['version']!r} for provider "
                    f"{params['name']!r} was not found in organization {params['organization_name']!r}"
                )
            result["registry_provider_version"] = provider_version

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
