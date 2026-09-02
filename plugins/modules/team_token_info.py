#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: team_token_info
version_added: "2.2.0"
short_description: Retrieve information about a Terraform Cloud and Terraform Enterprise team token.
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Retrieves read-only information about a team authentication token.
  - Provide O(team_id) to retrieve the team token associated with a team.
  - Provide O(token_id) to retrieve a specific token by its authentication-token ID.
  - This module never creates, updates, or deletes anything; C(changed) is always
    C(false).
  - The raw token secret is never returned by read operations; only metadata such as
    C(id), C(description), C(created_at), and C(expired_at) are available.
  - If the requested token is not found the module fails with a descriptive message.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  team_id:
    description:
      - The unique identifier of the team (e.g. C(team-xxxxxxxx)).
      - Retrieves the team token associated with this team.
      - Mutually exclusive with O(token_id).
    type: str
  token_id:
    description:
      - The unique identifier of an authentication token (e.g. C(at-xxxxxxxx)).
      - Retrieves a specific token by its ID.
      - Mutually exclusive with O(team_id).
    type: str
"""

EXAMPLES = r"""
- name: Retrieve the team token for a team
  hashicorp.terraform.team_token_info:
    team_id: "team-abc123"
  register: token_info

- name: Retrieve a specific token by token ID
  hashicorp.terraform.team_token_info:
    token_id: "at-abc123"
  register: token_info
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
team_token:
  description: A dictionary containing the team token metadata.
  returned: on success
  type: dict
  contains:
    id:
      description: The unique identifier of the token.
      returned: always
      type: str
      sample: "at-abc123"
    description:
      description: The token description (named tokens only).
      returned: when present and non-null
      type: str
      sample: "CI deploy token"
    created_at:
      description: ISO 8601 timestamp when the token was created.
      returned: when present
      type: str
      sample: "2026-05-01T10:00:00.000Z"
    last_used_at:
      description: ISO 8601 timestamp when the token was last used.
      returned: when present and non-null
      type: str
      sample: "2026-05-10T08:30:00.000Z"
    expired_at:
      description: ISO 8601 timestamp when the token expires, if set.
      returned: when present and non-null
      type: str
      sample: "2027-12-31T00:00:00Z"
"""

from copy import deepcopy
from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.team_token import (
    get_team_token,
    get_team_token_by_id,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "team_id": {"type": "str"},
            "token_id": {"type": "str"},
        },
        required_one_of=[("team_id", "token_id")],
        mutually_exclusive=[("team_id", "token_id")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}

    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            if params.get("token_id"):
                token_data = get_team_token_by_id(adapter, params["token_id"])
                if token_data is None:
                    raise ValueError(f"Team token with ID {params['token_id']} not found")
                result["team_token"] = token_data
            else:
                token_data = get_team_token(adapter, params["team_id"])
                if token_data is None:
                    raise ValueError(f"Team token for team {params['team_id']} not found")
                result["team_token"] = token_data

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
