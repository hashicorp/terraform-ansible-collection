# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Workspace adapter for pytfe SDK integration.

This module provides the WorkspaceAdapter class that handles workspace-specific
operations using the pytfe SDK, including create, read, update, delete, lock,
and unlock operations.

Example:
    adapter = WorkspaceAdapter(tfe_token="my-token", tfe_address="https://app.terraform.io")
    with adapter:
        workspace = adapter.get_workspace_by_name('my-org', 'my-workspace')
"""

from typing import Any, Dict

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

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient


class WorkspaceAdapter(TerraformClient):
    """Adapter for workspace operations using pytfe SDK.

    This adapter extends TerraformClient to provide workspace-specific
    functionality including:
    - Create workspace
    - Read workspace details
    - Update workspace attributes
    - Delete workspace (safe and force)
    - Lock/unlock workspace
    """

    def get_workspace_by_id(self, workspace_id: str) -> Dict[str, Any] | None:
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
            workspace = self.client.workspaces.read_by_id(workspace_id)
            return self.format_response(workspace)
        except NotFound:
            # workspace was not found
            # This should not raise an exception
            return None

    def get_workspace_by_name(self, organization: str, workspace_name: str) -> Dict[str, Any] | None:
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
            workspace = self.client.workspaces.read(workspace_name, organization=organization)
            return self.format_response(workspace)
        except NotFound:
            # workspace was not found
            # This should not raise an exception
            return None

    def _build_workspace_payload(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Build workspace payload from attributes for create/update operations.

        Args:
            attributes: Workspace attributes from Ansible module

        Returns:
            Dict with mapped attributes ready for SDK options
        """
        payload = {}

        # Map simple attributes (direct pass-through)
        simple_attrs = [
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

    def create_workspace(self, organization: str, **attributes) -> Dict[str, Any]:
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
        create_kwargs = {"name": attributes["name"]}
        create_kwargs.update(self._build_workspace_payload(attributes))

        create_options = WorkspaceCreateOptions(**create_kwargs)

        workspace = self.safe_api_call(
            self.client.workspaces.create,
            organization,
            create_options,
            error_context=f"Failed to create workspace {attributes.get('name', 'unknown')} in organization {organization}",
        )

        return self.format_response(workspace)

    def update_workspace(self, workspace_id: str, **attributes) -> Dict[str, Any]:
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
        # Build update options - name is required by SDK
        update_kwargs = {"name": attributes["name"]}
        update_kwargs.update(self._build_workspace_payload(attributes))

        update_options = WorkspaceUpdateOptions(**update_kwargs)

        workspace = self.safe_api_call(
            self.client.workspaces.update_by_id, workspace_id, update_options, error_context=f"Failed to update workspace {workspace_id}"
        )

        return self.format_response(workspace)

    def safe_delete_workspace(self, workspace_id: str) -> None:
        """
        Safe deletes a specified workspace in Terraform Cloud.

        Sends a POST request using the pytfe SDK to initiate the safe delete action for a given workspace id.

        Args:
            workspace_id (str): The ID of the workspace to safe delete.
        """
        self.safe_api_call(self.client.workspaces.safe_delete_by_id, workspace_id, error_context=f"Failed to safely delete workspace {workspace_id}")

    def force_delete_workspace(self, workspace_id: str) -> None:
        """
        Force deletes a specified workspace in Terraform Cloud.

        Sends a POST request using the pytfe SDK to initiate the delete action for a given workspace id.

        Args:
            workspace_id (str): The ID of the workspace to delete.
        """
        self.safe_api_call(self.client.workspaces.delete_by_id, workspace_id, error_context=f"Failed to force delete workspace {workspace_id}")

    def lock_workspace(self, workspace_id: str, reason: str) -> Dict[str, Any]:
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

        workspace = self.safe_api_call(self.client.workspaces.lock, workspace_id, lock_options, error_context=f"Failed to lock workspace {workspace_id}")

        return self.format_response(workspace)

    def unlock_workspace(
        self,
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
        workspace = self.safe_api_call(self.client.workspaces.unlock, workspace_id, error_context=f"Failed to unlock workspace {workspace_id}")

        return self.format_response(workspace)

    def force_unlock_workspace(self, workspace_id: str) -> Dict[str, Any]:
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
        workspace = self.safe_api_call(self.client.workspaces.force_unlock, workspace_id, error_context=f"Failed to force unlock workspace {workspace_id}")

        return self.format_response(workspace)
