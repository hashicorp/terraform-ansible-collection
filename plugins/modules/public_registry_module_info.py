#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: public_registry_module_info
version_added: "2.2.0"
short_description: Retrieve information about a module from the public Terraform Registry.
author: "Nimisha Shrivastava (@NimishaShrivastava-dev)"
description:
  - Retrieves information about a module from the public Terraform Registry
    (registry.terraform.io).
  - Looks up a module by C(namespace), C(name), and C(provider).
  - Returns the latest published version when C(version) is omitted, or the
    specific version requested when C(version) is provided.
  - The public Terraform Registry API is read-only. This module never changes
    state.
extends_documentation_fragment: hashicorp.terraform.common
options:
  namespace:
    description:
      - The module namespace on the public Terraform Registry
        (e.g. C(hashicorp)).
      - Typically the GitHub or GitLab organization that owns the module.
    type: str
    required: true
  name:
    description:
      - The module name (e.g. C(consul)).
    type: str
    required: true
  provider:
    description:
      - The provider name for the module (e.g. C(aws), C(azurerm)).
    type: str
    required: true
  version:
    description:
      - Specific module version to retrieve (e.g. C(0.1.0)).
      - When omitted the latest published version is returned.
    type: str
"""

EXAMPLES = r"""
- name: Retrieve the latest version of a public registry module
  hashicorp.terraform.public_registry_module_info:
    namespace: "hashicorp"
    name: "consul"
    provider: "aws"
  register: result

- name: Retrieve a specific version of a public registry module
  hashicorp.terraform.public_registry_module_info:
    namespace: "hashicorp"
    name: "consul"
    provider: "aws"
    version: "0.1.0"
  register: result

- name: Display the module version and source
  ansible.builtin.debug:
    msg: >-
      {{ result.public_registry_module.namespace }}/{{ result.public_registry_module.name }}
      v{{ result.public_registry_module.version }}
      ({{ result.public_registry_module.source }})
"""

RETURN = r"""
public_registry_module:
  description: Information about the public registry module.
  returned: always
  type: dict
  contains:
    id:
      description: >-
        The module identifier, typically in
        C(namespace/name/provider/version) form.
      returned: always
      type: str
      sample: "hashicorp/consul/aws/0.1.0"
    namespace:
      description: The module namespace.
      returned: always
      type: str
      sample: "hashicorp"
    name:
      description: The module name.
      returned: always
      type: str
      sample: "consul"
    provider:
      description: The provider name.
      returned: always
      type: str
      sample: "aws"
    version:
      description: The module version.
      returned: always
      type: str
      sample: "0.1.0"
    description:
      description: The module description.
      returned: when available
      type: str
      sample: "A module to deploy Consul clusters on AWS."
    source:
      description: The module source URL (e.g. the GitHub repository).
      returned: when available
      type: str
      sample: "github.com/hashicorp/terraform-aws-consul"
    published_at:
      description: ISO 8601 timestamp of when the version was published.
      returned: when available
      type: str
      sample: "2017-09-14T23:22:44.793604Z"
    downloads:
      description: Total download count for the module.
      returned: when available
      type: int
      sample: 213430
    verified:
      description: Whether the module is verified by HashiCorp.
      returned: when available
      type: bool
      sample: true
    owner:
      description: The owner of the module.
      returned: when available
      type: str
      sample: "hashicorp"
    root:
      description: Root module metadata (inputs, outputs, resources).
      returned: when available
      type: dict
    submodules:
      description: Submodule metadata entries.
      returned: when available
      type: list
      elements: dict
    examples:
      description: Example module metadata entries.
      returned: when available
      type: list
      elements: dict
    providers:
      description: List of providers this module supports.
      returned: when available
      type: list
      elements: str
    versions:
      description: List of all available version strings.
      returned: when available
      type: list
      elements: str
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.public_registry_module import (
    get_public_registry_module,
    get_public_registry_module_latest,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "namespace": {"type": "str", "required": True},
            "name": {"type": "str", "required": True},
            "provider": {"type": "str", "required": True},
            "version": {"type": "str"},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("version"):
                public_registry_module = get_public_registry_module(
                    adapter,
                    params["namespace"],
                    params["name"],
                    params["provider"],
                    params["version"],
                )
                if public_registry_module is None:
                    raise ValueError(
                        f"Public registry module '{params['namespace']}/{params['name']}/{params['provider']}' " f"version '{params['version']}' was not found."
                    )
            else:
                public_registry_module = get_public_registry_module_latest(
                    adapter,
                    params["namespace"],
                    params["name"],
                    params["provider"],
                )
                if public_registry_module is None:
                    raise ValueError(f"Public registry module '{params['namespace']}/{params['name']}/{params['provider']}' " f"was not found.")

            result["public_registry_module"] = public_registry_module
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
