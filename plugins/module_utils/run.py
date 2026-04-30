from __future__ import annotations

from typing import Any, Optional, Union

try:
    from pytfe.errors import NotFound
    from pytfe.models import ConfigurationVersion, RunApplyOptions, RunCancelOptions, RunCreateOptions, RunDiscardOptions, RunVariable, Workspace
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class ConfigurationVersion:  # type: ignore[no-redef]
        pass

    class RunApplyOptions:  # type: ignore[no-redef]
        pass

    class RunCancelOptions:  # type: ignore[no-redef]
        pass

    class RunCreateOptions:  # type: ignore[no-redef]
        pass

    class RunDiscardOptions:  # type: ignore[no-redef]
        pass

    class RunVariable:  # type: ignore[no-redef]
        pass

    class Workspace:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def create_run(adapter: TerraformClient, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Create a new run with the given parameters.
    Args:
        **kwargs: Keyword arguments to create a new run.
    Returns:
        The created run in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 201 status code.
    """
    if data.get("configuration_version"):
        data["configuration_version"] = ConfigurationVersion.model_validate({"id": data.pop("configuration_version"), "type": "configuration-versions"})
    if data.get("workspace_id"):
        data["workspace"] = Workspace.model_validate({"id": data.pop("workspace_id"), "type": "workspaces"})
    if data.get("variables"):
        data["variables"] = [RunVariable(**variable) for variable in data.pop("variables")]
    options = RunCreateOptions.model_validate(data)

    run_response = safe_api_call(adapter.client.runs.create, options)
    return format_response(run_response)


def apply_run(adapter: TerraformClient, run_id: str, comment: str | None = None) -> Optional[dict[str, Any]]:
    """
    Apply a run with the given run_id.
    Args:
        run_id(str): The ID of the run to apply.
    Returns:
        The applied run in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    apply_options = RunApplyOptions(comment=comment)
    safe_api_call(adapter.client.runs.apply, run_id, apply_options, error_context=f"Failed to apply run {run_id}")
    return {"data": {"id": run_id}}


def cancel_run(adapter: TerraformClient, run_id: str, comment: str | None = None) -> Optional[dict[str, Any]]:
    """
    Cancel a run with the given run_id.
    Args:
        run_id(str): The ID of the run to cancel.
    Returns:
        The cancelled run in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    cancel_options = RunCancelOptions(comment=comment)
    safe_api_call(adapter.client.runs.cancel, run_id, cancel_options, error_context=f"Failed to cancel run {run_id}")
    return {"data": {"id": run_id}}


def discard_run(adapter: TerraformClient, run_id: str, comment: str | None = None) -> Optional[dict[str, Any]]:
    """
    Discard a run with the given run_id.
    Args:
        run_id(str): The ID of the run to discard.
    Returns:
        The discarded run.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    discard_options = RunDiscardOptions(comment=comment)
    safe_api_call(adapter.client.runs.discard, run_id, discard_options, error_context=f"Failed to discard run {run_id}")
    return {"data": {"id": run_id}}


def get_run(adapter: TerraformClient, run_id: str) -> Optional[Union[dict[str, Any], tuple[int, str]]]:
    """
    Get a run with the given run_id.
    Args:
        run_id(str): The ID of the run to get.
    Returns:
        The run.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    try:
        run = adapter.client.runs.read(run_id)
        return format_response(run)
    except NotFound:
        return {}


def run_events(adapter: TerraformClient, run_id: str) -> Optional[dict[str, Any]]:
    """
    Get the events for a run.
    Args:
        run_id: The ID of the run to get the events for.
    Returns:
        The events for the run.
    Raises:
        TerraformError: If the events for the run does not return a 200
            status code.
    """
    events_response = list(adapter.client.run_events.list(run_id))
    return [format_response(event) for event in events_response]
