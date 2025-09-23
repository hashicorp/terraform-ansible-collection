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
  - If either I(workspace) (and I(organization)) or I(workspace_id) is specified, this module will retrieve the current
    configuration version of the workspace and return information about it.
  - If the workspace does not exist, the module will fail with an error message.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - Name of the organization that the workspace belongs to.
      - This is required when I(workspace) key is set.
    type: str
  workspace:
    description:
      - Name of the workspace.
      - When this key is set, I(organization) must be specified.
    type: str
  workspace_id:
    description:
      - ID of the workspace.
    type: str
  configuration_version_id:
    description:
      - The ID of the configuration version.
      - Either a combination of I(workspace) (and I(organization)), or one of I(workspace_id) or I(configuration_version_id)
        must be specified.
    type: str
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
#         "attributes": {
#             "auto-queue-runs": true,
#             "changed-files": [],
#             "error": null,
#             "error-message": null,
#             "provisional": false,
#             "source": "tfe-api",
#             "speculative": false,
#             "status": "uploaded",
#             "status-timestamps": {
#                 "uploaded-at": "2025-09-19T05:05:04+00:00"
#             }
#         },
#         "id": "cv-id",
#         "links": {
#             "download": "/api/v2/configuration-versions/cv-id/download",
#             "self": "/api/v2/configuration-versions/cv-id"
#         },
#         "relationships": {
#             "ingress-attributes": {
#                 "data": null,
#                 "links": {
#                     "related": "/api/v2/configuration-versions/cv-id/ingress-attributes"
#                 }
#             }
#         },
#         "type": "configuration-versions"
#     },
#     "failed": false
#     }

- name: Show the current configuration using workspace ID
  hashicorp.terraform.configuration_version_info:
    workspace_id: ws-6jrRyVDv1J8zQMB5

# Task output:
# ------------
# "result_get": {
#     "changed": false,
#     "configuration": {
#         "attributes": {
#             "auto-queue-runs": true,
#             "changed-files": [],
#             "error": null,
#             "error-message": null,
#             "provisional": false,
#             "source": "tfe-api",
#             "speculative": false,
#             "status": "uploaded",
#             "status-timestamps": {
#                 "uploaded-at": "2025-09-21T13:57:51+00:00"
#             }
#         },
#         "id": "cv-id",
#         "links": {
#             "download": "/api/v2/configuration-versions/cv-id/download",
#             "self": "/api/v2/configuration-versions/cv-id"
#         },
#         "relationships": {
#             "ingress-attributes": {
#                 "data": null,
#                 "links": {
#                     "related": "/api/v2/configuration-versions/cv-id/ingress-attributes"
#                 }
#             }
#         },
#         "type": "configuration-versions"
#     },
#     "failed": false
#     }

- name: Show the current configuration using workspace and organization name
  hashicorp.terraform.configuration_version_info:
    workspace: workspace-name
    organization: org-name

# Task output:
# ------------
# "result_get": {
#     "changed": false,
#     "configuration": {
#         "attributes": {
#             "auto-queue-runs": true,
#             "changed-files": [],
#             "error": null,
#             "error-message": null,
#             "provisional": false,
#             "source": "tfe-api",
#             "speculative": false,
#             "status": "uploaded",
#             "status-timestamps": {
#                 "uploaded-at": "2025-09-21T13:57:51+00:00"
#             }
#         },
#         "id": "cv-7ecoepBLNBJSohax",
#         "links": {
#             "download": "/api/v2/configuration-versions/cv-id/download",
#             "self": "/api/v2/configuration-versions/cv-id"
#         },
#         "relationships": {
#             "ingress-attributes": {
#                 "data": null,
#                 "links": {
#                     "related": "/api/v2/configuration-versions/cv-id/ingress-attributes"
#                 }
#             }
#         },
#         "type": "configuration-versions"
#     },
#     "failed": false
# }
"""

RETURN = r"""
configuration:
  type: dict
  description: A dictionary containing the configuration version information.
  returned: on success
  contains:
    id:
      type: str
      returned: always
      description: The unique identifier of the configuration version.
      sample: "cv-sample1234567890"
    type:
      type: str
      returned: always
      description: The type of the resource (always "configuration-versions").
      sample: "configuration-versions"
    attributes:
      type: dict
      returned: always
      description: The attributes of the configuration version.
    relationships:
      type: dict
      returned: always
      description: Relationships to other resources.
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
"""

from typing import TYPE_CHECKING

from ansible.module_utils._text import to_text


if TYPE_CHECKING:
    from typing import Any, Dict, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.configuration_version import (
    get_config,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import (
    get_workspace,
    get_workspace_by_id,
)


def fetch_current_config(workspace_response: Dict[str, Any], params: Dict[str, Any]) -> str:
    workspace_id = workspace_response.get("data", {}).get("id", {})
    relationships = workspace_response.get("data", {}).get("relationships", {})
    if relationships:
        current_config = relationships.get("current-configuration-version", {}).get("data", {})
        if current_config:
            return current_config.get("id")

    raise ValueError(f"Current configuration version for workspace '{workspace_id}' was not found.")


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "configuration_version_id": {"type": "str"},
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
        },
        supports_check_mode=True,
        required_together=[["workspace", "organization"]],
        required_one_of=[
            ["workspace_id", "workspace", "configuration_version_id"],
        ],
        mutually_exclusive=[
            ("workspace", "workspace_id", "configuration_version_id"),
        ],
    )

    warnings: list[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = module.params
    params["check_mode"] = module.check_mode
    try:
        client = TerraformClient(**module.params)

        configuration_data: Optional[Dict[str, Any]] = None
        workspace_data: Optional[Dict[str, Any]] = None
        if params.get("workspace_id"):
            # Retrieve workspace by ID
            workspace_data = get_workspace_by_id(client, params["workspace_id"])
            if not workspace_data:
                raise ValueError(f"Workspace '{params['workspace_id']}' was not found.")
            params["configuration_version_id"] = fetch_current_config(workspace_data, params)
        elif params.get("workspace") and params.get("organization"):
            # Retrieve workspace by name and organization
            workspace_data = get_workspace(client, params["organization"], params["workspace"])
            if not workspace_data:
                raise ValueError(f"The workspace {params['workspace']} in {params['organization']} organization was not found.")
            params["configuration_version_id"] = fetch_current_config(workspace_data, params)
        if params.get("configuration_version_id"):
            configuration_data = get_config(client, params["configuration_version_id"])
            if not configuration_data:
                raise ValueError(f"Configuration version '{params['configuration_version_id']}' was not found.")

        # Extract the data field to flatten the structure
        result["configuration"] = configuration_data.get("data", workspace_data)

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
