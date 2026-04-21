# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

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
