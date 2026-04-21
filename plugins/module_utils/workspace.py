# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Workspace adapter for pytfe SDK integration.

This module provides functions that handle workspace-specific
operations using the pytfe SDK, including create, read, update, delete, lock,
and unlock operations.

Example:
    adapter = TerraformClient(tfe_token="my-token", tfe_address="https://app.terraform.io")
    with adapter:
        workspace = get_workspace(adapter, 'my-org', 'my-workspace')
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        ExecutionMode,
        Project,
        TagBinding,
        WorkspaceCreateOptions,
        WorkspaceLockOptions,
        WorkspaceSettingOverwrites,
        WorkspaceUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class ExecutionMode:  # type: ignore[no-redef]
        pass

    class Project:  # type: ignore[no-redef]
        pass

    class TagBinding:  # type: ignore[no-redef]
        pass

    class WorkspaceCreateOptions:  # type: ignore[no-redef]
        pass

    class WorkspaceLockOptions:  # type: ignore[no-redef]
        pass

    class WorkspaceSettingOverwrites:  # type: ignore[no-redef]
        pass

    class WorkspaceUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def get_workspace_by_id(adapter: TerraformClient, workspace_id: str) -> Dict[str, Any] | None:
    """
    Retrieves a specified workspace from Terraform Cloud by its ID.

    Sends a GET request using the pytfe SDK to fetch details of a workspace identified by its unique ID.
    If the workspace is not found, returns None. If successful,
    returns the workspace data with an added "status" field. For any other error
    status, raises a TerraformError.

    Args:
        workspace_id (str): The unique ID of the workspace to retrieve.

    Returns:
        dict: A dictionary containing the workspace data (with an added "status" field)
        if found, or None if the workspace is not found.

    """
    try:
        workspace = adapter.client.workspaces.read_by_id(workspace_id)
        return format_response(workspace)
    except NotFound:
        # workspace was not found
        # This should not raise an exception
        return None


def get_workspace(adapter: TerraformClient, organization: str, workspace_name: str) -> Dict[str, Any] | None:
    """
    Retrieves a specified workspace from Terraform Cloud.

    Sends a GET request using the pytfe SDK to fetch details of a workspace identified by its name
    within a given organization. If the workspace is not found, returns None.
    If successful, returns the workspace data with an added "status" field.
    For any other error status, raises an HTTPError.

    Args:
        organization (str): The name of the Terraform Cloud organization..
        workspace_name (str): The name of the workspace to retrieve.

    Returns:
        dict: A dictionary containing the workspace data (with an added "status" field)
        if found, or None if the workspace is not found.

    """
    try:
        workspace = adapter.client.workspaces.read(workspace_name, organization=organization)
        return format_response(workspace)
    except NotFound:
        # workspace was not found
        # This should not raise an exception
        return None


def get_tag_bindings(adapter: TerraformClient, workspace_id: str) -> Optional[dict[str, Any]]:
    """
    Fetch tag bindings for a given Terraform workspace.

    This function calls the Terraform API to retrieve tag bindings associated
    with the specified workspace. It gracefully handles a 404 status (workspace not found),
    returns the response

    Args:
        client (TerraformClient): The Terraform API client instance.
        workspace_id (str): The ID of the workspace for which to fetch tag bindings.

    Returns:
        Dict[str, Any]: The tag bindings data, including the response status.
                        Returns an empty dict if the workspace is not found (404).
    """
    try:
        tag_bindings = list(adapter.client.workspaces.list_tag_bindings(workspace_id))
        return [format_response(tag_binding) for tag_binding in tag_bindings]
    except NotFound:
        # workspace was not found
        # This should not raise an exception
        return {}


