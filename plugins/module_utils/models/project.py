"""
Pydantic models for Terraform Cloud/Enterprise Project resources.

This module contains models specifically for project-related API operations.
"""

from typing import Dict, List, Literal, Optional

from .common import (
    BaseModel,
    BaseRequest,
    BaseTerraformResource,
    ConfigDict,
    Field,
    StrictStr,
)


class ProjectAttributes(BaseModel):
    """Attributes for project resources."""

    model_config = ConfigDict(populate_by_name=True)

    name: StrictStr
    description: Optional[StrictStr] = None
    auto_destroy_activity_duration: Optional[StrictStr] = Field(None, alias="auto-destroy-activity-duration")
    execution_mode: Optional[Literal["remote", "local"]] = None
    default_agent_pool_id: Optional[StrictStr] = Field(None, alias="default-agent-pool-id")
    setting_overwrites: Optional[Dict[str, bool]] = Field(None, alias="setting-overwrites")


class TagBindingAttributes(BaseModel):
    """Attributes for tag bindings resources."""

    model_config = ConfigDict(populate_by_name=True)

    key: StrictStr
    value: StrictStr


class TagBindingsRelationship(BaseModel):
    """Relationships for tag bindings resources."""

    model_config = ConfigDict(populate_by_name=True)

    data: Optional[List[TagBindingAttributes]] = None


class ProjectRelationships(BaseModel):
    """Relationships for project resources."""

    model_config = ConfigDict(populate_by_name=True)
    tag_bindings: Optional[TagBindingsRelationship] = Field(default=None, alias="tag-bindings")


class ProjectData(BaseTerraformResource[ProjectAttributes, ProjectRelationships]):
    """Model for project data in API requests."""

    model_config = ConfigDict(populate_by_name=True)
    type: Literal["projects"] = "projects"


class ProjectRequest(BaseRequest[ProjectData]):
    """Model for the complete project request."""

    @classmethod
    def create(cls, organization: str, **attributes) -> "ProjectRequest":
        """
        Create a ProjectRequest with organization.
        Args:
            organization: The organization name
            **attributes: Any project attributes
        Returns:
            A complete ProjectRequest with all nested structure built automatically
        """
        relationships = ProjectRelationships()
        if attributes.get("tag_bindings"):
            relationships.tag_bindings = TagBindingsRelationship(data=attributes["tag_bindings"])
        return cls(
            data=ProjectData(
                type="projects",
                attributes=ProjectAttributes.model_validate(attributes),
                relationships=relationships,
            )
        )
