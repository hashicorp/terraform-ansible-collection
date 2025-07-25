# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: configuration_version
version_added: 1.0.0
short_description: Manage configuration versions in Terraform Enterprise/Cloud.
author: "Kaushiki Singh (@kausingh)"
description:
  - Create/Archive/Upload configuration version in Terraform Enterprise/Cloud.
  - If a workspace and configuration_files_path is specified and the state is present, this module will create a configuration
    version in the workspace and upload the file to it.
  - If a configuration_version_id is specified and the state is archived, this module will discard the uploaded .tar.gz
    file associated with this configuration version. This can only archive the configuration versions that
    were created with the API or CLI, are in an uploaded state, have no runs in progress, and are not the
    current configuration version for any workspace.
extends_documentation_fragment: hashicorp.terraform.common
options:
  state:
    description:
      - The state the configuration version should be in.
      - Setting `state=present` creates a new configuration-version and upload to it.
      - Setting `state=archived` archives an existing configuration-version, if it exists. Requires the `configuration_version_id` field to be set.
    type: str
    choices: ["present", "absent", "archived"]
    default: present
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
    type: path
    aliases: [project_path]
  poll_interval:
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
    poll_interval: 3
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
    state: archived
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
      returned: when state is 'archived'
      description: The successfull completion of archive.
"""

import gzip
import os
import tarfile
import tempfile
import time

from pathlib import Path
from typing import TYPE_CHECKING

from ansible.module_utils._text import to_text


if TYPE_CHECKING:
    from typing import Any, Dict, Tuple

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    ArchivistClient,
    TerraformClient,
    TerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.configuration_version import (
    archive_config,
    create_config,
    get_config,
    upload_config,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace


def validate_and_prepare_tar(configuration_files_path: Path) -> str:
    """
    Validates and prepares the given path for upload.

    - If the path is a directory, it is archived into a temporary .tar.gz file.
    - If the path is a valid tar.gz archive, it's returned as-is after basic validation.
    - Other file types are rejected.

    Args:
        configuration_files_path (str): The file or directory path to validate and prepare.
        module (Any): Ansible module object used for error handling (fail_json).

    Raises:
        FileNotFoundError: If the given path does not exist.
        Exception: If an error occurs while archiving a directory, or if a `.tar.gz`
            file is malformed or unreadable as gzip.
        tarfile.TarError: If the given file is not a valid tar archive.
        ValueError: If the given path is neither a file nor a directory, or is not
            suitable for upload.
    """
    final_upload_path = None
    expanded_path = Path(configuration_files_path).resolve()

    if not expanded_path.exists():
        raise FileNotFoundError(f"The configuration_files_path '{expanded_path}' does not exist.")

    # create a tarfile from the project directory
    if expanded_path.is_dir():
        try:
            temp_fd, temp_tar_path = tempfile.mkstemp(suffix=".tar.gz")
            os.close(temp_fd)

            with tarfile.open(temp_tar_path, "w:gz") as tar:
                for item in os.listdir(expanded_path):
                    item_path = os.path.join(expanded_path, item)
                    tar.add(item_path, arcname=item)

            final_upload_path = temp_tar_path
        except Exception as e:
            raise Exception(f"Failed to create tar.gz from directory '{expanded_path}'") from e

    # validate if the provided file is a valid tarfile
    elif expanded_path.is_file():
        try:
            if tarfile.is_tarfile(expanded_path):
                try:
                    with gzip.open(expanded_path, "rb") as f:
                        f.read(1)
                    final_upload_path = to_text(expanded_path)
                except gzip.BadGzipFile as e:
                    raise Exception(f"The path {expanded_path} is a bad gzip file: {e}")
        except Exception as e:
            raise tarfile.TarError(f"The path '{expanded_path}' is not a valid tarfile: {e}")
    else:
        raise ValueError(f"The path '{expanded_path}' is not a file or recognized archive format.")

    return final_upload_path


def create_configuration_version(client_terraform: Any, params: Dict[str, Any]) -> Tuple[str, str]:
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

    Returns:
        Tuple[str, str]: A tuple containing the configuration version ID and the upload URL.
    """
    workspace_id = params["workspace_id"]
    attributes = {
        "auto-queue-runs": params["auto_queue_runs"],
        "speculative": params["speculative"],
        "provisional": params["provisional"],
    }

    # create a new configuration version
    config_version = create_config(client_terraform, workspace_id, attributes)

    # the newly created configuration version will always have an ID
    config_version_id = config_version.get("data", {}).get("id")

    # the newly created configuration version will always have an upload-url
    upload_url = config_version.get("data", {}).get("attributes", {}).get("upload-url")

    return config_version_id, upload_url


