#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: terraform_configuartion_version
version_added: 1.0.0
short_description: Create configuration version in Terraform Enterprise/Cloud.
description:
  - Create/Archive configuration version in Terraform Enterprise/Cloud.
  - If a workspace id is specified and the state is present, this module will create a configuration
    version in the workspace and return the upload url.
  - If a configuration_version_id is specified and the state is archive, this module will discard the uploaded .tar.gz
     file associated with this configuration version. This can only archive the configuration versions that
     were created with the API or CLI, are in an uploaded state, have no runs in progress, and are not the
     current configuration version for any workspace.
options:
  state:
    description: The action to be performed for the configuration version.
    type: str
    required: true
  organization:
    description:
      - Name of the organization that the workspace for the configuration-version belongs to.
      - This is required when `workspace` key is set.
    type: str
  workspace:
    description:
      - Name of the workspace for the configuration-version.
      - When this key is set, `organization` must be specified so that the ID of the workspace can be retrieved.
    type: str
  workspace_id:
    description:
      - ID of the workspace for the configuration-version.
      - Either `workspace` (and `organization`) or `workspace_id` must be specified when creating new a `configuration-version`.
    type: str
  auto-queue-runs: When true, runs are queued automatically when the configuration version is uploaded.
    type: boolean
    default: true
  speculative: When true, this configuration version may only be used to create runs which are speculative which cannot be confirmed or applied.
    type: boolean
    default: false
  provisional: When true, this configuration version does not immediately become the workspace current configuration version. If the associated run is applied, it then becomes the current configuration version unless a newer one exists.
    type: boolean
    default: false
  configuration_version_id:
    description: The id of the configuration version that needs to be archived.
    type: str
  archive:
    description: The option states if archive needs to be performed on the configuration version. Since deletion is not a supported
    option currently, hence this parameter is a required option as it is the only supported option for state 'absent' currently.
    type: bool
"""


EXAMPLES = r"""
- name: Create a configuration version
  hashicorp.terraform.terraform_configuration_version:
    workspace: <your-workspace-id>
    state: present
- name: Create a configuration version but do not queue runs automatically when the configuration version is uploaded.
  hashicorp.terraform.terraform_configuration_version:
    workspace_id: <your-workspace-id>
    state: present
    auto-queue-runs: false
- name: Create a configuration may only be used to create speculative runs
  hashicorp.terraform.terraform_configuration_version:
    workspace_id: <your-workspace-id>
    state: present
    speculative: true
- name: Create a configuration version that will not immediately become the workspace current configuration version
  hashicorp.terraform.terraform_configuration_version:
    workspace_id: <your-workspace-id>
    state: present
    provisional: true
- name: Discard a configuration version
  hashicorp.terraform.terraform_configuration_version:
    state: archive
    configuration_version_id: <configuration-version-id>
"""

RETURN = r"""
outputs:
  type: dict
  description: A dictionary of the configuration version details.
  returned: when state is create
  contains:
    configuration_version_id:
      type: str
      returned: always
      description: ID of the configuration version created
    upload-url:
      type: str
      returned: always
      description: Upload URL for the configuration version
    status:
      type: str
      returned: always
      description: The status of the configuration version (pending, errored, uploaded, etc)
  type: dict
  description: A status of the archive operation.
  returned: when state is archive
  contains:
    status:
      type: str
      returned: always
      description: The status code of the configuration version archive action
    configuration_version_id:
        type: str
        returned: always
        description: ID of the configuration version created
"""
