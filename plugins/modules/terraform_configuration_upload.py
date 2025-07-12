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
    description: The path to the configuration file to be uploaded
    type: path
    required: true
  state:
    description: The action to be performed.
    type: str
    required: true
  configuration_version_id:
    description: The configuration version ID to which the upload corresponds to.
    type: str
"""


EXAMPLES = r"""
- name: Upload file to the configuration version upload URL
  hashicorp.terraform.terraform_configuration_upload:
    state: present
    file_path: <path-to-the-configuration-file>
    upload_url: <configuration-version-upload-url>
    configuration_version_id: <id-of-the-configuration-version>
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


import tarfile
import tempfile
import os
import q
from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    TerraformClient,
    TerraformModule,
    ArchivistClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.configuration import upload_config, get_config


def main():
    module = TerraformModule(
        argument_spec=dict(
            configuration_version_id=dict(type="str", required=True),
            file_path=dict(type="str", required=True),
            state=dict(type="str", required=True),
            upload_url=dict(type="str", required=True),
        ),
    )
    warnings = []
    result = {"changed": False, "warnings": warnings}
    params = module.params
    file_path = params["file_path"]
    if os.path.isdir(file_path):
      module.fail_json(
          msg=f"The path '{file_path}' is a directory. Please provide a single file or a tar archive."
      )

    is_temp_tar = False
    if os.path.isfile(file_path) and not tarfile.is_tarfile(file_path):
        try:
            temp_fd, temp_tar_path = tempfile.mkstemp(suffix=".tar.gz")
            os.close(temp_fd)  # Close the open fd returned by mkstemp
            with tarfile.open(temp_tar_path, "w:gz") as tar:
                arcname = os.path.basename(file_path)
                tar.add(file_path, arcname=arcname)
            file_path = temp_tar_path
            is_temp_tar = True
        except Exception as e:
            module.fail_json(msg=f"Failed to create tar.gz from file '{params['file_path']}': {e}")

    # Final validation that it's a tarfile
    if not tarfile.is_tarfile(file_path):
        module.fail_json(
            msg=f"The file '{file_path}' is not a valid tar archive. "
                "Ensure the original file or generated archive is valid."
        )

    client_archivist = ArchivistClient(tf_hostname="archivist.terraform.io")
    client_terraform = TerraformClient(tf_hostname=params["tf_hostname"], tf_token=params["tf_token"])
    try:
        if params["state"] == "present":
            response = upload_config(client_archivist, upload_url=params["upload_url"],file_path=file_path)
            q(response)
            if response["status"] != 200:
                module.fail_json(msg=response["message"])
            if params.get('configuration_version_id'):
              config_response=get_config(client_terraform, config_version_id=params['configuration_version_id'])
              result.update({"configuration_status":config_response.get("data")['data']['attributes']['status']})
              result.update(params['configuration_version_id'])

            result.update({
                "changed": True,
                "upload_response":response,
            })

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == "__main__":
    main()