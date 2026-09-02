#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: registry_provider_platform_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud/Enterprise registry provider platform.
author: "Nimisha Shrivastava (@nimisha-shrivastava)"
description:
  - Retrieves information about a specific registry provider platform on Terraform Cloud and Terraform Enterprise.
  - Look up a single platform by C(organization), C(provider_name), C(namespace), C(registry_name),
    C(version), C(os), and C(arch).
  - This module only reads information and never changes state.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - The name of the organization that owns the registry provider.
      - Required for all operations.
    type: str
    required: true
  provider_name:
    description:
      - The name of the registry provider (e.g., C(aws), C(azurerm)).
      - Required.
    type: str
    required: true
  namespace:
    description:
      - The namespace for the registry provider.
      - For private providers, this is typically the organization name.
      - Required.
    type: str
    required: true
  registry_name:
    description:
      - The registry name (C(private) or C(public)).
      - Defaults to C(private).
    type: str
    choices: ["private", "public"]
    default: "private"
  version:
    description:
      - The version string of the provider version that this platform belongs to.
      - Required.
    type: str
    required: true
  os:
    description:
      - The operating system for the platform (e.g., C(linux), C(darwin), C(windows)).
      - Required.
    type: str
    required: true
  arch:
    description:
      - The CPU architecture for the platform (e.g., C(amd64), C(arm64), C(386)).
      - Required.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve a registry provider platform
  hashicorp.terraform.registry_provider_platform_info:
    organization: "my-org"
    provider_name: "aws"
    namespace: "my-org"
    registry_name: "private"
    version: "1.0.0"
    os: "linux"
    arch: "amd64"
  register: platform_info

- name: Display platform information
  ansible.builtin.debug:
    msg: "Platform {{ platform_info.registry_provider_platform.os }}/{{ platform_info.registry_provider_platform.arch }}"
"""

RETURN = r"""
registry_provider_platform:
  description: The registry provider platform information.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the platform.
      returned: always
      type: str
      sample: "provpltfm-abc123"
    os:
      description: The operating system for the platform.
      returned: always
      type: str
      sample: "linux"
    arch:
      description: The CPU architecture for the platform.
      returned: always
      type: str
      sample: "amd64"
    filename:
      description: The filename of the provider binary.
      returned: always
      type: str
      sample: "terraform-provider-aws_1.0.0_linux_amd64.zip"
    shasum:
      description: The SHA256 checksum of the provider binary.
      returned: always
      type: str
      sample: "abc123def456abc123def456abc123def456abc123def456abc123def456abc123"
    provider_binary_uploaded:
      description: Whether the provider binary has been uploaded.
      returned: always
      type: bool
      sample: false
    links:
      description: Links related to the platform (includes upload URL for provider binary).
      returned: always
      type: dict
      sample: {"provider-binary-upload": "https://archivist.terraform.io/v1/object/..."}
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider_platform import (
    get_registry_provider_platform,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "organization": {"type": "str", "required": True},
            "provider_name": {"type": "str", "required": True},
            "namespace": {"type": "str", "required": True},
            "registry_name": {"type": "str", "default": "private", "choices": ["private", "public"]},
            "version": {"type": "str", "required": True},
            "os": {"type": "str", "required": True},
            "arch": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            platform = get_registry_provider_platform(adapter, params)
            if not platform:
                raise ValueError(
                    f"Registry provider platform '{params['os']}/{params['arch']}' for provider "
                    f"'{params['provider_name']}' version '{params['version']}' "
                    f"was not found in organization '{params['organization']}'"
                )
            result["registry_provider_platform"] = platform
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
