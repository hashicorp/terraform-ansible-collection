from ansible.errors import AnsibleError
from ansible.module_utils.urls import SSLValidationError


class TerraformError(AnsibleError):
    """Base class for all Terraform-related exceptions."""
    pass

class TerraformTokenNotFoundError(AnsibleError):
    """Custom exception for Terraform token errors."""
    pass


class TerraformHostnameNotFoundError(AnsibleError):
    """Custom exception for Terraform hostname errors."""
    pass


class TerraformHostUnreachableError(AnsibleError):
    """Custom exception for unreachable Terraform host."""
    pass


class TerraformSSLValidationError(SSLValidationError):
    """Custom exception for SSL validation errors in Terraform."""
    pass
