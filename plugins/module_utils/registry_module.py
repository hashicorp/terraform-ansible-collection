# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        RegistryModuleCreateOptions,
        RegistryModuleCreateVersionOptions,
        RegistryModuleCreateWithVCSConnectionOptions,
        RegistryModuleID,
        RegistryModuleUpdateOptions,
        RegistryName,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class RegistryModuleCreateOptions:  # type: ignore[no-redef]
        pass

    class RegistryModuleCreateVersionOptions:  # type: ignore[no-redef]
        pass

    class RegistryModuleCreateWithVCSConnectionOptions:  # type: ignore[no-redef]
        pass

    class RegistryModuleID:  # type: ignore[no-redef]
        pass

    class RegistryModuleUpdateOptions:  # type: ignore[no-redef]
        pass

    class RegistryName:  # type: ignore[no-redef]
        PRIVATE = "private"
        PUBLIC = "public"


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_registry_module(adapter: TerraformClient, module_id: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Read a single registry module by its composite key. Returns None if not found."""
    try:
        # Build RegistryModuleID from dict
        registry_module_id = RegistryModuleID(
            id=module_id.get("id"),
            organization=module_id.get("organization"),
            name=module_id.get("name"),
            provider=module_id.get("provider"),
            namespace=module_id.get("namespace"),
            registry_name=RegistryName(module_id.get("registry_name", "private")),
        )
        module = adapter.client.registry_modules.read(registry_module_id)
        return format_response(module)
    except NotFound:
        return None


def get_registry_module_version(
    adapter: TerraformClient, module_id: Dict[str, Any], version: str
) -> Optional[Dict[str, Any]]:
    """Read a specific version of a registry module. Returns None if not found."""
    try:
        registry_module_id = RegistryModuleID(
            organization=module_id.get("organization"),
            name=module_id.get("name"),
            provider=module_id.get("provider"),
        )
        module_version = adapter.client.registry_modules.read_version(registry_module_id, version)
        return format_response(module_version)
    except NotFound:
        return None


def create_registry_module(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a registry module without VCS connection."""
    options = RegistryModuleCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.registry_modules.create,
        organization,
        options,
        error_context=f"Failed to create registry module {data.get('name')!r} in organization {organization}",
    )
    return format_response(response)


def create_registry_module_with_vcs(adapter: TerraformClient, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a registry module with VCS connection."""
    options = RegistryModuleCreateWithVCSConnectionOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.registry_modules.create_with_vcs_connection,
        options,
        error_context=f"Failed to create registry module with VCS connection",
    )
    return format_response(response)


def create_registry_module_version(
    adapter: TerraformClient, module_id: Dict[str, Any], data: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a new version for a registry module."""
    # Build RegistryModuleID from dict
    registry_module_id = RegistryModuleID(
        organization=module_id.get("organization"),
        name=module_id.get("name"),
        provider=module_id.get("provider"),
    )
    options = RegistryModuleCreateVersionOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.registry_modules.create_version,
        registry_module_id,
        options,
        error_context=f"Failed to create version {data.get('version')} for registry module",
    )
    return format_response(response)


def update_registry_module(adapter: TerraformClient, module_id: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing registry module."""
    # Build RegistryModuleID from dict
    registry_module_id = RegistryModuleID(
        organization=module_id.get("organization"),
        name=module_id.get("name"),
        provider=module_id.get("provider"),
        namespace=module_id.get("namespace"),
        registry_name=RegistryName(module_id.get("registry_name", "private")),
    )
    options = RegistryModuleUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.registry_modules.update,
        registry_module_id,
        options,
        error_context=f"Failed to update registry module",
    )
    return format_response(response)


def delete_registry_module_by_name(adapter: TerraformClient, module_id: Dict[str, Any]) -> None:
    """Delete the entire registry module by name."""
    registry_module_id = RegistryModuleID(
        organization=module_id.get("organization"),
        name=module_id.get("name"),
    )
    safe_api_call(
        adapter.client.registry_modules.delete_by_name,
        registry_module_id,
        error_context=f"Failed to delete registry module {module_id.get('name')}",
    )


def delete_registry_module_provider(adapter: TerraformClient, module_id: Dict[str, Any]) -> None:
    """Delete a specific provider for a registry module."""
    registry_module_id = RegistryModuleID(
        organization=module_id.get("organization"),
        name=module_id.get("name"),
        provider=module_id.get("provider"),
    )
    safe_api_call(
        adapter.client.registry_modules.delete_provider,
        registry_module_id,
        error_context=f"Failed to delete provider {module_id.get('provider')} for registry module {module_id.get('name')}",
    )


def delete_registry_module_version(adapter: TerraformClient, module_id: Dict[str, Any], version: str) -> None:
    """Delete a specific version of a registry module."""
    registry_module_id = RegistryModuleID(
        organization=module_id.get("organization"),
        name=module_id.get("name"),
        provider=module_id.get("provider"),
    )
    safe_api_call(
        adapter.client.registry_modules.delete_version,
        registry_module_id,
        version,
        error_context=f"Failed to delete version {version} for registry module {module_id.get('name')}",
    )


def upload_registry_module_version(
    adapter: TerraformClient, upload_url: str, archive_content: bytes
) -> None:
    """Upload a tar.gz archive to the registry module version upload URL."""
    import io

    archive = io.BytesIO(archive_content)
    safe_api_call(
        adapter.client.registry_modules.upload_tar_gzip,
        upload_url,
        archive,
        error_context="Failed to upload registry module version archive",
    )

# Made with Bob
