"""
Pydantic models for Terraform Cloud/Enterprise Run resources.

This module contains models specifically for run-related API operations.
"""

from typing import List, Literal, Optional

from .common import (
    BaseModel,
    BaseRequest,
    BaseTerraformResource,
    ConfigDict,
    Field,
    Relationship,
    StrictBool,
    StrictStr,
    create_configuration_version_reference,
    create_workspace_reference,
)


class Variables(BaseModel):
    """Model for variables in run requests."""

    model_config = ConfigDict(populate_by_name=True)

    key: StrictStr
    value: StrictStr


class RunAttributes(BaseModel):
    """Attributes for run resources with comprehensive run-specific fields."""

    model_config = ConfigDict(populate_by_name=True)

    run_message: Optional[StrictStr] = Field(None, alias="message")
    refresh_only: Optional[StrictBool] = Field(None, alias="refresh-only")
    plan_only: Optional[StrictBool] = Field(None, alias="plan-only")
    auto_apply: Optional[StrictBool] = Field(None, alias="auto-apply")
    save_plan: Optional[StrictBool] = Field(None, alias="save-plan")
    is_destroy: Optional[StrictBool] = Field(None, alias="is-destroy")
    target_addrs: Optional[List[StrictStr]] = Field(None, alias="target-addrs")
    replace_addrs: Optional[List[StrictStr]] = Field(None, alias="replace-addrs")
    refresh: Optional[StrictBool] = None
    variables: Optional[List[Variables]] = None
    allow_empty_apply: Optional[StrictBool] = Field(None, alias="allow-empty-apply")
    allow_config_generation: Optional[StrictBool] = Field(None, alias="allow-config-generation")
    debugging_mode: Optional[StrictBool] = Field(None, alias="debugging-mode")
    terraform_version: Optional[StrictStr] = Field(None, alias="terraform-version")


class RunRelationships(BaseModel):
    """Relationships for run resources."""

    model_config = ConfigDict(populate_by_name=True)

    workspace: Optional[Relationship] = None
    configuration_version: Optional[Relationship] = Field(default=None, alias="configuration-version")
    # the below relationships are not used in the run request, but are used in the run response
    policy_checks: Optional[Relationship] = Field(default=None, alias="policy-checks")
    run_events: Optional[Relationship] = Field(default=None, alias="run-events")
    task_stages: Optional[Relationship] = Field(default=None, alias="task-stages")


class RunData(BaseTerraformResource[RunAttributes, RunRelationships]):
    """Model for run data in API requests."""

    model_config = ConfigDict(populate_by_name=True)
    type: Literal["runs"] = "runs"


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
                         Can use either field names (run_message) or aliases (message)

        Returns:
            A complete RunRequest with all nested structure built automatically
        """
        # Create relationships using common utilities
        relationships = RunRelationships(workspace=Relationship(data=create_workspace_reference(workspace_id)))

        if configuration_version_id:
            relationships.configuration_version = Relationship(data=create_configuration_version_reference(configuration_version_id))

        return cls(
            data=RunData(
                type="runs",
                attributes=RunAttributes.model_validate(attributes),
                relationships=relationships,
            )
        )


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
