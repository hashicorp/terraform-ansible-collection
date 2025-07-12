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
  workspace:
    description: The workspace id for which the configuration version needs to be created.
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
    workspace: <your-workspace-id>
    state: present
    auto-queue-runs: false
- name: Create a configuration may only be used to create speculative runs
  hashicorp.terraform.terraform_configuration_version:
    workspace: <your-workspace-id>
    state: present
    speculative: true
- name: Create a configuration version that will not immediately become the workspace current configuration version
  hashicorp.terraform.terraform_configuration_version:
    workspace: <your-workspace-id>
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

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    TerraformClient,
    TerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.configuration import (
    create_config,
    archive_config,
)


def create_configuration_version(client_terraform, params, module):
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
        config_version = create_config(client_terraform, params["workspace"], payload)
        config_version_id = config_version.get("data").get("data", {}).get("id")
        upload_url = (
            config_version.get("data").get("data", {}).get("attributes", {}).get("upload-url")
        )
        return config_version_id, upload_url
    except Exception as e:
        module.fail_json(msg=str(e))


def main():
    module = TerraformModule(
        argument_spec=dict(
            workspace=dict(type="str", required=False),
            state=dict(type="str", required=True),
            configuration_version_id=dict(type="str", required=False),
            auto_queue_runs=dict(type="bool", required=False, default=True),
            speculative=dict(type="bool", required=False, default=False),
            provisional=dict(type="bool", required=False, default=False),
            archive=dict(type="bool", required=False, default=False),
        ),
    )
    warnings = []
    result = {"changed": False, "warnings": warnings}
    params = module.params
    client = TerraformClient(tf_hostname=params["tf_hostname"], tf_token=params["tf_token"])
    try:
        if params["state"] == "present":
            config_version_id, upload_url = create_configuration_version(client, params, module)
            result.update(
                {
                    "changed": True,
                    "msg": "Configuration version created successfully.",
                    "configuration_version_id": config_version_id,
                    "upload_url": upload_url,
                }
            )
            module.exit_json(**result)
        elif params["state"] == "archive":
            try:
                config_version = archive_config(client, params["configuration_version_id"])

                result.update(
                    {
                        "changed": True,
                        "msg": "Configuration version archived successfully.",
                        "configuration_version_id": params["configuration_version_id"],
                        "full_response": config_version,  # optional: remove if too verbose
                    }
                )
                module.exit_json(**result)
            except Exception as e:
                module.fail_json(
                    msg=str(e),
                )
            module.exit_json(**result)
        elif params["state"] == "absent":
            warning_msg = "The value false for param 'archive' is not yet supported as delete operation endpoint is exclusive to Terraform Enterprise, and not available in HCP Terraform."
            module.fail_json(msg=warning_msg)
    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
