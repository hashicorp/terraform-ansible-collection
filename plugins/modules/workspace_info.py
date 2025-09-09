# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: workspace_info
version_added: 1.0.0
short_description: Gather information about a workspace in Terraform Enterprise/Cloud.
author: "Shashank Venkat (@shvenkat)"
description:
  - This module retrieves information about a given workspace in Terraform Enterprise/Cloud.
  - It can be used to check if a workspace exists or to gather detailed information about it.
  - If I(workspace_id) is provided, the module will return information about that specific workspace.
  - If I(workspace) and I(organization) are provided, the module will return information about the workspace \
    with that name in the specified organization.
  - If the workspace does not exist, the module will fail with an error message.
extends_documentation_fragment: hashicorp.terraform.common
options:
  workspace_id:
    description:
      - The unique identifier of the workspace to retrieve information about.
      - Either I(workspace_id) or a combination of I(workspace) and I(organization) must be given to fetch workspace information.
    type: str
  workspace:
    description:
      - The name of the workspace to retrieve information about.
      - When this parameter is used, I(organization) must also be provided.
      - Either a combination of I(workspace) and I(organization) or I(workspace_id) must be given to fetch workspace information.
    type: str
  organization:
    description:
      - The name of the organization that contains the workspace.
      - This parameter is required when I(workspace) is provided.
    type: str
"""
EXAMPLES = r"""
- name: Gather information about a workspace by ID
  hashicorp.terraform.workspace_info:
    workspace_id: "ws-sample1234567890"
  register: workspace_info

# Task output:
# ------------
# "workspace_info": {
#     "changed": false,
#     "failed": false,
#     "workspace": {
#         "id": "ws-sample1234567890",
#         "type": "workspaces",
#         "attributes": {
#             "name": "sample_workspace",
#             "terraform-version": "1.10.5",
#             "execution-mode": "remote",
#             "allow-destroy-plan": true,
#             "auto-apply": false,
#             "locked": false,
#             "resource-count": 0,
#             "created-at": "2025-06-09T09:09:19.872Z",
#             "updated-at": "2025-07-30T11:15:20.689Z",
#             "permissions": {
#                 "can-update": true,
#                 "can-destroy": true,
#                 "can-queue-run": true
#             }
#         },
#         "relationships": {
#             "organization": {
#                 "data": {
#                     "id": "sample_organization",
#                     "type": "organizations"
#                 }
#             }
#         },
#         "links": {
#             "self": "/api/v2/workspaces/ws-sample1234567890",
#             "self-html": "/app/sample_organization/workspaces/sample_workspace"
#         }
#         }
#     }
# }

- name: Gather information about a workspace by name and organization
  hashicorp.terraform.workspace_info:
    workspace: "sample_workspace"
    organization: "sample_organization"
  register: workspace_info

# Task output:
# ------------
# "workspace_info": {
#     "changed": false,
#     "failed": false,
#     "workspace": {
#         "id": "ws-sample1234567890",
#         "type": "workspaces",
#         "attributes": {
#             "name": "sample_workspace",
#             "terraform-version": "1.10.5",
#             "execution-mode": "remote",
#             "allow-destroy-plan": true,
#             "auto-apply": false,
#             "locked": false,
#             "resource-count": 0,
#             "created-at": "2025-06-09T09:09:19.872Z",
#             "updated-at": "2025-07-30T11:15:20.689Z",
#             "permissions": {
#                 "can-update": true,
#                 "can-destroy": true,
#                 "can-queue-run": true
#             }
#         },
#         "relationships": {
#             "organization": {
#                 "data": {
#                     "id": "sample_organization",
#                     "type": "organizations"
#                 }
#             }
#         },
#         "links": {
#             "self": "/api/v2/workspaces/ws-sample1234567890",
#             "self-html": "/app/sample_organization/workspaces/sample_workspace"
#         }
#         }
#     }
# }

- name: Handle case when workspace does not exist by ID
  hashicorp.terraform.workspace_info:
    workspace_id: "ws-invalid-workspace-id"
  register: workspace_info
  ignore_errors: true

# Task output:
# ------------
# FAILED! => {
#     "changed": false,
#     "failed": true,
#     "msg": "Workspace 'ws-invalid-workspace-id' was not found."
# }

- name: Handle case when workspace does not exist by name
  hashicorp.terraform.workspace_info:
    workspace: "nonexistent-workspace-name"
    organization: "my-organization"
  register: workspace_info
  ignore_errors: true

# Task output:
# ------------
# FAILED! => {
#     "changed": false,
#     "failed": true,
#     "msg": "The workspace nonexistent-workspace-name in my-organization organization was not found."
# }

