"""
Pydantic models for Terraform Cloud/Enterprise Run resources.

This module contains models specifically for run-related API operations.
"""

from typing import Any, Dict, List, Literal, Optional


try:
    from pydantic import BaseModel, Field, StrictBool, StrictStr

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

    class BaseModel:
        """Fallback BaseModel class for when pydantic is not available."""

        pass

    def Field(*args, **kwargs):
        """Fallback Field class for when pydantic is not available."""
        return None

    StrictBool = bool
    StrictStr = str

from .common import (
    BaseAttributes,
    BaseRelationships,
    BaseRequest,
    BaseTerraformResource,
    Relationship,
    TerraformAPIResponse,
    create_configuration_version_reference,
    create_workspace_reference,
)


class RunAttributes(BaseAttributes):
    """Attributes for run resources with comprehensive run-specific fields."""

    run_message: Optional[StrictStr] = Field(None, alias="message")
    refresh_only: Optional[StrictBool] = Field(None, alias="refresh-only")
    plan_only: Optional[StrictBool] = Field(None, alias="plan-only")
    auto_apply: Optional[StrictBool] = Field(None, alias="auto-apply")
    save_plan: Optional[StrictBool] = Field(None, alias="save-plan")
    is_destroy: Optional[StrictBool] = Field(None, alias="is-destroy")
    target_addrs: Optional[List[StrictStr]] = Field(None, alias="target-addrs")
    replace_addrs: Optional[List[StrictStr]] = Field(None, alias="replace-addrs")
    refresh: Optional[StrictBool] = None
    variables: Optional[Dict[str, Any]] = None
    allow_empty_apply: Optional[StrictBool] = Field(None, alias="allow-empty-apply")
    allow_config_generation: Optional[StrictBool] = Field(None, alias="allow-config-generation")
    debugging_mode: Optional[StrictBool] = Field(None, alias="debugging-mode")
    terraform_version: Optional[StrictStr] = Field(None, alias="terraform-version")


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


class RunData(BaseModel):
    """Model for run data in API requests."""

    attributes: RunAttributes
    type: Literal["runs"] = "runs"
    relationships: RunRelationships

    class Config:
        populate_by_name = True


class RunRequest(BaseRequest[RunData]):
    """Model for the complete run request."""

    @classmethod
    def create(cls, workspace_id: str, configuration_version_id: Optional[str] = None, **attributes) -> "RunRequest":
        """
        Create a RunRequest with workspace_id and optional configuration version.

        Args:
            workspace_id: The workspace ID
            configuration_version_id: Optional configuration version ID
            **attributes: Any run attributes (message, plan_only, auto_apply, etc.)

        Returns:
            A complete RunRequest with all nested structure built automatically
        """
        # Create relationships using common utilities
        relationships = RunRelationships(workspace=Relationship(data=create_workspace_reference(workspace_id)))

        if configuration_version_id:
            relationships.configuration_version = Relationship(data=create_configuration_version_reference(configuration_version_id))

        return cls(
            data=RunData(
                attributes=RunAttributes(**attributes),
                relationships=relationships,
            )
        )


# aliases using common models
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


def create_run_request(
    workspace_id: str,
    message: Optional[str] = None,
    auto_apply: Optional[bool] = None,
    plan_only: Optional[bool] = None,
    is_destroy: Optional[bool] = None,
    configuration_version_id: Optional[str] = None,
    **kwargs,
) -> RunRequest:
    """
    Enhanced factory function to create run requests with better API.

    Args:
        workspace_id: The workspace ID
        message: Optional message for the run
        auto_apply: Whether to auto-apply the run
        plan_only: Whether this is a plan-only run
        is_destroy: Whether this is a destroy run
        configuration_version_id: Optional configuration version ID
        **kwargs: Additional run attributes

    Returns:
        A configured RunRequest instance
    """
    attributes: Dict[str, Any] = {}
    if message is not None:
        attributes["message"] = message
    if auto_apply is not None:
        attributes["auto_apply"] = auto_apply
    if plan_only is not None:
        attributes["plan_only"] = plan_only
    if is_destroy is not None:
        attributes["is_destroy"] = is_destroy

    attributes.update(kwargs)

    return RunRequest.create(workspace_id=workspace_id, configuration_version_id=configuration_version_id, **attributes)


def create_workspace_run_relationship(workspace_id: str) -> Relationship:
    """Create a workspace relationship for run requests."""
    return Relationship(data=create_workspace_reference(workspace_id))


def create_configuration_version_run_relationship(config_version_id: str) -> Relationship:
    """Create a configuration version relationship for run requests."""
    return Relationship(data=create_configuration_version_reference(config_version_id))
