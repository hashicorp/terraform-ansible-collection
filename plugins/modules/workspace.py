# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: workspace
version_added: 1.0.0
short_description: Manage workspaces in Terraform Enterprise/Cloud.
author: "Kaushiki Singh (@kausingh)"
description:
  - Create, Update, Lock, Unlock or Delete workspaces in Terraform Enterprise/Cloud.
  - If I(workspace) and I(organization) is specified for a non-existent workspace and the I(state) is C(present),
    this module will create a new workspace.
  - If either I(workspace) (and I(organization)) or I(workspace_id) is specified for an existing workspace and the I(state) is C(present),
    this module will update the existing workspace.
  - If a I(workspace_id) is specified, the I(state) is C(absent) and the I(force) is set C(true),
    this module will force delete the workspace, if it exists, without checking whether it is managing resources.
  - If a I(workspace_id) is specified, the I(state) is C(absent), this module will safe delete the
    workspace, if it exists. This would only delete the workspace if it is not managing any resources.
  - If a I(workspace_id) is specified, the I(state) is C(locked) and I(lock_reason) is set, this module will lock the workspace, if it exists.
  - If a I(workspace_id) is specified, the I(state) is C(unlocked) and I(force) is set C(true), this module will unlock the workspace,
    if it exists.
  - If a I(workspace_id) is specified, the I(state) is C(unlock) and I(force) is set C(true), this module will force unlock the workspace,
    if it exists.
extends_documentation_fragment: hashicorp.terraform.common
options:
  state:
    description:
      - The state the workspace should be in.
      - Setting `state=present` create a workspace if it does not exist, and updates the workspace, if it exists.
      - Setting `state=absent` deletes an existing workspace, if it exists.
      - Setting `state=locked` locks an existing workspace, if it exists.
      - Setting `state=unlocked` unlocks an existing workspace, if it exists.
    type: str
    choices: ["present", "absent", "locked", "unlocked"]
    default: present
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
  new_workspace_name:
    description:
      - This is the new name of the workspace.
      - It is tied to updating workspaces only and applicable to existing workspaces.
    type: str
  workspace_id:
    description:
      - ID of the workspace.
      - Either I(workspace) (and I(organization)) or I(workspace_id) must be specified when updating a `workspace`.
    type: str
  project_id:
    description:
      - ID of the project that the workspace will belong to.
      - If no I(project_id) is provided, the workspace is created in the organization's default project.
    type: str
  allow_destroy_plan:
    description:
      - When true, allows destroy plans to be queued on the workspace.
    type: bool
    default: true
  assessments_enabled:
    description:
      - When true, HCP Terraform performs health assessments for the workspace.
    type: bool
    default: false
  auto_apply:
    description:
      - When true, allows changes to automatically apply when a Terraform plan is successful.
    type: bool
    default: false
  auto_apply_run_trigger:
    description:
      - When true, allows changes to automatically apply when a Terraform plan is successful in runs initiated by run triggers.
    type: bool
    default: false
  auto_destroy_at:
    description:
      - The timestamp when the next scheduled destroy run will occur.
      - The recommended timestamp format is the ISO format for UTC time [YYYY-MM-DDTHH:mm:ssZ].
    type: str
  auto_destroy_activity_duration:
    description:
      - The value and units to automatically schedule destroy runs based on workspace activity.
      - The I(auto_destroy_activity_duration) takes precedence over I(auto_destroy_at), if both are set.
      - The valid values are greater than 0 and four digits or less.
      - The valid units are d and h.
    type: str
  source_name:
    description:
      - A friendly name for the application or client creating this workspace.
    type: str
  source_url:
    description:
      - A URL for the application or client creating this workspace.
    type: str
  description:
    description:
      - A description for the workspace.
    type: str
  terraform_version:
    description:
      - This specifies the version of Terraform to use for this workspace.
      - If a constraint is specified, the workspace always uses the newest release that meets that constraint.
      - If omitted when creating a new I(workspace), this defaults to the latest released version.
    type: str
  execution_mode:
    description:
      - This specifies the execution mode for the workspace.
      - This inherits the default project mode by default.
      - The I(agent_pool_id) must be provided when the I(execution_mode) is `agent`
    choices: ["remote", "local", "agent"]
    type: str
  agent_pool_id:
    description:
      - The ID of the agent pool belonging to the workspace's organization.
      - This value must not be specified if I(execution_mode) is set to `remote` or `local`.
    type: str
  tag_bindings:
    description:
      - The tags to attach to the workspace.
    type: dict
  setting_overwrites:
    description:
      - This paramter helps in overwriting default inherited values.
    type: dict
    suboptions:
      execution_mode:
        description:
          - Defines if the project I(execution_mode) is inherited.
        type: bool
        default: false
      agent_pool:
        description:
          - Defines if the project I(agent_pool) is inherited.
        type: bool
        default: false
  lock_reason:
    description:
      - The reason for locking the workspace.
      - This is only applicable with I(state) is C(locked).
    type: str
  force:
    description:
      - Determines if the specified operation should be forced.
      - This parameter is applicable only with states C(unlocked) and C(absent).
      - When set to C(True) with state C(absent), the module will attempt a force delete operation.
      - When set to C(True) with state C(unlocked), the module will attempt a force unlock.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Create a new workspace
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    description: This is a dev workspace.
    project_id: <your-project-id>
    tag_bindings:
      env: dev
      owner: abc
    execution_mode: remote
    source_name: xyz
    auto_apply: true
    state: present

