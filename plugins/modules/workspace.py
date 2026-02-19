# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: workspace
version_added: 1.1.0
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
  - If a I(workspace_id) is specified, the I(state) is C(unlocked), this module will unlock the workspace,
    if it exists.
  - If a I(workspace_id) is specified, the I(state) is C(unlocked) and I(force) is set C(true), this module will force unlock the workspace,
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
  assessments_enabled:
    description:
      - When true, HCP Terraform performs health assessments for the workspace.
      - Setting this attribute to true holds relevance in HCP Terraform Plus and Premium editions only.
    type: bool
  auto_apply:
    description:
      - When true, allows changes to automatically apply when a Terraform plan is successful.
    type: bool
  auto_apply_run_trigger:
    description:
      - When true, allows changes to automatically apply when a Terraform plan is successful in runs initiated by run triggers.
    type: bool
  auto_destroy_at:
    description:
      - The timestamp when the next scheduled destroy run will occur.
      - The recommended timestamp format is UTC ISO 8601 [YYYY-MM-DDTHH:mm:ssZ].
      - Setting this attribute value holds relevance in HCP Terraform Plus and Premium editions only.
    type: str
  auto_destroy_activity_duration:
    description:
      - The value and units to automatically schedule destroy runs based on workspace activity.
      - The I(auto_destroy_activity_duration) takes precedence over I(auto_destroy_at), if both are set.
      - The valid values are greater than 0 and four digits or less.
      - The valid units are d and h.
      - Setting this attribute value holds relevance in HCP Terraform Plus and Premium editions only.
    type: str
  source_name:
    description:
      - A friendly name for the application or client creating this workspace.
      - This parameter is applicable only for creating new workspaces.
    type: str
  source_url:
    description:
      - A URL for the application or client creating this workspace.
      - This parameter is applicable only for creating new workspaces.
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
      - When the I(execution_mode) inherited from the project default mode needs to be overridden,
        then I(setting_overwrites) parameter must be provided with this.
    choices: ["remote", "local", "agent"]
    type: str
  agent_pool_id:
    description:
      - The ID of the agent pool belonging to the workspace's organization.
      - This value must not be specified if I(execution_mode) is set to `remote` or `local`.
    type: str
  tag_bindings:
    description:
      - The tags to be bound to the workspace in key and value format.
    type: dict
  setting_overwrites:
    description:
      - This parameter helps in overwriting default inherited values.
      - When the inherited I(execution-mode) needs to be overridden, this parameter needs to be specified.
    type: dict
    suboptions:
      execution_mode:
        description:
          - Defines if the project I(execution_mode) is inherited.
        type: bool
      agent_pool:
        description:
          - Defines if the project I(agent_pool) is inherited.
        type: bool
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
"""

EXAMPLES = r"""
- name: Create a new workspace with minimal data
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    state: present

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
    auto_destroy_activity_duration: 14d
    auto_destroy_at: "2025-08-10T15:00:00Z"
    state: present

- name: Update an existing workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    description: This is an updated dev workspace.
    project_id: <your-new-project-id>
    tag_bindings:
      env: uat
      owner: abc
    execution_mode: remote
    auto_apply: true
    assessments_enabled: true
    state: present

- name: Update workspace execution mode to 'agent' by overwriting inherited execution mode from project
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    execution_mode: agent
    agent_pool_id: <your-agent-pool-id>
    setting_overwrites:
      execution_mode: true
      agent_pool: true
    state: present

- name: Safe delete a workspace
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    state: absent

# Task output:
# ------------
# "result_delete": {
#         "changed": true,
#         "failed": false,
#         "msg": "The workspace ws-id was safe-deleted successfully."
#     }

- name: Force delete a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    force: true
    state: absent

# Task output:
# ------------
# "result_delete": {
#         "changed": true,
#         "failed": false,
#         "msg": "The workspace ws-id was force-deleted successfully."
#     }

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
id:
  description: The unique identifier of the workspace.
  returned: when state is 'present' or 'locked' or 'unlocked'
  type: str
  sample: "ws-ybMGvqhs6MWLa5S2"
type:
    description: The resource type, always 'workspaces'.
    returned: when state is 'present' or 'locked' or 'unlocked'
    type: str
    sample: "workspaces"
attributes:
  type: dict
  returned: when state is 'present' or 'locked' or 'unlocked'
  description: The attributes of the workspace created/updated/locked/unlocked.
relationships:
  description: Related resources linked to the run.
  returned: when state is 'present' or 'locked' or 'unlocked'
  type: dict
links:
  description: API links for the run.
  returned: when state is 'present' or 'locked' or 'unlocked'
  type: dict
msg:
  type: str
  returned: when state is 'absent'.
  description: The status of the operation.
