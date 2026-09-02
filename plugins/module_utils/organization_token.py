# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        OrganizationTokenCreateOptions,
        OrganizationTokenDeleteOptions,
        OrganizationTokenReadOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class OrganizationTokenCreateOptions:  # type: ignore[no-redef]
        pass

    class OrganizationTokenDeleteOptions:  # type: ignore[no-redef]
        pass

    class OrganizationTokenReadOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_organization_token(adapter: TerraformClient, organization: str) -> Optional[Dict[str, Any]]:
    """Read the default organization token. Returns None if not found."""
    try:
        token = adapter.client.organization_tokens.read(organization)
        return format_response(token)
    except NotFound:
        return None


def get_organization_token_with_type(adapter: TerraformClient, organization: str, token_type: str) -> Optional[Dict[str, Any]]:
    """Read an organization token by token_type (e.g. ``"audit-trails"``). Returns None if not found."""
    try:
        options = OrganizationTokenReadOptions.model_validate({"token_type": token_type})
        token = adapter.client.organization_tokens.read_with_options(organization, options)
        return format_response(token)
    except NotFound:
        return None


def create_organization_token(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create (or replace) an organization token.

    *data* may contain ``expired_at`` and/or ``token_type``.  Both keys are
    passed directly to :class:`OrganizationTokenCreateOptions` via
    ``model_validate``; pytfe accepts the string value ``"audit-trails"`` and
    coerces it to ``TokenType.AUDIT_TRAILS``.
    """
    options = OrganizationTokenCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.organization_tokens.create_with_options,
        organization,
        options,
        error_context=f"Failed to create organization token for organization {organization!r}",
    )
    return format_response(response)


def delete_organization_token(adapter: TerraformClient, organization: str) -> None:
    """Delete the default organization token."""
    safe_api_call(
        adapter.client.organization_tokens.delete,
        organization,
        error_context=f"Failed to delete organization token for organization {organization!r}",
    )


def delete_organization_token_with_type(adapter: TerraformClient, organization: str, token_type: str) -> None:
    """Delete an organization token by token_type (e.g. ``"audit-trails"``)."""
    options = OrganizationTokenDeleteOptions.model_validate({"token_type": token_type})
    safe_api_call(
        adapter.client.organization_tokens.delete_with_options,
        organization,
        options,
        error_context=f"Failed to delete {token_type!r} organization token for organization {organization!r}",
    )