- name: Conditional workspace operations based on existence
  block:
    - name: Try to get workspace info
      hashicorp.terraform.workspace_info:
        workspace: "{{ workspace_name }}"
        organization: "{{ organization }}"
      register: workspace_info

    - name: Workspace exists - proceed with operations
      ansible.builtin.debug:
        msg: "Workspace {{ workspace_info.workspace.attributes.name }} exists with ID {{ workspace_info.workspace.id }}"

  rescue:
    - name: Workspace doesn't exist - handle appropriately
      ansible.builtin.debug:
        msg: "Workspace {{ workspace_name }} does not exist in {{ organization }}, proceeding with alternative logic"

- name: Use workspace information in subsequent tasks
  hashicorp.terraform.workspace_info:
    workspace_id: "ws-sample1234567890"
  register: workspace_info

- name: Display workspace details
  ansible.builtin.debug:
    msg: |
      Workspace Details:
      - Name: {{ workspace_info.workspace.attributes.name }}
      - ID: {{ workspace_info.workspace.id }}
      - Terraform Version: {{ workspace_info.workspace.attributes['terraform-version'] }}
      - Execution Mode: {{ workspace_info.workspace.attributes['execution-mode'] }}
      - Auto Apply: {{ workspace_info.workspace.attributes['auto-apply'] }}
      - Locked: {{ workspace_info.workspace.attributes.locked }}
      - Resource Count: {{ workspace_info.workspace.attributes['resource-count'] }}

- name: Check workspace permissions before performing operations
  hashicorp.terraform.workspace_info:
    workspace: "production-workspace"
    organization: "my-company"
  register: workspace_info

- name: Proceed only if user can update workspace
  ansible.builtin.debug:
    msg: "User has update permissions for workspace"
  when: workspace_info.workspace.attributes.permissions['can-update']

- name: Example with parameter validation errors
  block:
    - name: Invalid combination - workspace_id with workspace name (will fail)
      hashicorp.terraform.workspace_info:
        workspace_id: "ws-sample1234567890"
        workspace: "sample_workspace"
      register: result
      ignore_errors: true

# Task output:
# ------------
# FAILED! => {
#     "changed": false,
#     "failed": true,
#     "msg": "Parameters workspace_id and workspace are mutually exclusive"
# }

    - name: Missing organization parameter (will fail)
      hashicorp.terraform.workspace_info:
        workspace: "sample_workspace"
      register: result
      ignore_errors: true

# Task output:
# ------------
# FAILED! => {
#     "changed": false,
#     "failed": true,
#     "msg": "parameters are required together: workspace, organization"
# }
"""

RETURN = r"""
workspace:
  type: dict
  description: A dictionary containing the workspace information.
  returned: on success
  contains:
    id:
      type: str
      returned: always
      description: The unique identifier of the workspace.
      sample: "ws-sample1234567890"
    type:
      type: str
      returned: always
      description: The type of the resource (always "workspaces").
      sample: "workspaces"
    attributes:
      type: dict
      returned: always
      description: The attributes of the workspace.
    relationships:
      type: dict
      returned: always
      description: Relationships to other resources.
    links:
      type: dict
      returned: always
      description: Links related to the workspace.
      contains:
        self:
          type: str
          returned: always
          description: API endpoint for this workspace.
        self-html:
          type: str
          returned: always
          description: Web UI URL for this workspace.
"""


from typing import TYPE_CHECKING

from ansible.module_utils._text import to_text


if TYPE_CHECKING:
    from typing import Any, Dict, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import (
    get_workspace,
    get_workspace_by_id,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ["workspace_id", "workspace"],
            ["workspace_id", "organization"],
        ],
        required_one_of=[
            ["workspace_id", "workspace"],
        ],
        required_together=[
            ["workspace", "organization"],
        ],
    )

    warnings: list[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = module.params
    params["check_mode"] = module.check_mode
    try:
        client = TerraformClient(**module.params)

        workspace_data: Optional[Dict[str, Any]] = None
        if params["workspace_id"]:
            # Retrieve workspace by ID
            workspace_data = get_workspace_by_id(client, params["workspace_id"])
            if not workspace_data:
                raise ValueError(f"Workspace '{params['workspace_id']}' was not found.")
        else:
            # Retrieve workspace by name and organization
            workspace_data = get_workspace(client, params["organization"], params["workspace"])
            if not workspace_data:
                raise ValueError(f"The workspace {params['workspace']} in {params['organization']} organization was not found.")

        # Remove the status field from the response as it's internal
        workspace_data.pop("status", None)

        # Update result with workspace information
        # The workspace_data already contains the proper structure from the API
        result["workspace"] = workspace_data

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
