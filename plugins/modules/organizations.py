#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: organizations
version_added: "2.0.0"
short_description: Manage Terraform Cloud/Enterprise organizations (create, update, delete).
author: "Prabuddha Chakraborty (@prab-ch)"
description:
  - Manages Terraform Cloud and Terraform Enterprise organizations with create, update, and delete operations.
  - The C(present) state creates a new organization or updates an existing one with the specified parameters.
  - The C(absent) state deletes an existing organization by name.
  - The organization name functions as its identifier in TFC/TFE; there is no separate numeric ID.
  - Compatible with both Terraform Cloud and Terraform Enterprise environments. Some options
    (for example SAML-related settings) only take effect on deployments that license them.
extends_documentation_fragment: hashicorp.terraform.common
options:
  name:
    description:
      - The name of the organization. This value also serves as the organization identifier.
      - Must be unique within the TFC/TFE instance.
    type: str
    required: true
    aliases: ["organization"]
  email:
    description:
      - Admin email address for the organization.
      - Required when creating a new organization. Optional when updating.
    type: str
  collaborator_auth_policy:
    description:
      - Authentication policy for organization collaborators.
    type: str
    choices: ["password", "two_factor_mandatory"]
  cost_estimation_enabled:
    description:
      - Whether cost estimation is enabled for the organization.
    type: bool
  default_execution_mode:
    description:
      - Default execution mode for new workspaces created in this organization.
    type: str
    choices: ["remote", "local", "agent"]
  assessments_enforced:
    description:
      - Whether drift detection (health assessments) is enforced organization-wide.
    type: bool
  session_timeout:
    description:
      - Session expiration (in minutes) for UI sessions. Set to C(0) to use the TFC/TFE default.
    type: int
  session_remember:
    description:
      - Session "remember-me" duration (in minutes). Set to C(0) to use the TFC/TFE default.
    type: int
  owners_team_saml_role_id:
    description:
      - SAML role identifier mapped to the organization owners team.
      - Only meaningful when SAML is enabled on the instance.
    type: str
  saml_enabled:
    description:
      - Whether SAML authentication is enabled for this organization.
    type: bool
  allow_force_delete_workspaces:
    description:
      - Whether workspaces with managed resources can be force-deleted.
    type: bool
  aggregated_commit_status_enabled:
    description:
      - Whether commit statuses are aggregated when multiple workspaces trigger from the same commit.
    type: bool
  send_passing_statuses_for_untriggered_speculative_plans:
    description:
      - Whether to send passing commit statuses for untriggered speculative plans.
    type: bool
  speculative_plan_management_enabled:
    description:
      - Whether speculative plan management is enabled for the organization.
    type: bool
  state:
    description:
      - Desired state of the organization.
      - C(present) creates or updates the organization.
      - C(absent) deletes the organization if it exists.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a new organization
  hashicorp.terraform.organizations:
    name: "my-new-org"
    email: "platform@example.com"
    collaborator_auth_policy: "two_factor_mandatory"
    cost_estimation_enabled: true
    state: present

- name: Idempotent re-run with identical input
  hashicorp.terraform.organizations:
    name: "my-new-org"
    email: "platform@example.com"
    collaborator_auth_policy: "two_factor_mandatory"
    cost_estimation_enabled: true
    state: present

# Re-running with the same inputs yields:
# "changed": false

- name: Update an existing organization's settings
  hashicorp.terraform.organizations:
    name: "my-new-org"
    email: "platform-new@example.com"
    default_execution_mode: "agent"
    allow_force_delete_workspaces: true
    state: present

- name: Delete an organization
  hashicorp.terraform.organizations:
    name: "my-new-org"
    state: absent

# Output after delete:
# "changed": true
# "msg": "Organization my-new-org has been deleted successfully"
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The organization identifier (equal to the organization name).
  returned: when state is present
  type: str
  sample: "my-new-org"
name:
  description: The organization name.
  returned: when state is present
  type: str
  sample: "my-new-org"
email:
  description: The admin email for the organization.
  returned: when state is present
  type: str
  sample: "platform@example.com"
