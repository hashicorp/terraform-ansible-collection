# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


try:
    from pytfe.models import RegistryName
except ImportError:

    class RegistryName:  # type: ignore[no-redef]
        PRIVATE = "private"
        PUBLIC = "public"


try:
    from pytfe.models import (
        RegistryProviderPlatformCreateOptions,
        RegistryProviderPlatformID,
        RegistryProviderVersionID,
    )
except ImportError:

    class RegistryProviderPlatformCreateOptions:  # type: ignore[no-redef]
        pass

    class RegistryProviderPlatformID:  # type: ignore[no-redef]
        pass

    class RegistryProviderVersionID:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def _build_platform_id(params: Dict[str, Any]) -> RegistryProviderPlatformID:
    """Build a RegistryProviderPlatformID from a params dict."""
    return RegistryProviderPlatformID(
        organization_name=params["organization"],
        registry_name=RegistryName(params.get("registry_name", "private")),
        namespace=params["namespace"],
        name=params["provider_name"],
        version=params["version"],
        os=params["os"],
        arch=params["arch"],
    )


def get_registry_provider_platform(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Read a single registry provider platform. Returns None if not found."""
    try:
        platform_id = _build_platform_id(params)
        platform = adapter.client.registry_provider_platforms.read(platform_id)
        return format_response(platform)
    except NotFound:
        return None


def create_registry_provider_platform(adapter: TerraformClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a registry provider platform."""
    version_id = RegistryProviderVersionID(
        organization_name=params["organization"],
        registry_name=RegistryName(params.get("registry_name", "private")),
        namespace=params["namespace"],
        name=params["provider_name"],
        version=params["version"],
    )
    options = RegistryProviderPlatformCreateOptions.model_validate(
        {
            "os": params["os"],
            "arch": params["arch"],
            "shasum": params["shasum"],
            "filename": params["filename"],
        }
    )
    os_arch = f"{params.get('os')}/{params.get('arch')}"
    provider_ver = f"{params.get('provider_name')} version {params.get('version')}"
    response = safe_api_call(
        adapter.client.registry_provider_platforms.create,
        version_id,
        options,
        error_context=f"Failed to create registry provider platform {os_arch} for provider {provider_ver}",
    )
    return format_response(response)


def delete_registry_provider_platform(adapter: TerraformClient, params: Dict[str, Any]) -> None:
    """Delete a registry provider platform."""
    os_arch = f"{params.get('os')}/{params.get('arch')}"
    provider_ver = f"{params.get('provider_name')} version {params.get('version')}"
    platform_id = _build_platform_id(params)
    safe_api_call(
        adapter.client.registry_provider_platforms.delete,
        platform_id,
        error_context=f"Failed to delete registry provider platform {os_arch} for provider {provider_ver}",
    )
