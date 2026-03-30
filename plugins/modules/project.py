#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: project
version_added: "1.2.0"
short_description: Manage Terraform Cloud/Enterprise projects (create, update, delete).
author: "Siddarth Sharma (@siddasha)"
description:
  - Manages Terraform Cloud and Terraform Enterprise projects with support for creating, updating, and deleting operations.
  - Allows users to manage projects by specifying organization, project configuration, and other project parameters.
  - Can create new projects with customizable settings including auto-destroy duration, execution mode, and agent pools.
  - Provides comprehensive options for managing project attributes including descriptions, settings, and tag bindings.
  - Compatible with both Terraform Cloud and Terraform Enterprise environments.
  - The C(present) state creates a new project or updates an existing one with the specified parameters.
  - The C(absent) state deletes an existing project using its project ID.
extends_documentation_fragment: hashicorp.terraform.common
options:
    project_id:
        description: The unique identifier of the project to manage.
        type: str
    project:
        description: The name of the project.
        type: str
        aliases: ["name"]
    organization:
        description: The name of the organization that will own the project.
        type: str
    description:
        description: An optional description for the project.
        type: str
    auto_destroy_activity_duration:
        description:
          - The duration after which inactive workspaces in this project will be automatically destroyed.
          - Format should be a duration string like "14d" for 14 days or "720h" for 720 hours.
          - If not specified, workspaces will not be automatically destroyed.
        type: str
    default_execution_mode:
        description:
          - The execution mode for workspaces in this project.
          - Controls where Terraform operations are executed.
        type: str
        choices: ["remote", "local", "agent"]
    default_agent_pool_id:
        description:
          - The ID of the default agent pool for workspaces in this project.
          - Only applicable when default_execution_mode is set to 'agent'.
        type: str
    setting_overwrites:
        description:
          - A dictionary of setting overwrites for the project.
          - These settings will override workspace-level settings.
        type: dict
    tag_bindings:
        description:
          - A list of tag bindings to associate with the project.
          - Each tag binding should contain 'key' and 'value' fields.
        type: list
        elements: dict
        suboptions:
            key:
                description: The tag key.
                type: str
                required: true
            value:
                description: The tag value.
                type: str
                required: true
    state:
        description:
          - The desired state of the project to manage.
          - The C(present) state creates a new project or updates an existing one.
          - The C(absent) state deletes an existing project.
        type: str
        choices: ['present', 'absent']
        default: 'present'
"""

EXAMPLES = r"""
- name: Create a new Terraform project
  hashicorp.terraform.project:
    name: "my-infrastructure-project"
    organization: "my-org"
    description: "Project for managing production infrastructure"
    default_execution_mode: "remote"
    auto_destroy_activity_duration: "30d"
    state: "present"

# Task output:
# ------------
# "result": {
#     "auto_destroy_activity_duration": "30d",
#     "created_at": "2025-01-15T10:30:00.000Z",
#     "default_execution_mode": "remote",
#     "description": "Project for managing production infrastructure",
#     "name": "my-infrastructure-project",
#     "updated_at": "2025-01-15T10:30:00.000Z",
#     "changed": true,
#     "id": "prj-abc123def456",
#     "name": "my-infrastructure-project",
#     "organization": {
#         "id": "org-xyz789abc123"
#     },
#     "setting_overwrites": {
#         "agent_pool": true,
#         "execution_mode": true
#     },
#     "workspace_count": 0
# }

- name: Create a project with tag bindings
  hashicorp.terraform.project:
    name: "tagged-project"
    organization: "my-org"
    description: "Project with custom tags"
    tag_bindings:
      - key: "Environment"
        value: "Production"
      - key: "Team"
        value: "Infrastructure"
      - key: "Cost-Center"
        value: "Engineering"
    state: "present"

# Task output:
# ------------
# "result": {
#     "created_at": "2025-01-15T11:00:00.000Z",
#     "description": "Project with custom tags",
#     "name": "tagged-project",
#     "updated_at": "2025-01-15T11:00:00.000Z",
#     "id": "prj-def456ghi789",
#     "organization": {
#         "id": "org-xyz789abc123"
#     }
#     "changed": true,
# }

- name: Update an existing project
  hashicorp.terraform.project:
    project_id: "prj-abc123def456"
    name: "updated-infrastructure-project"
    description: "Updated project description"
    auto_destroy_activity_duration: "60d"
    state: "present"