- name: Create a new workspace
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    execution_mode: agent
    agent_pool_id: <your-agent-pool-id>
    setting_overwrites:
      execution_mode: true
      agent_pool: true
    auto_destroy_activity_duration: 14d
    auto_destroy_at: "2025-08-10T15:00:00Z"
    state: present

- name: Update an existing workspace
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    new_workspace_name: <new-name-for-the-workspace>
    description: This is an updated dev workspace.
    project_id: <your-new-project-id>
    tag_bindings:
      env: uat
      owner: abc
    execution_mode: remote
    source_name: xyz
    auto_apply: true
    assessments_enabled: true
    state: present

- name: Safe delete a workspace
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    state: absent

- name: Force delete a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    force: true
    state: absent

- name: Lock a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    lock_reason: "your specific reason"
    state: locked

- name: Unlock a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    state: unlocked

- name: Force unlock a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    force: true
    state: unlocked
"""

RETURN = r"""
outputs:
  type: dict
  description: A dictionary of the workspace details.
  returned: on success
  contains:
    attributes:
        type: dict
        returned: when state is 'present'
        description: The attributes of the workspace created/updated.
    workspace_id:
      type: str
      returned: always
      description: ID of the workspace created/updated/deleted.
    msg:
      type: str
      returned: when state is 'absent'/'locked'/'unlocked'.
      description: The status of the operation.
"""


from typing import TYPE_CHECKING
from datetime import datetime

from ansible.module_utils._text import to_text


if TYPE_CHECKING:
    from typing import Any, Dict

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import (
    create_workspace,
    force_delete_workspace,
    safe_delete_workspace,
    update_workspace,
    force_unlock_workspace,
    unlock_workspace,
    lock_workspace,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace, get_workspace_by_id
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.workspace import WorkspaceRequest


def workspace_create(client_terraform: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a new Terraform workspace using the provided client and parameters.

    This function filters out irrelevant parameters, formats the workspace data,
    and sends a request to create the workspace under the specified organization.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary of parameters including workspace details.

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): Always True, indicating that a workspace was created.
            - "msg" (str): Success message.
            - Additional data returned from the workspace creation API.

    Raises:
        Any exceptions raised by the underlying Terraform client or request methods
        will propagate up to the caller.
    """

    action_result = {}
    ignore_list = ["tf_hostname", "tf_token", "tf_timeout", "tf_max_retries", "tf_validate_certs", "check_mode", "state"]
    workspace_params = params.copy()
    for value in ignore_list:
        workspace_params.pop(value, None)
    workspace_params["name"] = workspace_params.pop("workspace")
    organization = workspace_params.pop("organization")
    project_id = workspace_params.pop("project_id", None)
    tag_bindings = workspace_params.pop("tag_bindings", None)
    workspace_request = WorkspaceRequest.create(project_id=project_id, tag_bindings=tag_bindings, **workspace_params)
    workspace_payload = workspace_request.model_dump(by_alias=True, exclude_unset=False, exclude_none=True)
    response = create_workspace(client_terraform, organization, workspace_payload)
    action_result.update(
        {"changed": True, "msg": "The workspace is created successfully", **response["data"]},
    )
    return action_result


