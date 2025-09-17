#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: project
version_added: "1.0.0"
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
        choices: ['remote', 'local']
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
