"""
Pydantic models for Terraform Cloud/Enterprise Run resources.

This module contains models specifically for run-related API operations.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, StrictBool, StrictStr

from .common import (
    BaseAttributes,
    BaseRelationships,
    BaseTerraformResource,
    Relationship,
    TerraformAPIResponse,
)


# Compatibility classes that match the original models.py structure


class WorkspaceData(BaseModel):
    """Model for workspace data in relationships."""
    type: Literal["workspaces"]
    id: str


class WorkspaceRelationship(BaseModel):
    """Model for workspace relationship."""
    data: WorkspaceData


class Relationships(BaseModel):
    """Model for all relationships."""
    workspace: WorkspaceRelationship


class Attributes(BaseModel):
    """Model for run attributes."""
    message: Optional[StrictStr] = None
    refresh_only: Optional[StrictBool] = Field(None, alias="refresh-only")
    plan_only: Optional[StrictBool] = Field(None, alias="plan-only")
    auto_apply: Optional[StrictBool] = Field(None, alias="auto-apply")
    save_plan: Optional[StrictBool] = Field(None, alias="save-plan")
    is_destroy: Optional[StrictBool] = Field(None, alias="is-destroy")
    target_addrs: Optional[List[StrictStr]] = Field(None, alias="target-addrs")
    refresh: Optional[StrictBool] = None
    variables: Optional[Dict[str, Any]] = None


class RunData(BaseModel):
    """Model for run data."""
    attributes: Attributes
    type: Literal["runs", "plans", "applies", "state-versions", "configuration-versions", "policy-checks"]
    relationships: Relationships


class RunRequest(BaseModel):
    """Model for the complete run request."""
    data: RunData

    class Config:
        populate_by_name = True

    @classmethod
    def create(
        cls,
        workspace_id: str,
        resource_type: Literal[
            "runs", "plans", "applies", "state-versions",
            "configuration-versions", "policy-checks"
        ] = "runs",
        **attributes
    ) -> "RunRequest":
        """
        Create a RunRequest with just workspace_id and attributes.

        Args:
            workspace_id: The workspace ID
            resource_type: The resource type (runs, plans, applies, state-versions,
                configuration-versions, policy-checks)
            **attributes: Any run attributes (message, plan_only, auto_apply, etc.)

        Returns:
            A complete RunRequest with all nested structure built automatically
        """
        return cls(
            data=RunData(
                attributes=Attributes(**attributes),
                type=resource_type,
                relationships=Relationships(
                    workspace=WorkspaceRelationship(
                        data=WorkspaceData(type="workspaces", id=workspace_id)
                    )
                ),
            )
        )


# Extended models for future use


class RunAttributes(BaseAttributes):
    """Attributes for run resources."""
    message: Optional[StrictStr] = None
    status: Optional[StrictStr] = None
    refresh_only: Optional[StrictBool] = Field(None, alias="refresh-only")
    plan_only: Optional[StrictBool] = Field(None, alias="plan-only")
    auto_apply: Optional[StrictBool] = Field(None, alias="auto-apply")
    save_plan: Optional[StrictBool] = Field(None, alias="save-plan")
    is_destroy: Optional[StrictBool] = Field(None, alias="is-destroy")
    target_addrs: Optional[List[StrictStr]] = Field(None, alias="target-addrs")
    refresh: Optional[StrictBool] = None
    variables: Optional[Dict[str, Any]] = None


class RunRelationships(BaseRelationships):
    """Relationships for run resources."""
    workspace: Optional[Relationship] = None
    configuration_version: Optional[Relationship] = Field(default=None, alias="configuration-version")
    plan: Optional[Relationship] = None
    apply: Optional[Relationship] = None
    created_by: Optional[Relationship] = Field(default=None, alias="created-by")
    policy_checks: Optional[Relationship] = Field(default=None, alias="policy-checks")
    run_events: Optional[Relationship] = Field(default=None, alias="run-events")
    task_stages: Optional[Relationship] = Field(default=None, alias="task-stages")


RunResource = BaseTerraformResource[RunAttributes, RunRelationships]
RunResponse = TerraformAPIResponse[RunResource]


class RunStates:
    """Data class containing run state definitions for Terraform Cloud/Enterprise."""

    SUCCESS_STATES = [
        "planned",
        "planned_and_finished",
        "planned_and_saved",
        "applied",
        "discarded",
        "canceled",
        "force_canceled",
        "policy_override",
        "post_plan_completed",
        "post_plan_awaiting_decision",
    ]

    FAILURE_STATES = ["errored", "policy_soft_failed"]

    INTERMEDIATE_STATES = ["plan_queued", "queuing", "planning", "applying"]

    @classmethod
    def is_success_state(cls, state: str) -> bool:
        """Check if the given state is a success state."""
        return state in cls.SUCCESS_STATES

    @classmethod
    def is_failure_state(cls, state: str) -> bool:
        """Check if the given state is a failure state."""
        return state in cls.FAILURE_STATES

    @classmethod
    def is_intermediate_state(cls, state: str) -> bool:
        """Check if the given state is an intermediate state."""
        return state in cls.INTERMEDIATE_STATES

    @classmethod
    def is_final_state(cls, state: str) -> bool:
        """Check if the given state is a final state (success or failure)."""
        return cls.is_success_state(state) or cls.is_failure_state(state)
