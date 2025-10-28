# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


DOCUMENTATION = r"""
name: tf_output
short_description: Retrieve Terraform Cloud/Enterprise output values
version_added: "1.2.0"
author: "Tanwi Geetika (@tgeetika)"
description:
  - Retrieve Terraform output values from HashiCorp Terraform Cloud or Terraform Enterprise.
  - Returns the actual output value for direct use in playbooks and templates.
  - Supports retrieving outputs by name from workspace or by specific output ID.
  - Sensitive values are masked as I('<sensitive>') for security.
options:
  state_version_output_id:
    description:
      - The ID of a specific state version output to retrieve.
      - Mutually exclusive with I(name) and all workspace parameters (I(workspace_id), I(workspace), I(organization)).
    type: str
  name:
    description:
      - Name of the specific output to retrieve.
      - Must be used with I(workspace) parameters.
    type: str
  workspace_id:
    description:
      - ID of the workspace to retrieve outputs from.
      - Required when looking up by output name.
    type: str
  workspace:
    description:
      - Name of the workspace to retrieve outputs from.
      - Must be used together with the I(organization) parameter.
    type: str
  organization:
    description:
      - Name of the organization that the workspace belongs to.
      - Required when the I(workspace) parameter is specified.
    type: str
  tf_hostname:
    description:
      - Terraform Cloud/Enterprise hostname.
      - Defaults to C(app.terraform.io) for Terraform Cloud.
    type: str
    default: app.terraform.io
    aliases: ['hostname']
  tf_token:
    description:
      - Terraform Cloud/Enterprise API token.
      - Can also be specified via the C(TF_CLOUD_TOKEN) environment variable.
    type: str
    aliases: ['token']
  tf_validate_certs:
    description:
      - Whether to validate SSL certificates for HTTPS requests.
      - Set to I(false) to disable certificate validation (not recommended for production).
    type: bool
    default: true
  display_sensitive:
    description:
      - Whether to return actual values for sensitive outputs.
      - When I(false) (default), sensitive values return I('<sensitive>').
      - When I(true), returns the actual sensitive value from the API.
      - For workspace-based lookups, this triggers individual API calls to retrieve actual sensitive values.
      - Use with caution — sensitive values may appear in logs and output.
    type: bool
    default: false
"""

EXAMPLES = r"""
# Get output value by name from workspace ID
- name: Get specific output from a workspace
  set_fact:
    api_token: "{{ lookup('hashicorp.terraform.tf_output', name='api_token', workspace_id='ws-123', display_sensitive=True) }}"

# Task output:
# ------------
# ok: [localhost] => {
#     "ansible_facts": {
#         "api_token": "tok_updated_xyz125"
#     },
#     "changed": false
# }

# Get all output values from workspace name and organization
- name: Get all outputs for a workspace
  ansible.builtin.debug:
    msg: "{{ lookup('hashicorp.terraform.tf_output', workspace='my_workspace', organization='my_org', display_sensitive=True) }}"

# Task output:
# ------------
# ok: [localhost] => {
#     "msg": [
#         {
#             "detailed_type": "string",
#             "id": "wsout-rEuZoKuZKwfD4tLn",
#             "name": "api_token",
#             "sensitive": true,
#             "type": "string",
#             "value": "tok_updated_xyz125"
#         },
#         {
#             "detailed_type": "string",
#             "id": "wsout-hVpLzbcKaJjhbgu4",
#             "name": "app_version",
#             "sensitive": false,
#             "type": "string",
#             "value": "1.1.0"
#         },
#         {
#             "detailed_type": "string",
#             "id": "wsout-3xhzxFtjP8g9AXxf",
#             "name": "database_password",
#             "sensitive": true,
#             "type": "string",
#             "value": "updated-secure-password-126"
#         }
#     ]
# }
# Get output value by specific output ID
- name: Get specific output
  ansible.builtin.debug:
    msg: "{{ lookup('hashicorp.terraform.tf_output', state_version_output_id='wsout-123abc') }}"

# Task output:
# ------------
# ok: [localhost] => {
#     "msg": "updated-secure-password-126"
# }
"""

RETURN = r"""
value:
  description:
    - The Terraform output value retrieved from Terraform Cloud or Terraform Enterprise.
    - The structure of the return value depends on the lookup parameters used.
    - When fetching a single output (by name or ID), returns the actual output value (string, list, or dict).
    - When fetching all outputs for a workspace, returns a list of output dictionaries with details.
    - Sensitive outputs are masked as <sensitive> unless display_sensitive=True is set.
  returned: success
  type: raw
  sample:
    - "Example single value: i-01fdABcdef57b5c4f"
"""

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output import (
    get_output_by_name,
    get_specific_output,
    get_workspace_outputs,
    resolve_workspace_id,
)


class LookupModule(LookupBase):
    """Terraform output lookup plugin."""

    def _validate_parameters(self, state_version_output_id, workspace_id, workspace, organization, name):
        """Validate parameter combinations and return whether to allow all outputs."""
        if state_version_output_id:
            if workspace_id or workspace or organization or name:
                raise AnsibleError(
                    "state_version_output_id is mutually exclusive with workspace/name parameters",
                )
            return None

        if not (workspace_id or (workspace and organization)):
            raise AnsibleError(
                "Either state_version_output_id or workspace identification must be provided",
            )
        return not name

    def _get_output_value(
        self,
        client,
        state_version_output_id,
        workspace_id,
        workspace,
        organization,
        name,
        allow_all_outputs,
        display_sensitive,
    ):
        """Retrieve output value based on the provided parameters."""
        if state_version_output_id:
            output_data = get_specific_output(
                client,
                state_version_output_id,
                display_sensitive=display_sensitive,
            )
            return output_data["value"]

        workspace_id = resolve_workspace_id(client, workspace_id, workspace, organization)

        if allow_all_outputs:
            return get_workspace_outputs(
                client,
                workspace_id,
                display_sensitive=display_sensitive,
            )

        output_data = get_output_by_name(
            client,
            workspace_id,
            name,
            display_sensitive=display_sensitive,
        )
        return output_data["value"]

    def run(self, terms, variables=None, **kwargs):
        """Run the lookup plugin."""
        state_version_output_id = kwargs.get("state_version_output_id")
        workspace_id = kwargs.get("workspace_id")
        workspace = kwargs.get("workspace")
        organization = kwargs.get("organization")
        name = kwargs.get("name")
        display_sensitive = kwargs.get("display_sensitive", False)
        kwargs.setdefault("tf_validate_certs", True)
        kwargs.setdefault("tf_hostname", "app.terraform.io")

        allow_all_outputs = self._validate_parameters(
            state_version_output_id,
            workspace_id,
            workspace,
            organization,
            name,
        )

        client = TerraformClient(**kwargs)

        try:
            value = self._get_output_value(
                client,
                state_version_output_id,
                workspace_id,
                workspace,
                organization,
                name,
                allow_all_outputs,
                display_sensitive,
            )
        except ValueError as e:
            raise AnsibleError(f"Output lookup failed - resource not found: {str(e)}")
        except Exception as e:
            raise AnsibleError(f"Output lookup failed - API error: {str(e)}")

        if allow_all_outputs is True:
            return value

        return [value]