def upload_configuration_version(
    client_archivist: Any,
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
    """
    response = upload_config(
        client_archivist,
        upload_url=upload_url,
        configuration_files_path=configuration_files_path,
    )
    return response["status"]


def get_configuration_version(client_terraform: Any, params: Dict[str, Any], config_version_id: str) -> str:
    """
    Polls the Terraform API for the status of a configuration version until it reaches 'uploaded'
    or the maximum number of retries is exhausted.

    Args:
        client_terraform (Any): Terraform API client instance.
        params (Dict[str, Any]): Dictionary containing polling parameters:
            - poll_interval (int): Time in seconds to wait between retries.
            - retries (int): Maximum number of polling attempts.
        module (Any): Ansible module object for error reporting.
        config_version_id (str): ID of the configuration version to check.

    Returns:
        str: The status of the configuration version when it becomes 'uploaded'.

    Raises:
        module.fail_json: If the configuration version doesn't reach 'uploaded' in time
                          or if an error occurs during polling.
    """
    poll_interval = params.get("poll_interval")
    retries = params.get("tf_max_retries")

    for iteration in range(max(1, retries)):
        config_response = get_config(client_terraform, config_version_id=config_version_id)
        status = config_response.get("data")["attributes"]["status"]

        if status == "uploaded":
            break

        time.sleep(poll_interval)

    return config_response


def state_present(client_terraform: Any, client_archivist: Any, params: Dict[str, Any]):
    """
    Ensures the Terraform configuration state is present and correctly uploaded.

    This function performs the following operations:
    1. Validates and prepares the configuration files as a tar archive.
    3. Creates a new Terraform configuration version.
    4. Uploads the configuration files to the generated upload URL.
    5. Retrieves the status of the uploaded configuration version.
    6. Updates the result dictionary and exits successfully.

    If any step fails, the function will call `module.fail_json()` with the error message.

    Args:
        client_terraform (Any): Client object used to interact with Terraform.
        client_archivist (Any): Client object used for uploading files to the archive service.
        params (Dict[str, Any]): Dictionary of parameters including configuration paths and options.

    Returns:
        dict: A result dictionary with the final status of the created configuration version.
    """
    action_result = {}

    # get the updated/validated configuration_files_path
    configuration_files_path = validate_and_prepare_tar(params.get("configuration_files_path"))

    # create a new configuration version and store the id and upload_url
    config_version_id, upload_url = create_configuration_version(client_terraform, params)

    # start configuration tarfile upload, if upload failed, this will raise an Exception
    upload_configuration_version(client_archivist, upload_url, configuration_files_path)

    final_config_status = get_configuration_version(client_terraform, params, config_version_id)

    status = final_config_status.get("data")["attributes"]["status"]

    if status == "uploaded":
        action_result.update(
            {
                "changed": True,
                **final_config_status["data"],
            },
        )
    else:
        action_result.update(
            {
                "failed": True,
                "msg": f"Configuration version {config_version_id} was created but could not transition to uploaded state.",
                **final_config_status["data"],
            },
        )
    return action_result


def state_archived(client_terraform: Any, configuration_version_id: str):
    """
    Archives a specified Terraform configuration version if it is not already archived.

    This function performs the following operations:
    1. Checks if the configuration version exists.
    2. If already archived, exits without making changes.
    3. Otherwise, archives the configuration version.
    4. Updates the result dictionary and exits.

    If any step fails, appropriate messages are returned.

    Args:
        client_terraform (Any): Client object used to interact with Terraform.
        configuration_version_id (str, Any): The configuration_version_id to archive.
    """
    archiving_result = {}

    config_response = get_config(client_terraform, config_version_id=configuration_version_id)
    if not config_response:
        archiving_result.update(
            {
                "changed": False,
                "msg": f"Configuration version '{configuration_version_id}' was not found.",
            },
        )
    else:
        current_status = config_response["data"]["attributes"]["status"]
        if current_status == "archived":
            archiving_result.update(
                {
                    "changed": False,
                    "msg": f"Configuration version '{configuration_version_id}' is already archived.",
                },
            )
        else:
            # configuration version is exists, but is not archived, attempt archiving
            archive_config(client_terraform, configuration_version_id)
            archiving_result.update(
                {
                    "changed": True,
                    "msg": f"Configuration version {configuration_version_id} archived successfully.",
                },
            )
    return archiving_result


def main():
    module = TerraformModule(
        argument_spec=dict(
            workspace_id=dict(type="str"),
            workspace=dict(type="str"),
            organization=dict(type="str"),
            state=dict(type="str", default="present", choices=["present", "absent", "archived"]),
            configuration_version_id=dict(type="str"),
            auto_queue_runs=dict(type="bool", default=True),
            speculative=dict(type="bool", default=False),
            provisional=dict(type="bool", default=False),
            configuration_files_path=dict(aliases=["project_path"], type="path"),
            poll_interval=dict(type="int", default=1),
        ),
        required_together=[["workspace", "organization"]],
        required_if=[
            ("state", "archived", ["configuration_version_id"]),
            ("state", "present", ("workspace_id", "workspace", "configuration_files_path"), True),
        ],
        mutually_exclusive=[
            ("workspace", "workspace_id"),
        ],
    )
    warnings = []
    result = {"changed": False, "warnings": warnings}
    action_result = {}
    params = module.params

    if params["tf_max_retries"] < 3:
        warnings.append(
            f"The value for tf_max_retries is set to {params['tf_max_retries']}, this maybe too low for the configuration_version module.",
        )

    try:
        client_archivist = ArchivistClient()
        client_terraform = TerraformClient(**module.params)

        if params["state"] == "present":
            # either workspace_id or workspace MUST be provided when state is present
            # when a workspace is provided, organization must be given
            # we use both these to get the workspace_id which is required when creating configuration-versions
            if not params["workspace_id"]:
                # get the workspace_id from the provided workspace name
                workspace_response = get_workspace(client_terraform, params["organization"], params["workspace"])
                if not workspace_response:
                    raise Exception(f"The workspace {params['workspace']} in {params['organization']} organization was not found.")
                # retrieve the workspace ID
                workspace_id = workspace_response.get("data")["id"]
                # update module params to have a workspace ID
                params["workspace_id"] = workspace_id

            action_result = state_present(client_terraform, client_archivist, params)

        elif params["state"] == "archived":
            # when state is archived, configuration_version_id will always be available
            action_result = state_archived(client_terraform, params["configuration_version_id"])

        result.update(action_result)
        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
