#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: organization_token
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise organization tokens.
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Manages organization-scoped authentication tokens on Terraform Cloud and Terraform Enterprise.
  - An organization token is used for organization-level API access.
  - The C(present) state creates the token if absent; if the token already exists it is kept
    unchanged (C(changed=false)).
  - The C(absent) state deletes the token if it exists.
  - Note - the raw token value is only returned by the API immediately after creation; subsequent
    reads do not include it.
  - Note - C(expired_at) is used only when creating a new token.  If a token already exists,
    changing C(expired_at) alone will I(not) modify or rotate the token.
  - When C(token_type=audit-trails) is set, all operations (read, create, delete) target the
    Audit Trails token and never affect the default organization token.
  - Default organization tokens are supported on both HCP Terraform and Terraform Enterprise.
  - C(token_type=audit-trails) (Audit Trails tokens) is supported on HCP Terraform only and
    is not available on Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - The name of the organization that owns the token.
      - Required for all operations.
    type: str
    required: true
  expired_at:
    description:
      - ISO 8601 expiration datetime for the token (e.g. C(2027-01-01T00:00:00Z)).
      - Only applied when creating a new token (C(state=present) and the token is absent).
      - Changing this value on an existing token has no effect.
      - Available in TFE release v202305-1 and later.
    type: str
  token_type:
    description:
      - The type of token to manage.
      - C(audit-trails) targets the Audit Trails token; omit (or leave C(null)) for the default
        organization token.
      - All operations (read, create, delete) respect this setting and never cross-operate
        between the default token and the Audit Trails token.
      - Only applicable to HCP Terraform.
    type: str
    choices: ["audit-trails"]
  state:
    description:
      - Desired state of the organization token.
      - C(present) creates or keeps the token; C(absent) deletes it.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create an organization token
  hashicorp.terraform.organization_token:
    organization: "my-org"
    state: present
  register: org_token
  no_log: true

- name: Idempotent re-run - token already exists, no change
  hashicorp.terraform.organization_token:
    organization: "my-org"
    state: present
# "changed": false

- name: Create a token with an expiry date
  hashicorp.terraform.organization_token:
    organization: "my-org"
    expired_at: "2027-01-01T00:00:00Z"
    state: present
  no_log: true

- name: Create the Audit Trails token (HCP Terraform only)
  hashicorp.terraform.organization_token:
    organization: "my-org"
    token_type: "audit-trails"
    state: present
  no_log: true

- name: Delete the organization token
  hashicorp.terraform.organization_token:
    organization: "my-org"
    state: absent

- name: Delete the Audit Trails token
  hashicorp.terraform.organization_token:
    organization: "my-org"
    token_type: "audit-trails"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The token identifier.
  returned: when state is present and a token exists or was created
  type: str
  sample: "at-example123"
created_at:
  description: ISO 8601 timestamp when the token was created.
  returned: when state is present and a token exists or was created
  type: str
  sample: "2024-01-15T12:00:00+00:00"
description:
  description: Human-readable description of the token.
  returned: when state is present and a token exists or was created
  type: str
  sample: ""
expired_at:
  description: ISO 8601 expiration timestamp, if set.
  returned: when state is present and a token has an expiry
  type: str
  sample: "2027-01-01T00:00:00+00:00"
token:
  description: >
    The raw token value. Only present in the response immediately after creation;
    subsequent reads from the API do not include this field.
  returned: when a token is created
  type: str
  sample: "example-token-value"
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Organization token for 'my-org' has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.organization_token import (
    create_organization_token,
    delete_organization_token,
    delete_organization_token_with_type,
    get_organization_token,
    get_organization_token_with_type,
)


def _fetch_organization_token(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Read the organization token that matches the requested token_type.

    Routes to ``read_with_options`` for ``token_type="audit-trails"`` and to
    plain ``read`` for the default organization token so the two token types
    are never confused.
    """
    organization = params["organization"]
    token_type = params.get("token_type")
    if token_type:
        return get_organization_token_with_type(adapter, organization, token_type)
    return get_organization_token(adapter, organization)


def _build_create_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build the creation payload from user-supplied (non-None) params."""
    data: Dict[str, Any] = {}
    if params.get("expired_at") is not None:
        data["expired_at"] = params["expired_at"]
    if params.get("token_type") is not None:
        data["token_type"] = params["token_type"]
    return data


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create the organization token if absent; skip if present (idempotent)."""
    organization = params["organization"]
    current = _fetch_organization_token(adapter, params)

    if current is not None:
        # Token exists — idempotent no-op.
        return {"changed": False, **current}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Organization token for {organization!r} would be created. Skipped due to check mode.",
        }

    created = create_organization_token(adapter, organization, _build_create_data(params))
    return {"changed": True, **created}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the organization token if present; no-op otherwise."""
    organization = params["organization"]
    token_type = params.get("token_type")
    current = _fetch_organization_token(adapter, params)

    if current is None:
        return {"changed": False, "msg": f"Organization token for {organization!r} is already absent."}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Organization token for {organization!r} would be deleted. Skipped due to check mode.",
        }

    if token_type:
        delete_organization_token_with_type(adapter, organization, token_type)
    else:
        delete_organization_token(adapter, organization)
    return {"changed": True, "msg": f"Organization token for {organization!r} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "organization": {"type": "str", "required": True},
            "expired_at": {"type": "str"},
            "token_type": {"type": "str", "choices": ["audit-trails"]},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    action_result: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

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
