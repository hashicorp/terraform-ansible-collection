# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


DOCUMENTATION = r"""
---
module: output
version_added: "1.1.0"
short_description: Retrieve Terraform Cloud/Enterprise state version outputs
author: "Tanwi Geetika (@tgeetika)"
description:
  - Retrieve state version output information from HashiCorp Terraform Cloud or Terraform Enterprise.
  - Can retrieve a specific output by its ID or all outputs for a workspace's current state version.
  - Supports both Terraform Cloud and Terraform Enterprise deployments.
  - Returns output names, values, types, and sensitivity information.
  - Sensitive values are masked and handled according to Terraform's sensitivity flags for security.
options:
  state_version_output_id:
    description:
      - The ID of a specific state version output to retrieve.
      - When provided, only this specific output will be retrieved.
      - Mutually exclusive with workspace identification parameters.
    type: str
    aliases: ['output_id']
  workspace_id:
    description:
      - ID of the workspace to retrieve current state version outputs from.
      - When provided, all outputs for the workspace's current state version are retrieved.
      - Mutually exclusive with state_version_output_id.
      - Either workspace_id or both workspace and organization must be specified.
    type: str
  workspace:
    description:
      - Name of the workspace to retrieve current state version outputs from.
      - Must be used together with organization parameter.
      - Mutually exclusive with state_version_output_id.
      - Either both workspace and organization or workspace_id must be specified.
    type: str
  organization:
    description:
      - Name of the organization that the workspace belongs to.
      - Required when workspace parameter is specified.
      - Used to resolve workspace name to workspace ID.
    type: str
extends_documentation_fragment:
  - hashicorp.terraform.common
"""

