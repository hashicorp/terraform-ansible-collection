# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Test constants and payload factory functions for Terraform collection unit tests.

This module provides reusable factory functions to create consistent test data
and API response payloads, reducing duplication across test files.
"""

from typing import Any, Dict, Optional


# ============================================================================
# Common Test IDs and Values
# ============================================================================

TEST_RUN_ID = "run-test123"
TEST_WORKSPACE_ID = "ws-test123"
TEST_ORGANIZATION_ID = "org-test123"
TEST_CONFIGURATION_VERSION_ID = "cv-test123"
TEST_PLAN_ID = "plan-test123"

# Common test attributes
TEST_WORKSPACE_NAME = "test-workspace"
TEST_ORGANIZATION_NAME = "test-org"
TEST_RUN_MESSAGE = "Test run"


# ============================================================================
# Payload Factory Functions
# ============================================================================


def create_run_response(
    run_id: str = TEST_RUN_ID,
    status: str = "applied",
    message: Optional[str] = None,
    workspace_id: str = TEST_WORKSPACE_ID,
    is_destroy: bool = False,
    auto_apply: bool = False,
    **extra_attributes
) -> Dict[str, Any]:
    """
    Create a Terraform run API response payload.

    Args:
        run_id: The run identifier
        status: Run status (e.g., 'applied', 'planned', 'errored', 'pending')
        message: Optional run message
        workspace_id: Associated workspace ID
        is_destroy: Whether this is a destroy run
        auto_apply: Whether auto-apply is enabled
        **extra_attributes: Additional attributes to merge into the response

    Returns:
        Dictionary representing a Terraform run API response

    Example:
        >>> response = create_run_response(status="planned", message="Custom message")
        >>> response = create_run_response(run_id="run-123", status="errored")
    """
    attributes = {
        "status": status,
        "created-at": "2025-01-15T10:00:00.000Z",
        "is-destroy": is_destroy,
        "auto-apply": auto_apply,
    }

    if message:
        attributes["message"] = message

    # Merge extra attributes
    attributes.update(extra_attributes)

    return {
        "data": {
            "id": run_id,
            "type": "runs",
            "attributes": attributes,
            "relationships": {"workspace": {"data": {"id": workspace_id, "type": "workspaces"}}},
        }
    }


def create_workspace_response(
    workspace_id: str = TEST_WORKSPACE_ID,
    name: str = TEST_WORKSPACE_NAME,
    description: Optional[str] = None,
    locked: bool = False,
    execution_mode: str = "remote",
    organization_id: str = TEST_ORGANIZATION_ID,
    **extra_attributes
) -> Dict[str, Any]:
    """
    Create a Terraform workspace API response payload.

    Args:
        workspace_id: The workspace identifier
        name: Workspace name
        description: Optional workspace description
        locked: Whether the workspace is locked
        execution_mode: Execution mode ('remote', 'local', 'agent')
        organization_id: Associated organization ID
        **extra_attributes: Additional attributes to merge into the response

    Returns:
        Dictionary representing a Terraform workspace API response

    Example:
        >>> response = create_workspace_response(name="my-workspace", locked=True)
        >>> response = create_workspace_response(workspace_id="ws-custom")
    """
    attributes = {
        "name": name,
        "created-at": "2025-01-15T09:00:00.000Z",
        "locked": locked,
        "execution-mode": execution_mode,
    }

    if description:
        attributes["description"] = description

    # Merge extra attributes
    attributes.update(extra_attributes)

    return {
        "data": {
            "id": workspace_id,
            "type": "workspaces",
            "attributes": attributes,
            "relationships": {"organization": {"data": {"id": organization_id, "type": "organizations"}}},
        }
    }


def create_configuration_version_response(
    cv_id: str = TEST_CONFIGURATION_VERSION_ID, status: str = "uploaded", upload_url: Optional[str] = None, **extra_attributes
) -> Dict[str, Any]:
    """
    Create a Terraform configuration version API response payload.

    Args:
        cv_id: The configuration version identifier
        status: Configuration version status ('uploaded', 'pending', 'errored')
        upload_url: Optional upload URL
        **extra_attributes: Additional attributes to merge into the response

    Returns:
        Dictionary representing a Terraform configuration version API response

    Example:
        >>> response = create_configuration_version_response(status="pending")
        >>> response = create_configuration_version_response(cv_id="cv-custom")
    """
    attributes = {
        "status": status,
        "created-at": "2025-01-15T10:30:00.000Z",
    }

    if upload_url:
        attributes["upload-url"] = upload_url

    # Merge extra attributes
    attributes.update(extra_attributes)

    return {
        "data": {
            "id": cv_id,
            "type": "configuration-versions",
            "attributes": attributes,
        }
    }


def create_plan_response(plan_id: str = TEST_PLAN_ID, status: str = "finished", has_changes: bool = True, **extra_attributes) -> Dict[str, Any]:
    """
    Create a Terraform plan API response payload.

    Args:
        plan_id: The plan identifier
        status: Plan status ('finished', 'pending', 'errored')
        has_changes: Whether the plan has changes
        **extra_attributes: Additional attributes to merge into the response

    Returns:
        Dictionary representing a Terraform plan API response

    Example:
        >>> response = create_plan_response(status="pending")
        >>> response = create_plan_response(plan_id="plan-123", has_changes=False)
    """
    attributes = {
        "status": status,
        "has-changes": has_changes,
    }

    # Merge extra attributes
    attributes.update(extra_attributes)

    return {
        "data": {
            "id": plan_id,
            "type": "plans",
            "attributes": attributes,
        }
    }


def create_error_response(
    status: str = "404",
    title: str = "Not Found",
    detail: str = "Resource not found",
) -> Dict[str, Any]:
    """
    Create a Terraform API error response payload.

    Args:
        status: HTTP status code as string
        title: Error title
        detail: Error detail message

    Returns:
        Dictionary representing a Terraform API error response

    Example:
        >>> response = create_error_response(status="500", title="Server Error")
        >>> response = create_error_response(detail="Workspace not found")
    """
    return {
        "errors": [
            {
                "status": status,
                "title": title,
                "detail": detail,
            }
        ]
    }


def create_empty_response() -> Dict[str, Any]:
    """
    Create an empty Terraform API response payload.

    Returns:
        Dictionary representing an empty API response

    Example:
        >>> response = create_empty_response()
    """
    return {"data": {}}


def create_list_response(items: list, meta: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Create a Terraform API list response payload.

    Args:
        items: List of data items
        meta: Optional metadata (pagination, etc.)

    Returns:
        Dictionary representing a list API response

    Example:
        >>> runs = [create_run_response(run_id=f"run-{i}") for i in range(3)]
        >>> response = create_list_response([r["data"] for r in runs])
    """
    response = {"data": items}
    if meta:
        response["meta"] = meta
    return response


SAMPLE_RUN_RESPONSE = create_run_response()
SAMPLE_WORKSPACE_RESPONSE = create_workspace_response()
SAMPLE_CONFIGURATION_VERSION_RESPONSE = create_configuration_version_response()
SAMPLE_ERROR_RESPONSE = create_error_response()
SAMPLE_PLAN_RESPONSE = create_plan_response()

# Consolidated dictionary for easy access
SAMPLE_TERRAFORM_RESPONSES = {
    "run": SAMPLE_RUN_RESPONSE,
    "workspace": SAMPLE_WORKSPACE_RESPONSE,
    "configuration_version": SAMPLE_CONFIGURATION_VERSION_RESPONSE,
    "plan": SAMPLE_PLAN_RESPONSE,
    "error": SAMPLE_ERROR_RESPONSE,
}
