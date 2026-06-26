#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: team_info
version_added: 2.1.0
short_description: Retrieve information about a team in Terraform Cloud/Enterprise.
author: "Tanya Singh (@tanyasingh)"
description:
  - Retrieves information about a team in Terraform Cloud/Enterprise by its unique ID.
  - Lists teams in an organization when O(organization) is provided without O(name).
  - Searches for a team by name when O(organization) and O(name) are provided.
  - Fails if a requested team does not exist.
extends_documentation_fragment: hashicorp.terraform.common
options:
  team_id:
    description:
      - The unique identifier of the team to retrieve.
      - Mutually exclusive with O(organization) and O(name).
    type: str
  organization:
    description:
      - The organization whose teams should be listed or searched.
      - Required when O(team_id) is not provided.
      - Mutually exclusive with O(team_id).
    type: str
  name:
    description:
      - Team name to search for within O(organization).
      - Requires O(organization).
      - Mutually exclusive with O(team_id).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve information about a team by ID
  hashicorp.terraform.team_info:
    team_id: "team-abc123xyz"
  register: team_info

# Task output:
# ------------
# "team_info": {
#     "changed": false,
#     "failed": false,
#     "team": {
#         "id": "team-abc123xyz",
#         "name": "platform-team",
#         "visibility": "secret",
#         "allow_member_token_management": false,
#         "user_count": 5,
#         "is_unified": false,
#         "organization_access": {
#             "manage_workspaces": true,
#             "read_projects": true
#         },
#         "permissions": {
#             "can_destroy": true,
#             "can_update_membership": true
#         }
#     }
# }

- name: Handle case when team does not exist
  hashicorp.terraform.team_info:
    team_id: "team-invalid-id"
  register: team_info
  ignore_errors: true

# Task output:
# ------------
# FAILED! => {
#     "changed": false,
#     "failed": true,
#     "msg": "Team with ID team-invalid-id not found"
# }

- name: Search for a team by organization and name
  hashicorp.terraform.team_info:
    organization: "my-org"
    name: "platform-team"
  register: team_info

- name: List teams in an organization
  hashicorp.terraform.team_info:
    organization: "my-org"
  register: team_list
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
team:
  description: A dictionary containing the team information.
  returned: when O(team_id) or O(name) is provided
  type: dict
  contains:
    id:
      description: The unique identifier of the team.
      returned: always
      type: str
      sample: "team-abc123xyz"
    name:
      description: The name of the team.
      returned: always
      type: str
      sample: "platform-team"
    visibility:
      description: The visibility of the team.
      returned: always
      type: str
      sample: "secret"
    sso_team_id:
      description: The SAML Group ID for the team.
      returned: when configured
      type: str
      sample: "sso-group-123"
    allow_member_token_management:
      description: Whether team members can manage tokens.
      returned: always
      type: bool
      sample: false
    user_count:
      description: The number of users in the team.
      returned: always
      type: int
      sample: 5
    is_unified:
      description: Whether the team is unified.
      returned: always
      type: bool
      sample: false
    organization_access:
      description: Organization access permissions for the team.
      returned: when configured
      type: dict
      sample: {"manage_workspaces": true, "read_projects": true}
    permissions:
      description: Current user's permissions on the team.
      returned: when available
      type: dict
      contains:
        can_destroy:
          description: Whether the user can destroy the team.
          returned: always
          type: bool
        can_update_membership:
          description: Whether the user can update team membership.
          returned: always
          type: bool
teams:
  description: A list of teams matching the query.
  returned: when O(organization) is provided
  type: list
  elements: dict
"""


from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.team import (
    get_team,
    get_team_by_name,
    list_teams,
    normalize_team_response,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "team_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
        },
        required_one_of=[("team_id", "organization")],
        required_by={"name": ("organization",)},
        mutually_exclusive=[("team_id", "organization"), ("team_id", "name")],
        supports_check_mode=True,
    )

    warnings: list[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            if params.get("team_id"):
                team_data = get_team(adapter, params["team_id"])
                if not team_data:
                    raise ValueError(f"Team with ID {params['team_id']} not found")
                result["team"] = normalize_team_response(team_data)
            elif params.get("name"):
                team_data = get_team_by_name(adapter, params["organization"], params["name"])
                if not team_data:
                    raise ValueError(f"Team '{params['name']}' was not found in organization '{params['organization']}'")
                team = normalize_team_response(team_data)
                result["team"] = team
                result["teams"] = [team]
            else:
                result["teams"] = [normalize_team_response(team) for team in list_teams(adapter, params["organization"])]

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
