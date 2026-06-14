#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.team import (
    get_team,
    list_teams,
)

DOCUMENTATION = r"""
---
module: team_info
version_added: 1.4.0
short_description: Retrieve information about teams in Terraform Cloud/Enterprise.
author: "Terraform Ansible Collection Contributors"
description:
  - Retrieve information about teams from Terraform Cloud/Enterprise.
  - List teams in an organization with optional filtering and searching.
  - Get detailed information about a specific team.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - The name of the Terraform Cloud/Enterprise organization.
      - Required when listing teams without specifying team_id.
    type: str
  team_id:
    description:
      - The unique identifier of a specific team to retrieve.
      - If specified, organization is not required.
    type: str
  page_size:
    description:
      - The number of items per page when listing teams.
      - Defaults to the API's default page size.
    type: int
  query:
    description:
      - Search query string to filter teams by name.
      - Can be used to search for teams matching a partial name.
    type: str
  names:
    description:
      - List of exact team names to filter by.
      - Only teams with names in this list will be returned.
    type: list
    elements: str
  include:
    description:
      - List of relations to include in the response.
      - C(users) - include team members.
      - C(organization-memberships) - include organization memberships.
    type: list
    elements: str
    choices: ["users", "organization-memberships"]
"""

EXAMPLES = r"""
- name: List all teams in an organization
  hashicorp.terraform.team_info:
    organization: "my-org"
  register: teams_info

- name: Get information about a specific team
  hashicorp.terraform.team_info:
    team_id: "team-abc123xyz"
  register: team_info

- name: Search for teams by name
  hashicorp.terraform.team_info:
    organization: "my-org"
    query: "platform"
  register: teams_found

- name: List teams with members included
  hashicorp.terraform.team_info:
    organization: "my-org"
    include:
      - "users"
      - "organization-memberships"
  register: teams_with_members

- name: Filter teams by exact names
  hashicorp.terraform.team_info:
    organization: "my-org"
    names:
      - "platform-team"
      - "admin-team"
  register: filtered_teams
"""

RETURN = r"""
teams:
  description: List of teams.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the team.
      type: str
      sample: "team-abc123xyz"
    name:
      description: The name of the team.
      type: str
      sample: "platform-team"
    visibility:
      description: The visibility of the team (secret or organization).
      type: str
      sample: "secret"
    sso_team_id:
      description: The SAML Group ID for the team.
      type: str
    allow_member_token_management:
      description: Whether team members can manage tokens.
      type: bool
    user_count:
      description: The number of users in the team.
      type: int
    is_unified:
      description: Whether the team is unified.
      type: bool
    organization_access:
      description: Organization access permissions for the team.
      type: dict
    permissions:
      description: Current user's permissions on the team.
      type: dict
    users:
      description: List of users in the team (if include contains 'users').
      type: list
    organization_memberships:
      description: List of organization memberships in the team (if include contains 'organization-memberships').
      type: list
team:
  description: Details of a specific team (when team_id is provided).
  returned: when team_id is specified
  type: dict
  contains:
    id:
      description: The unique identifier of the team.
      type: str
    name:
      description: The name of the team.
      type: str
    visibility:
      description: The visibility of the team.
      type: str
    sso_team_id:
      description: The SAML Group ID for the team.
      type: str
    allow_member_token_management:
      description: Whether team members can manage tokens.
      type: bool
    user_count:
      description: The number of users in the team.
      type: int
    is_unified:
      description: Whether the team is unified.
      type: bool
    organization_access:
      description: Organization access permissions for the team.
      type: dict
    permissions:
      description: Current user's permissions on the team.
      type: dict
    users:
      description: List of users in the team.
      type: list
    organization_memberships:
      description: List of organization memberships in the team.
      type: list
"""


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

    if team_data.get("users"):
        normalized["users"] = team_data["users"]

    if team_data.get("organization_memberships"):
        normalized["organization_memberships"] = team_data["organization_memberships"]

    return normalized


def main():
    module = AnsibleTerraformModule(
        argument_spec={
            "organization": {
                "type": "str",
            },
            "team_id": {
                "type": "str",
            },
            "page_size": {
                "type": "int",
            },
            "query": {
                "type": "str",
            },
            "names": {
                "type": "list",
                "elements": "str",
            },
            "include": {
                "type": "list",
                "elements": "str",
                "choices": ["users", "organization-memberships"],
            },
        },
    )

    try:
        with module.client() as adapter:
            team_id = module.params.get("team_id")
            organization = module.params.get("organization")
            page_size = module.params.get("page_size")
            query = module.params.get("query")
            names = module.params.get("names")
            include = module.params.get("include")

            result = {}

            if team_id:
                # Retrieve a specific team
                team = get_team(adapter, team_id, include=include)
                if team:
                    result["team"] = normalize_team_response(team)
                else:
                    module.fail_json(msg=f"Team with ID {team_id} not found")
            else:
                # List teams in organization
                if not organization:
                    module.fail_json(msg="organization is required when team_id is not specified")

                teams = list_teams(
                    adapter,
                    organization=organization,
                    page_size=page_size,
                    query=query,
                    names=names,
                    include=include,
                )

                result["teams"] = [normalize_team_response(team) for team in teams]

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
