# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module wrapper for Terraform Cloud/Enterprise modules.

This module provides the AnsibleTerraformModule class which extends
AnsibleModule with automatic authentication parameter injection and
common functionality for TFE/TFC modules. It also provides TerraformClient
for interfacing with the pytfe SDK.
"""

import traceback
from typing import Any, Mapping

from ansible.module_utils.basic import AnsibleModule, env_fallback, missing_required_lib
from ansible.module_utils.errors import AnsibleFallbackNotFound

try:
    from pytfe import TFEClient, TFEConfig

    HAS_PYTFE = True
    PYTFE_IMPORT_ERROR = None
except ImportError:
    HAS_PYTFE = False
    PYTFE_IMPORT_ERROR = traceback.format_exc()
    TFEClient = None  # type: ignore[assignment,misc]
    TFEConfig = None  # type: ignore[assignment,misc]

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformTokenNotFoundError,
)

# Authentication argument specification injected into all modules.
# This is the single source of truth for every auth/transport option the
# collection exposes to users. Each key must also appear in _ARGSPEC_TO_SDK
# below to be forwarded to pytfe.TFEConfig.
AUTH_ARGSPEC = {
    "tfe_token": {
        "type": "str",
        "required": True,
        "aliases": ["tf_token"],
        "fallback": (env_fallback, ["TFE_TOKEN"]),
        "no_log": True,
    },
    "tfe_address": {
        "type": "str",
        "required": False,
        "default": "https://app.terraform.io",
        "fallback": (env_fallback, ["TFE_ADDRESS"]),
    },
    "tfe_timeout": {
        "type": "float",
        "required": False,
        "default": 30.0,
        "fallback": (env_fallback, ["TFE_TIMEOUT"]),
    },
    "tfe_verify_tls": {
        "type": "bool",
        "required": False,
        "default": True,
        "fallback": (env_fallback, ["TFE_VERIFY_TLS"]),
    },
    "tfe_max_retries": {
        "type": "int",
        "required": False,
        "default": 5,
        "fallback": (env_fallback, ["TFE_MAX_RETRIES"]),
    },
    "tfe_ca_bundle": {
        "type": "path",
        "required": False,
        "fallback": (env_fallback, ["SSL_CERT_FILE"]),
    },
    "tfe_proxies": {
        "type": "str",
        "required": False,
    },
}

# Ordered tuple of every allowlisted auth key. Anything outside this set
# is rejected by from_mapping() to prevent argspec collisions from silently
# leaking into TFEConfig.
AUTH_KEYS = tuple(AUTH_ARGSPEC.keys())

# Translation between the collection's Ansible-facing argspec names and
# pytfe.TFEConfig field names. Keeping the two namespaces separate lets
# Ansible keep its tfe_* convention while the SDK evolves independently.
_ARGSPEC_TO_SDK = {
    "tfe_token": "token",
    "tfe_address": "address",
    "tfe_timeout": "timeout",
    "tfe_verify_tls": "verify_tls",
    "tfe_max_retries": "max_retries",
    "tfe_ca_bundle": "ca_bundle",
    "tfe_proxies": "proxies",
}

# Identifier attached to every HCP API request originating from this collection,
# forwarded to pytfe via TFEConfig.user_agent_suffix. Enables attribution and
# support triage for collection-sourced traffic.
COLLECTION_USER_AGENT_SUFFIX = "terraform-ansible-collection/2.0 pytfe/0.1"


def _resolve_argspec_fallback(key: str) -> Any:
    """Resolve an AUTH_ARGSPEC fallback outside AnsibleModule processing."""
    fallback = AUTH_ARGSPEC.get(key, {}).get("fallback")
    if not fallback:
        return None

    fallback_fn, fallback_args = fallback
    try:
        return fallback_fn(*fallback_args)
    except AnsibleFallbackNotFound:
        return None


class AnsibleTerraformModule:
    """Wrapper for AnsibleModule with TFE-specific enhancements.

    This class automatically injects authentication parameters
    and provides convenience methods for TFE/TFC modules.

    Attributes:
        module: Underlying AnsibleModule instance
    """

    def __init__(self, argument_spec, **kwargs):
        """Initialize the Terraform module wrapper.

        Args:
            argument_spec: Module-specific argument specification
            **kwargs: Additional arguments passed to AnsibleModule
        """
        merged_spec = dict(AUTH_ARGSPEC)
        merged_spec.update(argument_spec)
        self.module = AnsibleModule(argument_spec=merged_spec, **kwargs)

    def client(self) -> "TerraformClient":
        """Build a TerraformClient bound to this module's authenticated params.

        Intended use:
            with module.client() as adapter:
                ...
        """
        return TerraformClient.from_module(self)

    def __getattr__(self, name):
        """Delegate attribute access to underlying AnsibleModule."""
        return getattr(self.module, name)


class TerraformClient:
    """Adapter between Ansible modules and the pytfe SDK.

    Responsibilities:
    - Own the pytfe client lifecycle (lazy init, cleanup).
    - Normalize construction across entry points (modules, lookup, inventory)
      via the classmethod constructors below.

    The constructor takes only pytfe-SDK kwargs (token, address, timeout, ...).
    Callers holding Ansible-style argspec dicts should use
    :meth:`from_mapping` or :meth:`from_module`, which apply the allowlist.
    """

    def __init__(self, **sdk_kwargs: Any) -> None:
        """Initialize with pytfe SDK kwargs.

        Args:
            **sdk_kwargs: Keyword arguments forwarded to pytfe.TFEConfig.
                Only SDK-native names are accepted (e.g. ``token``, not
                ``tfe_token``). Use :meth:`from_mapping` or :meth:`from_module`
                to translate from Ansible argspec names.
        """
        self._sdk_kwargs: dict = dict(sdk_kwargs)
        self._sdk_kwargs.setdefault("user_agent_suffix", COLLECTION_USER_AGENT_SUFFIX)
        self._client: TFEClient = None
        self._config: TFEConfig = None
        self._prechecks()

    @classmethod
    def from_mapping(cls, params: Mapping[str, Any]) -> "TerraformClient":
        """Build a client from an Ansible-style params mapping.

        Only keys in :data:`AUTH_KEYS` are read; every other key is ignored.
        Values equal to ``None`` are dropped so pytfe's defaults apply.

        Args:
            params: Any mapping whose keys may include Ansible argspec names
                such as ``tfe_token``. Non-auth keys are silently ignored.
        """
        mapped = {}
        for key in AUTH_KEYS:
            if key not in _ARGSPEC_TO_SDK:
                continue
            value = params.get(key)
            if value is None:
                for alias in AUTH_ARGSPEC.get(key, {}).get("aliases", []) or []:
                    if params.get(alias) is not None:
                        value = params[alias]
                        break
            if value is None:
                value = _resolve_argspec_fallback(key)
            if value is not None:
                mapped[_ARGSPEC_TO_SDK[key]] = value
        return cls(**mapped)

    @classmethod
    def from_module(cls, module: "AnsibleTerraformModule") -> "TerraformClient":
        """Build a client from an :class:`AnsibleTerraformModule`."""
        return cls.from_mapping(module.params)

    def _prechecks(self) -> None:
        """Validate runtime prerequisites before any SDK construction.

        Raises:
            ImportError: If pytfe is not installed.
            TerraformTokenNotFoundError: If authentication token is missing.
        """
        if not HAS_PYTFE:
            raise ImportError(missing_required_lib("pytfe", url="https://pypi.org/project/pytfe/"))
        if not self._sdk_kwargs.get("token"):
            raise TerraformTokenNotFoundError("Authentication token is required")

    @property
    def client(self) -> TFEClient:
        """Lazy-loaded TFE client instance."""
        if self._client is None:
            self._client = TFEClient(config=self.config)
        return self._client

    @property
    def config(self) -> TFEConfig:
        """Lazy-loaded TFE config instance."""
        if self._config is None:
            self._config = TFEConfig(**self._sdk_kwargs)
        return self._config

    def cleanup(self) -> None:
        """Release the underlying transport. Safe to call multiple times."""
        if self._client:
            self._client.close()
            self._client = None
        self._config = None

    def __enter__(self) -> "TerraformClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()
