#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: team
version_added: 2.1.0
short_description: Manage teams in Terraform Cloud/Enterprise.
author: "Tanya Singh (@tanyasingh)"
description:
  - Create, update, and delete teams in Terraform Cloud/Enterprise.
  - Configure organization access permissions and team visibility.
  - Supports SSO team ID and member token management settings.
  - When O(state=present) with O(organization) and O(name), the module looks up
    the team by name first and updates it if it exists, making the create operation
    idempotent without needing to know the team ID in advance.
extends_documentation_fragment: hashicorp.terraform.common
options:
  state:
    description:
      - The desired state of the team.
      - V(present) - creates or updates a team.
      - V(absent) - deletes a team.
    type: str
    choices: ["present", "absent"]
    default: present
  organization:
    description:
      - The name of the organization that owns the team.
      - Required when O(team_id) is not provided.
      - Mutually exclusive with O(team_id).
      - Must be supplied together with O(name).
    type: str
  team_id:
    description:
      - The unique identifier of the team.
      - Required when updating or deleting an existing team by ID.
      - Required when O(state=absent).
      - Mutually exclusive with O(organization).
    type: str
  name:
    description:
      - The name of the team.
      - Must be between 1 and 90 characters.
      - Required together with O(organization) when O(team_id) is not provided.
      - When supplied with O(organization) and the team already exists, the module
        updates it instead of creating a duplicate.
    type: str
  visibility:
    description:
      - The visibility of the team.
      - V(secret) - only visible to organization members with appropriate permissions.
      - V(organization) - visible to all organization members.
    type: str
    choices: ["secret", "organization"]
  sso_team_id:
    description:
      - The SAML Group ID that controls membership via SAML.
    type: str
  allow_member_token_management:
    description:
      - Whether team members can manage their own tokens.
    type: bool
  organization_access:
    description:
      - Organization access permissions for the team.
      - Each permission can be set to true or false.
    type: dict
    suboptions:
      manage_policies:
        description: Can manage policies.
        type: bool
      manage_policy_overrides:
        description: Can manage policy overrides.
        type: bool
      manage_workspaces:
        description: Can manage workspaces.
        type: bool
      manage_vcs_settings:
        description: Can manage VCS settings.
        type: bool
      manage_providers:
        description: Can manage providers.
        type: bool
      manage_modules:
        description: Can manage modules.
        type: bool
      manage_run_tasks:
        description: Can manage run tasks.
        type: bool
      manage_projects:
        description: Can manage projects.
        type: bool
      read_workspaces:
        description: Can read workspaces.
        type: bool
      read_projects:
        description: Can read projects.
        type: bool
      manage_membership:
        description: Can manage team membership.
        type: bool
      manage_teams:
        description: Can manage teams.
        type: bool
      manage_organization_access:
        description: Can manage organization access.
        type: bool
      access_secret_teams:
        description: Can access secret teams.
        type: bool
      manage_agent_pools:
        description: Can manage agent pools.
        type: bool
"""

EXAMPLES = r"""
- name: Create a new team (idempotent - updates if team name already exists)
  hashicorp.terraform.team:
    name: "platform-team"
    organization: "my-org"
    visibility: "organization"
    allow_member_token_management: true
    organization_access:
      manage_workspaces: true
      read_projects: true
    state: present

- name: Create a secret team with SSO
  hashicorp.terraform.team:
    name: "admin-team"
    organization: "my-org"
    visibility: "secret"
    sso_team_id: "team-123-sso"
    organization_access:
      manage_teams: true
      manage_policies: true
    state: present

- name: Update team settings by team ID
  hashicorp.terraform.team:
    team_id: "team-abc123xyz"
    name: "platform-team-updated"
    allow_member_token_management: false
    organization_access:
      manage_workspaces: true
      manage_projects: true
    state: present

- name: Delete a team
  hashicorp.terraform.team:
    team_id: "team-abc123xyz"
    state: absent
