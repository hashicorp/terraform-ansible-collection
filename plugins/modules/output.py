# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: output
version_added: "1.2.0"
short_description: Retrieve Terraform Cloud/Enterprise state version outputs
author: "Tanwi Geetika (@tgeetika)"
description:
  - Retrieve state version output information from HashiCorp Terraform Cloud or Terraform Enterprise.
  - Can retrieve a specific output by its ID, by name, or all outputs for a workspace's current state version.
  - Supports both Terraform Cloud and Terraform Enterprise deployments.
  - Returns output names, values, types, and sensitivity information.
  - Sensitive values are masked and handled according to Terraform's sensitivity flags for security.
options:
  state_version_output_id:
    description:
      - The ID of a specific state version output to retrieve.
      - When provided, only this specific output will be retrieved.
      - Mutually exclusive with I(workspace_id), I(workspace), I(organization), and I(name).
    type: str
    aliases: ['output_id']
  workspace_id:
    description:
      - ID of the workspace to retrieve current state version outputs from.
      - When provided without I(name), all outputs for the workspace's current state version are retrieved.
      - Required when using I(name).
      - Mutually exclusive with I(state_version_output_id).
      - Either I(workspace_id) or both I(workspace) and I(organization) must be specified.
    type: str
  workspace:
    description:
      - Name of the workspace to retrieve current state version outputs from.
      - Must be used together with I(organization) parameter.
      - Mutually exclusive with I(state_version_output_id).
      - Either both I(workspace) and I(organization) or I(workspace_id) must be specified.
    type: str
  organization:
    description:
      - Name of the organization that the workspace belongs to.
      - Required when I(workspace) parameter is specified.
      - Used to resolve workspace name to workspace ID.
    type: str
  name:
    description:
      - Name of a specific output to retrieve from the workspace.
      - Must be used with workspace identification (I(workspace_id) or I(workspace)/I(organization)).
      - Mutually exclusive with I(state_version_output_id) parameter.
      - Returns a single output in the same format as I(state_version_output_id).
      - "Note: For sensitive outputs, use display_sensitive=true to retrieve actual values."
      - "Example: api_token, web_server_id"
    type: str
  display_sensitive:
    description:
      - Whether to return actual values for sensitive outputs.
      - When I(false) (default), sensitive values are masked as I('<sensitive>').
      - When I(true), returns the actual sensitive value from the API.
      - For workspace-based lookups (name or all outputs), when I(display_sensitive=true),
        the module makes individual API calls to retrieve actual sensitive values.
    type: bool
    default: false
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

# Get a specific output by name with workspace_id
- name: Get API token output by name
  hashicorp.terraform.output:
    workspace_id: ws-G4zMABcdeffc10E5
    name: api_token
  register: api_token

# Task output:
# ------------
# "api_token": {
#         "changed": false,
#         "failed": false,
#         "output": {
#             "detailed_type": "string",
#             "id": "wsout-rEuZoKuZKwfD4tLn",
#             "name": "api_token",
#             "sensitive": true,
#             "type": "string",
#             "value": "<sensitive>"
#     }

# }

# Get a specific output by name with workspace name and organization
- name: Get web server ID by name using workspace name
  hashicorp.terraform.output:
    workspace: my-workspace
    organization: my-org
    name: web_server_id
  register: server_id

# Task output:
# ------------
# "server_id": {
#         "changed": false,
#         "failed": false,
#         "output": {
#             "detailed_type": "string",
#             "id": "wsout-Z36hVVywsh6zVFfN",
#             "name": "web_server_id",
#             "sensitive": false,
#             "type": "string",
#             "value": "i-01fdf53b9d57b5c4f"
#         }
#     }
# }

# Get all outputs for a workspace using workspace ID
- name: Get workspace outputs by workspace ID
  hashicorp.terraform.output:
    workspace_id: ws-G4zMABcdefGc10E5
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
    display_sensitive: true
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
#                 "value": "tok_updated_xyz125"
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
#                 "value": {
#                   "api_token": "tok_updated_xyz125",
#                   "app_version": "1.1.0",
#                   "database_password": "updated-secure-password-126",
#                   "environment": "staged"
#               }
#           },
#      ]
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
#     "msg": "State version output with ID 'wsout-INVALID1234' was not found."
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
#     "msg": "Workspace with ID 'ws-INVALID4567' was not found."
# }
"""

RETURN = r"""
output:
  description: Single state version output information (when state_version_output_id or name is provided).
  returned: when state_version_output_id or name is specified and found
  type: dict
  contains:
    id:
      description: The unique identifier of the state version output.
      type: str
      sample: "wsout-fPuxNABcdefEidjE"
    name:
      description: The name of the output variable.
      type: str
      sample: "combined_config"
    value:
      description: The output value. Shows I('<sensitive>') for sensitive outputs unless I(display_sensitive) is C(true).
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
  returned: when workspace_id or workspace + organization is specified without name parameter.
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the state version output.
      type: str
      sample: "wsout-fPuxNABcdefEidjE"
    name:
      description: The name of the output variable.
      type: str
      sample: "combined_config"
    value:
      description:
        - The output value.
        - Shows I('<sensitive>') for sensitive outputs unless I(display_sensitive) is C(true).
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
count:
  description: Number of outputs returned when retrieving workspace outputs.
  returned: when workspace_id or workspace + organization is specified without name parameter.
  type: int
  sample: 6
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Dict

from copy import deepcopy

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output import (
    get_output_by_name,
    get_specific_output,
    get_workspace_outputs,
    resolve_workspace_id,
)


def main() -> None:
    """Main module execution function."""
    module = AnsibleTerraformModule(
        argument_spec={
            "state_version_output_id": {"type": "str", "aliases": ["output_id"]},
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
            "display_sensitive": {"type": "bool", "default": False},
        },
        mutually_exclusive=[
            ["state_version_output_id", "workspace_id"],
            ["state_version_output_id", "workspace"],
            ["state_version_output_id", "organization"],
            ["state_version_output_id", "name"],
        ],
        required_together=[["workspace", "organization"]],
        required_one_of=[
            ["state_version_output_id", "workspace_id", "workspace"],
        ],
    )

    params = deepcopy(module.params)
    state_version_output_id = params.get("state_version_output_id")
    workspace_id = params.get("workspace_id")
    workspace = params.get("workspace")
    organization = params.get("organization")
    name = params.get("name")
    display_sensitive = params.get("display_sensitive", False)

    result: Dict[str, Any] = {"changed": False}

    try:
        client = TerraformClient(**params)

        if state_version_output_id:
            output_data = get_specific_output(client, state_version_output_id, display_sensitive=display_sensitive)
            result["output"] = output_data
        else:
            workspace_id = resolve_workspace_id(client, workspace_id, workspace, organization)
            if name:
                output_data = get_output_by_name(client, workspace_id, name, display_sensitive=display_sensitive)
                result["output"] = output_data
            else:
                outputs = get_workspace_outputs(client, workspace_id, display_sensitive=display_sensitive)
                if outputs:
                    result["outputs"] = outputs
                    result["count"] = len(outputs)
                else:
                    result["outputs"] = []
                    result["count"] = 0
                    result["msg"] = "No outputs found for workspace."

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
