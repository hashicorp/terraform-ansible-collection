#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: registry_provider_platform
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise registry provider platforms.
author: "Nimisha Shrivastava (@nimisha-shrivastava)"
description:
  - Manages registry provider platforms on Terraform Cloud and Terraform Enterprise.
  - A provider platform represents an OS/architecture combination for a specific
    provider version in the private registry.
  - Supports creating and deleting platforms; updates are not supported by the API.
  - Identify a platform by C(organization), C(provider_name), C(namespace),
    C(registry_name), C(version), C(os), and C(arch).
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
      - Required for all operations.
    type: str
    required: true
  os:
    description:
      - The operating system for this platform (e.g., C(linux), C(darwin), C(windows)).
      - Required for all operations.
    type: str
    required: true
  arch:
    description:
      - The CPU architecture for this platform (e.g., C(amd64), C(arm64), C(386)).
      - Required for all operations.
    type: str
    required: true
  shasum:
    description:
      - The SHA256 checksum of the provider binary for this platform.
      - Required when O(state=present).
    type: str
  filename:
    description:
      - The filename of the provider binary for this platform.
      - Required when O(state=present).
    type: str
  state:
    description:
      - Desired state of the registry provider platform.
      - C(present) creates the platform if it does not already exist.
      - C(absent) deletes the platform if it exists.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a registry provider platform
  hashicorp.terraform.registry_provider_platform:
    organization: "my-org"
    provider_name: "aws"
    namespace: "my-org"
    registry_name: "private"
    version: "1.0.0"
    os: "linux"
    arch: "amd64"
    shasum: "abc123def456abc123def456abc123def456abc123def456abc123def456abc123"
    filename: "terraform-provider-aws_1.0.0_linux_amd64.zip"
    state: present
  register: result_platform

- name: Idempotent create (no-op if platform already exists)
  hashicorp.terraform.registry_provider_platform:
    organization: "my-org"
    provider_name: "aws"
    namespace: "my-org"
    registry_name: "private"
    version: "1.0.0"
    os: "linux"
    arch: "amd64"
    shasum: "abc123def456abc123def456abc123def456abc123def456abc123def456abc123"
    filename: "terraform-provider-aws_1.0.0_linux_amd64.zip"
    state: present

- name: Delete a registry provider platform
  hashicorp.terraform.registry_provider_platform:
    organization: "my-org"
    provider_name: "aws"
    namespace: "my-org"
    registry_name: "private"
    version: "1.0.0"
    os: "linux"
    arch: "amd64"
    state: absent
  register: result_delete
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The registry provider platform identifier.
  returned: when state is present and the platform exists
  type: str
  sample: "provpltfm-abc123"
os:
  description: The operating system for the platform.
  returned: when state is present and the platform exists
  type: str
  sample: "linux"
arch:
  description: The CPU architecture for the platform.
  returned: when state is present and the platform exists
  type: str
  sample: "amd64"
filename:
  description: The filename of the provider binary.
  returned: when state is present and the platform exists
  type: str
  sample: "terraform-provider-aws_1.0.0_linux_amd64.zip"
shasum:
  description: The SHA256 checksum of the provider binary.
  returned: when state is present and the platform exists
  type: str
  sample: "abc123def456abc123def456abc123def456abc123def456abc123def456abc123"
provider_binary_uploaded:
  description: Whether the provider binary has been uploaded.
  returned: when state is present and the platform exists
  type: bool
  sample: false
links:
  description: Links related to the platform (includes upload URL for provider binary).
  returned: when state is present and the platform exists
  type: dict
  sample: {"provider-binary-upload": "https://archivist.terraform.io/v1/object/..."}
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Registry provider platform linux/amd64 has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider_platform import (
    create_registry_provider_platform,
    delete_registry_provider_platform,
    get_registry_provider_platform,
)


def _fetch_registry_provider_platform(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target registry provider platform using the read API."""
    return get_registry_provider_platform(adapter, params)


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Ensure the registry provider platform exists."""
    if not params.get("shasum") or not params.get("filename"):
        raise ValueError("'shasum' and 'filename' are required when state is present")

    current = _fetch_registry_provider_platform(adapter, params)
    if current is not None:
        return {"changed": False, **current}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Registry provider platform {params.get('os')}/{params.get('arch')} would be created. Skipped creation due to check mode.",
            "os": params.get("os"),
            "arch": params.get("arch"),
        }

    created = create_registry_provider_platform(adapter, params)
    return {"changed": True, **created}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the registry provider platform if it exists."""
    current = _fetch_registry_provider_platform(adapter, params)
    if current is None:
        return {"changed": False, "msg": "Registry provider platform is already absent."}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Registry provider platform {params.get('os')}/{params.get('arch')} would be deleted. Skipped deletion due to check mode.",
        }

    delete_registry_provider_platform(adapter, params)
    return {
        "changed": True,
        "msg": f"Registry provider platform {params.get('os')}/{params.get('arch')} has been deleted successfully",
    }


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
            "shasum": {"type": "str"},
            "filename": {"type": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_if=[("state", "present", ["shasum", "filename"])],
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
