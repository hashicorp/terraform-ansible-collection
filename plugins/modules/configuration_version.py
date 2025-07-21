#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# language=yaml
DOCUMENTATION = r"""
---
module: configuration_version
version_added: 1.0.0
short_description: Create configuration version in Terraform Enterprise/Cloud.
description:
  - Create/Archive/Upload configuration version in Terraform Enterprise/Cloud.
  - If a workspace and configuration_files_path is specified and the state is present, this module will create a configuration
    version in the workspace and upload the file to it.
  - If a configuration_version_id is specified and the state is archive, this module will discard the uploaded .tar.gz
    file associated with this configuration version. This can only archive the configuration versions that
    were created with the API or CLI, are in an uploaded state, have no runs in progress, and are not the
    current configuration version for any workspace.
options:
  state:
    description:
      - The state the configuration version should be in.
      - Setting `state=present` creates a new configuration-version and upload to it.
      - Setting `state=absent` attempts to delete a configuration-version, if it exists. Requires the `configuration_version_id` field to be set.
        This would fail if not run against a Terraform Enterprise instance since deleting a configuration version is exclusively supported with TFE.
      - Setting `state=archive` archives an existing configuration-version, if it exists. Requires the `configuration_version_id` field to be set.
    type: str
    choices: ["present", "absent", "archive"]
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
  auto_queue_runs:
    description:
      - When true, runs are queued automatically when the configuration version is uploaded.
    type: bool
    default: true
  speculative:
    description:
      - When true, this configuration version may only be used to create runs which are speculative which cannot be confirmed or applied.
    type: bool
    default: false
  provisional:
    description:
      - When true, this configuration version does not immediately become the workspace current configuration version.
        If the associated run is applied, it then becomes the current configuration version unless a newer one exists.
    type: bool
    default: false
  configuration_version_id:
    description:
      - The id of the configuration version that needs to be archived.
    type: str
  configuration_files_path:
    description:
      - Path to the configuration file that should be uploaded for the configuration version.
      - This can be a directory or a tarball (`.tar.gz`) containing configuration-related files.
      - When a path to a directory is provided, all it's content will be built into a tarball ('.tar.gz') within the module.
      - This file will be read from the Ansible 'host' context and not the 'controller' context.
    type: str
    required: true
  interval:
    description:
      - Configures the interval (in seconds) to wait between retries of inspecting the `configuration-version` status.
      - This is used with `state=present` when creating a new configuration-version and uploading a configuration file for it.
      - This works in conjunction with the `tf_max_retries` parameter.
    type: int
    default: 1
"""


EXAMPLES = r"""
- name: Create a configuration version and queue runs
  hashicorp.terraform.configuration_version:
    workspace: <your-workspace-id>
    state: present
    configuration_files_path: <path-to-your-configuration-files>
    interval: 3
    tf_max_retries: 1
- name: Create a configuration version but do not queue runs automatically when the configuration version is uploaded.
  hashicorp.terraform.configuration_version:
    workspace: <your-workspace-name>
    organization: <your-organization-name>
    state: present
    auto-queue-runs: false
    configuration_files_path: <path-to-your-configuration-file>
- name: Create a configuration for speculative runs
  hashicorp.terraform.configuration_version:
    workspace_id: <your-workspace-id>
    state: present
    speculative: true
    configuration_files_path: <path-to-your-configuration-file>
- name: Create a configuration version that will not immediately become the workspace current configuration version
  hashicorp.terraform.configuration_version:
    workspace_id: <your-workspace-id>
    state: present
    provisional: true
    configuration_files_path: <path-to-your-configuration-file>
- name: Discard a configuration version
  hashicorp.terraform.configuration_version:
    state: archive
    configuration_version_id: <configuration-version-id>
"""

RETURN = r"""
outputs:
  type: dict
  description: A dictionary of the configuration version details.
  returned: on success
  contains:
    configuration_version_id:
      type: str
      returned: always
      description: ID of the configuration version created/archived.
    upload_response:
      type: str
      returned: when state is 'present'
      description: The status code of the configuration version.
    status:
      type: str
      returned: when state is 'present'
      description: The status of the configuration version (pending, errored, uploaded, etc).
    msg:
      type: str
      returned: when state is 'archive'
      description: The successfull completion of archive.
"""