"""

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import (
    dict_diff,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import (
    WorkspaceAdapter,
)


IGNORE_LIST = [
    "tfe_token",
    "tfe_address",
    "check_mode",
    "state",
]


def normalize_workspace_attributes(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize module parameters to workspace attributes format.

    Args:
        params: Module parameters

    Returns:
        Normalized attributes dictionary
    """
    normalized = {}

    # Map module parameters to API attributes
    field_mapping = [
        "name",
        "description",
        "allow_destroy_plan",
        "assessments_enabled",
        "auto_apply",
        "auto_apply_run_trigger",
        "auto_destroy_at",
        "auto_destroy_activity_duration",
        "terraform_version",
        "execution_mode",
        "agent_pool_id",
        "setting_overwrites",
        "project_id",
        "tag_bindings",
        "source_name",
        "source_url",
    ]

    for param_key in field_mapping:
        # Check if key exists and value is not None (allows False, 0, empty strings, etc.)
        if param_key in params and params[param_key] is not None:
            normalized[param_key] = params[param_key]

    return normalized


def extract_comparable_attributes(workspace_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract comparable attributes from workspace SDK response.

    Args:
        workspace_data: Workspace data from SDK adapter (flat format with underscored keys)

    Returns:
        Dictionary of comparable attributes with normalized values
    """
    comparable = {
        "name": workspace_data.get("name"),
        "description": workspace_data.get("description"),
        "allow_destroy_plan": workspace_data.get("allow_destroy_plan"),
        "assessments_enabled": workspace_data.get("assessments_enabled"),
        "auto_apply": workspace_data.get("auto_apply"),
        "auto_apply_run_trigger": workspace_data.get("auto_apply_run_trigger"),
        "auto_destroy_at": workspace_data.get("auto_destroy_at"),
        "auto_destroy_activity_duration": workspace_data.get("auto_destroy_activity_duration"),
        "terraform_version": workspace_data.get("terraform_version"),
        "execution_mode": workspace_data.get("execution_mode"),
        "setting_overwrites": workspace_data.get("setting_overwrites", {}),
        "agent_pool_id": workspace_data.get("agent_pool_id"),
        "project_id": workspace_data.get("project_id"),
    }

    # Normalize auto_destroy_at timestamp for consistent comparison
    auto_destroy_at = comparable.get("auto_destroy_at")
    if auto_destroy_at:
        try:
            # Parse and reformat to remove milliseconds for comparison
            dt = datetime.strptime(auto_destroy_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            comparable["auto_destroy_at"] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            # If parsing fails, keep original value
            pass

    # Remove None values
    return {k: v for k, v in comparable.items() if v is not None}


def state_create(adapter: WorkspaceAdapter, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Creates a new Terraform workspace using the provided client and parameters.

    This function filters out irrelevant parameters, formats the workspace data,
    and sends a request to create the workspace under the specified organization.

    Args:
        adapter: WorkspaceAdapter instance to communicate with the API using pytfe
        params (Dict[str, Any]): A dictionary of parameters including workspace details.
        check_mode (bool): A check mode parameter.

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): Always True, indicating that a workspace was created.
            - "msg" (str): Success message.
            - Additional data returned from the workspace creation API.
    """
    action_result = {}
    ignore_list = ["force"]
    ignore_list.extend(IGNORE_LIST)
    workspace_params = params.copy()
    # pop unwanted values
    for value in ignore_list:
        workspace_params.pop(value, None)
    # store required values for the api endpoint and relationships
    workspace_params["name"] = workspace_params.pop("workspace")
    organization = workspace_params.pop("organization")

    # Extract attributes
    attributes = normalize_workspace_attributes(workspace_params)

    if not check_mode:
        workspace = adapter.create_workspace(organization=organization, **attributes)
        action_result.update({"changed": True, "msg": f"Workspace '{params['workspace']}' created successfully.", **workspace.get("data", workspace)})
    else:
        action_result.update(
            {
                "changed": True,
                "msg": f"The workspace {params['workspace']} would be created with the given options. Skipped creation due to check mode.",
                **attributes,
            },
        )
    return action_result


def state_update(adapter: WorkspaceAdapter, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Updates an existing Terraform workspace using the provided client and parameters.

    This function filters out irrelevant parameters, prepares the updated workspace data,
    and sends a request to update the workspace with the specified ID.

    Args:
        adapter: WorkspaceAdapter instance
        params (Dict[str, Any]): A dictionary of parameters including updated workspace details.

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): True if workspace was updated, False if no changes needed.
            - "msg" (str): Status message.
            - Additional data returned from the workspace update API.
    """

    action_result = {}
    # pop unwanted values and also remove source_name and source_url if present as they are not applicable for update operations
    ignore_list = [
        "lock_reason",
        "force",
        "organization",
        "source_name",
        "source_url",
    ]
    ignore_list.extend(IGNORE_LIST)
    workspace_params = params.copy()
    for value in ignore_list:
        workspace_params.pop(value, None)
    workspace_id = workspace_params.pop("workspace_id")
    workspace_response = adapter.get_workspace_by_id(workspace_id)
    if not workspace_response:
        raise ValueError(f"The workspace {workspace_id} was not found.")

    workspace_name = workspace_params.pop("workspace", None)
    if workspace_name:
        workspace_params["name"] = workspace_name
    else:
        workspace_params["name"] = workspace_response.get("name")

    # the keys and their corresponding values the workspace already has
    have = extract_comparable_attributes(workspace_response.get("data", workspace_response))
    # the keys input by the user
    want = normalize_workspace_attributes(workspace_params)
    want = {k: v for k, v in want.items() if v is not None}
    # removing excessive keys from have to match it to want
    have = {k: v for k, v in have.items() if k in want}
    # comparing the two dictionaries
    updates_response = dict_diff(have, want)

    if not updates_response:
        action_result.update(
            {
                "changed": False,
            },
        )
        return action_result

    # Coupled fields that must be sent together to avoid mismatches
    preserve_keys = {"name", "setting_overwrites", "execution_mode", "agent_pool_id"}

    # Remove keys from workspace_params that are not in updates (unless they're preserve_keys)
    for key in list(workspace_params.keys()):
        if key not in updates_response and key not in preserve_keys:
            workspace_params.pop(key)

    if not check_mode:
        updated_workspace = adapter.update_workspace(workspace_id, **workspace_params)
        action_result.update(
            {"changed": True, **updated_workspace.get("data", updated_workspace)},
        )
    else:
        action_result.update(
            {
                "changed": True,
                "msg": f"The workspace {params['workspace_id']} would be updated with the given options. Skipped update due to check mode.",
                **workspace_params,
            },
        )
    return action_result


def state_absent(adapter: WorkspaceAdapter, params: Dict[str, Any], workspace_response: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Deletes a Terraform workspace using either a safe or force delete method.

    If a workspace ID is not provided in the parameters, the function attempts to retrieve it
    using the organization and workspace name. Based on the `force_delete` flag, it will perform
    either a forceful or safe deletion.

    Args:
        adapter: WorkspaceAdapter instance
        params (Dict[str, Any]): A dictionary of module parameters.
        workspace_response (Dict[str, Any]): A dictionary of workspace response parameters.
        check_mode (bool): A check mode parameter.

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): True if the workspace was deleted.
            - "msg" (str): A message describing the result of the deletion.
    """
    action_result = {
        "changed": False,
    }
    if not workspace_response:
        action_result["msg"] = f"The workspace {params['workspace_id']} was not found."
        return action_result
    if not check_mode:
        if params["force"]:
            adapter.force_delete_workspace(workspace_response["id"])
            msg = f"The workspace {params['workspace_id']} was force-deleted successfully."
            action_result["changed"] = True
        else:
            adapter.safe_delete_workspace(workspace_response["id"])
            msg = f"The workspace {params['workspace_id']} was safe-deleted successfully."
            action_result["changed"] = True
    else:
        msg = f"The workspace {params['workspace_id']} was found. Skipped delete due to check mode."
        action_result["changed"] = True
    action_result["msg"] = msg
    return action_result


def state_unlocked(adapter: WorkspaceAdapter, params: Dict[str, Any], workspace_response: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Unlocks a Terraform workspace, either forcefully or gracefully depending on the provided parameters.

    If the workspace ID is not provided, it attempts to retrieve it using the organization and workspace name.
    Unlocking is then performed based on the value of the `force` flag.


    Args:
        adapter: WorkspaceAdapter instance
        params (Dict[str, Any]): A dictionary of module parameters.
        workspace_response (Dict[str, Any]): A dictionary of workspace response parameters.
        check_mode (bool): A check mode parameter.

    Returns:
        Dict[str, Any]: A dictionary with the result of the unlock operation, including:
            - "changed" (bool): Always True, indicating the workspace was unlocked.
            - "msg" (str): A success message.
            - Additional data returned from the unlock operation.
    """
    action_result = {}
    if not workspace_response:
        raise ValueError(f"The workspace {params['workspace_id']} was not found, hence cannot proceed with unlocking.")
    locked_status = workspace_response.get("locked")
    if not locked_status:
        action_result.update(
            {"changed": False, "msg": f"The workspace {params['workspace_id']} is already unlocked."},
        )
        return action_result
    if not check_mode:
        if params["force"]:
            response = adapter.force_unlock_workspace(workspace_response["id"])
        else:
            response = adapter.unlock_workspace(workspace_response["id"])
        action_result.update(
            {"changed": True, "msg": f"The workspace {params['workspace_id']} was unlocked successfully.", **response},
        )
    else:
        action_result.update(
            {"changed": True, "msg": f"The workspace {params['workspace_id']} was found. Skipped unlocking due to check mode."},
        )
    return action_result


def state_locked(adapter: WorkspaceAdapter, params: Dict[str, Any], workspace_response: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Locks a Terraform workspace.

    If the workspace ID is not provided, the function retrieves it using the organization
    and workspace name. It then locks the workspace with the given reason.

    Args:
        adapter: WorkspaceAdapter instance
        params (Dict[str, Any]): A dictionary of module parameters.
        workspace_response (Dict[str, Any]): A dictionary of workspace response parameters.
        check_mode (bool): A check mode parameter.

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): True if the workspace was successfully locked.
            - "msg" (str): A message indicating success.
            - Additional data returned from the lock operation.
    """
    action_result = {
        "changed": False,
    }
    if not workspace_response:
        raise ValueError(f"The workspace {params['workspace_id']} was not found, hence cannot proceed with locking.")
    locked_status = workspace_response.get("locked")
    if locked_status:
        action_result.update(
            {"changed": False, "msg": f"The workspace {params['workspace_id']} is already locked."},
        )
        return action_result
    if not check_mode:
        response = adapter.lock_workspace(workspace_response["id"], reason=params["lock_reason"])
        action_result.update(
            {"changed": True, "msg": f"The workspace {params['workspace_id']} was locked successfully.", **response},
        )
    else:
        action_result.update(
            {"changed": True, "msg": f"The workspace {params['workspace_id']} was found. Skipped locking due to check mode."},
        )

    return action_result


def main():
    module = AnsibleTerraformModule(
        argument_spec={
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent", "unlocked", "locked"]},
            "project_id": {"type": "str"},
            "allow_destroy_plan": {"type": "bool"},
            "assessments_enabled": {"type": "bool"},
            "auto_apply": {"type": "bool"},
            "auto_apply_run_trigger": {"type": "bool"},
            "auto_destroy_at": {"type": "str"},
            "auto_destroy_activity_duration": {"type": "str"},
            "source_name": {"type": "str"},
            "source_url": {"type": "str"},
            "description": {"type": "str"},
            "terraform_version": {"type": "str"},
            "execution_mode": {"type": "str", "choices": ["remote", "local", "agent"]},
            "agent_pool_id": {"type": "str"},
            "tag_bindings": {"type": "dict"},
            "setting_overwrites": {"type": "dict"},
            "force": {"type": "bool"},
            "lock_reason": {"type": "str"},
        },
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
    params = deepcopy(module.params)
    params["check_mode"] = module.check_mode
    state = params["state"]

    try:
        # Create adapter with params dict
        adapter = WorkspaceAdapter(tfe_token=params.get("tfe_token"), tfe_address=params.get("tfe_address"))

        if state == "present":
            # validate the format of the timestamp
            if params.get("auto_destroy_at"):
                datetime.strptime(params["auto_destroy_at"], "%Y-%m-%dT%H:%M:%SZ")
            # either workspace_id or workspace MUST be provided when state is present
            # when a workspace is provided, organization must be given
            if not params.get("workspace_id"):
                # get the workspace_id from the provided workspace name
                workspace_response = adapter.get_workspace_by_name(params.get("organization"), params.get("workspace"))
                if not workspace_response:
                    action_result = state_create(adapter, params, params["check_mode"])
                else:
                    # retrieve the workspace ID
                    workspace_id = workspace_response.get("id")
                    # update module params to have a workspace ID
                    params["workspace_id"] = workspace_id
                    action_result = state_update(adapter, params, params["check_mode"])
            else:
                # if workspace_id is provided then update is triggered
                action_result = state_update(adapter, params, params["check_mode"])
        elif state in ("absent", "locked", "unlocked"):
            # get the workspace response
            if not params.get("workspace_id"):
                workspace_response = adapter.get_workspace_by_name(params.get("organization"), params.get("workspace"))
                if not workspace_response:
                    raise ValueError(f"The workspace {params['workspace']} in {params['organization']} organization was not found.")
                params["workspace_id"] = workspace_response["id"]
            else:
                workspace_response = adapter.get_workspace_by_id(params["workspace_id"])

            if state == "absent":
                action_result = state_absent(adapter, params, workspace_response, params["check_mode"])

            elif state == "locked":
                action_result = state_locked(adapter, params, workspace_response, params["check_mode"])

            elif state == "unlocked":
                action_result = state_unlocked(adapter, params, workspace_response, params["check_mode"])

        result.update(action_result)
        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))
    finally:
        adapter.cleanup()


if __name__ == "__main__":
    main()
