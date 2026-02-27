# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module wrapper for Terraform Cloud/Enterprise modules.

This module provides the AnsibleTerraformModule class which extends
AnsibleModule with automatic authentication parameter injection and
common functionality for TFE/TFC modules. It also provides TerraformClient
for interfacing with the pytfe SDK.
"""

from typing import Any, Callable, Dict, Optional

from ansible.module_utils.basic import AnsibleModule, env_fallback
from pytfe import TFEClient, TFEConfig
from pytfe.errors import AuthError, NotFound, ServerError, TFEError

from .exceptions import TerraformError, TerraformTokenNotFoundError


# Authentication argument specification injected into all modules
AUTH_ARGSPEC = {
    "tfe_token": {
        "required": False,
        "fallback": (env_fallback, ["TFE_TOKEN", "TF_TOKEN"]),
        "no_log": True,
    },
    "tfe_address": {
        "required": False,
        "default": "https://app.terraform.io",
        "fallback": (env_fallback, ["TFE_ADDRESS", "TF_HOSTNAME"]),
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
    - Implements error translation from SDK to exceptions
    - Offers common helper methods for API operations

    Attributes:
        token: TFE API token for authentication
        address: TFE/TFC instance URL
    """

    def __init__(self, **kwargs):
        """Initialize the TFE client.

        Args:
            kwargs: Dictionary containing authentication parameters (tfe_token, tfe_address)

        Raises:
            TerraformTokenNotFoundError: If token is not provided and not in environment
        """
        self.token: Optional[str] = kwargs.get("tfe_token")
        self.address: str = kwargs.get("tfe_address", "https://app.terraform.io")

        # Validate that we have a token
        if not self.token:
            raise TerraformTokenNotFoundError("TFE token is required (tfe_token parameter or TFE_TOKEN environment variable)")

        self._client: Optional[TFEClient] = None
        self._config: Optional[TFEConfig] = None

    @property
    def config(self) -> TFEConfig:
        """Get or create TFEConfig instance.

        Returns:
            TFEConfig instance configured with token and address
        """
        if self._config is None:
            self._config = TFEConfig(token=self.token, address=self.address)
        return self._config

    @property
    def client(self) -> TFEClient:
        """Get or create TFEClient instance.

        Returns:
            TFEClient instance for SDK operations
        """
        if self._client is None:
            self._client = TFEClient(config=self.config)
        return self._client

    def handle_error(self, error: Exception, operation: str = "API operation") -> TerraformError:
        """Translate SDK errors to TerraformError.

        Args:
            error: Exception from pytfe SDK
            operation: Description of the operation that failed

        Returns:
            TerraformError with appropriate message
        """
        if isinstance(error, NotFound):
            return TerraformError(f"Resource not found: {str(error)}")
        elif isinstance(error, AuthError):
            return TerraformError(f"Authentication error: {str(error)}")
        elif isinstance(error, ServerError):
            return TerraformError(f"Server error during {operation}: {str(error)}")
        elif isinstance(error, TFEError):
            return TerraformError(f"TFE error during {operation}: {str(error)}")
        else:
            return TerraformError(f"Error during {operation}: {str(error)}")

    def safe_api_call(
        self,
        operation: Callable[..., Any],
        *args,
        error_context: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Safely call a pytfe SDK method with error handling.

        Args:
            operation: Callable SDK method to execute
            *args: Positional arguments for the operation
            error_context: Description of what operation is being performed
            **kwargs: Keyword arguments for the operation

        Returns:
            Result from the SDK operation

        Raises:
            TerraformError: If the operation fails
        """
        try:
            return operation(*args, **kwargs)
        except NotFound:
            # Re-raise NotFound to allow callers to handle 404 specially
            raise
        except Exception as error:
            raise self.handle_error(error, error_context or "API operation")

    def format_response(self, response: Any) -> Dict[str, Any]:
        """Format SDK response for Ansible output.

        Args:
            response: Response object from SDK (Pydantic model)

        Returns:
            Dictionary formatted for Ansible with JSON-serializable types
        """
        # Convert SDK response (Pydantic model) to dictionary with JSON-serializable types
        if hasattr(response, "model_dump"):
            return response.model_dump(mode="json", exclude_none=True)
        return response

    def cleanup(self) -> None:
        """Cleanup resources.

        Close any open connections and reset client instances.
        """
        if self._client is not None:
            # Close the client if it has a close method
            if hasattr(self._client, "close"):
                self._client.close()
            self._client = None

        self._config = None
