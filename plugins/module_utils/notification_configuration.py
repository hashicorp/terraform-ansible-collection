# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Helpers for workspace notification configurations."""

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        NotificationConfigurationCreateOptions,
        NotificationConfigurationUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class NotificationConfigurationCreateOptions:  # type: ignore[no-redef]
        pass

    class NotificationConfigurationUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_notification_configurations(adapter: TerraformClient, workspace_id: str) -> List[Dict[str, Any]]:
    """List notification configurations for a workspace."""
    try:
        return [format_response(nc) for nc in adapter.client.notification_configurations.list(workspace_id)]
    except NotFound:
        return []


def get_notification_configuration(adapter: TerraformClient, notification_config_id: str) -> Optional[Dict[str, Any]]:
    """Read a notification configuration by ID."""
    try:
        return format_response(adapter.client.notification_configurations.read(notification_config_id))
    except NotFound:
        return None


def get_notification_configuration_by_name(
    adapter: TerraformClient,
    workspace_id: str,
    name: str,
) -> Optional[Dict[str, Any]]:
    """Look up a notification configuration by name on the given workspace."""
    for nc in list_notification_configurations(adapter, workspace_id):
        if nc.get("name") == name:
            return nc
    return None


def create_notification_configuration(
    adapter: TerraformClient,
    workspace_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a notification configuration on the given workspace."""
    options = NotificationConfigurationCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.notification_configurations.create,
        workspace_id,
        options,
        error_context=f"Failed to create notification {data.get('name')!r} on workspace {workspace_id}",
    )
    return format_response(response)


def update_notification_configuration(
    adapter: TerraformClient,
    notification_config_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Update an existing notification configuration."""
    options = NotificationConfigurationUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.notification_configurations.update,
        notification_config_id,
        options,
        error_context=f"Failed to update notification {notification_config_id}",
    )
    return format_response(response)


def delete_notification_configuration(adapter: TerraformClient, notification_config_id: str) -> None:
    """Delete a notification configuration."""
    safe_api_call(
        adapter.client.notification_configurations.delete,
        notification_config_id,
        error_context=f"Failed to delete notification {notification_config_id}",
    )
