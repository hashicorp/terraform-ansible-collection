# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""HYOK OIDC configuration adapter for pytfe SDK integration.

Wraps ``client.{aws,azure,gcp,vault}_oidc_configurations``
(``/api/v2/organizations/{org}/oidc-configurations`` for create,
``/api/v2/oidc-configurations/{id}`` for read/update/delete). All four
providers share identical CRUD verbs - full create/read/update/delete, no
list endpoint at all - so this single adapter is parameterized by a
``provider`` key rather than duplicated four times; only the per-provider
Create/Update option classes and field names differ, and those live in
``pytfe.models`` already.

Unlike every other org-scoped resource in this collection, there is no
``list`` and no ``name`` field on any of the four response models - the API
gives no way to search for an existing configuration by any user-meaningful
key. ``get_oidc_configuration_by_name``-style lookups are therefore
impossible here; callers must track ``oidc_configuration_id`` themselves
(e.g. via a prior ``register:``). See
``plugins/modules/{aws,azure,gcp,vault}_oidc_configuration.py`` for how that
shapes idempotency.
"""

from __future__ import annotations

from typing import Any, Dict, NamedTuple, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        AWSOIDCConfigurationCreateOptions,
        AWSOIDCConfigurationUpdateOptions,
        AzureOIDCConfigurationCreateOptions,
        AzureOIDCConfigurationUpdateOptions,
        GCPOIDCConfigurationCreateOptions,
        GCPOIDCConfigurationUpdateOptions,
        VaultOIDCConfigurationCreateOptions,
        VaultOIDCConfigurationUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    AWSOIDCConfigurationCreateOptions = None  # type: ignore[assignment]
    AWSOIDCConfigurationUpdateOptions = None  # type: ignore[assignment]
    AzureOIDCConfigurationCreateOptions = None  # type: ignore[assignment]
    AzureOIDCConfigurationUpdateOptions = None  # type: ignore[assignment]
    GCPOIDCConfigurationCreateOptions = None  # type: ignore[assignment]
    GCPOIDCConfigurationUpdateOptions = None  # type: ignore[assignment]
    VaultOIDCConfigurationCreateOptions = None  # type: ignore[assignment]
    VaultOIDCConfigurationUpdateOptions = None  # type: ignore[assignment]


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff, format_response, safe_api_call


class _ProviderSpec(NamedTuple):
    client_attr: str
    create_options_cls: Any
    update_options_cls: Any


# Maps each module's short provider key to the pytfe client attribute and
# option classes it needs. Adding a fifth provider (should HCP Terraform
# ever add one) means one new entry here plus one new module - the CRUD
# functions below never change.
PROVIDERS: Dict[str, _ProviderSpec] = {
    "aws": _ProviderSpec("aws_oidc_configurations", AWSOIDCConfigurationCreateOptions, AWSOIDCConfigurationUpdateOptions),
    "azure": _ProviderSpec("azure_oidc_configurations", AzureOIDCConfigurationCreateOptions, AzureOIDCConfigurationUpdateOptions),
    "gcp": _ProviderSpec("gcp_oidc_configurations", GCPOIDCConfigurationCreateOptions, GCPOIDCConfigurationUpdateOptions),
    "vault": _ProviderSpec("vault_oidc_configurations", VaultOIDCConfigurationCreateOptions, VaultOIDCConfigurationUpdateOptions),
}


def _service(adapter: TerraformClient, provider: str) -> Any:
    return getattr(adapter.client, PROVIDERS[provider].client_attr)


def get_oidc_configuration(adapter: TerraformClient, provider: str, oidc_configuration_id: str) -> Optional[Dict[str, Any]]:
    """Read an OIDC configuration by its ID. Returns None if not found."""
    try:
        config = _service(adapter, provider).read(oidc_configuration_id)
        return format_response(config)
    except NotFound:
        return None


def create_oidc_configuration(adapter: TerraformClient, provider: str, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an OIDC configuration under the given organization."""
    options = PROVIDERS[provider].create_options_cls.model_validate(data)
    config = safe_api_call(
        _service(adapter, provider).create,
        organization,
        options,
        error_context=f"Failed to create {provider} OIDC configuration in organization {organization}",
    )
    return format_response(config)


