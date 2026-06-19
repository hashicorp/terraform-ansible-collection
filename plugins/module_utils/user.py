# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""User adapter for pytfe SDK integration.

This module provides functions that handle user-specific operations using the
pytfe SDK, including read operations for users and current user details.

Example:
    adapter = TerraformClient(tfe_token="my-token", tfe_address="https://app.terraform.io")
    with adapter:
        user = get_user(adapter, 'user-MA4GL63FmYRpSFxa')
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_user(adapter: TerraformClient, user_id: str) -> Optional[Dict[str, Any]]:
    """Read a user by ID.

    Args:
        adapter: Authenticated TerraformClient.
        user_id: User ID (e.g., 'user-MA4GL63FmYRpSFxa').

    Returns:
        Formatted user dict, or ``None`` if the user does not exist.
    """
    if not user_id:
        raise ValueError("invalid user id")

    try:
        user = adapter.client.users.read(user_id)
        return format_response(user)
    except NotFound:
        return None


def get_current_user(adapter: TerraformClient) -> Dict[str, Any]:
    """Read the currently authenticated user.

    Args:
        adapter: Authenticated TerraformClient.

    Returns:
        Formatted user dict for the current authenticated user.
    """
    user = safe_api_call(
        adapter.client.users.read_current,
        error_context="Failed to read current user",
    )
    return format_response(user)