"""

RETURN = r"""
id:
  description: The unique identifier of the team.
  returned: when state is present and team exists
  type: str
  sample: "team-abc123xyz"
name:
  description: The name of the team.
  returned: when state is present and team exists
  type: str
  sample: "platform-team"
visibility:
  description: The visibility of the team.
  returned: when state is present and team exists
  type: str
  sample: "secret"
sso_team_id:
  description: The SAML Group ID for the team.
  returned: when state is present and team exists
  type: str
  sample: "team-123-sso"
allow_member_token_management:
  description: Whether team members can manage tokens.
  returned: when state is present and team exists
  type: bool
  sample: true
user_count:
  description: The number of users in the team.
  returned: when state is present and team exists
  type: int
  sample: 5
is_unified:
  description: Whether the team is a unified team.
  returned: when state is present and team exists
  type: bool
  sample: false
organization_access:
  description: The organization access permissions for the team.
  returned: when state is present and team exists
  type: dict
  sample: {"manage_workspaces": true, "read_projects": true}
permissions:
  description: The current user's permissions for the team.
  returned: when state is present and team exists
  type: dict
  contains:
    can_destroy:
      description: Whether the user can destroy the team.
      type: bool
    can_update_membership:
      description: Whether the user can update team membership.
      type: bool
changed:
  description: Whether the team was changed.
  returned: always
  type: bool
  sample: true
msg:
  description: Status message of the operation.
  returned: always
  type: str
  sample: "Team 'platform-team' created successfully."
"""

from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.team import (
    create_team,
    delete_team,
    get_team,
    get_team_by_name,
    normalize_team_response,
    update_team,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import (
    dict_diff,
)


def extract_comparable_attributes(team_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return the subset of team attributes used for idempotency comparison."""
    comparable = {
        "name": team_data.get("name"),
        "visibility": team_data.get("visibility"),
        "sso_team_id": team_data.get("sso_team_id"),
        "allow_member_token_management": team_data.get("allow_member_token_management"),
    }

    if team_data.get("organization_access"):
        comparable["organization_access"] = team_data.get("organization_access")

    return {k: v for k, v in comparable.items() if v is not None}