import os
import tarfile
import tempfile
import gzip
import time
from typing import Any, Dict, Tuple
from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    TerraformClient,
    TerraformModule,
    ArchivistClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.configuration import (
    create_config,
    archive_config,
    upload_config,
    get_config,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace


def validate_and_prepare_tar(configuration_files_path: str, module: Any) -> str:
    """
    Validates and prepares the given path for upload.

    - If the path is a directory, it is archived into a temporary .tar.gz file.
    - If the path is a valid tar.gz archive, it's returned as-is after basic validation.
    - Other file types are rejected.

    Args:
        configuration_files_path (str): The file or directory path to validate and prepare.
        module (Any): Ansible module object used for error handling (fail_json).

    Returns:
        str: A path to the prepared tar.gz file or the original valid file.
    """
    if os.path.isdir(configuration_files_path):
        try:
            temp_fd, temp_tar_path = tempfile.mkstemp(suffix=".tar.gz")
            os.close(temp_fd)
            with tarfile.open(temp_tar_path, "w:gz") as tar:
                for item in os.listdir(configuration_files_path):
                    item_path = os.path.join(configuration_files_path, item)
                    tar.add(item_path, arcname=item)
            return temp_tar_path
        except Exception as e:
            module.fail_json(
                msg=f"Failed to create tar.gz from directory '{configuration_files_path}': {e}"
            )

    if os.path.isfile(configuration_files_path):
        if tarfile.is_tarfile(configuration_files_path):
            try:
                with gzip.open(configuration_files_path, "rb") as f:
                    f.read(1)
                return configuration_files_path
            except Exception as e:
                module.fail_json(msg="Bad gzip file")
        else:
            module.fail_json(
                msg=f"The path '{configuration_files_path}' is not a valid tar.gz archive. "
            )

    else:
        module.fail_json(
            msg=f"The path '{configuration_files_path}' is not a file or recognized archive format."
        )


def create_configuration_version(
    client_terraform: Any, params: Dict[str, Any], module: Any
) -> Tuple[str, str]:
    """
    Creates a new Terraform configuration version using the given client and parameters.

    This function builds the payload based on input parameters and invokes the Terraform API
    to create a configuration version for the specified workspace. It returns the configuration
    version ID and the upload URL for uploading the configuration tarball.

    Args:
        client_terraform (Any): Authenticated Terraform API client.
        params (Dict[str, Any]): Dictionary containing configuration parameters such as:
            - workspace_id (str)
            - auto_queue_runs (bool)
            - speculative (bool)
            - provisional (bool)
        module (Any): Ansible module object for error reporting.

    Returns:
        Tuple[str, str]: A tuple containing the configuration version ID and the upload URL.

    Raises:
        module.fail_json: If the request to create a configuration version fails.
    """
    try:
        payload = {
            "data": {
                "type": "configuration-versions",
                "attributes": {
                    "auto-queue-runs": params["auto_queue_runs"],
                    "speculative": params["speculative"],
                    "provisional": params["provisional"],
                },
            }
        }
        config_version = create_config(client_terraform, params["workspace_id"], payload)
        config_version_id = config_version.get("data").get("data", {}).get("id")
        upload_url = (
            config_version.get("data").get("data", {}).get("attributes", {}).get("upload-url")
        )
        return config_version_id, upload_url
    except Exception as e:
        module.fail_json(msg=str(e))


def upload_configuration_version(
    client_archivist: Any,
    params: dict,
    module: Any,
    upload_url: str,
    configuration_files_path: str,
) -> int:
    """
    Uploads a Terraform configuration tarball to the specified upload URL.

    This function uses the provided file path to prepare a tar.gz archive (if necessary),
    then uploads it using the provided client. It validates the response and returns
    the HTTP status code on success.

    Args:
        client_archivist (Any): Client instance used to perform the upload.
        params (dict): Dictionary containing parameters including:
            - configuration_files_path (str): Path to the file or directory to upload.
        module (Any): Ansible module object for error handling (fail_json).
        upload_url (str): Pre-signed upload URL for the configuration version.

    Returns:
        int: HTTP status code from the upload response.

    Raises:
        module.fail_json: If file preparation fails, or the upload fails with a non-200 status.
    """
    try:
        response = upload_config(
            client_archivist,
            upload_url=upload_url,
            configuration_files_path=configuration_files_path,
        )
        if response["status"] != 200:
            module.fail_json(msg=response["message"])
        return response["status"]

    except Exception as e:
        module.fail_json(msg=str(e))


def get_configuration_version(
    client_terraform: Any, params: Dict[str, Any], module: Any, config_version_id: str
) -> str:
    """
    Polls the Terraform API for the status of a configuration version until it reaches 'uploaded'
    or the maximum number of retries is exhausted.

    Args:
        client_terraform (Any): Terraform API client instance.
        params (Dict[str, Any]): Dictionary containing polling parameters:
            - interval (int): Time in seconds to wait between retries.
            - retries (int): Maximum number of polling attempts.
        module (Any): Ansible module object for error reporting.
        config_version_id (str): ID of the configuration version to check.

    Returns:
        str: The status of the configuration version when it becomes 'uploaded'.

    Raises:
        module.fail_json: If the configuration version doesn't reach 'uploaded' in time
                          or if an error occurs during polling.
    """
    interval = params.get("interval")
    retries = params.get("tf_max_retries")
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
            workspace_id=dict(type="str", required=False),
            workspace=dict(type="str", required=False),
            organization=dict(type="str", required=False),
            state=dict(type="str", required=True),
            configuration_version_id=dict(type="str", required=False),
            auto_queue_runs=dict(type="bool", required=False, default=True),
            speculative=dict(type="bool", required=False, default=False),
            provisional=dict(type="bool", required=False, default=False),
            configuration_files_path=dict(aliases=["project_path"], type="str", required=False),
            interval=dict(type="int", required=False, default=1),
        ),
    )
    warnings = []
    result = {"changed": False, "warnings": warnings}
    params = module.params
    client_archivist = ArchivistClient()
    client_terraform = TerraformClient(**module.params)
    params["tf_max_retries"] = client_terraform.session_args.get("tf_max_retries")
    try:
        if params.get("workspace"):
            workspace_response = get_workspace(
                client_terraform, params["organization"], params["workspace"]
            )
            workspace_id = workspace_response.get("data")["data"]["id"]
            params["workspace_id"] = workspace_id
    except Exception as e:
        module.fail_json(msg=str(e))

    try:
        if params.get("state") == "present" and params.get("configuration_files_path"):
            try:
                if params.get("tf_max_retries") is None:
                    module.fail_json(msg="Retries has not been set")
                configuration_files_path = validate_and_prepare_tar(
                    params.get("configuration_files_path"), module
                )
                config_version_id, upload_url = create_configuration_version(
                    client_terraform, params, module
                )
                upload_response = upload_configuration_version(
                    client_archivist, params, module, upload_url, configuration_files_path
                )
                config_status = get_configuration_version(
                    client_terraform, params, module, config_version_id
                )

                result.update(
                    {
                        "changed": True,
                        "configuration_version_id": config_version_id,
                        "upload_response": upload_response,
                        "config_status": config_status,
                    }
                )
                module.exit_json(**result)

            except Exception as e:
                module.fail_json(msg=str(e))

        elif params.get("state") == "archive":
            try:
                config_version = archive_config(
                    client_terraform, params["configuration_version_id"]
                )

                result.update(
                    {
                        "changed": True,
                        "msg": "Configuration version archived successfully.",
                        "configuration_version_id": params["configuration_version_id"],
                        "full_response": config_version,
                    }
                )
                module.exit_json(**result)
            except Exception as e:
                module.fail_json(
                    msg=str(e),
                )
            module.exit_json(**result)
        elif params.get("state") == "absent":
            warning_msg = (
                "The value 'absent' for param 'state' is not yet supported as delete operation "
                "endpoint is exclusive to Terraform Enterprise, and not available in HCP Terraform."
            )
            module.fail_json(msg=warning_msg)

    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
