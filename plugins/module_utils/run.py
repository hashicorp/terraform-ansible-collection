from typing import Any, Optional, Union

from ansible.module_utils.common.text.converters import to_text

from .exceptions import TerraformError


def create_run(client, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Create a new run with the given parameters.
    Args:
        **kwargs: Keyword arguments to create a new run.
    Returns:
        The created run in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 201 status code.
    """
    response = client.post("/runs", data=data)
    if response.get("status") != 201:
        raise TerraformError(to_text(response))
    return response.get("data")


def apply_run(client, run_id: str) -> Optional[dict[str, Any]]:
    """
    Apply a run with the given run_id.
    Args:
        run_id(str): The ID of the run to apply.
    Returns:
        The applied run in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    response = client.post(f"/runs/{run_id}/actions/apply")
    if response.get("status") != 202:
        raise TerraformError(to_text(response))
    return response


def cancel_run(client, run_id: str) -> Optional[dict[str, Any]]:
    """
    Cancel a run with the given run_id.
    Args:
        run_id(str): The ID of the run to cancel.
    Returns:
        The cancelled run in the form of a dictionary.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    response = client.post(f"/runs/{run_id}/actions/cancel")
    if response.get("status") != 202:
        raise TerraformError(to_text(response))
    return response


def discard_run(client, run_id: str) -> Optional[dict[str, Any]]:
    """
    Discard a run with the given run_id.
    Args:
        run_id(str): The ID of the run to discard.
    Returns:
        The discarded run.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    response = client.post(f"/runs/{run_id}/actions/discard")
    if response.get("status") != 202:
        raise TerraformError(to_text(response))
    return response


def get_run(client, run_id: str) -> Optional[Union[dict[str, Any], tuple[int, str]]]:
    """
    Get a run with the given run_id.
    Args:
        run_id(str): The ID of the run to get.
    Returns:
        The run.
    Raises:
        TerraformError: If the response does not return a 200 status code.
    """
    response = client.get(f"/runs/{run_id}")
    if response.get("status") != 200:
        raise TerraformError(str(response))
    return response.get("data")
