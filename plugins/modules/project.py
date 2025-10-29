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
    execution_mode:
        description:
          - The execution mode for workspaces in this project.
          - Controls where Terraform operations are executed.
        type: str
        choices: ["remote", "local", "agent"]
    default_agent_pool_id:
        description:
          - The ID of the default agent pool for workspaces in this project.
          - Only applicable when execution_mode is set to 'agent'.
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
    execution_mode: "remote"
    auto_destroy_activity_duration: "30d"
    state: "present"

# Task output:
# ------------
# "result": {
#     "attributes": {
#         "auto-destroy-activity-duration": "30d",
#         "created-at": "2025-01-15T10:30:00.000Z",
#         "description": "Project for managing production infrastructure",
#         "execution-mode": "remote",
#         "name": "my-infrastructure-project",
#         "permissions": {
#             "can-access": true,
#             "can-create-team": true,
#             "can-create-workspace": true,
#             "can-destroy": true,
#             "can-update": true
#         },
#         "updated-at": "2025-01-15T10:30:00.000Z"
#     },
#     "changed": true,
#     "id": "prj-abc123def456",
#     "links": {
#         "self": "/api/v2/projects/prj-abc123def456"
#     },
#     "relationships": {
#         "organization": {
#             "data": {
#                 "id": "org-xyz789abc123",
#                 "type": "organizations"
#             }
#         }
#     },
#     "type": "projects"
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
#     "attributes": {
#         "created-at": "2025-01-15T11:00:00.000Z",
#         "description": "Project with custom tags",
#         "name": "tagged-project",
#         "permissions": {
#             "can-access": true,
#             "can-create-team": true,
#             "can-create-workspace": true,
#             "can-destroy": true,
#             "can-update": true
#         },
#         "updated-at": "2025-01-15T11:00:00.000Z"
#     },
#     "changed": true,
#     "id": "prj-def456ghi789",
#     "links": {
#         "self": "/api/v2/projects/prj-def456ghi789"
#     },
#     "relationships": {
#         "organization": {
#             "data": {
#                 "id": "org-xyz789abc123",
#                 "type": "organizations"
#             }
#         },
#         "tag-bindings": {
#             "data": [
#                 {
#                     "key": "Environment",
#                     "value": "Production"
#                 },
#                 {
#                     "key": "Team",
#                     "value": "Infrastructure"
#                 },
#                 {
#                     "key": "Cost-Center",
#                     "value": "Engineering"
#                 }
#             ]
#         }
#     },
#     "type": "projects"
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
#     "attributes": {
#         "auto-destroy-activity-duration": "60d",
#         "created-at": "2025-01-15T10:30:00.000Z",
#         "description": "Updated project description",
#         "execution-mode": "remote",
#         "name": "updated-infrastructure-project",
#         "permissions": {
#             "can-access": true,
#             "can-create-team": true,
#             "can-create-workspace": true,
#             "can-destroy": true,
#             "can-update": true
#         },
#         "updated-at": "2025-01-15T12:15:00.000Z"
#     },
#     "changed": true,
#     "id": "prj-abc123def456",
#     "links": {
#         "self": "/api/v2/projects/prj-abc123def456"
#     },
#     "relationships": {
#         "organization": {
#             "data": {
#                 "id": "org-xyz789abc123",
#                 "type": "organizations"
#             }
#         }
#     },
#     "type": "projects"
# }

- name: Create a project with custom settings
  hashicorp.terraform.project:
    name: "custom-settings-project"
    organization: "my-org"
    description: "Project with custom workspace settings"
    execution_mode: "local"
    setting_overwrites:
      auto_apply: true
      global_remote_state: false
    state: "present"