def state_create(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create a new team in the specified organization."""
    action_result = {}

    organization = params.get("organization")
    name = params.get("name")

    # Validate required parameters
    if not organization or not name:
        raise ValueError("Both 'organization' and 'name' are required when creating a team")
    if len(name) < 1 or len(name) > 90:
        raise ValueError("Team name must be between 1 and 90 characters")

    visibility = params.get("visibility")
    sso_team_id = params.get("sso_team_id")
    allow_member_token_management = params.get("allow_member_token_management")
    organization_access = params.get("organization_access")

    if not check_mode:
        team = create_team(
            adapter,
            organization=organization,
            name=name,
            visibility=visibility,
            sso_team_id=sso_team_id,
            organization_access=organization_access,
            allow_member_token_management=allow_member_token_management,
        )
        action_result.update(
            {
                "changed": True,
                "msg": f"Team '{name}' created successfully.",
                **normalize_team_response(team),
            }
        )
    else:
        action_result.update(
            {
                "changed": True,
                "msg": f"Team '{name}' would be created. Skipped due to check mode.",
                "name": name,
                "visibility": visibility,
            }
        )

    return action_result


def state_update(
    adapter: TerraformClient,
    params: Dict[str, Any],
    current_team: Dict[str, Any],
    check_mode: bool = False,
) -> Dict[str, Any]:
    """Update an existing team, skipping the API call when nothing has changed."""
    action_result = {}

    if not current_team:
        raise ValueError(f"Team '{params.get('team_id')}' was not found")

    team_id = params["team_id"]

    have = extract_comparable_attributes(current_team)
    want = {}

    if params.get("name") is not None:
        name = params["name"]
        if len(name) < 1 or len(name) > 90:
            raise ValueError("Team name must be between 1 and 90 characters")
        want["name"] = name
    if params.get("visibility") is not None:
        want["visibility"] = params["visibility"]
    if params.get("sso_team_id") is not None:
        want["sso_team_id"] = params["sso_team_id"]
    if params.get("allow_member_token_management") is not None:
        want["allow_member_token_management"] = params["allow_member_token_management"]
    if params.get("organization_access") is not None:
        want["organization_access"] = params["organization_access"]

    # Filter have to only keys in want
    have = {k: v for k, v in have.items() if k in want}

    updates_response = dict_diff(have, want)

    if not updates_response:
        action_result.update(
            {
                "changed": False,
                "msg": "Team already has the desired state.",
                **normalize_team_response(current_team),
            }
        )
        return action_result

    if not check_mode:
        updated_team = update_team(
            adapter,
            team_id=team_id,
            name=want.get("name"),
            visibility=want.get("visibility"),
            sso_team_id=want.get("sso_team_id"),
            organization_access=want.get("organization_access"),
            allow_member_token_management=want.get("allow_member_token_management"),
        )
        action_result.update(
            {
                "changed": True,
                "msg": f"Team '{team_id}' updated successfully.",
                **normalize_team_response(updated_team),
            }
        )
    else:
        action_result.update(
            {
                "changed": True,
                "msg": f"Team '{team_id}' would be updated with changes: {updates_response}. Skipped due to check mode.",
                **normalize_team_response(current_team),
            }
        )

    return action_result


def state_absent(
    adapter: TerraformClient,
    params: Dict[str, Any],
    current_team: Dict[str, Any],
    check_mode: bool = False,
) -> Dict[str, Any]:
    """Delete a team. No-op (changed=False) if the team does not exist."""
    action_result = {}

    if not current_team:
        action_result.update(
            {
                "changed": False,
                "msg": f"Team {params.get('team_id')} was not found.",
            }
        )
        return action_result

    team_id = params["team_id"]

    if not check_mode:
        delete_team(adapter, team_id)
        action_result.update(
            {
                "changed": True,
                "msg": f"Team '{team_id}' deleted successfully.",
            }
        )
    else:
        action_result.update(
            {
                "changed": True,
                "msg": f"Team '{team_id}' would be deleted. Skipped due to check mode.",
            }
        )

    return action_result


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "state": {"type": "str", "choices": ["present", "absent"], "default": "present"},
            "organization": {"type": "str"},
            "team_id": {"type": "str"},
            "name": {"type": "str"},
            "visibility": {"type": "str", "choices": ["secret", "organization"]},
            "sso_team_id": {"type": "str"},
            "allow_member_token_management": {"type": "bool"},
            "organization_access": {"type": "dict"},
        },
        mutually_exclusive=[
            ["team_id", "organization"],
        ],
        required_one_of=[
            ["team_id", "organization"],
        ],
        required_together=[
            ["organization", "name"],
        ],
        required_if=[
            ("state", "absent", ["team_id"]),
        ],
        supports_check_mode=True,
    )
    warnings = []

    state = module.params["state"]
    check_mode = module.check_mode

    try:
        with module.client() as adapter:
            result = {"changed": False, "warnings": warnings}

            if state == "present":
                if module.params.get("team_id"):
                    current_team = get_team(adapter, module.params["team_id"])
                    result = state_update(adapter, module.params, current_team, check_mode)

                else:
                    organization = module.params["organization"]
                    name = module.params.get("name")
                    current_team = get_team_by_name(adapter, organization, name) if name else None
                    if current_team:
                        params = dict(module.params)
                        params["team_id"] = current_team["id"]
                        result = state_update(adapter, params, current_team, check_mode)
                    else:
                        result = state_create(adapter, module.params, check_mode)

            elif state == "absent":
                current_team = get_team(adapter, module.params["team_id"])

                result = state_absent(adapter, module.params, current_team, check_mode)

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
