# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""HYOK (Hold Your Own Key) configuration adapter for pytfe SDK integration.

Wraps ``client.hyok_configurations`` (``/api/v2/organizations/{org}/hyok-configurations``,
``/api/v2/hyok-configurations/{id}``). Unlike most resources in this collection, the
underlying API has no update endpoint at all - every attribute is immutable once a
HYOK configuration is created. It also has two async action endpoints (``test``,
``revoke``) with no combined status-returning response body; callers poll ``read()``
to observe the resulting status transition. That polling lives in
``plugins/modules/hyok_configuration.py``, not here - this module stays a thin,
side-effect-free wrapper per the collection's adapter/module split.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        HYOKConfigurationCreateOptions,
        HYOKKMSOptions,
        OIDCConfigurationType,
    )

    # Maps the short, user-facing argspec choice to the wire-level JSON:API
    # type pytfe's OIDCConfigurationType enum expects.
    OIDC_CONFIGURATION_TYPE_MAP = {
        "aws": OIDCConfigurationType.AWS,
        "azure": OIDCConfigurationType.AZURE,
        "gcp": OIDCConfigurationType.GCP,
        "vault": OIDCConfigurationType.VAULT,
    }
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class HYOKConfigurationCreateOptions:  # type: ignore[no-redef]
        pass

    class HYOKKMSOptions:  # type: ignore[no-redef]
        pass

    class OIDCConfigurationType:  # type: ignore[no-redef]
        pass

    OIDC_CONFIGURATION_TYPE_MAP = {
        "aws": "aws-oidc-configurations",
        "azure": "azure-oidc-configurations",
        "gcp": "gcp-oidc-configurations",
        "vault": "vault-oidc-configurations",
    }


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_hyok_configurations(adapter: TerraformClient, organization: str) -> List[Dict[str, Any]]:
    """List HYOK configurations for an organization."""
    try:
        return [format_response(c) for c in adapter.client.hyok_configurations.list(organization)]
    except NotFound:
        return []


def get_hyok_configuration(adapter: TerraformClient, hyok_configuration_id: str) -> Optional[Dict[str, Any]]:
    """Read a single HYOK configuration by its ID. Returns None if not found."""
    try:
        config = adapter.client.hyok_configurations.read(hyok_configuration_id)
        return format_response(config)
    except NotFound:
        return None


def get_hyok_configuration_by_name(adapter: TerraformClient, organization: str, name: str) -> Optional[Dict[str, Any]]:
    """Locate a HYOK configuration by name within an organization.

    There is no read-by-name endpoint; this scans the organization's list, the
    same approach ``get_ssh_key_by_name`` uses.
    """
    for config in list_hyok_configurations(adapter, organization):
        if config.get("name") == name:
            return config
    return None


def create_hyok_configuration(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a HYOK configuration under the given organization.

    Args:
        adapter: Authenticated TerraformClient.
        organization: The organization name.
        data: Attributes matching ``HYOKConfigurationCreateOptions`` fields, with
            ``oidc_configuration_type`` already mapped to the pytfe enum member
            (see ``OIDC_CONFIGURATION_TYPE_MAP``) and ``kms_options`` as a plain
            dict (validated into ``HYOKKMSOptions`` here).
    """
    payload = dict(data)
    kms_options = payload.get("kms_options")
    if kms_options is not None:
        payload["kms_options"] = HYOKKMSOptions.model_validate(kms_options)

    options = HYOKConfigurationCreateOptions.model_validate(payload)
    config = safe_api_call(
        adapter.client.hyok_configurations.create,
        organization,
        options,
        error_context=f"Failed to create HYOK configuration {data.get('name')!r} in organization {organization}",
    )
    return format_response(config)


def delete_hyok_configuration(adapter: TerraformClient, hyok_configuration_id: str) -> None:
    """Delete a HYOK configuration. The API rejects this unless status is 'revoked'."""
    safe_api_call(
        adapter.client.hyok_configurations.delete,
        hyok_configuration_id,
        error_context=f"Failed to delete HYOK configuration {hyok_configuration_id}",
    )


def revoke_hyok_configuration(adapter: TerraformClient, hyok_configuration_id: str) -> None:
    """Trigger an async revoke. Poll read(...).status for completion."""
    safe_api_call(
        adapter.client.hyok_configurations.revoke,
        hyok_configuration_id,
        error_context=f"Failed to revoke HYOK configuration {hyok_configuration_id}",
    )


def run_hyok_configuration_test(adapter: TerraformClient, hyok_configuration_id: str) -> None:
    """Trigger an async key-access test. Poll read(...).status for completion."""
    safe_api_call(
        adapter.client.hyok_configurations.test,
        hyok_configuration_id,
        error_context=f"Failed to test HYOK configuration {hyok_configuration_id}",
    )
