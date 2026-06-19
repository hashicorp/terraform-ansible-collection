# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: user_info
version_added: 2.1.0
short_description: Gather information about a user in Terraform Enterprise/Cloud.
author: "Tanya Singh (@tanyasingh)"
description:
  - This module retrieves information about a given user in Terraform Enterprise/Cloud.
  - It can be used to check if a user exists or to gather detailed information about them.
  - If I(user_id) is provided, the module will return information about that specific user.
  - If I(current) is set to true, the module will return information about the currently authenticated user.
  - If the user does not exist, the module will fail with an error message.
extends_documentation_fragment: hashicorp.terraform.common
options:
  user_id:
    description:
      - The unique identifier of the user to retrieve information about.
      - Either I(user_id) or I(current) must be specified.
    type: str
  current:
    description:
      - Set to true to retrieve information about the currently authenticated user.
      - Either I(user_id) or I(current) must be specified.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Gather information about a user by ID
  hashicorp.terraform.user_info:
    user_id: "user-XXXXXXXXXXXX"
  register: user_info

# Task output:
# ------------
# "user_info": {
#     "changed": false,
#     "failed": false,
#     "user": {
#         "id": "user-XXXXXXXXXXXX",
#         "username": "example-user",
#         "email": "user@example.com",
#         "is_service_account": false,
#         "auth_method": "hcp_sso",
#         "avatar_url": "https://www.gravatar.com/avatar/...",
#         "v2_only": true,
#         "permissions": {
#             "can_create_organizations": false,
#             "can_change_email": true,
#             "can_change_username": true
#         }
#     }
# }

- name: Gather information about the current authenticated user
  hashicorp.terraform.user_info:
    current: true
  register: current_user_info

# Task output:
# ------------
# "current_user_info": {
#     "changed": false,
#     "failed": false,
#     "user": {
#         "id": "user-XXXXXXXXXXXX",
#         "username": "example-user",
#         "email": "user@example.com",
#         "is_service_account": false,
#         "auth_method": "hcp_sso",
#         "avatar_url": "https://www.gravatar.com/avatar/...",
#         "v2_only": true,
#         "permissions": {
#             "can_create_organizations": false,
#             "can_change_email": true,
#             "can_change_username": true
#         }
#     }
# }

- name: Handle case when user does not exist by ID
  hashicorp.terraform.user_info:
    user_id: "user-invalid-user-id"
  register: user_info
  ignore_errors: true

# Task output:
# ------------
# FAILED! => {
#     "changed": false,
#     "failed": true,
#     "msg": "User 'user-invalid-user-id' was not found."
# }

- name: Use user information in subsequent tasks
  hashicorp.terraform.user_info:
    user_id: "user-XXXXXXXXXXXX"
  register: user_info

- name: Display user details
  ansible.builtin.debug:
    msg: |
      User Details:
      - ID: {{ user_info.user.id }}
      - Username: {{ user_info.user.username }}
      - Email: {{ user_info.user.email }}
      - Service Account: {{ user_info.user.is_service_account }}
      - Auth Method: {{ user_info.user.auth_method }}
      - Can Create Organizations: {{ user_info.user.permissions.can_create_organizations }}

- name: Check current user permissions
  hashicorp.terraform.user_info:
    current: true
  register: current_user

- name: Proceed only if user can create organizations
  ansible.builtin.debug:
    msg: "User has permission to create organizations"
  when: current_user.user.permissions.can_create_organizations
"""

RETURN = r"""
user:
  type: dict
  description: A dictionary containing the user information.
  returned: on success
  contains:
    id:
      type: str
      returned: always
      description: The unique identifier of the user.
      sample: "user-XXXXXXXXXXXX"
    username:
      type: str
      returned: always
      description: The username of the user.
      sample: "example-user"
    email:
      type: str
      returned: when available
      description: The email address of the user.
      sample: "user@example.com"
    is_service_account:
      type: bool
      returned: always
      description: Whether this is a service account.
      sample: false
    auth_method:
      type: str
      returned: when available
      description: The authentication method used by the user.
      sample: "hcp_sso"
    avatar_url:
      type: str
      returned: when available
      description: URL to the user's avatar image.
      sample: "https://www.gravatar.com/avatar/..."
    v2_only:
      type: bool
      returned: always
      description: Whether the user only has access to v2 API.
      sample: true
    unconfirmed_email:
      type: str
      returned: when available
      description: Unconfirmed email address if email change is pending.
      sample: "newemail@example.com"
    is_site_admin:
      type: bool
      returned: when available
      description: Whether the user is a site admin (deprecated).
      sample: false
    is_admin:
      type: bool
      returned: when available
      description: Whether the user is an admin.
      sample: false
    is_sso_login:
      type: bool
      returned: when available
      description: Whether the user uses SSO login.
      sample: true
    two_factor:
      type: dict
      returned: when available
      description: Two-factor authentication status.
      contains:
        enabled:
          type: bool
          description: Whether two-factor authentication is enabled.
          sample: true
        verified:
          type: bool
          description: Whether two-factor authentication is verified.
          sample: false
    permissions:
      type: dict
      returned: when available
      description: User permissions.
      contains:
        can_create_organizations:
          type: bool
          description: Whether the user can create organizations.
          sample: false
        can_change_email:
          type: bool
          description: Whether the user can change their email.
          sample: true
        can_change_username:
          type: bool
          description: Whether the user can change their username.
          sample: true
        can_manage_user_tokens:
          type: bool
          description: Whether the user can manage user tokens.
          sample: false
        can_view_2fa_settings:
          type: bool
          description: Whether the user can view 2FA settings.
          sample: false
        can_manage_hcp_account:
          type: bool
          description: Whether the user can manage HCP account.
          sample: false
"""


from copy import deepcopy
from typing import TYPE_CHECKING

from ansible.module_utils._text import to_text

if TYPE_CHECKING:
    from typing import Any, Dict, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.user import (
    get_current_user,
    get_user,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "user_id": {"type": "str"},
            "current": {"type": "bool", "default": False},
        },
        supports_check_mode=True,
        required_one_of=[
            ["user_id", "current"],
        ],
        mutually_exclusive=[
            ["user_id", "current"],
        ],
    )

    warnings: list[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            user_data: Optional[Dict[str, Any]] = None

            if params["current"]:
                # Retrieve current authenticated user
                user_data = get_current_user(adapter)
            elif params["user_id"]:
                # Retrieve user by ID
                user_data = get_user(adapter, params["user_id"])
                if not user_data:
                    raise ValueError(f"User '{params['user_id']}' was not found.")

            # Update result with user information
            result["user"] = user_data

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
