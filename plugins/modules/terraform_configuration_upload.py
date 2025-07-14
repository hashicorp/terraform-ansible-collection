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
  - Upload configuration version in Terraform Enterprise/Cloud.
  - If a upload URL and file path is specified and the state is present, this module will upload your configuration
    file to the upload url.
options:
  upload_url:
    description: The URL to which the configuration file will be uploaded.
    type: str
    required: true
  file_path:
   description:
    - Path to the configuration file that should be uploaded for the configuration version.
    - This can be a single `.tf` file or a tarball (`.tar.gz`) containing configuration-related files. When a single file `.tf` file is provided, the module creates a tarball and then uploads it to Archivist.
    - This file will be read from the Ansible 'host' context and not the 'controller' context.
  type: str
  state:
    description: The state the upload in configuration version should be in.
    type: str
    required: true
  configuration_version_id:
   description:
    - The ID of an configuration version.
  type: str
  interval:
   description:
    - Configures the interval (in seconds) to wait between retries of inspecting the `configuration-version` status.
    - This is used with `state=present` when creating a new configuration-version and uploading a configuration file for it.
    - This works in conjunction with the `retries` parameter.
  type: int
  default: 1
  retries:
   description:
    - Specifies the number of retries to perform while waiting for the `status` of a newly created configuration to be `uploaded`.
    - This is used with `state=present` when creating a new configuration-version and uploading a configuration file for it.
    - This works in conjunction with the `interval` parameter.
"""


EXAMPLES = r"""
- name: Upload file to the configuration version upload URL
  hashicorp.terraform.terraform_configuration_upload:
    state: present
    file_path: <path-to-the-configuration-file>
    upload_url: <configuration-version-upload-url>
    configuration_version_id: <id-of-the-configuration-version>
    interval: 1
    retries: 20
"""

RETURN = r"""
outputs:
  type: str
  description: A status of the upload state.
  returned: when state is present
  contains:
    status:
      type: str
      returned: always
      description: The status of the configuration version (pending, errored, uploaded, etc)
"""