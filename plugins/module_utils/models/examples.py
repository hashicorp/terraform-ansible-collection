#!/usr/bin/env python3
"""
Example usage of the reorganized models.

This file demonstrates how to use the models organized by resource type
for creating runs, workspaces, and configuration versions.
"""

from .common import (
    create_configuration_version_reference,
    create_organization_reference,
    create_workspace_reference,
)
from .configuration_versions import ConfigurationVersionRequest
from .runs import RunRequest
from .workspaces import WorkspaceRequest


def example_workspace_creation():
    """Example: Create a workspace request."""
    # Simple workspace creation
    workspace_request = WorkspaceRequest.create(
        name="my-terraform-workspace",
        organization_name="my-org",
        description="Example workspace for Terraform configurations",
        auto_apply=True,
        terraform_version="1.5.0",
    )

    # Convert to dict for API request
    payload = workspace_request.model_dump(by_alias=True, exclude_unset=True)
    print("Workspace creation payload:")
    print(payload)
    return workspace_request


def example_run_creation():
    """Example: Create a run request."""
    # Simple run creation
    run_request = RunRequest.create(
        workspace_id="ws-123456789",
        message="Deploy infrastructure changes",
        auto_apply=False,
        plan_only=True,
        variables={"environment": "production", "region": "us-west-2"},
    )

    # Convert to dict for API request
    payload = run_request.model_dump(by_alias=True, exclude_unset=True)
    print("Run creation payload:")
    print(payload)
    return run_request


def example_run_with_configuration_version():
    """Example: Create a run with specific configuration version."""
    run_request = RunRequest.create(
        workspace_id="ws-123456789", configuration_version_id="cv-987654321", message="Deploy with specific config version", auto_apply=True, is_destroy=False
    )

    payload = run_request.model_dump(by_alias=True, exclude_unset=True)
    print("Run with config version payload:")
    print(payload)
    return run_request


def example_configuration_version_creation():
    """Example: Create a configuration version request."""
    # Simple configuration version creation
    config_request = ConfigurationVersionRequest.create(auto_queue_runs=True, speculative=False, provisional=False)

    # Convert to dict for API request
    payload = config_request.model_dump(by_alias=True, exclude_unset=True)
    print("Configuration version creation payload:")
    print(payload)
    return config_request


def example_speculative_configuration_version():
    """Example: Create a speculative configuration version."""
    config_request = ConfigurationVersionRequest.create(auto_queue_runs=False, speculative=True, provisional=True)

    payload = config_request.model_dump(by_alias=True, exclude_unset=True)
    print("Speculative configuration version payload:")
    print(payload)
    return config_request


def example_using_utility_functions():
    """Example: Using utility functions for references."""
    # Create references for use in relationships
    workspace_ref = create_workspace_reference("ws-123456789")
    config_ref = create_configuration_version_reference("cv-987654321")
    org_ref = create_organization_reference("my-organization")

    print("Workspace reference:", workspace_ref.model_dump())
    print("Configuration version reference:", config_ref.model_dump())
    print("Organization reference:", org_ref.model_dump())


def example_importing_from_package():
    """Example: Different ways to import models."""
    print("=== Import Examples ===")

    # Option 1: Import specific models from their modules
    print("1. Import specific models from their modules:")
    print("   from .runs import RunRequest")
    print("   from .workspaces import WorkspaceRequest")
    print("   from .configuration_versions import ConfigurationVersionRequest")

    # Option 2: Import common utilities
    print("\n2. Import common utilities:")
    print("   from .common import create_workspace_reference, create_organization_reference")

    # Option 3: Import all from specific module (if needed)
    print("\n3. Import all from specific module (use sparingly):")
    print("   from .runs import *")

    # Option 4: Import with full path (recommended for clarity)
    print("\n4. Import with full path (recommended):")
    print("   from ansible_collections.hashicorp.terraform.plugins.module_utils.models.runs import RunRequest")


if __name__ == "__main__":
    print("=== Terraform Cloud/Enterprise API Model Examples ===")
    print("(Using reorganized models by resource type)\n")

    print("1. Workspace Creation Example:")
    example_workspace_creation()
    print("\n" + "=" * 50 + "\n")

    print("2. Run Creation Example:")
    example_run_creation()
    print("\n" + "=" * 50 + "\n")

    print("3. Run with Configuration Version Example:")
    example_run_with_configuration_version()
    print("\n" + "=" * 50 + "\n")

    print("4. Configuration Version Creation Example:")
    example_configuration_version_creation()
    print("\n" + "=" * 50 + "\n")

    print("5. Speculative Configuration Version Example:")
    example_speculative_configuration_version()
    print("\n" + "=" * 50 + "\n")

    print("6. Utility Functions Example:")
    example_using_utility_functions()
    print("\n" + "=" * 50 + "\n")

    print("7. Import Examples:")
    example_importing_from_package()
