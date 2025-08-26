"""
Pydantic models for Terraform Cloud/Enterprise Run resources.

This module contains models specifically for run-related API operations.
"""

from typing import Any, Dict, List, Literal, Optional

from .common import (
    BaseModel,
    BaseRequest,
    BaseTerraformResource,
    ConfigDict,
    Field,
    Relationship,
    StrictBool,
    StrictStr,
    create_project_reference,
)


class WorkspaceAttributes(BaseModel):
    """Model for workspace attributes."""

    name: Optional[StrictStr] = None
    allow_destroy_plan: Optional[StrictBool] = Field(None, alias="allow-destroy-plan")
    assessments_enabled: Optional[StrictBool] = Field(None, alias="assessments-enabled")
    auto_apply: Optional[StrictBool] = Field(None, alias="auto-apply")
    auto_apply_run_trigger: Optional[StrictBool] = Field(None, alias="auto-apply-run-trigger")
    auto_destroy_at: Optional[StrictStr] = Field(None, alias="auto_destroy_at")
    auto_destroy_activity_duration: Optional[StrictStr] = Field(None, alias="auto-destroy-activity-duration")
    source_name: Optional[StrictStr] = Field(None, alias="source-name")
    source_url: Optional[StrictStr] = Field(None, alias="source-url")
    description: Optional[StrictStr] = None
    terraform_version: Optional[StrictStr] = Field(None, alias="terraform-version")
    execution_mode: Optional[StrictStr] = Field(None, alias="execution-mode")
    agent_pool_id: Optional[StrictStr] = Field(None, alias="agent-pool-id")
    setting_overwrites: Optional[Dict[str, bool]] = Field(None, alias="setting-overwrites")

    model_config = ConfigDict(populate_by_name=True)


class TagBindingAttributes(BaseModel):
    key: StrictStr
    value: StrictStr


class TagBindingResourceData(BaseModel):
    type: Literal["tag-bindings"]
    attributes: TagBindingAttributes


class TagBindingsRelationship(BaseModel):
    data: Optional[List[TagBindingResourceData]] = None


class WorkspaceRelationships(BaseModel):
    """Relationships for workspace resources."""

    model_config = ConfigDict(populate_by_name=True)

    project: Optional[Relationship] = None
    tag_bindings: Optional[TagBindingsRelationship] = Field(None, alias="tag-bindings")


class WorkspaceData(BaseTerraformResource[WorkspaceAttributes, WorkspaceRelationships]):
    """Model for workspace data."""

    model_config = ConfigDict(populate_by_name=True)
    type: Literal["workspaces"]


class WorkspaceRequest(BaseRequest[WorkspaceData]):
    """Model for the complete workspace request."""

    @staticmethod
    def create_tag_bindings_reference(tag_bindings: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Create a list of tag-binding resource dictionaries for use in relationships.

        Args:
            tag_bindings: A dictionary like {"environment": "uat", "team": "devops"}

        Returns:
            A list of dictionaries representing tag-binding resources
        """
        return [TagBindingResourceData(type="tag-bindings", attributes=TagBindingAttributes(key=key, value=value)) for key, value in tag_bindings.items()]

    @classmethod
    def create(cls, project_id: Optional[str] = None, tag_bindings: Optional[Dict[str, str]] = None, **attributes) -> "WorkspaceRequest":
        """
        Create a WorkspaceRequest with organization.
        Args:
            oragnization: The organization name
            project_id: Optional project ID
            **attributes: Any workspace attributes
        Returns:
            A complete WorkspaceRequest with all nested structure built automatically
        """
        relationships = WorkspaceRelationships()
        if project_id:
            relationships.project = Relationship(data=create_project_reference(project_id))

        # Add configuration version if provided
        if tag_bindings:
            relationships.tag_bindings = TagBindingsRelationship(data=cls.create_tag_bindings_reference(tag_bindings))
        return cls(
            data=WorkspaceData(
                type="workspaces",
                attributes=WorkspaceAttributes.model_validate(attributes),
                relationships=relationships,
            )
        )