# Task output:
# ------------
# "result": {
#     "attributes": {
#         "created-at": "2025-01-15T13:00:00.000Z",
#         "description": "Project with custom workspace settings",
#         "execution-mode": "local",
#         "name": "custom-settings-project",
#         "permissions": {
#             "can-access": true,
#             "can-create-team": true,
#             "can-create-workspace": true,
#             "can-destroy": true,
#             "can-update": true
#         },
#         "setting-overwrites": {
#             "auto_apply": true,
#             "global_remote_state": false
#         },
#         "updated-at": "2025-01-15T13:00:00.000Z"
#     },
#     "changed": true,
#     "id": "prj-ghi789jkl012",
#     "links": {
#         "self": "/api/v2/projects/prj-ghi789jkl012"
#     },
#     "relationships": {
#         "organization": {
#             "data": {
#                 "id": "org-xyz789abc123",
#                 "type": "organizations"
#             }
#         }
#     },
#     "type": "projects"
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
data:
    description: The main data object containing project information.
    returned: when state is present
    type: complex
    contains:
        id:
            description: The unique identifier of the project.
            returned: always
            type: str
            sample: "prj-7TwrwCoRQ3FXbFtP"
        type:
            description: The resource type, always 'projects'.
            returned: always
            type: str
            sample: "projects"
        attributes:
            description: The project's attributes and configuration.
            returned: always
            type: dict
            sample: {
                "auto-destroy-activity-duration": "30d",
                "created-at": "2025-07-03T08:10:20.479Z",
                "description": "Production infrastructure project",
                "execution-mode": "remote",
                "name": "my-infrastructure-project",
                "permissions": {
                    "can-access": true,
                    "can-create-team": true,
                    "can-create-workspace": true,
                    "can-destroy": true,
                    "can-update": true
                },
                "setting-overwrites": {
                    "auto_apply": false,
                    "global_remote_state": true
                },
                "updated-at": "2025-07-03T08:10:20.651Z"
            }
        relationships:
            description: Related resources linked to the project.
            returned: always
            type: dict
            sample: {
                "organization": {
                    "data": {
                        "id": "org-82Qk88p7boaHK2BT",
                        "type": "organizations"
                    }
                },
                "tag-bindings": {
                    "data": [
                        {
                            "key": "Environment",
                            "value": "Production"
                        },
                        {
                            "key": "Team",
                            "value": "Infrastructure"
                        }
                    ]
                }
            }
        links:
            description: API links for the project.
            returned: always
            type: dict
            sample: {
                "self": "/api/v2/projects/prj-7TwrwCoRQ3FXbFtP"
            }
"""
from copy import deepcopy
from typing import Any, Dict, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.project import ProjectRequest
from ansible_collections.hashicorp.terraform.plugins.module_utils.project import (
    create_project,
    delete_project,
    get_project_by_id,
    get_project_tag_bindings,
    list_projects,
    update_project,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff


def get_project_by_name(client: TerraformClient, organization: str, name: str) -> Dict[str, Any]:
    """
    Get a project by name.
    Args:
        client: TerraformClient instance
        organization: The name of the organization
        name: The name of the project
    Returns:
        The project in the form of a dictionary, or empty dict if not found.
    """
    response = list_projects(client, organization, query_params={"filter[names]": name})
    data = response.get("data", [])
    return data[0] if data else {}


def fetch_project_tag_bindings(client: TerraformClient, project_id: str) -> dict:
    """
    Fetch actual tag key-value pairs for a project's tag bindings.

    Args:
        client: An instance of TerraformClient.
        project_id (str): The project ID.

    Returns:
        Dict[str, str]: A mapping of tag keys to values.
    """
    response = get_project_tag_bindings(client, project_id)

    if not response or "data" not in response:
        return {}

    tag_values = {}
    for item in response["data"]:
        if item.get("type") == "tag-bindings":
            attributes = item.get("attributes", {})
            key = attributes.get("key")
            value = attributes.get("value")
            if key is not None:
                tag_values[key] = value

    return tag_values


def normalize_project_response(response_data: dict, client: TerraformClient, project_id: str) -> dict:
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
        "name": response_data["data"].get("attributes", {}).get("name"),
        "description": response_data["data"].get("attributes", {}).get("description"),
        "auto_destroy_activity_duration": response_data["data"].get("attributes", {}).get("auto-destroy-activity-duration"),
        "execution_mode": response_data["data"].get("attributes", {}).get("default-execution-mode"),
        "default_agent_pool_id": response_data["data"].get("attributes", {}).get("default-agent-pool-id"),
        "setting_overwrites": response_data["data"].get("attributes", {}).get("setting-overwrites"),
    }

    # Include tag bindings (keep even if empty to allow comparison)
    tag_bindings = fetch_project_tag_bindings(client, project_id)
    if tag_bindings:  # Only include if there are actual tag bindings
        normalized["tag_bindings"] = tag_bindings

    return normalized


def fetch_project(client: TerraformClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if a project exists.
    client: TerraformClient instance
    params: Dictionary of parameters for the project
    Returns:
        True if the project exists, False otherwise.
    """
    project_id = params.get("project_id")
    project_name = params.get("project")
    organization = params.get("organization")

    if project_id:
        project = get_project_by_id(client, project_id)
        if project:
            return project

    if project_name and organization:
        existing_project: Optional[Dict[str, Any]] = get_project_by_name(client, organization, project_name)
        if existing_project and (project_id := existing_project.get("id")):
            project = get_project_by_id(client, project_id)
            return project

    return {}


