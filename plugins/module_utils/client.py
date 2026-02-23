# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module wrapper for Terraform Cloud/Enterprise modules.

This module provides the AnsibleTerraformModule class which extends
AnsibleModule with automatic authentication parameter injection and
common functionality for TFE/TFC modules. It also provides TerraformClient
for interfacing with the pytfe SDK.
"""

from ansible.module_utils.basic import AnsibleModule, env_fallback
from pytfe import TFEClient, TFEConfig

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformTokenNotFoundError,
)

# Authentication argument specification injected into all modules
AUTH_ARGSPEC = {
    "tfe_token": {
        "required": False,
        "fallback": (env_fallback, ["TFE_TOKEN"]),
        "no_log": True,
    },
    "tfe_address": {
        "required": False,
        "default": "https://app.terraform.io",
        "fallback": (env_fallback, ["TFE_ADDRESS"]),
    },
}


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
        # Merge authentication parameters with module-specific parameters
        merged_spec = dict(AUTH_ARGSPEC)
        merged_spec.update(argument_spec)

        # Initialize the underlying AnsibleModule
        self.module = AnsibleModule(argument_spec=merged_spec, **kwargs)

    def __getattr__(self, name):
        """Delegate attribute access to underlying AnsibleModule.

        All attribute access (params, check_mode, fail_json, exit_json, warn, debug, etc.)
        is automatically delegated to the underlying AnsibleModule instance.

        Args:
            name: Attribute name

        Returns:
            Attribute from the underlying module
        """
        return getattr(self.module, name)


class TerraformClient:
    """Client for interfacing between Ansible modules and pytfe SDK.

    This client:
    - Manages SDK client lifecycle (initialization, configuration, cleanup)
    - Provides authentication handling

    Attributes:
        client: TFEClient instance for API operations
        config: TFEConfig instance for SDK configuration
    """

    def __init__(self, **kwargs):
        """Initialize the TFE client.

        Args:
            kwargs: Dictionary containing authentication parameters (tfe_token, tfe_address)
        """
        self._client: TFEClient = None
        self._config: TFEConfig = None
        self.token = kwargs.get("tfe_token")
        self.address = kwargs.get("tfe_address", "https://app.terraform.io")

        self.prechecks()

    def prechecks(self):
        """Perform pre-checks to validate authentication parameters.

        Raises:
            TerraformTokenNotFoundError: If authentication token is missing
        """
        if not self.token:
            raise TerraformTokenNotFoundError("Authentication token is required")

    @property
    def client(self) -> TFEClient:
        """Lazy-loaded TFE client instance.

        Returns:
            Configured TFEClient instance

        Raises:
            Exception: If client initialization fails
        """
        if self._client is None:
            self._client = TFEClient(config=self.config)
        return self._client

    @property
    def config(self) -> TFEConfig:
        """Lazy-loaded TFE config instance.

        Returns:
            Configured TFEConfig instance
        """
        if self._config is None:
            self._config = TFEConfig(
                address=self.address,
                token=self.token,
            )
        return self._config

    def cleanup(self) -> None:
        """Cleanup resources (if needed).

        This method can be called explicitly or used in a context manager.
        """
        # Close any open connections or resources
        if self._client:
            self._client.close()
            self._client = None

        self._config = None
