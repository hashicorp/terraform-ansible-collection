#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: terraform_configuration_upload
version_added: 1.0.0
short_description: Upload configuration version in Terraform Enterprise/Cloud.
description:
  - List/Show configuration versions in Terraform Enterprise/Cloud.
  - If a workspace ID is specified, this module will list the configuration
    versions in the workspace.
  - If a configuration version ID is specified, this module will show the configuration
    versions details.
  - If a configuration version ID is specified and configuration_files is set to true, this module retrieves the configuration files of
    the configuration version.
options:
  workspace:
    description: The workspace ID for which the configuration version needs to be listed.
    type: str
  configuration_id:
    description: The ID of the configuration to show
    type: str
"""


EXAMPLES = r"""
- name: List the configuration versions of a workspace
  hashicorp.terraform.terraform_configuration_info:
    workspace: <your-workspace-id>

- name: Show the configuration
  hashicorp.terraform.terraform_configuration_info:
    configuration_id: <your-configuration-id>

- name: Retrieve the configuration files
  hashicorp.terraform.terraform_configuration_info:
    configuration_id: <your-configuration-id>
    configuration_files: true
"""

RETURN = r"""
outputs:
  type: list
  description: A list of dictionaries of configurations persent in the workspace
  returned: when workspace ID is provided
  contains:
    id:
      type: str
      returned: always
      description: The ID of the configuration version
    attributes:
        type: dictionary
        returned: always
        description: The attributes(status, source, etc.) of the configuration version
  type: dict
  description: A dictionary of details of the configuration pertaining to the configuration id provided
  returned: when configuration ID is provided
  contains:
    id:
      type: str
      returned: always
      description: The ID of the configuration version
    attributes:
        type: dictionary
        returned: always
        description: The attributes(status, source, etc.) of the configuration version  
  type: files
  description: Configuration files retrieved from the configuration version
  returned: when configuration ID is provided and configuration_files is set to true

"""