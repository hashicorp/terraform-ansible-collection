#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: registry_provider_version
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise private registry provider versions.
author: "Nimisha Shrivastava (@nimisha-shrivastava)"
description:
  - Manages private registry provider versions on Terraform Cloud and Terraform Enterprise.
  - Registry provider versions allow you to publish provider binaries within your organization's
    private registry.
  - Identify a provider version by C(organization_name), C(namespace), C(name), and C(version).
  - The C(present) state creates the provider version if it does not already exist.
  - The C(absent) state deletes the provider version if it exists.
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
      - The semantic version string of the provider version (e.g., C(1.0.0)).
      - Required for all operations.
    type: str
    required: true
  key_id:
    description:
      - The GPG key ID used to sign the provider release.
      - Required when C(state=present).
    type: str
  protocols:
    description:
      - List of Terraform plugin protocol versions supported by this provider version (e.g., C(["5.0"])).
      - Required when C(state=present).
    type: list
    elements: str
  state:
    description:
      - Desired state of the registry provider version.
      - C(present) creates the provider version if it does not exist.
      - C(absent) deletes the provider version if it exists.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a private registry provider version
  hashicorp.terraform.registry_provider_version:
    organization_name: "my-org"
    namespace: "my-org"
    name: "aws"
    version: "1.0.0"
    key_id: "ABCDEF1234567890"
    protocols:
      - "5.0"
    state: present
  register: provider_version

- name: Delete a registry provider version
  hashicorp.terraform.registry_provider_version:
    organization_name: "my-org"
    namespace: "my-org"
    name: "aws"
    version: "1.0.0"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The registry provider version identifier.
  returned: when state is present and the version exists
  type: str
  sample: "provver-abc123"
version:
  description: The provider version string.
  returned: when state is present and the version exists
  type: str
  sample: "1.0.0"
key_id:
  description: The GPG key ID used to sign this provider version.
  returned: when state is present and the version exists
  type: str
  sample: "ABCDEF1234567890"
protocols:
  description: The Terraform plugin protocols supported by this version.
  returned: when state is present and the version exists
  type: list
  elements: str
  sample: ["5.0"]
shasums_uploaded:
  description: Whether the shasums file has been uploaded.
  returned: when state is present and the version exists
  type: bool
  sample: false
shasums_sig_uploaded:
  description: Whether the shasums signature file has been uploaded.
  returned: when state is present and the version exists
  type: bool
  sample: false
links:
  description: Links related to the provider version (includes upload URLs).
  returned: when state is present and the version is newly created
  type: dict
  sample: {"shasums-upload": "https://...", "shasums-sig-upload": "https://..."}
msg:
  description: Informational message, primarily for delete, no-op, and check-mode operations.
  returned: when relevant
  type: str
  sample: "Registry provider version 1.0.0 has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider_version import (
    create_registry_provider_version,
    delete_registry_provider_version,
    get_registry_provider_version,
)


def _build_provider_id(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build a provider ID dict from params."""
    return {
        "organization_name": params.get("organization_name"),
        "registry_name": "private",
        "namespace": params.get("namespace"),
        "name": params.get("name"),
    }


def _fetch_registry_provider_version(
    adapter: TerraformClient,
    params: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Resolve the target provider version using the read API."""
    organization_name = params.get("organization_name")
    namespace = params.get("namespace")
    name = params.get("name")
    version = params.get("version")

    if organization_name and namespace and name and version:
        provider_id = _build_provider_id(params)
        return get_registry_provider_version(adapter, provider_id, version)
    return None


def state_present(
    adapter: TerraformClient,
    params: Dict[str, Any],
    check_mode: bool = False,
) -> Dict[str, Any]:
    """Ensure the registry provider version exists."""
    current = _fetch_registry_provider_version(adapter, params)
    if current is not None:
        return {"changed": False, **current}

    if check_mode:
        return {
            "changed": True,
            "msg": (
                f"Registry provider version {params.get('version')!r} for provider "
                f"{params.get('name')!r} would be created. Skipped creation due to check mode."
            ),
            "version": params.get("version"),
        }

    if not params.get("key_id"):
        raise ValueError("'key_id' is required when state is present")
    if not params.get("protocols"):
        raise ValueError("'protocols' is required when state is present")

    provider_id = _build_provider_id(params)
    created = create_registry_provider_version(
        adapter,
        provider_id,
        {
            "version": params["version"],
            "key_id": params["key_id"],
            "protocols": params["protocols"],
        },
    )
    return {"changed": True, **created}


def state_absent(
    adapter: TerraformClient,
    params: Dict[str, Any],
    check_mode: bool = False,
) -> Dict[str, Any]:
    """Delete the registry provider version if it exists."""
    current = _fetch_registry_provider_version(adapter, params)
    if current is None:
        return {"changed": False, "msg": "Registry provider version is already absent."}

    if check_mode:
        return {
            "changed": True,
            "msg": (f"Registry provider version {params.get('version')!r} would be deleted. " "Skipped deletion due to check mode."),
        }

    provider_id = _build_provider_id(params)
    delete_registry_provider_version(adapter, provider_id, params["version"])
    return {
        "changed": True,
        "msg": f"Registry provider version {params.get('version')!r} has been deleted successfully",
    }


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "organization_name": {"type": "str", "required": True},
            "namespace": {"type": "str", "required": True},
            "name": {"type": "str", "required": True},
            "version": {"type": "str", "required": True},
            "key_id": {"type": "str"},
            "protocols": {"type": "list", "elements": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_if=[
            ("state", "present", ["key_id", "protocols"]),
        ],
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
