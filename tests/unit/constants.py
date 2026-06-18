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
TEST_PROJECT_ID = "prj-test123"
TEST_TEAM_ID = "team-test123"
TEST_TEAM_WORKSPACE_ACCESS_ID = "tws-test123"
TEST_TEAM_PROJECT_ACCESS_ID = "tpa-test123"

# Common test attributes
TEST_WORKSPACE_NAME = "test-workspace"
TEST_ORGANIZATION_NAME = "test-org"
TEST_RUN_MESSAGE = "Test run"
TEST_PROJECT_NAME = "test-project"


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
    status: Optional[int] = None,
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
        status: Optional HTTP status code (e.g., 200)
        **extra_attributes: Additional attributes to merge into the response

    Returns:
        Dictionary representing a Terraform workspace API response

    Example:
        >>> response = create_workspace_response(name="my-workspace", locked=True)
        >>> response = create_workspace_response(workspace_id="ws-custom", status=200)
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

    response = {
        "data": {
            "id": workspace_id,
            "type": "workspaces",
            "attributes": attributes,
            "relationships": {"organization": {"data": {"id": organization_id, "type": "organizations"}}},
        }
    }

    if status is not None:
        response["status"] = status

    return response


def create_configuration_version_response(
    cv_id: str = TEST_CONFIGURATION_VERSION_ID,
    status: str = "uploaded",
    upload_url: Optional[str] = None,
    http_status: Optional[int] = None,
    **extra_attributes
) -> Dict[str, Any]:
    """
    Create a Terraform configuration version API response payload.

    Args:
        cv_id: The configuration version identifier
        status: Configuration version status ('uploaded', 'pending', 'errored')
        upload_url: Optional upload URL
        http_status: Optional HTTP status code (e.g., 201, 200)
        **extra_attributes: Additional attributes to merge into the response

    Returns:
        Dictionary representing a Terraform configuration version API response

    Example:
        >>> response = create_configuration_version_response(status="pending")
        >>> response = create_configuration_version_response(cv_id="cv-custom", http_status=201)
    """
    attributes = {
        "status": status,
        "created-at": "2025-01-15T10:30:00.000Z",
    }

    if upload_url:
        attributes["upload-url"] = upload_url

    # Merge extra attributes
    attributes.update(extra_attributes)

    response = {
        "data": {
            "id": cv_id,
            "type": "configuration-versions",
            "attributes": attributes,
        }
    }

    if http_status is not None:
        response["status"] = http_status

    return response


def create_plan_response(
    plan_id: str = TEST_PLAN_ID, status: str = "finished", has_changes: bool = True, http_status: Optional[int] = None, **extra_attributes
) -> Dict[str, Any]:
    """
    Create a Terraform plan API response payload.

    Args:
        plan_id: The plan identifier
        status: Plan status ('finished', 'pending', 'errored')
        has_changes: Whether the plan has changes
        http_status: Optional HTTP status code (e.g., 200)
        **extra_attributes: Additional attributes to merge into the response

    Returns:
        Dictionary representing a Terraform plan API response

    Example:
        >>> response = create_plan_response(status="pending")
        >>> response = create_plan_response(plan_id="plan-123", has_changes=False, http_status=200)
    """
    attributes = {
        "status": status,
        "has-changes": has_changes,
    }

    # Merge extra attributes
    attributes.update(extra_attributes)

    response = {
        "data": {
            "id": plan_id,
            "type": "plans",
            "attributes": attributes,
        }
    }

    if http_status is not None:
        response["status"] = http_status

    return response


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


def create_project_response(
    project_id: str = TEST_PROJECT_ID,
    name: str = TEST_PROJECT_NAME,
    description: Optional[str] = None,
    organization_id: str = TEST_ORGANIZATION_ID,
    http_status: Optional[int] = None,
    **extra_attributes
) -> Dict[str, Any]:
    """
    Create a Terraform API project response payload.

    Args:
        project_id: Project ID (e.g., "prj-123abc456def")
        name: Project name
        description: Optional project description
        organization_id: Organization ID this project belongs to
        http_status: Optional HTTP status code at root level
        **extra_attributes: Additional project attributes

    Returns:
        Dictionary representing a project API response

    Example:
        >>> response = create_project_response(
        ...     project_id="prj-123",
        ...     name="my-project",
        ...     description="Test project"
        ... )
    """
    attributes = {"name": name}
    if description is not None:
        attributes["description"] = description
    attributes.update(extra_attributes)

    response = {
        "data": {
            "id": project_id,
            "type": "projects",
            "attributes": attributes,
            "relationships": {"organization": {"data": {"id": organization_id, "type": "organizations"}}},
        }
    }

    if http_status is not None:
        response["status"] = http_status

    return response


TEST_TEAM_ID = "team-test123"
TEST_TEAM_WORKSPACE_ACCESS_ID = "tws-test123"


