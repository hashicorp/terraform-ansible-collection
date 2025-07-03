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
  file_path:
    description: The path to the configuration file to be uploaded
    type: path
    required: true
  state:
    description: The action to be performed.
    type: str
    required: true
"""


EXAMPLES = r"""
- name: Upload file to the configuration version upload URL
  hashicorp.terraform.terraform_configuration_upload:
    state: present
    file_path: <path-to-the-configuration-file>
    upload_url: <configuration-version-upload-url>
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
