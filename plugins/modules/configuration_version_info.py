# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

DOCUMENTATION = r"""
---
module: configuration_version_info
version_added: 1.1.0
short_description: Retrieve information about configuration versions in Terraform Enterprise/Cloud.
author: "Kaushiki Singh (@kausingh)"
description:
  - This module retrieves information about a given configuration version in Terraform Enterprise/Cloud.
  - If I(configuration_version_id) is specified, this module will retrieve and return information about it.
extends_documentation_fragment: hashicorp.terraform.common
options:
  configuration_version_id:
    description:
      - The ID of the configuration version.
      - I(configuration_version_id) must be specified.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Show the configuration using ID
  hashicorp.terraform.configuration_version_info:
    configuration_version_id: cv-UYwHEakurukz85nW

# Task output:
# ------------
# "result_get": {
#     "changed": false,
#     "configuration": {
#         "auto_queue_runs": true,
#         "id": "cv-rp6DujcQxCsgr7QE",
#         "links": {
#             "download": "/api/v2/configuration-versions/cv-rp6DujcQxCsgr7QE/download",
#             "self": "/api/v2/configuration-versions/cv-rp6DujcQxCsgr7QE"
#         },
#         "provisional": false,
#         "source": "tfe-api",
#         "speculative": false,
#         "status": "uploaded",
#         "status_timestamps": {
#             "uploaded-at": "2026-04-20T06:43:23+00:00"
#         }
#     },
#     "failed": false
#     }
"""

RETURN = r"""
configuration:
  type: dict
  description: A dictionary containing the configuration version information.
  returned: on success
  contains:
    auto_queue_runs:
      type: bool
      returned: when set
      description: Whether runs are automatically queued for this configuration version.
    id:
      type: str
      returned: always
      description: The unique identifier of the configuration version.
      sample: "cv-sample1234567890"
    links:
      type: dict
      returned: always
      description: Links related to the configuration version.
      contains:
        self:
          type: str
          returned: always
          description: API endpoint for this configuration version.
        download:
          type: str
          returned: always
          description: Download link for this configuration version.
    provisional:
      type: bool
      returned: when set
      description: Whether this is a provisional configuration version.
    source:
      type: str
      returned: when set
      description: Source of the configuration version.
    speculative:
      type: bool
      returned: when set
      description: Whether the configuration version is speculative.
    status:
      type: str
      returned: when set
      description: Current processing state of the configuration version.
    status_timestamps:
      type: dict
      returned: when set
      description: Timestamps for configuration version state transitions.
"""

from copy import deepcopy
from typing import TYPE_CHECKING

from ansible.module_utils._text import to_text

if TYPE_CHECKING:
    from typing import Any, Dict, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.configuration_version import (
    get_config,
)


def fetch_current_config_version_id(workspace_response: Dict[str, Any], workspace_identifier: str) -> str:
    relationships = workspace_response.get("data", {}).get("relationships", {})
    if relationships and (current_config := relationships.get("current-configuration-version", {}).get("data", {})):
        if current_config:
            return current_config.get("id")
    raise ValueError(f"Current configuration version for workspace '{workspace_identifier}' was not found.")


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "configuration_version_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            configuration_data: Optional[Dict[str, Any]] = None
            if params.get("configuration_version_id"):
                configuration_data = get_config(adapter, params["configuration_version_id"])
                if not configuration_data:
                    raise ValueError(f"Configuration version '{params['configuration_version_id']}' was not found.")

            # Extract the data field to flatten the structure
            result["configuration"] = configuration_data

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
