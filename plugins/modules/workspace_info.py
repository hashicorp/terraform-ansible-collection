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
  - If I(workspace_name) and I(organization_name) are provided, the module will return information about the workspace \
    with that name in the specified organization.
  - If the workspace does not exist, the module will fail with an error message.
extends_documentation_fragment: hashicorp.terraform.common
options:
  workspace_id:
    description:
      - The unique identifier of the workspace to retrieve information about.
      - Either I(workspace_id) or a combination of I(workspace_name) and I(organization_name) must be given to fetch workspace information.
    type: str
  workspace_name:
    description:
      - The name of the workspace to retrieve information about.
      - When this parameter is used, I(organization_name) must also be provided.
      - Either a combination of I(workspace_name) and I(organization_name) or I(workspace_id) must be given to fetch workspace information.
    type: str
  organization_name:
    description:
      - The name of the organization that contains the workspace.
      - This parameter is required when I(workspace_name) is provided.
    type: str
"""
EXAMPLES = r"""
- name: Gather information about a workspace by ID
  hashicorp.terraform.workspace_info:
    workspace_id: "ws-sample1234567890"
  register: workspace_info

- name: Gather information about a workspace by name and organization
  hashicorp.terraform.workspace_info:
    workspace_name: "sample_workspace"
    organization_name: "sample_organization"
  register: workspace_info

# Example output from workspace_info task:
# {
#   "workspace": {
#     "id": "ws-sample1234567890",
#     "type": "workspaces",
#     "attributes": {
#       "name": "sample_workspace",
#       "terraform-version": "1.10.5",
#       "execution-mode": "remote",
#       "allow-destroy-plan": true,
#       "auto-apply": false,
#       "locked": false,
#       "resource-count": 0,
#       "created-at": "2025-06-09T09:09:19.872Z",
#       "updated-at": "2025-07-30T11:15:20.689Z",
#       "permissions": {
#         "can-update": true,
#         "can-destroy": true,
#         "can-queue-run": true
#       }
#     },
#     "relationships": {
#       "organization": {
#         "data": {
#           "id": "sample_organization",
#           "type": "organizations"
#         }
#       }
#     }
#   }
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
    changed:
      description: Indicates if the module execution resulted in any changes. Always returns false for info modules.
      returned: always
      type: bool
      default: false
"""
