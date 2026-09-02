# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        NoCodeModuleCreateOptions,
        NoCodeModuleUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class NoCodeModuleCreateOptions:  # type: ignore[no-redef]
        pass

    class NoCodeModuleUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_no_code_module(adapter: TerraformClient, no_code_module_id: str) -> Optional[Dict[str, Any]]:
    """Read a no-code module by ID. Returns None if not found."""
    try:
        module = adapter.client.no_code_modules.read(no_code_module_id)
        return format_response(module)
    except NotFound:
        return None


def create_no_code_module(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Enable no-code provisioning on a registry module."""
    options = NoCodeModuleCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.no_code_modules.create,
        organization,
        options,
        error_context=(f"Failed to create no-code module for registry module {data.get('registry_module_id')!r}" f" in organization {organization}"),
    )
    return format_response(response)


def update_no_code_module(adapter: TerraformClient, no_code_module_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update no-code provisioning settings."""
    options = NoCodeModuleUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.no_code_modules.update,
        no_code_module_id,
        options,
        error_context=f"Failed to update no-code module {no_code_module_id!r}",
    )
    return format_response(response)


def delete_no_code_module(adapter: TerraformClient, no_code_module_id: str) -> None:
    """Disable no-code provisioning for a registry module."""
    safe_api_call(
        adapter.client.no_code_modules.delete,
        no_code_module_id,
        error_context=f"Failed to delete no-code module {no_code_module_id!r}",
    )
