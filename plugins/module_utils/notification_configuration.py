# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Helpers for workspace notification configurations.

Notes on pytfe compatibility:
- ``NotificationConfiguration`` (response object) is a plain class in all current
  pytfe releases — it has no ``model_dump``. A dedicated ``_notification_to_dict``
  serializer is used instead of the generic ``format_response``.
- ``NotificationConfigurationCreateOptions`` / ``UpdateOptions`` are pydantic on
  ``pytfe`` main but plain classes in earlier releases. Building them by direct
  keyword instantiation works in both cases.
"""

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


# The models live on the submodule reliably across pytfe versions; some
# older releases don't re-export them from ``pytfe.models``.
try:
    from pytfe.models.notification_configuration import (
        NotificationConfigurationCreateOptions,
        NotificationConfigurationUpdateOptions,
        NotificationDestinationType,
        NotificationTriggerType,
    )
except ImportError:

    class NotificationConfigurationCreateOptions:  # type: ignore[no-redef]
        pass

    class NotificationConfigurationUpdateOptions:  # type: ignore[no-redef]
        pass

    class NotificationDestinationType:  # type: ignore[no-redef]
        pass

    class NotificationTriggerType:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import safe_api_call


def _enum_value(member: Any) -> Any:
    """Return ``member.value`` for Enum members, otherwise the member itself."""
    return member.value if hasattr(member, "value") else member


def _notification_to_dict(nc: Any) -> Dict[str, Any]:
    """Serialize a pytfe ``NotificationConfiguration`` (plain class) for Ansible output.

    The response model is not pydantic, so ``format_response`` can't be used.
    Only the fields the collection surfaces to users are included.
    """
    created_at = getattr(nc, "created_at", None)
    updated_at = getattr(nc, "updated_at", None)
    return {
        "id": getattr(nc, "id", None),
        "name": getattr(nc, "name", None),
        "destination_type": getattr(nc, "destination_type", None),
        "enabled": getattr(nc, "enabled", None),
        "url": getattr(nc, "url", None) or None,
        "token": getattr(nc, "token", None) or None,
        "triggers": [_enum_value(t) for t in (getattr(nc, "triggers", None) or [])],
        "email_addresses": list(getattr(nc, "email_addresses", None) or []),
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


def _coerce_destination_type(value: Any) -> Any:
    """Coerce a destination-type string (e.g. ``'generic'``) to the pytfe enum.

    ``NotificationDestinationType(x)`` is idempotent for enum members thanks to
    Enum's value-lookup semantics, so we don't need to special-case them.
    """
    if value is None:
        return value
    return NotificationDestinationType(value)


def _coerce_triggers(values: Any) -> List[Any]:
    """Coerce a list of trigger strings to pytfe ``NotificationTriggerType`` members."""
    if not values:
        return []
    return [NotificationTriggerType(v) for v in values]


def _build_create_options(data: Dict[str, Any]) -> NotificationConfigurationCreateOptions:
    """Translate an Ansible-facing spec dict to pytfe create options."""
    return NotificationConfigurationCreateOptions(
        destination_type=_coerce_destination_type(data["destination_type"]),
        enabled=bool(data.get("enabled", True)),
        name=data["name"],
        token=data.get("token"),
        url=data.get("url"),
        triggers=_coerce_triggers(data.get("triggers")),
        email_addresses=list(data.get("email_addresses") or []),
    )


def _build_update_options(data: Dict[str, Any]) -> NotificationConfigurationUpdateOptions:
    """Translate a partial update dict to pytfe update options.

    Only keys present in ``data`` are forwarded, so unspecified fields are left
    untouched by the API (PATCH semantics).
    """
    kwargs: Dict[str, Any] = {}
    if "enabled" in data:
        kwargs["enabled"] = data["enabled"]
    if "name" in data:
        kwargs["name"] = data["name"]
    if "token" in data:
        kwargs["token"] = data["token"]
    if "url" in data:
        kwargs["url"] = data["url"]
    if "triggers" in data:
        kwargs["triggers"] = _coerce_triggers(data["triggers"])
    if "email_addresses" in data:
        kwargs["email_addresses"] = list(data["email_addresses"] or [])
    return NotificationConfigurationUpdateOptions(**kwargs)


def list_notification_configurations(adapter: TerraformClient, workspace_id: str) -> List[Dict[str, Any]]:
    """List notification configurations for a workspace."""
    try:
        return [_notification_to_dict(nc) for nc in adapter.client.notification_configurations.list(workspace_id)]
    except NotFound:
        return []


def get_notification_configuration(adapter: TerraformClient, notification_config_id: str) -> Optional[Dict[str, Any]]:
    """Read a notification configuration by ID."""
    try:
        return _notification_to_dict(adapter.client.notification_configurations.read(notification_config_id))
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
    options = _build_create_options(data)
    response = safe_api_call(
        adapter.client.notification_configurations.create,
        workspace_id,
        options,
        error_context=f"Failed to create notification {data.get('name')!r} on workspace {workspace_id}",
    )
    return _notification_to_dict(response)


def update_notification_configuration(
    adapter: TerraformClient,
    notification_config_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Update an existing notification configuration."""
    options = _build_update_options(data)
    response = safe_api_call(
        adapter.client.notification_configurations.update,
        notification_config_id,
        options,
        error_context=f"Failed to update notification {notification_config_id}",
    )
    return _notification_to_dict(response)


def delete_notification_configuration(adapter: TerraformClient, notification_config_id: str) -> None:
    """Delete a notification configuration."""
    safe_api_call(
        adapter.client.notification_configurations.delete,
        notification_config_id,
        error_context=f"Failed to delete notification {notification_config_id}",
    )
