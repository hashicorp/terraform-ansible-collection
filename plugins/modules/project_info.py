# -*- coding: utf-8 -*-
# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type
DOCUMENTATION = r"""
---
module: project_info
version_added: 1.2.0
short_description: Gather information about a project in Terraform Enterprise/Cloud.
author: "Shashank Venkat (@shvenkat)"
description:
  - This module retrieves information about a given project in Terraform Enterprise/Cloud.
  - It can be used to check if a project exists or to gather detailed information about it.
  - If I(project_id) is provided, the module will return information about that specific project.
  - If the project does not exist, the module will fail with an error message.
extends_documentation_fragment: hashicorp.terraform.common
options:
  project_id:
    description:
      - The unique identifier of the project to retrieve information about.
    type: str
    required: true
"""
EXAMPLES = r"""
- name: Gather information about a project by ID
  hashicorp.terraform.project_info:
    project_id: "prj-sample1234567890"
  register: project_info

# Task output:
# ------------
# "project_info": {
#     "changed": false,
#     "failed": false,
#     "project": {
#         "id": "prj-sample1234567890",
#         "type": "projects",
#         "attributes": {
#             "name": "sample_project",
#             "description": "A sample Terraform project for demonstration purposes",
#             "created-at": "2025-06-09T09:09:18.024Z",
#             "permissions": {
#                 "can-read": true,
#                 "can-update": true,
#                 "can-destroy": true,
#                 "can-create-workspace": true,
#                 "can-move-workspace": true,
#                 "can-move-stack": true,
#                 "can-deploy-no-code-modules": true,
#                 "can-read-teams": true,
#                 "can-manage-tags": true,
#                 "can-manage-teams": true,
#                 "can-manage-in-hcp": false,
#                 "can-manage-ephemeral-workspace-for-projects": true,
#                 "can-manage-varsets": true
#             },
#             "workspace-count": 3,
#             "team-count": 0,
#             "stack-count": 0,
#             "auto-destroy-activity-duration": null,
#             "default-execution-mode": "remote",
#             "setting-overwrites": {
#                 "default-execution-mode": false,
#                 "default-agent-pool": false
#             }
#         },
#         "relationships": {
#             "organization": {
#                 "data": {
#                     "id": "sample_organization",
#                     "type": "organizations"
#                 },
#                 "links": {
#                     "related": "/api/v2/organizations/sample_organization"
#                 }
#             },
#             "default-agent-pool": {
#                 "data": null
#             }
#         },
#         "links": {
#             "self": "/api/v2/projects/prj-sample1234567890"
#         }
#     }
# }

- name: Handle case when project does not exist by ID
  hashicorp.terraform.project_info:
    project_id: "prj-invalid-project-id"
  register: project_info
  ignore_errors: true

# Task output:
# ------------
# FAILED! => {
#     "changed": false,
#     "failed": true,
#     "msg": "Project 'prj-invalid-project-id' was not found."
# }
"""

RETURN = r"""
project:
  type: dict
  description: A dictionary containing the project information.
  returned: on success
  contains:
    id:
      type: str
      returned: always
      description: The unique identifier of the project.
      sample: "prj-sample1234567890"
    type:
      type: str
      returned: always
      description: The type of the resource (always "projects").
      sample: "projects"
    attributes:
      type: dict
      returned: always
      description: The attributes of the project.
      contains:
        name:
          type: str
          returned: always
          description: The name of the project.
          sample: "sample_project"
        description:
          type: str
          returned: always
          description: The description of the project.
          sample: "A sample Terraform project for demonstration purposes"
        created_at:
          type: str
          returned: always
          description: The creation timestamp of the project.
          sample: "2025-06-09T09:09:18.024Z"
        permissions:
          type: dict
          returned: always
          description: The permissions for the current user on this project.
        workspace_count:
          type: int
          returned: always
          description: The number of workspaces in the project.
          sample: 3
        team_count:
          type: int
          returned: always
          description: The number of teams associated with the project.
          sample: 0
        stack_count:
          type: int
          returned: always
          description: The number of stacks in the project.
          sample: 0
        auto_destroy_activity_duration:
          type: str
          returned: always
          description: The auto-destroy activity duration setting.
          sample: null
        default_execution_mode:
          type: str
          returned: always
          description: The default execution mode for workspaces in this project.
          sample: "remote"
        setting_overwrites:
          type: dict
          returned: always
          description: Settings that are overwritten at the project level.
    relationships:
      type: dict
      returned: always
      description: Relationships to other resources.
      contains:
        organization:
          type: dict
          returned: always
          description: The organization this project belongs to.
        default_agent_pool:
          type: dict
          returned: always
          description: The default agent pool for the project.
    links:
      type: dict
      returned: always
      description: Links related to the project.
      contains:
        self:
          type: str
          returned: always
          description: API endpoint for this project.
          sample: "/api/v2/projects/prj-sample1234567890"
"""
from copy import deepcopy
from typing import TYPE_CHECKING

from ansible.module_utils._text import to_text

if TYPE_CHECKING:
    from typing import Any, Dict, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    TerraformClient,
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.project import (
    get_project_by_id,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "project_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    

    try:
        # Adapter initialization (pytfe SDK)
        adapter = TerraformClient(
            tfe_token=params.get("tfe_token"),
            tfe_address=params.get("tfe_address"),
        )

        project_data: Optional[Dict[str, Any]] = None

        if params["project_id"]:
            project_data = get_project_by_id(adapter, params["project_id"])

            if not project_data:
                raise ValueError(f"Project '{params['project_id']}' was not found.")
        else:
            raise ValueError("Project ID is required.")

        project_data.pop("status", None)

        

        result["project"] = project_data.get("data", project_data)  

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))

    finally:
        if adapter:
            adapter.cleanup()


if __name__ == "__main__":
    main()
