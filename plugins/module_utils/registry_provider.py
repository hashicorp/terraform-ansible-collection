# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import RegistryProviderCreateOptions, RegistryProviderID
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class RegistryProviderCreateOptions:  # type: ignore[no-redef]
        pass

    class RegistryProviderID:  # type: ignore[no-redef]
        @classmethod
        def model_validate(cls, value):
            return value


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def _build_registry_provider_id(organization: str, registry_name: str, namespace: str, name: str) -> Any:
    return RegistryProviderID.model_validate(
        {
            "organization_name": organization,
            "registry_name": registry_name,
            "namespace": namespace,
            "name": name,
        }
    )


def get_registry_provider(
    adapter: TerraformClient,
    organization: str,
    registry_name: str,
    namespace: str,
    name: str,
) -> Optional[Dict[str, Any]]:
    """Read a registry provider by composite identifier."""
    provider_id = _build_registry_provider_id(organization, registry_name, namespace, name)
    try:
        provider = adapter.client.registry_providers.read(provider_id)
        return format_response(provider)
    except NotFound:
        return None


def create_registry_provider(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a registry provider in the specified organization."""
    options = RegistryProviderCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.registry_providers.create,
        organization,
        options,
        error_context=f"Failed to create registry provider {data.get('name')!r} in organization {organization}",
    )
    return format_response(response)


def delete_registry_provider(
    adapter: TerraformClient,
    organization: str,
    registry_name: str,
    namespace: str,
    name: str,
) -> None:
    """Delete a registry provider by composite identifier."""
    provider_id = _build_registry_provider_id(organization, registry_name, namespace, name)
    safe_api_call(
        adapter.client.registry_providers.delete,
        provider_id,
        error_context=f"Failed to delete registry provider {name!r} in organization {organization}",
    )