def workspace_update(client_terraform: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates an existing Terraform workspace using the provided client and parameters.

    This function filters out irrelevant parameters, prepares the updated workspace data,
    and sends a request to update the workspace with the specified ID.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary of parameters including updated workspace details.

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): Always True, indicating that the workspace was updated.
            - "msg" (str): Success message.
            - Additional data returned from the workspace update API.

    Raises:
        Any exceptions raised by the underlying Terraform client or request methods
        will propagate up to the caller.
    """
    action_result = {}
    ignore_list = ["tf_hostname", "tf_token", "tf_timeout", "tf_max_retries", "tf_validate_certs", "check_mode", "state"]
    workspace_params = params.copy()
    for value in ignore_list:
        workspace_params.pop(value, None)
    if workspace_params["new_workspace_name"]:
        workspace_params["name"] = workspace_params.pop("new_workspace_name")
    else:
        workspace_params["name"] = workspace_params.pop("workspace")
    workspace_id = workspace_params.pop("workspace_id")
    try:
        workspace_exists(client_terraform, workspace_id)
    except ValueError as e:
        raise ValueError(f"Cannot update workspace. Reason: {e}")
    project_id = workspace_params.pop("project_id", None)
    tag_bindings = workspace_params.pop("tag_bindings", None)
    workspace_request = WorkspaceRequest.create(project_id=project_id, tag_bindings=tag_bindings, **workspace_params)
    workspace_payload = workspace_request.model_dump(by_alias=True, exclude_unset=False, exclude_none=True)
    response = update_workspace(client_terraform, workspace_id, workspace_payload)
    action_result.update(
        {"changed": True, "msg": "The workspace is updated successfully", **response["data"]},
    )
    return action_result


def get_workspace_id(client_terraform: Any, params: Dict[str, Any]) -> str:
    """
    Retrieves the ID of a Terraform workspace based on its name and organization.

    This function queries the Terraform API to fetch workspace details and returns
    the corresponding workspace ID. If the workspace is not found, it raises a ValueError.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary containing:
            - "organization" (str): The name of the organization that owns the workspace.
            - "workspace" (str): The name of the workspace to retrieve.

    Returns:
        str: The ID of the workspace.

    Raises:
        ValueError: If the specified workspace does not exist in the given organization.
    """
    # get the workspace_id from the provided workspace name
    workspace_response = get_workspace(client_terraform, params["organization"], params["workspace"])
    if not workspace_response:
        raise ValueError(f"The workspace {params['workspace']} in {params['organization']} organization was not found.")
    # retrieve the workspace ID
    workspace_id = workspace_response.get("data")["id"]
    # update module params to have a workspace ID
    return workspace_id


def workspace_exists(client_terraform: Any, workspace_id: str) -> None:
    """
    Validates that a Terraform workspace exists by its ID.

    This function checks whether a workspace with the specified ID exists
    by attempting to retrieve it from the Terraform API. If the workspace
    does not exist, it raises a ValueError. Otherwise, it completes silently.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        workspace_id (str): The unique ID of the Terraform workspace to validate.

    Raises:
        ValueError: If the specified workspace does not exist or cannot be retrieved.
    """

    # get the workspace from workspace_id
    workspace_response = get_workspace_by_id(client_terraform, workspace_id)
    if not workspace_response:
        raise ValueError(f"The workspace {workspace_id} was not found.")


def workspace_delete(client_terraform: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deletes a Terraform workspace using either a safe or force delete method.

    If a workspace ID is not provided in the parameters, the function attempts to retrieve it
    using the organization and workspace name. Based on the `force_delete` flag, it will perform
    either a forceful or safe deletion.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary of module parameters

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): True if the workspace was deleted.
            - "msg" (str): A message describing the result of the deletion.

    Raises:
        ValueError: If the workspace cannot be found when attempting to resolve the ID.
        Any exceptions from the delete functions will propagate up to the caller.
    """
    action_result = {
        "changed": False,
    }
    if not params["workspace_id"]:
        workspace_id = get_workspace_id(client_terraform, params)
        params["workspace_id"] = workspace_id
    try:
        workspace_exists(client_terraform, params["workspace_id"])
    except ValueError as e:
        raise ValueError(f"The workspace could not be deleted. Reason: {e}")
    if params["force_delete"]:
        force_delete_workspace(client_terraform, params["workspace_id"])
        msg = f"Configuration version {params['workspace_id']} force deleted successfully."
        action_result["changed"] = True
    else:
        safe_delete_workspace(client_terraform, params["workspace_id"])
        msg = f"Configuration version {params['workspace_id']} safe deleted successfully."
        action_result["changed"] = True
    action_result["msg"] = msg
    return action_result