# Task output:
# ------------
# "result": {
#     "changed": true,
#     "auto_destroy_activity_duration": "60d",
#     "created_at": "2025-01-15T10:30:00.000Z",
#     "default_execution_mode": "remote",
#     "description": "Updated project description",
#     "id": "prj-abc123def456",
#     "name": "updated-infrastructure-project"
#     "updated_at": "2025-01-15T12:00:00.000Z",
#     "organization": {
#         "id": "org-xyz789abc123"
#     }
# }

- name: Create a project with custom settings
  hashicorp.terraform.project:
    name: "custom-settings-project"
    organization: "my-org"
    description: "Project with custom workspace settings"
    default_execution_mode: "local"
    setting_overwrites:
      auto_apply: true
      global_remote_state: false
    state: "present"

# Task output:
# ------------
# "result": {
#     "changed": true,
#     "created_at": "2025-01-15T13:00:00.000Z",
#     "default_execution_mode": "local",
#     "description": "Project with custom workspace settings",
#     "id": "prj-ghi789jkl012",
#     "name": "custom-settings-project",
#     "setting_overwrites": {
#         "auto_apply": true,
#         "global_remote_state": false
#     }
#     "updated_at": "2025-01-15T13:00:00.000Z",
# }

- name: Delete a project
  hashicorp.terraform.project:
    project_id: "prj-abc123def456"
    state: "absent"

# Task output:
# ------------
# "result": {
#     "changed": true,
#     "msg": "Project prj-abc123def456 has been deleted successfully"
# }
"""

RETURN = r"""
changed:
    description: Whether the module made a change.
    returned: always
    type: bool
    sample: true
id:
    description: The unique identifier of the project.
    returned: when state is present
    type: str
    sample: "prj-7TwrwCoRQ3FXbFtP"
name:
    description: The project name.
    returned: when state is present
    type: str
    sample: "my-infrastructure-project"
description:
    description: The project description.
    returned: when set
    type: str
    sample: "Production infrastructure project"
created_at:
    description: The project creation timestamp.
    returned: when state is present
    type: str
    sample: "2025-07-03T08:10:20.479Z"
default_execution_mode:
    description: Default execution mode for the project.
    returned: when state is present
    type: str
    sample: "remote"
auto_destroy_activity_duration:
    description: Auto destroy activity duration.
    returned: when provided by the API response
    type: str
    sample: "30d"
default_agent_pool:
    description: Default agent pool details for agent mode.
    returned: when execution mode is C(agent)
    type: dict
    sample: {
        "id": "apool-abc123",
        "agent_count": 0,
        "agents": [],
        "workspaces": []
    }
organization:
    description: Organization associated with the project.
    returned: when state is present
    type: dict
    sample: {
        "id": "my-org"
    }
setting_overwrites:
    description: Project setting overwrite toggles.
    returned: when state is present
    type: dict
    sample: {
        "agent_pool": true,
        "execution_mode": true
    }
workspace_count:
    description: Number of workspaces currently assigned to the project.
    returned: when state is present
    type: int
    sample: 2
msg:
    description: Informational message, primarily for delete and check mode operations.
    returned: when relevant
    type: str
    sample: "Project prj-7TwrwCoRQ3FXbFtP has been deleted successfully"
