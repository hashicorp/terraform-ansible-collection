from ansible.module_utils.urls import SSLValidationError


class TerraformError(Exception):
    """Base class for all Terraform-related exceptions."""

    pass


class TerraformTokenNotFoundError(Exception):
    """Custom exception for Terraform token errors."""

    pass


class TerraformHostnameNotFoundError(Exception):
    """Custom exception for Terraform hostname errors."""

    pass


class TerraformHostUnreachableError(Exception):
    """Custom exception for unreachable Terraform host."""

    pass


class TerraformSSLValidationError(SSLValidationError):
    """Custom exception for SSL validation errors in Terraform."""

    pass