EXAMPLES = r"""
# Get a specific output by ID
- name: Retrieve specific state version output
  hashicorp.terraform.output:
    state_version_output_id: wsout-J2zM24JRHbfabcd5
  register: result

# Task output:
# ------------
# "result": {
#         "changed": false,
#         "failed": false,
#         "output": {
#             "detailed_type": [
#                 "object",
#                 {
#                     "api_token": "string",
#                     "app_version": "string",
#                     "database_password": "string",
#                     "environment": "string"
#                 }
#             ],
#             "id": "wsout-fPuxNABcdefEidjE",
#             "name": "combined_config",
#             "sensitive": true,
#             "type": "object",
#             "value": "<sensitive>"
#         }
# }

# Get all outputs for a workspace using workspace ID
- name: Get workspace outputs by workspace ID
  hashicorp.terraform.output:
    workspace_id: ws-G4zM21234TGc10E5
  register: results

# Task output:
# ------------
# "results": {
#         "changed": false,
#         "count": 6,
#         "failed": false,
#         "outputs": [
#             {
#                 "detailed_type": "string",
#                 "id": "wsout-rEuZABcdeffD4tLn",
#                 "name": "api_token",
#                 "sensitive": true,
#                 "type": "string",
#                 "value": "<sensitive>"
#             },
#             {
#                 "detailed_type": "string",
#                 "id": "wsout-hVpLABcdefjhbgu4",
#                 "name": "app_version",
#                 "sensitive": false,
#                 "type": "string",
#                 "value": "1.1.0"
#             },
#             {
#                 "detailed_type": [
#                     "object",
#                     {
#                         "api_token": "string",
#                         "app_version": "string",
#                         "database_password": "string",
#                         "environment": "string"
#                     }
#                 ],
#                 "id": "wsout-fPuxABcdefrEidjE",
#                 "name": "combined_config",
#                 "sensitive": true,
#                 "type": "object",
#                 "value": "<sensitive>"
#             },
#             {
#                 "detailed_type": "string",
#                 "id": "wsout-3xhzABcdef9AXxf",
#                 "name": "database_password",
#                 "sensitive": true,
#                 "type": "string",
#                 "value": "<sensitive>"
#             },
#             {
#                 "detailed_type": "string",
#                 "id": "wsout-14doABcdefpRw51d",
#                 "name": "environment",
#                 "sensitive": false,
#                 "type": "string",
#                 "value": "staged"
#             },
#             {
#                 "detailed_type": "string",
#                 "id": "wsout-Z36hABcdef6zVFfN",
#                 "name": "web_server_id",
#                 "sensitive": false,
#                 "type": "string",
#                 "value": "i-01fdf53b9d57b5c4f"
#             }
#         ]
# }

- name: Display all workspace outputs
  ansible.builtin.debug:
    msg: |
      Found {{ results.count }} outputs:
      {% for output in results.outputs %}
      - {{ output.name }}: {{ output.value }} (type: {{ output.type }}, sensitive: {{ output.sensitive }})
      {% endfor %}

# Task output:
# ------------
# {
#     "msg": "Found 6 outputs:
# - api_token: <sensitive> (type: string, sensitive: True)
# - app_version: 1.1.0 (type: string, sensitive: False)
# - combined_config: <sensitive> (type: object, sensitive: True)
# - database_password: <sensitive> (type: string, sensitive: True)
# - environment: staged (type: string, sensitive: False)
# - web_server_id: i-01fdf53b9abcdef4f (type: string, sensitive: False)"
# }

# Get all outputs for a workspace using workspace and organization name
- name: Get workspace outputs by workspace and organization name
  hashicorp.terraform.output:
    workspace: plan_info_module
    organization: Ansible-BU-TFC
  register: results

# Task output:
# ------------
# "results": {
#         "changed": false,
#         "count": 6,
#         "failed": false,
#         "outputs": [
#             {
#                 "detailed_type": "string",
#                 "id": "wsout-rEuZABcdeffD4tLn",
#                 "name": "api_token",
#                 "sensitive": true,
#                 "type": "string",
#                 "value": "<sensitive>"
#             },
#             {
#                 "detailed_type": [
#                     "object",
#                     {
#                         "api_token": "string",
#                         "app_version": "string",
#                         "database_password": "string",
#                         "environment": "string"
#                     }
#                 ],
#                 "id": "wsout-fPuxABcdefrEidjE",
#                 "name": "combined_config",
#                 "sensitive": true,
#                 "type": "object",
#                 "value": "<sensitive>"
#             },
#         ]
# }

# Invalid state_version_output_id
- name: Retrieve output with invalid state_version_output_id
  hashicorp.terraform.output:
    state_version_output_id: wsout-INVALID1234
  register: result

# Task output:
# ------------
# FAILED! => {
#     "changed": false,
#     "failed": true,
#     "msg": "State version output with ID 'wsout-fPuxABcdrEidj' was not found."
# }

# Invalid workspace_id
- name: Get workspace outputs with invalid workspace_id
  hashicorp.terraform.output:
    workspace_id: ws-INVALID4567
  register: results

# Task output:
# ------------
# FAILED! => {
#     "changed": false,
#     "failed": true,
#     "msg": "Workspace with ID 'ws-INVALID456' was not found."
# }
"""

RETURN = r"""
output:
  description: Single state version output information (when state_version_output_id is provided).
  returned: when state_version_output_id is specified
  type: dict
  contains: &output_fields
    id:
      description: The unique identifier of the state version output.
      type: str
      sample: "wsout-fPuxNABcdefEidjE"
    name:
      description: The name of the output variable.
      type: str
      sample: "combined_config"
    value:
      description: The output value. Shows "<sensitive>" for sensitive outputs.
      type: raw
      sample: "<sensitive>"
    type:
      description: The basic type of the output (string, object, etc.).
      type: str
      sample: "object"
    detailed_type:
      description: Detailed type information including nested structure.
      type: raw
      sample: ["object", {"api_token": "string"}]
    sensitive:
      description: Whether the output is marked as sensitive.
      type: bool
      sample: true
outputs:
  description: List of workspace state version outputs (when workspace parameters are provided).
  returned: when workspace_id or workspace+organization is specified
  type: list
  elements: dict
  contains: *output_fields
"""
