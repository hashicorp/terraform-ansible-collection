# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        RegistryName,
        RegistryProviderID,
        RegistryProviderVersionCreateOptions,
        RegistryProviderVersionID,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class RegistryName:  # type: ignore[no-redef]
        PRIVATE = "private"

    class RegistryProviderID:  # type: ignore[no-redef]
        pass

    class RegistryProviderVersionCreateOptions:  # type: ignore[no-redef]
        pass

    class RegistryProviderVersionID:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_registry_provider_version(
    adapter: TerraformClient,
    provider_id: Dict[str, Any],
    version: str,
) -> Optional[Dict[str, Any]]:
    """Read a specific registry provider version. Returns None if not found."""
    try:
        version_id = RegistryProviderVersionID(
            organization_name=provider_id.get("organization_name"),
            registry_name=RegistryName(provider_id.get("registry_name", "private")),
            namespace=provider_id.get("namespace"),
            name=provider_id.get("name"),
            version=version,
        )
        result = adapter.client.registry_provider_versions.read(version_id)
        return format_response(result)
    except NotFound:
        return None


def create_registry_provider_version(
    adapter: TerraformClient,
    provider_id: Dict[str, Any],
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a registry provider version."""
    pid = RegistryProviderID(
        organization_name=provider_id.get("organization_name"),
        registry_name=RegistryName(provider_id.get("registry_name", "private")),
        namespace=provider_id.get("namespace"),
        name=provider_id.get("name"),
    )
    options = RegistryProviderVersionCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.registry_provider_versions.create,
        pid,
        options,
        error_context=(
            f"Failed to create registry provider version {data.get('version')!r} "
            f"for provider {provider_id.get('name')!r} "
            f"in organization {provider_id.get('organization_name')!r}"
        ),
    )
    return format_response(response)


def delete_registry_provider_version(
    adapter: TerraformClient,
    provider_id: Dict[str, Any],
    version: str,
) -> None:
    """Delete a specific registry provider version."""
    version_id = RegistryProviderVersionID(
        organization_name=provider_id.get("organization_name"),
        registry_name=RegistryName(provider_id.get("registry_name", "private")),
        namespace=provider_id.get("namespace"),
        name=provider_id.get("name"),
        version=version,
    )
    safe_api_call(
        adapter.client.registry_provider_versions.delete,
        version_id,
        error_context=(f"Failed to delete registry provider version {version!r} " f"for provider {provider_id.get('name')!r}"),
    )