def create_team_workspace_access_response(
    twa_id: str = TEST_TEAM_WORKSPACE_ACCESS_ID,
    access: str = "read",
    team_id: str = TEST_TEAM_ID,
    workspace_id: str = TEST_WORKSPACE_ID,
    runs: Optional[str] = None,
    variables: Optional[str] = None,
    state_versions: Optional[str] = None,
    sentinel_mocks: Optional[str] = None,
    workspace_locking: Optional[bool] = None,
    run_tasks: Optional[bool] = None,
    policy_overrides: Optional[bool] = None,
    **extra_attributes
) -> Dict[str, Any]:
    """Create a team-workspace access API response payload.

    Args:
        twa_id: The team-workspace access identifier (e.g. ``tws-xxx``).
        access: Access level (``read``, ``plan``, ``write``, ``admin``, ``custom``).
        team_id: The team identifier.
        workspace_id: The workspace identifier.
        runs: Runs permission for custom access.
        variables: Variables permission for custom access.
        state_versions: State versions permission for custom access.
        sentinel_mocks: Sentinel mocks permission for custom access.
        workspace_locking: Workspace locking permission for custom access.
        run_tasks: Run tasks permission for custom access.
        policy_overrides: Policy overrides permission for custom access.
        **extra_attributes: Additional attributes to merge into the response.

    Returns:
        Dictionary representing a team-workspace access API response.

    Example:
        >>> response = create_team_workspace_access_response(access="write")
        >>> response = create_team_workspace_access_response(
        ...     access="custom", runs="apply", variables="write"
        ... )
    """
    attributes: Dict[str, Any] = {"access": access}
    if runs is not None:
        attributes["runs"] = runs
    if variables is not None:
        attributes["variables"] = variables
    if state_versions is not None:
        attributes["state-versions"] = state_versions
    if sentinel_mocks is not None:
        attributes["sentinel-mocks"] = sentinel_mocks
    if workspace_locking is not None:
        attributes["workspace-locking"] = workspace_locking
    if run_tasks is not None:
        attributes["run-tasks"] = run_tasks
    if policy_overrides is not None:
        attributes["policy-overrides"] = policy_overrides
    attributes.update(extra_attributes)

    return {
        "data": {
            "id": twa_id,
            "type": "team-workspaces",
            "attributes": attributes,
            "relationships": {
                "team": {"data": {"id": team_id, "type": "teams"}},
                "workspace": {"data": {"id": workspace_id, "type": "workspaces"}},
            },
        }
    }


SAMPLE_RUN_RESPONSE = create_run_response()
SAMPLE_WORKSPACE_RESPONSE = create_workspace_response()
SAMPLE_CONFIGURATION_VERSION_RESPONSE = create_configuration_version_response()
SAMPLE_ERROR_RESPONSE = create_error_response()
SAMPLE_PLAN_RESPONSE = create_plan_response()
SAMPLE_PROJECT_RESPONSE = create_project_response()


def create_team_workspace_access_response(
    twa_id: str = TEST_TEAM_WORKSPACE_ACCESS_ID,
    team_id: str = TEST_TEAM_ID,
    workspace_id: str = TEST_WORKSPACE_ID,
    access: str = "read",
    runs: str = "read",
    variables: str = "read",
    state_versions: str = "read",
    sentinel_mocks: str = "none",
    workspace_locking: bool = False,
    run_tasks: bool = False,
    policy_overrides: bool = False,
) -> dict:
    """Create a normalized team-workspace access response (as returned by format_response + _normalize_response)."""
    return {
        "id": twa_id,
        "access": access,
        "runs": runs,
        "variables": variables,
        "state_versions": state_versions,
        "sentinel_mocks": sentinel_mocks,
        "workspace_locking": workspace_locking,
        "run_tasks": run_tasks,
        "policy_overrides": policy_overrides,
        "team_id": team_id,
        "workspace_id": workspace_id,
    }


def create_team_project_access_response(
    tpa_id: str = TEST_TEAM_PROJECT_ACCESS_ID,
    team_id: str = TEST_TEAM_ID,
    project_id: str = TEST_PROJECT_ID,
    access: str = "read",
    project_settings: Optional[str] = None,
    project_teams: Optional[str] = None,
    project_variable_sets: Optional[str] = None,
    workspace_runs: Optional[str] = None,
    workspace_sentinel_mocks: Optional[str] = None,
    workspace_state_versions: Optional[str] = None,
    workspace_variables: Optional[str] = None,
    workspace_create: Optional[bool] = None,
    workspace_delete: Optional[bool] = None,
    workspace_locking: Optional[bool] = None,
    workspace_move: Optional[bool] = None,
    workspace_run_tasks: Optional[bool] = None,
) -> dict:
    """Create a normalized team-project access response (as returned by format_response + _normalize_response)."""
    result: Dict[str, Any] = {
        "id": tpa_id,
        "access": access,
        "team_id": team_id,
        "project_id": project_id,
    }
    optional_fields = {
        "project_settings": project_settings,
        "project_teams": project_teams,
        "project_variable_sets": project_variable_sets,
        "workspace_runs": workspace_runs,
        "workspace_sentinel_mocks": workspace_sentinel_mocks,
        "workspace_state_versions": workspace_state_versions,
        "workspace_variables": workspace_variables,
        "workspace_create": workspace_create,
        "workspace_delete": workspace_delete,
        "workspace_locking": workspace_locking,
        "workspace_move": workspace_move,
        "workspace_run_tasks": workspace_run_tasks,
    }
    for key, value in optional_fields.items():
        if value is not None:
            result[key] = value
    return result


# Consolidated dictionary for easy access
SAMPLE_TERRAFORM_RESPONSES = {
    "run": SAMPLE_RUN_RESPONSE,
    "workspace": SAMPLE_WORKSPACE_RESPONSE,
    "configuration_version": SAMPLE_CONFIGURATION_VERSION_RESPONSE,
    "plan": SAMPLE_PLAN_RESPONSE,
    "project": SAMPLE_PROJECT_RESPONSE,
    "error": SAMPLE_ERROR_RESPONSE,
}