"""
from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.project import (
    create_project,
    delete_project,
    get_project_by_id,
    get_project_by_name,
    get_project_tag_bindings,
    update_project,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff


def normalize_project_response(response_data: dict, adapter: TerraformClient, project_id: str) -> dict:
    """
    Normalizes the raw project API response into a simplified, structured dictionary
    representing the current state of a project.

    This function extracts key attributes and relationships from the Terraform project
    API response and formats certain fields for consistency. It also includes related data such
    as tag bindings.

    Args:
        response_data (dict): The raw JSON response from the project API.
        client: A client instance used to fetch additional project data
        project_id (str): The ID of the project whose data is being normalized.

    Returns:
        dict: A dictionary representing the normalized state of the project, excluding
              any fields that are `None`.
    """

    normalized = {
        "name": response_data.get("name"),
        "description": response_data.get("description"),
        "auto_destroy_activity_duration": response_data.get("auto_destroy_activity_duration"),
        "default_execution_mode": response_data.get("default_execution_mode"),
        "setting_overwrites": response_data.get("setting_overwrites"),
        "default_agent_pool_id": None,
    }

    # Extract default_agent_pool_id from response
    default_agent_pool_rel = response_data.get("default_agent_pool")
    if default_agent_pool_rel and "id" in default_agent_pool_rel:
        normalized["default_agent_pool_id"] = default_agent_pool_rel.get("id")

    # Include tag bindings (keep even if empty to allow comparison)
    tag_bindings = get_project_tag_bindings(adapter, project_id)
    if tag_bindings:  # Only include if there are actual tag bindings
        if isinstance(tag_bindings, list):
            normalized["tag_bindings"] = _normalize_tag_bindings(tag_bindings)
        else:
            normalized["tag_bindings"] = tag_bindings

    return normalized


def fetch_project(adapter: TerraformClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if a project exists.
    adapter: TerraformClient instance
    params: Dictionary of parameters for the project
    Returns:
        True if the project exists, False otherwise.
    """
    project_id = params.get("project_id")
    project_name = params.get("project")
    organization = params.get("organization")

    if project_id:
        if project := get_project_by_id(adapter, project_id):
            return project

    if project_name and organization:
        if project := get_project_by_name(adapter, organization, project_name):
            if project.get("id"):
                project = get_project_by_id(adapter, project.get("id"))
            return project

    return {}


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Optional[Dict[str, Any]]:
    """
    Create/update a Terraform project.
    adapter: TerraformClient instance
    params: Dictionary of parameters for the project
    check_mode: If True, only report what would be changed without making changes
    Returns:
        The created/updated project in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 201/200 status code.
    """
    ignore_params = {"check_mode", "state", "organization", "project_id"}
    project_params = {key: value for key, value in params.items() if not key.startswith(("tf_", "tfe_", "poll_")) and key not in ignore_params}

    # Map module argument names to SDK option field names.
    if "project" in project_params:
        project_params["name"] = project_params.pop("project")

    if project := fetch_project(adapter, params):
        # Project exists, perform update logic with diff
        return state_update(adapter, params, project, check_mode)
    else:
        # Project doesn't exist, create it
        if not check_mode:
            response = create_project(adapter, organization=params.get("organization"), data=project_params)
            return {"changed": True, **response.get("data", response)}
        else:
            return {
                "changed": True,
                "msg": f"The project {params.get('project')} would be created with the given options. Skipped creation due to check mode.",
                **project_params,
            }


def _normalize_tag_bindings(tag_bindings_list: list) -> dict:
    """
    Normalize tag_bindings from list format to dict format for comparison.

    The API returns tag_bindings as {"key": "value"} but users provide it as
    [{"key": "k", "value": "v"}].

    Args:
        tag_bindings_list: List of tag binding dictionaries with 'key' and 'value' keys

    Returns:
        Dictionary mapping tag keys to values
    """
    tag_bindings_dict = {}
    for tag in tag_bindings_list:
        if isinstance(tag, dict) and "key" in tag and "value" in tag:
            tag_bindings_dict[tag["key"]] = tag["value"]
    return tag_bindings_dict


