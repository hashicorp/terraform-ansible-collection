# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models.stack_configuration import (
        StackConfigurationCreateOptions,
        StackConfigurationSource,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class StackConfigurationCreateOptions:  # type: ignore[no-redef]
        pass

    class StackConfigurationSource:  # type: ignore[no-redef]
        MANUAL = "manual"
        FETCH = "fetch"
        REUSE = "reuse"


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_stack_configuration(adapter: TerraformClient, stack_configuration_id: str) -> Optional[Dict[str, Any]]:
    """Read a single stack configuration by its ID. Returns None if not found."""
    try:
        stack_configuration = adapter.client.stack_configurations.read(stack_configuration_id=stack_configuration_id)
        return format_response(stack_configuration)
    except NotFound:
        return None


def list_stack_configurations(adapter: TerraformClient, stack_id: str) -> List[Dict[str, Any]]:
    """List all stack configurations for a stack. Returns an empty list if none exist."""
    try:
        configs = adapter.client.stack_configurations.list(stack_id)
        return [format_response(c) for c in configs]
    except NotFound:
        return []


def create_stack_configuration(adapter: TerraformClient, stack_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a stack configuration for the given stack."""
    # Extract source before building create options
    source_value = data.pop("source", None)
    if source_value is None:
        source = StackConfigurationSource.MANUAL
    elif isinstance(source_value, str):
        source = StackConfigurationSource(source_value)
    else:
        source = source_value

    options = StackConfigurationCreateOptions.model_validate(data) if data else None

    response = safe_api_call(
        adapter.client.stack_configurations.create,
        stack_id,
        options,
        source,
        error_context=f"Failed to create stack configuration for stack {stack_id}",
    )
    return format_response(response)