def workspace_unlock(client_terraform: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unlocks a Terraform workspace, either forcefully or gracefully depending on the provided parameters.

    If the workspace ID is not provided, it attempts to retrieve it using the organization and workspace name.
    Unlocking is then performed based on the value of the `force` flag.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary of module parameters.

    Returns:
        Dict[str, Any]: A dictionary with the result of the unlock operation, including:
            - "changed" (bool): Always True, indicating the workspace was unlocked.
            - "msg" (str): A success message.
            - Additional data returned from the unlock operation.

    Raises:
        ValueError: If the workspace ID could not be resolved.
        Any exceptions raised by the underlying unlock functions will propagate up to the caller.
    """
    action_result = {}
    if not params["workspace_id"]:
        workspace_id = get_workspace_id(client_terraform, params)
        params["workspace_id"] = workspace_id
    try:
        workspace_exists(client_terraform, params["workspace_id"])
    except ValueError as e:
        raise ValueError(f"The workspace could not be unlocked. Reason: {e}")
    if params["force"]:
        response = force_unlock_workspace(client_terraform, params["workspace_id"])
    elif not params["force"]:
        response = unlock_workspace(client_terraform, params["workspace_id"])
    action_result.update(
        {"changed": True, "msg": f"Workspace {params['workspace_id']} unlocked successfully.", **response["data"]},
    )
    return action_result


def workspace_lock(client_terraform: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Locks a Terraform workspace.

    If the workspace ID is not provided, the function retrieves it using the organization
    and workspace name. It then locks the workspace with the given reason.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary of module parameters.

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): True if the workspace was successfully locked.
            - "msg" (str): A message indicating success.
            - Additional data returned from the lock operation.

    Raises:
        ValueError: If the workspace cannot be found or resolved.
        Any exceptions from the lock operation will propagate to the caller.
    """
    action_result = {
        "changed": False,
    }
    if not params["workspace_id"]:
        workspace_id = get_workspace_id(client_terraform, params)
        params["workspace_id"] = workspace_id
    try:
        workspace_exists(client_terraform, params["workspace_id"])
    except ValueError as e:
        raise ValueError(f"The workspace could not be locked. Reason: {e}")
    response = lock_workspace(client_terraform, params["workspace_id"], params["lock_reason"])
    action_result.update(
        {"changed": True, "msg": "The workspace is locked successfully", **response["data"]},
    )
    return action_result


def main():
    module = AnsibleTerraformModule(
        argument_spec=dict(
            workspace_id=dict(type="str"),
            workspace=dict(type="str"),
            organization=dict(type="str"),
            state=dict(type="str", default="present", choices=["present", "absent", "unlocked", "locked"]),
            new_workspace_name=dict(type="str"),
            project_id=dict(type="str"),
            allow_destroy_plan=dict(type="bool", default=True),
            assessments_enabled=dict(type="bool", default=False),
            auto_apply=dict(type="bool", default=False),
            auto_apply_run_trigger=dict(type="bool", default=False),
            auto_destroy_at=dict(type="str"),
            auto_destroy_activity_duration=dict(type="str"),
            source_name=dict(type="str"),
            soruce_url=dict(type="str"),
            description=dict(type="str"),
            terraform_version=dict(type="str"),
            execution_mode=dict(type="str"),
            agent_pool_id=dict(type="str"),
            tag_bindings=dict(type="dict"),
            setting_overwrites=dict(type="dict"),
            force=dict(type="bool", default=False),
            lock_reason=dict(type="str", default=""),
        ),
        supports_check_mode=True,
        required_together=[["workspace", "organization"]],
        required_if=[
            ("state", "absent", ("workspace_id", "workspace"), True),
            ("state", "present", ("workspace_id", "workspace"), True),
        ],
        mutually_exclusive=[
            ("workspace", "workspace_id"),
        ],
    )
    warnings = []
    result = {"changed": False, "warnings": warnings}
    action_result = {}
    params = module.params
    params["check_mode"] = module.check_mode

    try:
        client_terraform = TerraformClient(**module.params)

        if params["state"] == "present":
            # either workspace_id or workspace MUST be provided when state is present
            # when a workspace is provided, organization must be given
            # we use both these to get the workspace_id which is required when creating configuration-versions
            if params["auto_destroy_at"]:
                datetime.strptime(params["auto_destroy_at"], "%Y-%m-%dT%H:%M:%SZ")
            if not params["workspace_id"]:
                # get the workspace_id from the provided workspace name
                workspace_response = get_workspace(client_terraform, params["organization"], params["workspace"])
                if not workspace_response:
                    if params["new_workspace_name"]:
                        raise ValueError(
                            f"The workspace {params['workspace']} in {params['organization']} organization was not found so workspace name cannot be updated"
                        )
                    action_result = workspace_create(client_terraform, params)
                else:
                    # retrieve the workspace ID
                    workspace_id = workspace_response.get("data")["id"]
                    # update module params to have a workspace ID
                    params["workspace_id"] = workspace_id
                    action_result = workspace_update(client_terraform, params)
            else:
                action_result = workspace_update(client_terraform, params)

        elif params["state"] == "absent":
            action_result = workspace_delete(client_terraform, params)

        elif params["state"] == "locked":
            action_result = workspace_lock(client_terraform, params)

        elif params["state"] == "unlocked":
            action_result = workspace_unlock(client_terraform, params)

        result.update(action_result)
        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
