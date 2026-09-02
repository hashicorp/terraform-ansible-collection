# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        RunTaskCreateOptions,
        RunTaskUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class RunTaskCreateOptions:  # type: ignore[no-redef]
        pass

    class RunTaskUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_run_tasks(adapter: TerraformClient, organization: str) -> List[Dict[str, Any]]:
    """List run tasks for an organization."""
    try:
        return [format_response(task) for task in adapter.client.run_tasks.list(organization)]
    except NotFound:
        return []


def get_run_task(adapter: TerraformClient, run_task_id: str) -> Optional[Dict[str, Any]]:
    """Read a single run task by its ID. Returns None if not found."""
    try:
        task = adapter.client.run_tasks.read(run_task_id)
        return format_response(task)
    except NotFound:
        return None


def get_run_task_by_name(adapter: TerraformClient, organization: str, name: str) -> Optional[Dict[str, Any]]:
    """Locate a run task by name within an organization."""
    for task in list_run_tasks(adapter, organization):
        if task.get("name") == name:
            return task
    return None


def create_run_task(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a run task under the given organization."""
    options = RunTaskCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.run_tasks.create,
        organization,
        options,
        error_context=f"Failed to create run task {data.get('name')!r} in organization {organization}",
    )
    return format_response(response)


def update_run_task(adapter: TerraformClient, run_task_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing run task."""
    options = RunTaskUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.run_tasks.update,
        run_task_id,
        options,
        error_context=f"Failed to update run task {run_task_id}",
    )
    return format_response(response)


def delete_run_task(adapter: TerraformClient, run_task_id: str) -> None:
    """Delete a run task by its ID."""
    safe_api_call(
        adapter.client.run_tasks.delete,
        run_task_id,
        error_context=f"Failed to delete run task {run_task_id}",
    )