def update_oidc_configuration(adapter: TerraformClient, provider: str, oidc_configuration_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing OIDC configuration."""
    options = PROVIDERS[provider].update_options_cls.model_validate(data)
    config = safe_api_call(
        _service(adapter, provider).update,
        oidc_configuration_id,
        options,
        error_context=f"Failed to update {provider} OIDC configuration {oidc_configuration_id}",
    )
    return format_response(config)


def delete_oidc_configuration(adapter: TerraformClient, provider: str, oidc_configuration_id: str) -> None:
    """Delete an OIDC configuration by its ID."""
    safe_api_call(
        _service(adapter, provider).delete,
        oidc_configuration_id,
        error_context=f"Failed to delete {provider} OIDC configuration {oidc_configuration_id}",
    )


# ---------------------------------------------------------------------------
# Shared state machine
# ---------------------------------------------------------------------------
#
# All four provider modules (plugins/modules/{aws,azure,gcp,vault}_oidc_configuration.py)
# have byte-for-byte identical present/absent semantics - only the provider
# key, argspec, and "required to create" field list differ. Rather than
# duplicate that logic four times (and risk the four copies quietly
# diverging), it lives once here; each module's main() just supplies its
# provider identity.

_NON_SDK_KEYS = {"oidc_configuration_id", "organization", "state", "check_mode"}


def build_desired_state(params: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the SDK-relevant, non-None attributes the user asked for."""
    return {key: value for key, value in params.items() if not key.startswith(("tf_", "tfe_")) and key not in _NON_SDK_KEYS and value is not None}


def state_present(adapter: TerraformClient, provider: str, required_fields: tuple, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create a new OIDC configuration, or update an existing one identified by ID.

    There is no read-by-name or list for this resource (see module docstring),
    so idempotency is only possible when the caller supplies
    ``oidc_configuration_id``. Without it, this always creates - callers are
    expected to save the returned ``id`` (e.g. via ``register:``) for any
    future run that should update rather than duplicate.
    """
    oidc_configuration_id = params.get("oidc_configuration_id")
    want = build_desired_state(params)

    if oidc_configuration_id:
        current = get_oidc_configuration(adapter, provider, oidc_configuration_id)
        if current is None:
            raise ValueError(f"{provider} OIDC configuration {oidc_configuration_id} not found")

        have = {key: current.get(key) for key in want.keys()}
        diff = dict_diff(have, want)
        if not diff:
            return {"changed": False, **current}

        if check_mode:
            return {
                "changed": True,
                "msg": f"{provider} OIDC configuration {oidc_configuration_id} would be updated. Skipped update due to check mode.",
                **want,
            }
        updated = update_oidc_configuration(adapter, provider, oidc_configuration_id, want)
        return {"changed": True, **updated}

    organization = params.get("organization")
    if not organization:
        raise ValueError(f"'organization' is required when creating a new {provider} OIDC configuration.")
    missing = [field for field in required_fields if not want.get(field)]
    if missing:
        raise ValueError(f"{missing!r} are required when creating a new {provider} OIDC configuration.")

    if check_mode:
        return {"changed": True, "msg": f"A new {provider} OIDC configuration would be created. Skipped creation due to check mode."}
    created = create_oidc_configuration(adapter, provider, organization, want)
    return {"changed": True, **created}


def state_absent(adapter: TerraformClient, provider: str, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the OIDC configuration if present; no-op otherwise.

    Requires ``oidc_configuration_id`` - there is no other way to identify
    the record to delete.
    """
    oidc_configuration_id = params.get("oidc_configuration_id")
    if not oidc_configuration_id:
        raise ValueError(f"'oidc_configuration_id' is required for state=absent on a {provider} OIDC configuration.")

    current = get_oidc_configuration(adapter, provider, oidc_configuration_id)
    if current is None:
        return {"changed": False, "msg": f"{provider} OIDC configuration {oidc_configuration_id} is already absent."}

    if check_mode:
        return {"changed": True, "msg": f"{provider} OIDC configuration {oidc_configuration_id} would be deleted. Skipped deletion due to check mode."}

    delete_oidc_configuration(adapter, provider, oidc_configuration_id)
    return {"changed": True, "msg": f"{provider} OIDC configuration {oidc_configuration_id} has been deleted successfully"}