collaborator_auth_policy:
  description: Collaborator authentication policy in effect.
  returned: when state is present
  type: str
  sample: "two_factor_mandatory"
cost_estimation_enabled:
  description: Whether cost estimation is enabled.
  returned: when state is present
  type: bool
  sample: true
default_execution_mode:
  description: Default execution mode for new workspaces.
  returned: when state is present
  type: str
  sample: "remote"
created_at:
  description: Creation timestamp.
  returned: when state is present
  type: str
  sample: "2026-01-15T10:30:00.000Z"
permissions:
  description: Effective permissions for the authenticated user on this organization.
  returned: when state is present
  type: dict
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Organization my-new-org has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.organizations import (
    create_organization,
    delete_organization,
    get_organization,
    update_organization,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff

# Argspec keys that are plumbing, not organization attributes, and must be
# filtered out before diffing / sending to pytfe.
_NON_SDK_KEYS = {"state", "check_mode"}


def _build_desired_state(params: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the SDK-relevant, non-None attributes the user asked for.

    Authentication params (``tfe_*``/``tf_*``) and control flags are stripped;
    ``None`` values are dropped so that unset module params don't register as
    drift against server defaults.
    """
    return {
        key: value
        for key, value in params.items()
        if not key.startswith(("tf_", "tfe_"))
        and key not in _NON_SDK_KEYS
        and value is not None
    }


def _filter_current_state(have: Dict[str, Any], want: Dict[str, Any]) -> Dict[str, Any]:
    """Project the server-reported state down to only the keys the user specified.

    Keeps diff comparisons focused on user-managed fields and avoids spurious
    "drift" from server-populated attributes (timestamps, permissions, etc.).
    """
    return {key: have.get(key) for key in want.keys() if key in have}


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update an organization to match the desired state."""
    name = params["name"]
    want = _build_desired_state(params)
    # The SDK accepts name in both Create and Update options, but the API
    # treats the URL path name as authoritative on update — no need to resend.
    want.pop("name", None)

    current = get_organization(adapter, name)

    if current is None:
        if not want.get("email"):
            raise ValueError("'email' is required when creating a new organization.")
        create_payload = {"name": name, **want}
        if check_mode:
            return {
                "changed": True,
                "msg": f"Organization {name} would be created. Skipped creation due to check mode.",
                **create_payload,
            }
        created = create_organization(adapter, create_payload)
        return {"changed": True, **created}

    have = _filter_current_state(current, want)
    diff = dict_diff(have, want)
    if not diff:
        return {"changed": False, **current}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Organization {name} would be updated with the given options. Skipped update due to check mode.",
            **want,
        }
    updated = update_organization(adapter, name, want)
    return {"changed": True, **updated}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the organization if present; no-op otherwise."""
    name = params["name"]
    current = get_organization(adapter, name)
    if current is None:
        return {"changed": False, "msg": f"Organization {name} is already absent."}

    if check_mode:
        return {"changed": True, "msg": f"Organization {name} would be deleted. Skipped deletion due to check mode."}

    delete_organization(adapter, name)
    return {"changed": True, "msg": f"Organization {name} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "name": {"type": "str", "required": True, "aliases": ["organization"]},
            "email": {"type": "str"},
            "collaborator_auth_policy": {"type": "str", "choices": ["password", "two_factor_mandatory"]},
            "cost_estimation_enabled": {"type": "bool"},
            "default_execution_mode": {"type": "str", "choices": ["remote", "local", "agent"]},
            "assessments_enforced": {"type": "bool"},
            "session_timeout": {"type": "int"},
            "session_remember": {"type": "int"},
            "owners_team_saml_role_id": {"type": "str"},
            "saml_enabled": {"type": "bool"},
            "allow_force_delete_workspaces": {"type": "bool"},
            "aggregated_commit_status_enabled": {"type": "bool"},
            "send_passing_statuses_for_untriggered_speculative_plans": {"type": "bool"},
            "speculative_plan_management_enabled": {"type": "bool"},
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
