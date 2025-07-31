import time

from typing import Any, Literal, Optional

from pydantic import BaseModel, StrictBool, StrictStr

from .common import TerraformClient
from .exceptions import TerraformError


class WorkspaceData(BaseModel):
    type: Literal["workspaces"]
    id: str


class WorkspaceRelationship(BaseModel):
    data: WorkspaceData


class Relationships(BaseModel):
    workspace: WorkspaceRelationship


class Attributes(BaseModel):
    message: Optional[StrictStr] = None
    auto_apply: Optional[StrictBool] = None
    plan_only: Optional[StrictBool] = None
    save_plan: Optional[StrictBool] = None
    is_destroy: Optional[StrictBool] = None
    target_addrs: Optional[list[StrictStr]] = None
    refresh: Optional[StrictBool] = None
    variables: Optional[dict] = None


class RunData(BaseModel):
    attributes: Attributes
    type: Literal["runs"]
    relationships: Relationships


class RunRequest(BaseModel):
    data: RunData


class TerraformRun:
    def __init__(self, client: TerraformClient):
        self.client = client

    def create(self, **kwargs: Any):
        """
        Create a new run.
        Args:
            **kwargs: Keyword arguments to create a new run.
        Returns:
            The created run.
        """
        payload = RunRequest(**kwargs)
        payload_json = payload.model_dump_json(exclude_unset=True)
        response = self.client.post("/runs", data=payload_json)
        if response.get("status") == 201:
            return response.get("data")
        else:
            raise TerraformError(str(response))

    def apply(self, run_id: str):
        """
        Apply a run.
        Args:
            run_id: The ID of the run to apply.
        Returns:
            The applied run.
        """
        response = self.client.post(f"/runs/{run_id}/actions/apply")
        if response.get("status") == 200:
            return response.get("data")
        else:
            raise TerraformError(str(response))

    def cancel(self, run_id: str):
        response = self.client.post(f"/runs/{run_id}/actions/cancel")
        if response.get("status") == 200:
            return response.get("data")
        else:
            raise TerraformError(str(response))

    def discard(self, run_id: str):
        """
        Discard a run.
        Args:
            run_id: The ID of the run to discard.
        Returns:
            The discarded run.
        """
        response = self.client.post(f"/runs/{run_id}/actions/discard")
        if response.get("status") == 200:
            return response.get("data")
        else:
            raise TerraformError(str(response))

    def get(self, run_id: str):
        """
        Get a run.
        Args:
            run_id: The ID of the run to get.
        Returns:
            The run.
        """
        response = self.client.get(f"/runs/{run_id}")
        if response.get("status") == 200:
            return response.get("data")
        else:
            raise TerraformError(str(response))

    def run_events(self, run_id: str):
        """
        Get the events for a run.
        Args:
            run_id: The ID of the run to get the events for.
        Returns:
            The events for the run.
        """
        response = self.client.get(f"/runs/{run_id}/run-events")
        if response.get("status") == 200:
            return response.get("data")
        else:
            raise TerraformError(str(response))

    def task_stages(self, run_id: str):
        """
        Get the tasks for a run.
        Args:
            run_id: The ID of the run to get the tasks for.
        Returns:
            The tasks for the run.
        """
        response = self.client.get(f"/runs/{run_id}/task-stages")
        if response.get("status") == 200:
            return response.get("data")
        else:
            raise TerraformError(str(response))

    def wait_for_state(self, run_id: str, expected_states: list[str], expected_key: str, timeout: int = 25, polling_interval: int = 5):
        """
        Wait for a run to reach a specific state.
        Args:
            run_id: The ID of the run to wait for.
            expected_state: The expected state of the run.
            expected_key: The expected key of the run.
            timeout: The timeout for the wait.
            polling_interval: The polling interval.
        """
        start_time = time.time()
        while time.time() - start_time <= timeout:
            run = self.get(run_id)
            if run.get(expected_key) in expected_states:
                return run
            time.sleep(polling_interval)
        raise TerraformError(f"Run {run_id} did not reach expected state {expected_states} within {timeout} seconds")
