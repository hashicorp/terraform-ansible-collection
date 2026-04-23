# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        RunTriggerCreateOptions,
        RunTriggerFilterOp,
        RunTriggerListOptions,
        Workspace,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class RunTriggerCreateOptions:  # type: ignore[no-redef]
        pass

    class RunTriggerListOptions:  # type: ignore[no-redef]
        pass

    class RunTriggerFilterOp:  # type: ignore[no-redef]
        RUN_TRIGGER_INBOUND = "inbound"
        RUN_TRIGGER_OUTBOUND = "outbound"

    class Workspace:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_run_triggers(
    adapter: TerraformClient,
    workspace_id: str,
    run_trigger_type: str = "inbound",
) -> List[Dict[str, Any]]:
    """List run triggers for a workspace.

    ``run_trigger_type`` is required by the TFE API and must be either
    ``inbound`` (triggers that cause this workspace to run) or ``outbound``
    (triggers that cause other workspaces to run when this one runs).
    """
    filter_op = RunTriggerFilterOp.RUN_TRIGGER_OUTBOUND if run_trigger_type == "outbound" else RunTriggerFilterOp.RUN_TRIGGER_INBOUND
    options = RunTriggerListOptions(run_trigger_type=filter_op)
    try:
        return [format_response(rt) for rt in adapter.client.run_triggers.list(workspace_id, options)]
    except NotFound:
        return []


def get_run_trigger(adapter: TerraformClient, run_trigger_id: str) -> Optional[Dict[str, Any]]:
    """Read a run trigger by its ID. Returns None if not found."""
    try:
        trigger = adapter.client.run_triggers.read(run_trigger_id)
        return format_response(trigger)
    except NotFound:
        return None


def find_run_trigger(
    adapter: TerraformClient,
    workspace_id: str,
    sourceable_id: str,
    run_trigger_type: str = "inbound",
) -> Optional[Dict[str, Any]]:
    """Locate a run trigger by (workspace_id, sourceable workspace id).

    TFE does not expose a direct lookup endpoint, so we scan the workspace's
    triggers and match on the sourceable workspace ID.
    """
    for trigger in list_run_triggers(adapter, workspace_id, run_trigger_type=run_trigger_type):
        sourceable = trigger.get("sourceable") or {}
        if isinstance(sourceable, dict) and sourceable.get("id") == sourceable_id:
            return trigger
    return None


def create_run_trigger(adapter: TerraformClient, workspace_id: str, sourceable_id: str) -> Dict[str, Any]:
    """Create a run trigger on ``workspace_id`` sourced from ``sourceable_id``."""
    options = RunTriggerCreateOptions(sourceable=Workspace(id=sourceable_id))
    response = safe_api_call(
        adapter.client.run_triggers.create,
        workspace_id,
        options,
        error_context=f"Failed to create run trigger on workspace {workspace_id} from {sourceable_id}",
    )
    return format_response(response)


def delete_run_trigger(adapter: TerraformClient, run_trigger_id: str) -> None:
    """Delete a run trigger by its ID."""
    safe_api_call(
        adapter.client.run_triggers.delete,
        run_trigger_id,
        error_context=f"Failed to delete run trigger {run_trigger_id}",
    )