def _build_desired_state(project_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the desired state dictionary from project parameters.

    Handles field name mapping (e.g., 'project' -> 'name') and normalizes
    tag_bindings format.

    Args:
        project_params: Dictionary of project parameters from user input

    Returns:
        Dictionary representing the desired state with normalized field names
    """
    want = {}
    for k, v in project_params.items():
        if k == "project":
            want["name"] = v
        elif k == "execution_mode":
            want["default_execution_mode"] = v
        elif k == "tag_bindings" and isinstance(v, list):
            tag_bindings_dict = _normalize_tag_bindings(v)
            if tag_bindings_dict:  # Only add if not empty
                want[k] = tag_bindings_dict
        elif v is not None and v != {}:
            want[k] = v
    return want


def _filter_current_state(have: Dict[str, Any], want: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter the current state to match keys in desired state and ensure type compatibility.

    Removes excessive keys from 'have', filters out None values and empty dicts,
    and handles type mismatches to prevent dict_diff errors.

    Args:
        have: Dictionary representing current state
        want: Dictionary representing desired state

    Returns:
        Filtered current state dictionary
    """
    # Remove excessive keys from have to match it to want
    # Also filter out None values and empty dicts from have for consistency
    filtered = {k: v for k, v in have.items() if k in want and v is not None and v != {}}

    # Ensure type compatibility: if have has a dict value, want must also have a dict value
    # This prevents dict_diff from trying to recursively compare incompatible types
    for key, value in list(filtered.items()):
        if isinstance(value, dict) and key in want and not isinstance(want[key], dict):
            # Type mismatch: remove from have to avoid dict_diff error
            # This will cause the field to be treated as an update
            del filtered[key]

    return filtered


def _filter_tag_binding_updates(updates: Dict[str, Any], have: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out tag_bindings from updates if not present in current state.

    This handles the case where tag bindings aren't fetched/supported properly.

    Args:
        updates: Dictionary of detected updates
        have: Dictionary representing current state

    Returns:
        Filtered updates dictionary
    """
    if "tag_bindings" in updates and "tag_bindings" not in have:
        # Tag bindings are in updates but not in current state
        # This means we tried to set them but they're not readable via API
        # Remove from updates to avoid false positives
        updates.pop("tag_bindings", None)

    return updates


def _create_update_response(
    adapter: TerraformClient, project_id: str, project_params: Dict[str, Any], params: Dict[str, Any], check_mode: bool
) -> Dict[str, Any]:
    """
    Create and execute the update request or return check mode message.

    Args:
        adapter: TerraformClient instance
        project_id: ID of the project to update
        project_params: Dictionary of project parameters
        params: Full parameters dictionary including organization
        check_mode: If True, return what would be changed without making changes

    Returns:
        Dictionary with update results or check mode message
    """

    if not check_mode:
        response = update_project(adapter, project_id, data=project_params)
        return {"changed": True, **response.get("data", response)}
    else:
        return {
            "changed": True,
            "msg": f"The project {project_id} would be updated with the given options. Skipped update due to check mode.",
            **project_params,
        }


def state_update(adapter: TerraformClient, params: Dict[str, Any], project: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Update an existing Terraform project using the provided client and parameters.

    This function compares the current project state with desired state and only
    updates if there are differences.

    Args:
        adapter: TerraformClient instance
        params: Dictionary of parameters for the project
        project: Existing project data from API
        check_mode: If True, only report what would be changed without making changes
    Returns:
        Dictionary indicating the result of the operation
    """
    ignore_params = {"check_mode", "state", "organization", "project_id"}
    project_params = {key: value for key, value in params.items() if not key.startswith(("tf_", "tfe_", "poll_")) and key not in ignore_params}

    if "project" in project_params:
        project_params["name"] = project_params.pop("project")

    project_id = project.get("id")

    # Get current state (what we have)
    have = normalize_project_response(project, adapter, project_id)

    # Get desired state (what we want) - handle field name mapping
    want = _build_desired_state(project_params)

    # Filter current state to match desired state
    have = _filter_current_state(have, want)

    # Compare the two dictionaries to find differences
    updates_response = dict_diff(have, want)

    # Filter out tag_bindings from updates if have doesn't have it
    updates_response = _filter_tag_binding_updates(updates_response, have)

    if not updates_response:
        return {"changed": False}

    return _create_update_response(adapter, project_id, project_params, params, check_mode)


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Delete a Terraform project.
    adapter: TerraformClient instance
    params: Dictionary of parameters for the project
    check_mode: If True, only report what would be changed without making changes
    Returns:
        The deleted project in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    project_id = params.get("project_id")
    if not project_id:
        project = fetch_project(adapter, params)
        if project:
            project_id = project.get("id")

    if not project_id:
        return {"changed": False, "msg": "Project not found"}

    if not check_mode:
        delete_project(adapter, project_id)
        return {"changed": True, "msg": f"Project {project_id} has been deleted successfully"}
    else:
        return {"changed": True, "msg": f"The project {project_id} would be deleted. Skipped deletion due to check mode."}


def main():
    module = AnsibleTerraformModule(
        argument_spec={
            "project_id": {"type": "str"},
            "project": {"type": "str", "aliases": ["name"]},
            "organization": {"type": "str"},
            "description": {"type": "str"},
            "auto_destroy_activity_duration": {"type": "str"},
            "default_execution_mode": {"type": "str", "choices": ["remote", "local", "agent"]},
            "default_agent_pool_id": {"type": "str"},
            "setting_overwrites": {"type": "dict"},
            "tag_bindings": {"type": "list", "elements": "dict"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_together=[["project", "organization"]],
        required_if=[
            ("state", "present", ("project_id", "project"), True),
            ("state", "absent", ("project_id", "project"), True),
        ],
        supports_check_mode=True,
        mutually_exclusive=[
            ("project", "project_id"),
        ],
    )
    warnings = []
    result = {"changed": False, "warnings": warnings}
    action_result = {}
    params = deepcopy(module.params)
    params["check_mode"] = module.check_mode
    adapter = None

    try:
        adapter = TerraformClient(tfe_token=params.get("tfe_token"), tfe_address=params.get("tfe_address"))

        match params["state"]:
            case "present":
                action_result = state_present(adapter, params, params["check_mode"])
            case "absent":
                action_result = state_absent(adapter, params, params["check_mode"])

        result.update(action_result)
        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))
    finally:
        if adapter:
            adapter.cleanup()


if __name__ == "__main__":
    main()
