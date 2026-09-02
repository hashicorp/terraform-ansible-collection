# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import TaskStageIncludeOpt, TaskStageReadOptions
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class TaskStageIncludeOpt:  # type: ignore[no-redef]
        pass

    class TaskStageReadOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response

# Maps the module's underscore-style include choices to the API's include values.
_INCLUDE_MAP = {
    "run": "run",
    "run.workspace": "run.workspace",
    "task_results": "task-results",
    "policy_evaluations": "policy-evaluations",
}


def get_task_stage(adapter: TerraformClient, task_stage_id: str, include: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Read a single task stage by its ID. Returns None if not found."""
    options = None
    if include:
        mapped = [TaskStageIncludeOpt(_INCLUDE_MAP[opt]) for opt in include]
        options = TaskStageReadOptions(include=mapped)
    try:
        stage = adapter.client.task_stages.read(task_stage_id, options)
        return format_response(stage)
    except NotFound:
        return None


def list_task_stages(adapter: TerraformClient, run_id: str) -> List[Dict[str, Any]]:
    """List the task stages for a run."""
    try:
        return [format_response(stage) for stage in adapter.client.task_stages.list(run_id)]
    except NotFound:
        return []
