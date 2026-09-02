#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: team_token
version_added: "2.2.0"
short_description: Manage Terraform Cloud and Terraform Enterprise team tokens.
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Manages team authentication tokens on Terraform Cloud and Terraform Enterprise.
  - C(state=present) with O(team_id) ensures a team token exists for the given team.
    If a token already exists, the module returns C(changed=false) without regenerating
    it. O(expired_at) is applied only when creating a new token; it does not update an
    existing token.
  - C(state=present) with O(description) creates a new named team token on every
    invocation. Named-token lookup is outside the scope of this module, so repeated
    runs with O(description) are not idempotent.
  - C(state=absent) deletes a token. Supply O(team_id) to delete the team token
    associated with that team, or O(token_id) to delete a specific named token.
  - The raw token secret (C(token)) is returned only at creation time.
    Store it immediately; subsequent read operations do not return it.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  team_id:
    description:
      - The unique identifier of the team (e.g. C(team-xxxxxxxx)).
      - Required for C(state=present).
      - When used with C(state=absent), deletes the team token associated with
        this team.
      - Mutually exclusive with O(token_id).
    type: str
  token_id:
    description:
      - The unique identifier of a specific authentication token
        (e.g. C(at-xxxxxxxx)).
      - Used with C(state=absent) to delete a specific named token by its ID.
      - Mutually exclusive with O(team_id).
      - Not valid for C(state=present).
    type: str
  description:
    description:
      - Human-readable description for the token.
      - When supplied, creates a new named team token.
      - Named-token lookup is outside the scope of this module; each invocation
        with O(description) creates a new token and is not idempotent.
      - Only valid for C(state=present).
    type: str
  expired_at:
    description:
      - ISO 8601 datetime string after which the token expires
        (e.g. C(2027-12-31T00:00:00Z)).
      - Applied only when creating a new token. If a team token already exists,
        the module returns C(changed=false) and does not update the expiry.
      - Only valid for C(state=present).
    type: str
  state:
    description:
      - Desired state of the team token.
      - C(present) ensures a team token exists, or creates a named team token
        when O(description) is supplied.
      - C(absent) ensures the specified team token is absent.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Ensure a team token exists (idempotent - will not regenerate if one already exists)
  hashicorp.terraform.team_token:
    team_id: "team-abc123"
    state: present
  register: result
  no_log: true

- name: Ensure a team token exists with an expiry date
  hashicorp.terraform.team_token:
    team_id: "team-abc123"
    expired_at: "2027-12-31T00:00:00Z"
    state: present
  register: result
  no_log: true

- name: Create a named team token (not idempotent - creates a new token on each run)
  hashicorp.terraform.team_token:
    team_id: "team-abc123"
    description: "CI deploy token"
    expired_at: "2027-12-31T00:00:00Z"
    state: present
  register: named_token
  no_log: true

- name: Delete the team token for a team
  hashicorp.terraform.team_token:
    team_id: "team-abc123"
    state: absent

- name: Delete a specific named token by token ID
  hashicorp.terraform.team_token:
    token_id: "at-abc123"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The authentication token identifier.
  returned: when state is present and a token exists or was created
  type: str
  sample: "at-abc123"
token:
  description: >
    The raw authentication token secret. Available only at creation time;
    not returned by subsequent runs. Mark tasks that use this value with
    C(no_log=true).
  returned: when a new token was just created
  type: str
  sample: "<sensitive>"
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
expired_at:
  description: ISO 8601 timestamp when the token expires, if set.
  returned: when present and non-null
  type: str
  sample: "2027-12-31T00:00:00Z"
last_used_at:
  description: ISO 8601 timestamp when the token was last used.
  returned: when present and non-null
  type: str
  sample: "2026-05-10T08:30:00.000Z"
msg:
  description: Informational message for delete, no-op, and check-mode operations.
  returned: when relevant
  type: str
  sample: "Team token at-abc123 has been deleted successfully."
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.team_token import (
    create_team_token,
    delete_team_token,
    delete_team_token_by_id,
    get_team_token,
    get_team_token_by_id,
)


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create a team token.

    Named-token flow (non-empty description):
        A new named token is created on every invocation.  Named-token lookup is
        outside the scope of this module, so this path is intentionally not idempotent.

    Team-token flow (no description; expired_at optional):
        Reads the existing team token first.
        - existing: changed=False (expired_at is not updated on an existing token)
        - absent + check_mode: changed=True, no mutation
        - absent: create, changed=True
    """
    team_id = params.get("team_id")
    description = params.get("description") or None  # normalise "" to None
    expired_at = params.get("expired_at")

    if not team_id:
        raise ValueError("'team_id' is required when creating a team token.")

    if description:
        # Named-token flow: creates a new named token on every invocation.
        if check_mode:
            return {
                "changed": True,
                "msg": f"Named team token would be created for team {team_id}. Skipped creation due to check mode.",
            }
        data: Dict[str, Any] = {"description": description}
        if expired_at:
            data["expired_at"] = expired_at
        created = create_team_token(adapter, team_id, data)
        return {"changed": True, **created}

    # Team-token flow (no description). Read before create to preserve idempotency.
    current = get_team_token(adapter, team_id)
    if current is not None:
        return {"changed": False, **current}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Team token would be created for team {team_id}. Skipped creation due to check mode.",
        }
    data = {}
    if expired_at:
        data["expired_at"] = expired_at
    created = create_team_token(adapter, team_id, data)
    return {"changed": True, **created}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete a team token if present; no-op otherwise."""
    team_id = params.get("team_id")
    token_id = params.get("token_id")

    if token_id:
        # Read before delete so check-mode and idempotency are both deterministic.
        existing = get_team_token_by_id(adapter, token_id)
        if existing is None:
            return {"changed": False, "msg": f"Team token {token_id} is already absent."}
        if check_mode:
            return {
                "changed": True,
                "msg": f"Team token {token_id} would be deleted. Skipped deletion due to check mode.",
            }
        delete_team_token_by_id(adapter, token_id)
        return {"changed": True, "msg": f"Team token {token_id} has been deleted successfully."}

    if not team_id:
        raise ValueError("'team_id' or 'token_id' is required when deleting a team token.")

    # Read before delete for idempotency.
    current = get_team_token(adapter, team_id)
    if current is None:
        return {"changed": False, "msg": f"Team token for team {team_id} is already absent."}

    found_token_id = current.get("id", team_id)
    if check_mode:
        return {
            "changed": True,
            "msg": f"Team token {found_token_id} would be deleted. Skipped deletion due to check mode.",
        }
    delete_team_token(adapter, team_id)
    return {"changed": True, "msg": f"Team token {found_token_id} has been deleted successfully."}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "team_id": {"type": "str"},
            "token_id": {"type": "str"},
            "description": {"type": "str"},
            "expired_at": {"type": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_if=[
            ("state", "present", ("team_id",)),
        ],
        mutually_exclusive=[("team_id", "token_id")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    action_result: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    # description and expired_at are only meaningful for state=present.
    if params["state"] == "absent":
        for opt in ("description", "expired_at"):
            if params.get(opt) is not None:
                module.fail_json(msg=f"'{opt}' is not valid for state=absent.")

    try:
        with module.client() as adapter:
            match params["state"]:
                case "present":
                    action_result = state_present(adapter, params, params["check_mode"])
                case "absent":
                    action_result = state_absent(adapter, params, params["check_mode"])

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
