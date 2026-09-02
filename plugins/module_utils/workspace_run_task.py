# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        WorkspaceRunTaskCreateOptions,
        WorkspaceRunTaskUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class WorkspaceRunTaskCreateOptions:  # type: ignore[no-redef]
        pass

    class WorkspaceRunTaskUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_workspace_run_tasks(adapter: TerraformClient, workspace_id: str) -> List[Dict[str, Any]]:
    """List the run tasks attached to a workspace."""
    try:
        return [format_response(task) for task in adapter.client.workspace_run_tasks.list(workspace_id)]
    except NotFound:
        return []


def get_workspace_run_task(adapter: TerraformClient, workspace_id: str, workspace_run_task_id: str) -> Optional[Dict[str, Any]]:
    """Read a single workspace run task association by its ID. Returns None if not found."""
    try:
        task = adapter.client.workspace_run_tasks.read(workspace_id, workspace_run_task_id)
        return format_response(task)
    except NotFound:
        return None


def get_workspace_run_task_by_run_task(adapter: TerraformClient, workspace_id: str, run_task_id: str) -> Optional[Dict[str, Any]]:
    """Locate the association linking a given run task to a workspace."""
    for task in list_workspace_run_tasks(adapter, workspace_id):
        run_task = task.get("run_task") or {}
        current_id = run_task.get("id") if isinstance(run_task, dict) else getattr(run_task, "id", None)
        if current_id == run_task_id:
            return task
    return None


def create_workspace_run_task(adapter: TerraformClient, workspace_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Attach a run task to a workspace."""
    options = WorkspaceRunTaskCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.workspace_run_tasks.create,
        workspace_id,
        options,
        error_context=f"Failed to attach run task to workspace {workspace_id}",
    )
    return format_response(response)


def update_workspace_run_task(adapter: TerraformClient, workspace_id: str, workspace_run_task_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing workspace run task association."""
    options = WorkspaceRunTaskUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.workspace_run_tasks.update,
        workspace_id,
        workspace_run_task_id,
        options,
        error_context=f"Failed to update workspace run task {workspace_run_task_id}",
    )
    return format_response(response)


def delete_workspace_run_task(adapter: TerraformClient, workspace_id: str, workspace_run_task_id: str) -> None:
    """Detach a run task from a workspace by the association ID."""
    safe_api_call(
        adapter.client.workspace_run_tasks.delete,
        workspace_id,
        workspace_run_task_id,
        error_context=f"Failed to delete workspace run task {workspace_run_task_id}",
    )
