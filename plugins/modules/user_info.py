#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: user_info
version_added: 2.1.0
short_description: Retrieve information about a user in Terraform Cloud/Enterprise.
author: "Tanya Singh (@tanyasingh)"
description:
  - Retrieves information about a user in Terraform Cloud/Enterprise.
  - Provide O(user_id) to look up a specific user, or set O(current=true) to return
    the currently authenticated user.
  - Fails if the specified user does not exist.
extends_documentation_fragment: hashicorp.terraform.common
options:
  user_id:
    description:
      - The unique identifier of the user to retrieve.
      - Required when O(current) is not set.
      - Mutually exclusive with O(current).
    type: str
  current:
    description:
      - Set to V(true) to retrieve the currently authenticated user.
      - Required when O(user_id) is not provided.
      - Mutually exclusive with O(user_id).
    type: bool
"""

EXAMPLES = r"""
- name: Retrieve information about a user by ID
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

- name: Retrieve the current authenticated user
  hashicorp.terraform.user_info:
    current: true
  register: current_user_info

- name: Proceed only if user can create organizations
  ansible.builtin.debug:
    msg: "User has permission to create organizations"
  when: current_user_info.user.permissions.can_create_organizations
"""

RETURN = r"""
changed:
  description: Always false - this module never modifies state.
  returned: always
  type: bool
  sample: false
user:
  description: A dictionary containing the user information.
  returned: on success
  type: dict
  contains:
    id:
      description: The unique identifier of the user.
      returned: always
      type: str
      sample: "user-XXXXXXXXXXXX"
    username:
      description: The username of the user.
      returned: always
      type: str
      sample: "example-user"
    email:
      description: The email address of the user.
      returned: when available
      type: str
      sample: "user@example.com"
    is_service_account:
      description: Whether this is a service account.
      returned: always
      type: bool
      sample: false
    auth_method:
      description: The authentication method used by the user.
      returned: when available
      type: str
      sample: "hcp_sso"
    avatar_url:
      description: URL to the user's avatar image.
      returned: when available
      type: str
      sample: "https://www.gravatar.com/avatar/..."
    v2_only:
      description: Whether the user only has access to the v2 API.
      returned: always
      type: bool
      sample: true
    unconfirmed_email:
      description: Unconfirmed email address if an email change is pending.
      returned: when available
      type: str
      sample: "newemail@example.com"
    is_site_admin:
      description: Whether the user is a site admin (deprecated).
      returned: when available
      type: bool
      sample: false
    is_admin:
      description: Whether the user is an admin.
      returned: when available
      type: bool
      sample: false
    is_sso_login:
      description: Whether the user uses SSO login.
      returned: when available
      type: bool
      sample: true
    two_factor:
      description: Two-factor authentication status.
      returned: when available
      type: dict
      contains:
        enabled:
          description: Whether two-factor authentication is enabled.
          type: bool
          sample: true
        verified:
          description: Whether two-factor authentication is verified.
          type: bool
          sample: false
    permissions:
      description: User permissions.
      returned: when available
      type: dict
      contains:
        can_create_organizations:
          description: Whether the user can create organizations.
          type: bool
          sample: false
        can_change_email:
          description: Whether the user can change their email.
          type: bool
          sample: true
        can_change_username:
          description: Whether the user can change their username.
          type: bool
          sample: true
        can_manage_user_tokens:
          description: Whether the user can manage user tokens.
          type: bool
          sample: false
        can_view_2fa_settings:
          description: Whether the user can view 2FA settings.
          type: bool
          sample: false
        can_manage_hcp_account:
          description: Whether the user can manage their HCP account.
          type: bool
          sample: false
"""

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.user import (
    get_current_user,
    get_user,
)


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "user_id": {"type": "str"},
            "current": {"type": "bool"},
        },
        supports_check_mode=True,
        required_one_of=[
            ["user_id", "current"],
        ],
        mutually_exclusive=[
            ["user_id", "current"],
        ],
    )

    try:
        with module.client() as adapter:
            if module.params["current"]:
                user_data = get_current_user(adapter)
            else:
                user_data = get_user(adapter, module.params["user_id"])
                if not user_data:
                    raise ValueError(f"User '{module.params['user_id']}' was not found.")

            module.exit_json(changed=False, user=user_data)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