def _build_workspace_payload(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """Build workspace payload from attributes for create/update operations.

    Args:
        attributes: Workspace attributes from Ansible module

    Returns:
        Dict with mapped attributes ready for SDK options
    """
    payload = {}

    # Map simple attributes (direct pass-through)
    simple_attrs = [
        "name",
        "description",
        "auto_apply",
        "terraform_version",
        "agent_pool_id",
        "auto_destroy_activity_duration",
        "source_name",
        "source_url",
        "assessments_enabled",
        "auto_apply_run_trigger",
        "auto_destroy_at",
        "allow_destroy_plan",
    ]
    for attr in simple_attrs:
        if attr in attributes:
            payload[attr] = attributes[attr]

    # Handle execution_mode (convert string to ExecutionMode enum)
    if "execution_mode" in attributes and attributes["execution_mode"]:
        payload["execution_mode"] = ExecutionMode(attributes["execution_mode"].lower())

    # Handle setting_overwrites (convert dict to WorkspaceSettingOverwrites, skip if empty)
    if "setting_overwrites" in attributes and attributes["setting_overwrites"]:
        payload["setting_overwrites"] = WorkspaceSettingOverwrites(**attributes["setting_overwrites"])

    # Handle project_id (convert to Project object, skip if empty)
    if "project_id" in attributes and attributes["project_id"]:
        payload["project"] = Project(id=attributes["project_id"])

    # Handle tag_bindings (convert dict to TagBinding list, skip if empty)
    if "tag_bindings" in attributes and attributes["tag_bindings"]:
        payload["tag_bindings"] = [TagBinding(key=k, value=v) for k, v in attributes["tag_bindings"].items()]

    return payload


def _normalize_auto_destroy_at_for_request(options: WorkspaceCreateOptions | WorkspaceUpdateOptions) -> None:
    """Ensure auto_destroy_at is JSON-serializable for SDK request payload building."""
    auto_destroy_at = getattr(options, "auto_destroy_at", None)
    if isinstance(auto_destroy_at, datetime):
        options.auto_destroy_at = auto_destroy_at.strftime("%Y-%m-%dT%H:%M:%SZ")


def create_workspace(adapter: TerraformClient, organization: str, **attributes) -> Dict[str, Any]:
    """
    Creates a new workspace for a specified Terraform Cloud workspace.

    Sends a POST request using the pytfe SDK to the Terraform Cloud API to create a workspace
    associated with the given organization. If the operation is successful, returns the
    workspace data with the response status code included.

    Args:
        organization (str): The name of the organization
        **attributes: A dictionary of attributes to include in the workspace payload.

    Returns:
        dict: The response data from Terraform Cloud, including the created
        workspace details.
    """
    # Build create options from attributes
    create_kwargs = _build_workspace_payload(attributes)

    create_options = WorkspaceCreateOptions(**create_kwargs)
    _normalize_auto_destroy_at_for_request(create_options)

    workspace = safe_api_call(
        adapter.client.workspaces.create,
        organization,
        create_options,
        error_context=f"Failed to create workspace {attributes.get('name', 'unknown')} in organization {organization}",
    )

    return format_response(workspace)


def update_workspace(adapter: TerraformClient, workspace_id: str, **attributes) -> Dict[str, Any]:
    """
    Updates an existing workspace for a specified Terraform Cloud workspace.

    Sends a POST request using the pytfe SDK to the Terraform Cloud API to update a workspace
    associated with the given organization. If the operation is successful, returns the
    workspace data with the response status code included.

    Args:
        workspace_id (str): The ID of the workspace to update.
        **attributes: A dictionary of attributes to include in the workspace payload.

    Returns:
        dict: The response data from Terraform Cloud, including the updated
        workspace details.
    """
    # Build update options from provided attributes
    update_kwargs = _build_workspace_payload(attributes)

    update_options = WorkspaceUpdateOptions(**update_kwargs)
    _normalize_auto_destroy_at_for_request(update_options)

    workspace = safe_api_call(adapter.client.workspaces.update_by_id, workspace_id, update_options, error_context=f"Failed to update workspace {workspace_id}")

    return format_response(workspace)


def safe_delete_workspace(adapter: TerraformClient, workspace_id: str) -> None:
    """
    Safe deletes a specified workspace in Terraform Cloud.

    Sends a POST request using the pytfe SDK to initiate the safe delete action for a given workspace id.

    Args:
        workspace_id (str): The ID of the workspace to safe delete.
    """
    safe_api_call(adapter.client.workspaces.safe_delete_by_id, workspace_id, error_context=f"Failed to safely delete workspace {workspace_id}")


def force_delete_workspace(adapter: TerraformClient, workspace_id: str) -> None:
    """
    Force deletes a specified workspace in Terraform Cloud.

    Sends a POST request using the pytfe SDK to initiate the delete action for a given workspace id.

    Args:
        workspace_id (str): The ID of the workspace to delete.
    """
    safe_api_call(adapter.client.workspaces.delete_by_id, workspace_id, error_context=f"Failed to force delete workspace {workspace_id}")


def lock_workspace(adapter: TerraformClient, workspace_id: str, reason: str) -> Dict[str, Any]:
    """
    Lock a specified workspace in Terraform Cloud.

    Sends a POST request using the pytfe SDK to initiate the lock action for a given workspace id.
    If the lock action is successfully initiated, returns the response data.

    Args:
        workspace_id (str): The ID of the workspace to lock.
        reason (str): The reason for locking the workspace.

    Returns:
        dict: The response data from Terraform Cloud, including the locked
        workspace details.
    """
    lock_options = WorkspaceLockOptions(reason=reason)

    workspace = safe_api_call(adapter.client.workspaces.lock, workspace_id, lock_options, error_context=f"Failed to lock workspace {workspace_id}")

    return format_response(workspace)


def unlock_workspace(
    adapter: TerraformClient,
    workspace_id: str,
) -> Dict[str, Any]:
    """
    Unlock a specified workspace in Terraform Cloud.

    Sends a POST request to initiate the unlock action for a given workspace.
    If the unlock action is successfully initiated, returns the response data.

    Args:
        workspace_id (str): The ID of the workspace to unlock.

    Returns:
        dict: The response data from Terraform Cloud, including the unlocked
        workspace details.
    """
    workspace = safe_api_call(adapter.client.workspaces.unlock, workspace_id, error_context=f"Failed to unlock workspace {workspace_id}")

    return format_response(workspace)


def force_unlock_workspace(adapter: TerraformClient, workspace_id: str) -> Dict[str, Any]:
    """
    Force unlock a specified workspace in Terraform Cloud.

    Sends a POST request to initiate the force unlock action for a given workspace.
    If the force unlock action is successfully initiated, returns the response data.

    Args:
        workspace_id (str): The ID of the workspace to force unlock.

    Returns:
        dict: The response data from Terraform Cloud, including the force unlocked
        workspace details.
    """
    workspace = safe_api_call(adapter.client.workspaces.force_unlock, workspace_id, error_context=f"Failed to force unlock workspace {workspace_id}")

    return format_response(workspace)
