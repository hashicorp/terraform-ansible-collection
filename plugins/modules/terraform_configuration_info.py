# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function


DOCUMENTATION = r"""
---
module: terraform_configuration_info
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
      - When this key is set, I(organization) must be specified so that the ID of the workspace can be retrieved.
      - Workspace names can only include letters, numbers, -, and _.
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
  hashicorp.terraform.terraform_configuration_info:
    configuration_version_id: cv-UYwHEakurukz85nW

- name: Show the current configuration using workspace ID
  hashicorp.terraform.terraform_configuration_info:
    workspace_id: ws-6jrRyVDv1J8zQMB5

- name: Show the current configuration using workspace and organization name
  hashicorp.terraform.terraform_configuration_info:
    workspace: workspace-name
    organization: org-name
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