def state_present(client: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Optional[Dict[str, Any]]:
    """
    Create/update a Terraform project.
    client: TerraformClient instance
    params: Dictionary of parameters for the project
    check_mode: If True, only report what would be changed without making changes
    Returns:
        The created/updated project in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 201/200 status code.
    """
    ignore_params = {"check_mode", "state", "organization", "project_id"}
    project_params = {key: value for key, value in params.items() if not key.startswith(("tf_", "poll_")) and key not in ignore_params}

    if project := fetch_project(client, params):
        # Project exists, perform update logic with diff
        return state_update(client, params, project, check_mode)
    else:
        # Project doesn't exist, create it
        project_request = ProjectRequest.create(organization=params.get("organization"), **project_params).model_dump(
            by_alias=True, exclude_unset=False, exclude_none=True
        )
        if not check_mode:
            response = create_project(client, organization=params.get("organization"), data=project_request)
            return {"changed": True, **response.get("data")}
        else:
            return {
                "changed": True,
                "msg": f"The project {params.get('project')} would be created with the given options. Skipped creation due to check mode.",
                **project_request["data"],
            }


def state_update(client: TerraformClient, params: Dict[str, Any], project: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Update an existing Terraform project using the provided client and parameters.

    This function compares the current project state with desired state and only
    updates if there are differences.

    Args:
        client: TerraformClient instance
        params: Dictionary of parameters for the project
        project: Existing project data from API
        check_mode: If True, only report what would be changed without making changes
    Returns:
        Dictionary indicating the result of the operation
    """
    ignore_params = {"check_mode", "state", "organization", "project_id"}
    project_params = {key: value for key, value in params.items() if not key.startswith(("tf_", "poll_")) and key not in ignore_params}

    project_id = project["data"].get("id")

    # Get current state (what we have)
    have = normalize_project_response(project, client, project_id)

    # Get desired state (what we want) - handle field name mapping
    want = {}
    for k, v in project_params.items():
        if k == "project":
            want["name"] = v
        elif k == "tag_bindings" and isinstance(v, list):
            # Normalize tag_bindings from list format to dict format for comparison
            # The API returns tag_bindings as {"key": "value"} but users provide it as [{"key": "k", "value": "v"}]
            tag_bindings_dict = {}
            for tag in v:
                if isinstance(tag, dict) and "key" in tag and "value" in tag:
                    tag_bindings_dict[tag["key"]] = tag["value"]
            if tag_bindings_dict:  # Only add if not empty
                want[k] = tag_bindings_dict
        elif v is not None and v != {}:
            want[k] = v

    # Remove excessive keys from have to match it to want
    # Also filter out None values and empty dicts from have for consistency
    have = {k: v for k, v in have.items() if k in want and v is not None and v != {}}

    # Ensure type compatibility: if have has a dict value, want must also have a dict value
    # This prevents dict_diff from trying to recursively compare incompatible types
    for key, value in list(have.items()):
        if isinstance(value, dict) and key in want and not isinstance(want[key], dict):
            # Type mismatch: remove from have to avoid dict_diff error
            # This will cause the field to be treated as an update
            del have[key]

    # Compare the two dictionaries to find differences
    updates_response = dict_diff(have, want)

    # Filter out tag_bindings from updates if have doesn't have it
    # This handles the case where tag bindings aren't fetched/supported properly
    if "tag_bindings" in updates_response and "tag_bindings" not in have:
        # Tag bindings are in updates but not in current state
        # This means we tried to set them but they're not readable via API
        # Remove from updates to avoid false positives
        updates_response.pop("tag_bindings", None)

    if not updates_response:
        return {"changed": False}

    project_request = ProjectRequest.create(organization=params.get("organization"), **project_params).model_dump(
        by_alias=True, exclude_unset=False, exclude_none=True
    )
    if not check_mode:
        response = update_project(client, project_id, project_request)
        return {"changed": True, **response.get("data")}
    else:
        return {
            "changed": True,
            "msg": f"The project {project_id} would be updated with the given options. Skipped update due to check mode.",
            **project_request.get("data"),
        }


def state_absent(client: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Delete a Terraform project.
    client: TerraformClient instance
    params: Dictionary of parameters for the project
    check_mode: If True, only report what would be changed without making changes
    Returns:
        The deleted project in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    project_id = params.get("project_id")
    if not project_id:
        project = fetch_project(client, params)
        if project:
            project_data = project.get("data")
            if project_data:
                project_id = project_data.get("id")

    if not project_id:
        return {"changed": False, "msg": "Project not found"}

    if not check_mode:
        delete_project(client, project_id)
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
            "execution_mode": {"type": "str", "choices": ["remote", "local", "agent"]},
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

    try:
        tf_client = TerraformClient(**params)

        match params["state"]:
            case "present":
                action_result = state_present(tf_client, params, params["check_mode"])
            case "absent":
                action_result = state_absent(tf_client, params, params["check_mode"])

        result.update(action_result)
        module.exit_json(**result)

    except Exception as e:
        module.fail_from_exception(e)


if __name__ == "__main__":
    main()
