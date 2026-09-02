#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: registry_provider
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise registry providers.
author: "Nimisha Shrivastava (@nimisha-shrivastava)"
description:
  - Manages registry providers in Terraform Cloud and Terraform Enterprise.
  - Registry providers are identified by organization, registry namespace, and provider name.
  - Create operations are idempotent; absent operations delete the provider if it exists.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - The name of the organization that owns the registry provider.
    type: str
    required: true
  name:
    description:
      - The provider name in the registry (for example C(aws), C(azurerm), or C(google)).
    type: str
    required: true
  namespace:
    description:
      - The registry namespace to which the provider belongs.
      - For private providers, this is typically the organization name.
    type: str
    required: true
  registry_name:
    description:
      - The registry name, either C(private) or C(public).
      - Defaults to C(private).
    type: str
    choices: ["private", "public"]
    default: "private"
  state:
    description:
      - Desired state of the registry provider.
      - C(present) ensures the provider exists.
      - C(absent) deletes the provider.
    type: str
    default: "present"
    choices: ["present", "absent"]
"""

EXAMPLES = r"""
- name: Create a private registry provider
  hashicorp.terraform.registry_provider:
    organization: "my-org"
    name: "aws"
    namespace: "my-org"
    state: present
  register: provider

- name: Idempotent create of the same provider
  hashicorp.terraform.registry_provider:
    organization: "my-org"
    name: "aws"
    namespace: "my-org"
    state: present
  register: provider_again

- name: Delete a registry provider
  hashicorp.terraform.registry_provider:
    organization: "my-org"
    name: "aws"
    namespace: "my-org"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The registry provider identifier.
  returned: when state is present
  type: str
  sample: "regprov-abc123"
name:
  description: The registry provider name.
  returned: when state is present
  type: str
  sample: "aws"
namespace:
  description: The registry namespace.
  returned: when state is present
  type: str
  sample: "my-org"
registry_name:
  description: The registry name.
  returned: when state is present
  type: str
  sample: "private"
created_at:
  description: Timestamp of when the registry provider was created.
  returned: when state is present
  type: str
  sample: "2026-07-21T07:06:30.510000Z"
updated_at:
  description: Timestamp of when the registry provider was last updated.
  returned: when state is present
  type: str
  sample: "2026-07-21T07:06:30.510000Z"
permissions:
  description: The permissions the caller has on the registry provider.
  returned: when state is present
  type: dict
  contains:
    can_delete:
      description: Whether the caller can delete the registry provider.
      returned: always
      type: bool
      sample: true
organization:
  description: The organization that owns the provider.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The organization ID.
      returned: always
      type: str
      sample: "my-org"
    type:
      description: The resource type of the organization relationship.
      returned: always
      type: str
      sample: "organizations"
registry_provider_versions:
  description: The versions published for the registry provider.
  returned: when state is present
  type: list
  elements: dict
  sample: []
links:
  description: Links related to the registry provider.
  returned: when state is present
  type: dict
  sample: {"self": "https://..."}
msg:
  description: Informational message for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Registry provider aws has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_provider import (
    create_registry_provider,
    delete_registry_provider,
    get_registry_provider,
)


def _require_provider_identifiers(params: Dict[str, Any]) -> None:
    if not params.get("organization") or not params.get("name") or not params.get("namespace"):
        raise ValueError("'organization', 'name', and 'namespace' are required to manage a registry provider")


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    _require_provider_identifiers(params)
    registry_name = params.get("registry_name", "private")
    current = get_registry_provider(
        adapter,
        params["organization"],
        registry_name,
        params["namespace"],
        params["name"],
    )
    if current is not None:
        return {"changed": False, **current}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Registry provider {params['name']} would be created. Skipped creation due to check mode.",
        }

    created = create_registry_provider(
        adapter,
        params["organization"],
        {
            "name": params["name"],
            "namespace": params["namespace"],
            "registry_name": registry_name,
        },
    )
    return {"changed": True, **created}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    _require_provider_identifiers(params)
    registry_name = params.get("registry_name", "private")
    current = get_registry_provider(
        adapter,
        params["organization"],
        registry_name,
        params["namespace"],
        params["name"],
    )
    if current is None:
        return {"changed": False, "msg": "Registry provider is already absent."}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Registry provider {params['name']} would be deleted. Skipped deletion due to check mode.",
        }

    delete_registry_provider(
        adapter,
        params["organization"],
        registry_name,
        params["namespace"],
        params["name"],
    )
    return {"changed": True, "msg": f"Registry provider {params['name']} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "organization": {"type": "str", "required": True},
            "name": {"type": "str", "required": True},
            "namespace": {"type": "str", "required": True},
            "registry_name": {"type": "str", "default": "private", "choices": ["private", "public"]},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    action_result: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            if params["state"] == "present":
                action_result = state_present(adapter, params, params["check_mode"])
            else:
                action_result = state_absent(adapter, params, params["check_mode"])

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
