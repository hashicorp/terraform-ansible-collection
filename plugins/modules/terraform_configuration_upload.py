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


import tarfile
import tempfile
import os
import time
from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    TerraformClient,
    TerraformModule,
    ArchivistClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.configuration import (
    upload_config,
    get_config,
)


def validate_and_prepare_tar(file_path, module):
    """
    Validates the given file path. If it's a single file and not a tar archive,
    it creates a temporary tar.gz archive and returns the new path and a flag.

    Returns:
        (file_path, is_temp_tar)
    """
    if os.path.isdir(file_path):
        module.fail_json(
            msg=f"The path '{file_path}' is a directory. Please provide a single file or a tar archive."
        )

    if os.path.isfile(file_path):
        if tarfile.is_tarfile(file_path):
            return file_path

        # Only allow .tf and .tf.json files to be tarred
        if file_path.endswith(".tf") or file_path.endswith(".tf.json"):
            try:
                temp_fd, temp_tar_path = tempfile.mkstemp(suffix=".tar.gz")
                os.close(temp_fd)
                with tarfile.open(temp_tar_path, "w:gz") as tar:
                    arcname = os.path.basename(file_path)
                    tar.add(file_path, arcname=arcname)
                file_path = temp_tar_path
            except Exception as e:
                module.fail_json(msg=f"Failed to create tar.gz from file '{file_path}': {e}")
        else:
            module.fail_json(
                msg=f"The file '{file_path}' is not a .tf or .tf.json file and is not a valid tar archive. "
                "Only .tf/.tf.json files are allowed for single-file uploads."
            )

    else:
        module.fail_json(msg=f"The path '{file_path}' is not a file or recognized archive format.")


def upload_configuration_version(client_archivist, params, module, upload_url):
    try:
        file_path = params["file_path"]
        file_path = validate_and_prepare_tar(file_path, module)
        response = upload_config(client_archivist, upload_url=upload_url, file_path=file_path)
        if response["status"] != 200:
            module.fail_json(msg=response["message"])
        return response["status"]

    except Exception as e:
        module.fail_json(msg=str(e))


def get_configuration_version(client_terraform, params, module, config_version_id):
    interval = params.get("interval")
    retries = params.get("retries")
    try:
        for attempt in range(retries):
            config_response = get_config(client_terraform, config_version_id=config_version_id)
            status = config_response.get("data")["data"]["attributes"]["status"]

            if status == "uploaded":
                return status

            time.sleep(interval)

        module.fail_json(
            msg=f"Configuration version status did not reach 'uploaded' after {retries} retries."
        )
    except Exception as e:
        module.fail_json(msg=str(e))


def main():
    module = TerraformModule(
        argument_spec=dict(
            configuration_version_id=dict(type="str", required=True),
            file_path=dict(type="str", required=True),
            state=dict(type="str", required=True),
            upload_url=dict(type="str", required=True),
            interval=dict(type="int", required=False, default=1),
            retries=dict(type="int", required=False, default=30),
        ),
    )
    warnings = []
    result = {"changed": False, "warnings": warnings}
    params = module.params
    client_archivist = ArchivistClient(tf_hostname="archivist.terraform.io")
    client_terraform = TerraformClient(
        tf_hostname=params["tf_hostname"], tf_token=params["tf_token"]
    )
    try:
        upload_response = upload_configuration_version(
            client_archivist, params, module, params["upload_url"]
        )
        config_status = get_configuration_version(
            client_terraform, params, module, params["configuration_version_id"]
        )

        result.update(
            {
                "changed": True,
                "upload_response": upload_response,
                "config_status": config_status,
                "configuration_version_id": params["configuration_version_id"],
            }
        )

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
