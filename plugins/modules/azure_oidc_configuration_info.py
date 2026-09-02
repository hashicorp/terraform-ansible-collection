#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: azure_oidc_configuration_info
version_added: "2.2.0"
short_description: Retrieve information about an HCP Terraform Azure OIDC configuration.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieves an Azure OIDC configuration by its unique ID.
  - There is no C(list) endpoint and the configuration has no C(name) field, so lookup is
    only possible by O(oidc_configuration_id).
  - Fails if the requested configuration does not exist.
extends_documentation_fragment: hashicorp.terraform.common
options:
  oidc_configuration_id:
    description:
      - The unique identifier of the OIDC configuration to retrieve.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve an Azure OIDC configuration by ID
  hashicorp.terraform.azure_oidc_configuration_info:
    oidc_configuration_id: "oidc-azure-1"
  register: azure_oidc_config
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
oidc_configuration:
  description: A dictionary containing the Azure OIDC configuration information.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the OIDC configuration.
      type: str
      sample: "oidc-azure-1"
    client_id:
      description: Azure AD application (client) ID.
      type: str
    subscription_id:
      description: Azure subscription ID.
      type: str
    tenant_id:
      description: Azure AD tenant ID.
      type: str
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.oidc_configuration import get_oidc_configuration

_PROVIDER = "azure"


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "oidc_configuration_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            config = get_oidc_configuration(adapter, _PROVIDER, params["oidc_configuration_id"])
            if config is None:
                raise ValueError(f"{_PROVIDER} OIDC configuration {params['oidc_configuration_id']} not found")
            result["oidc_configuration"] = config
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
