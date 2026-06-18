#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: team_info
version_added: 1.4.0
short_description: Retrieve information about a team in Terraform Cloud/Enterprise.
author: "Terraform Ansible Collection Contributors"
description:
  - This module retrieves information about a given team in Terraform Cloud/Enterprise.
  - If I(team_id) is provided, the module will return information about that specific team.
  - If the team does not exist, the module will fail with an error message.
extends_documentation_fragment: hashicorp.terraform.common
options:
  team_id:
    description:
      - The unique identifier of the team to retrieve information about.
    type: str
    required: true
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
#         "sso_team_id": null,
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
"""

RETURN = r"""
team:
  type: dict
  description: A dictionary containing the team information.
  returned: on success
  contains:
    id:
      type: str
      returned: always
      description: The unique identifier of the team.
      sample: "team-abc123xyz"
    name:
      type: str
      returned: always
      description: The name of the team.
      sample: "platform-team"
    visibility:
      type: str
      returned: always
      description: The visibility of the team (secret or organization).
      sample: "secret"
    sso_team_id:
      type: str
      returned: always
      description: The SAML Group ID for the team.
      sample: null
    allow_member_token_management:
      type: bool
      returned: always
      description: Whether team members can manage tokens.
      sample: false
    user_count:
      type: int
      returned: always
      description: The number of users in the team.
      sample: 5
    is_unified:
      type: bool
      returned: always
      description: Whether the team is unified.
      sample: false
    organization_access:
      type: dict
      returned: when available
      description: Organization access permissions for the team.
      sample: {"manage_workspaces": true, "read_projects": true}
    permissions:
      type: dict
      returned: when available
      description: Current user's permissions on the team.
      contains:
        can_destroy:
          type: bool
          returned: always
          description: Whether the user can destroy the team.
        can_update_membership:
          type: bool
          returned: always
          description: Whether the user can update team membership.
"""


from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict

from ansible.module_utils._text import to_text

if TYPE_CHECKING:
    from typing import Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.team import (
    get_team,
)


def normalize_team_response(team_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize team response data.

    Args:
        team_data: Team data from SDK response

    Returns:
        Normalized team data dictionary
    """
    normalized = {
        "id": team_data.get("id"),
        "name": team_data.get("name"),
        "visibility": team_data.get("visibility"),
        "sso_team_id": team_data.get("sso_team_id"),
        "allow_member_token_management": team_data.get("allow_member_token_management"),
        "user_count": team_data.get("user_count"),
        "is_unified": team_data.get("is_unified"),
    }

    if team_data.get("organization_access"):
        normalized["organization_access"] = team_data["organization_access"]

    if team_data.get("permissions"):
        normalized["permissions"] = team_data["permissions"]

    return normalized


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "team_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            team_data: Optional[Dict[str, Any]] = None

            team_data = get_team(adapter, params["team_id"])

            if not team_data:
                raise ValueError(f"Team with ID {params['team_id']} not found")

            result["team"] = normalize_team_response(team_data)

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
