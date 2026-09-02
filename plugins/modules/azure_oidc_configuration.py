#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: azure_oidc_configuration
version_added: "2.2.0"
short_description: Manage HCP Terraform Azure OIDC configurations for HYOK.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Manages the HCP Terraform-side record of an Azure OIDC configuration - the Azure AD
    application, subscription, and tenant identifiers HCP Terraform federates against, most
    commonly as the C(oidc_configuration_id) dependency of a
    M(hashicorp.terraform.hyok_configuration).
  - Does B(not) create or manage the Azure-side app registration, service principal, or
    federated credential - only the HCP Terraform-side configuration record. Provision the
    Azure side with your usual Azure tooling first.
  - The API has no C(list) endpoint and the configuration record has no C(name) field, so
    there is no way to search for an existing configuration by any user-supplied key.
    C(state=present) is only idempotent when C(oidc_configuration_id) is supplied (it then
    reads, diffs, and updates that specific record); without it, every run creates a B(new)
    configuration. Save the returned C(id) (for example via C(register:)) and pass it back in
    on subsequent runs to update in place instead of duplicating.
  - C(state=absent) requires C(oidc_configuration_id) - there is no other way to identify the
    record to delete.
extends_documentation_fragment: hashicorp.terraform.common
options:
  oidc_configuration_id:
    description:
      - The unique identifier of the OIDC configuration (e.g. C(oidc-...)).
      - Required for C(state=absent), and for an idempotent C(state=present) update.
      - Omit on C(state=present) to create a new configuration.
    type: str
  organization:
    description:
      - The name of the organization to create the configuration in.
      - Required when creating (C(oidc_configuration_id) not supplied).
    type: str
  client_id:
    description:
      - Azure AD application (client) ID.
      - Required when creating a new configuration.
    type: str
  subscription_id:
    description:
      - Azure subscription ID.
      - Required when creating a new configuration.
    type: str
  tenant_id:
    description:
      - Azure AD tenant ID.
      - Required when creating a new configuration.
    type: str
  state:
    description:
      - Desired state of the OIDC configuration.
      - C(present) creates a new configuration, or updates an existing one identified by
        C(oidc_configuration_id).
      - C(absent) deletes the configuration identified by C(oidc_configuration_id).
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create an Azure OIDC configuration
  hashicorp.terraform.azure_oidc_configuration:
    organization: "my-org"
    client_id: "client-uuid"
    subscription_id: "sub-uuid"
    tenant_id: "tenant-uuid"
    state: present
  register: result

- name: Update the client ID on an existing configuration (idempotent)
  hashicorp.terraform.azure_oidc_configuration:
    oidc_configuration_id: "{{ result.id }}"
    client_id: "new-client-uuid"
    state: present

- name: Delete an Azure OIDC configuration
  hashicorp.terraform.azure_oidc_configuration:
    oidc_configuration_id: "{{ result.id }}"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The OIDC configuration identifier.
  returned: when state is present
  type: str
  sample: "oidc-azure-1"
client_id:
  description: Azure AD application (client) ID.
  returned: when state is present
  type: str
subscription_id:
  description: Azure subscription ID.
  returned: when state is present
  type: str
tenant_id:
  description: Azure AD tenant ID.
  returned: when state is present
  type: str
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "azure OIDC configuration oidc-azure-1 has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.oidc_configuration import state_absent, state_present

_PROVIDER = "azure"
_REQUIRED_FIELDS = ("client_id", "subscription_id", "tenant_id")


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "oidc_configuration_id": {"type": "str"},
            "organization": {"type": "str"},
            "client_id": {"type": "str"},
            "subscription_id": {"type": "str"},
            "tenant_id": {"type": "str"},
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
            match params["state"]:
                case "present":
                    action_result = state_present(adapter, _PROVIDER, _REQUIRED_FIELDS, params, params["check_mode"])
                case "absent":
                    action_result = state_absent(adapter, _PROVIDER, params, params["check_mode"])

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
