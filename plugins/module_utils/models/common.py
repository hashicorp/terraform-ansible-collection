from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from datetime import datetime
from pydantic import BaseModel, Field


T = TypeVar('T')
AttributesType = TypeVar('AttributesType', bound=BaseModel)
RelationshipsType = TypeVar('RelationshipsType', bound=BaseModel)


class ResourceData(BaseModel):
    """Base model for resource data in relationships."""
    type: str
    id: str


class Relationship(BaseModel):
    """Generic relationship model."""
    data: Optional[Union[ResourceData, List[ResourceData]]] = None
    links: Optional[Dict[str, str]] = None


class Links(BaseModel):
    """Common links structure for API responses."""
    self: Optional[str] = None
    related: Optional[str] = None
    download: Optional[str] = None


class BaseTerraformResource(BaseModel, Generic[AttributesType, RelationshipsType]):
    """
    Generic base model for Terraform Cloud/Enterprise API resources.

    This model provides the common structure used by most Terraform API responses:
    - id: Resource identifier
    - type: Resource type
    - attributes: Resource-specific attributes
    - relationships: Related resources
    - links: API links for the resource
    """
    id: Optional[str] = None
    type: str
    attributes: Optional[AttributesType] = None
    relationships: Optional[RelationshipsType] = None
    links: Optional[Links] = None


class BaseRequest(BaseModel, Generic[T]):
    """Base model for API request payloads."""
    data: T

    class Config:
        populate_by_name = True


class BaseAttributes(BaseModel):
    """Base attributes model with common timestamp fields."""
    created_at: Optional[datetime] = Field(None, alias="created-at")
    updated_at: Optional[datetime] = Field(None, alias="updated-at")

    class Config:
        populate_by_name = True


class BaseRelationships(BaseModel):
    """Base relationships model."""

    class Config:
        populate_by_name = True
        extra = "allow"


class TerraformAPIResponse(BaseModel, Generic[T]):
    """Generic model for Terraform API responses."""
    data: Optional[Union[T, List[T]]] = None
    included: Optional[List[Dict[str, Any]]] = None
    meta: Optional[Dict[str, Any]] = None
    links: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None


def create_workspace_reference(workspace_id: str) -> ResourceData:
    """Create a workspace reference for use in relationships."""
    return ResourceData(type="workspaces", id=workspace_id)


def create_configuration_version_reference(config_version_id: str) -> ResourceData:
    """Create a configuration version reference for use in relationships."""
    return ResourceData(type="configuration-versions", id=config_version_id)


def create_organization_reference(organization_name: str) -> ResourceData:
    """Create an organization reference for use in relationships."""
    return ResourceData(type="organizations", id=organization_name)


def create_run_reference(run_id: str) -> ResourceData:
    """Create a run reference for use in relationships."""
    return ResourceData(type="runs", id=run_id)
