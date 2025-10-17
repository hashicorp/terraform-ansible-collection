from typing import Any, Dict, Generic, List, Optional, TypeVar, Union


HAS_PYDANTIC = False

# Import pydantic components with fallbacks
try:
    from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StrictBool, StrictStr

    HAS_PYDANTIC = True
except ImportError:
    # Fallback implementations when pydantic is not available
    class BaseModel:  # type: ignore[no-redef]
        """Fallback BaseModel class for when pydantic is not available."""

        pass

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[no-redef]
        """Fallback Field function for when pydantic is not available."""
        return None

    # Create fallback types - use built-in types directly
    StrictBool = bool  # type: ignore[misc,assignment]
    StrictStr = str  # type: ignore[misc,assignment]

    class ConfigDict:  # type: ignore[no-redef]
        """Fallback ConfigDict for when pydantic is not available."""

        def __init__(self, populate_by_name: Any = None, **kwargs: Any) -> None:
            self.populate_by_name = populate_by_name
            for key, value in kwargs.items():
                setattr(self, key, value)


T = TypeVar("T")
AttributesType = TypeVar("AttributesType", bound=BaseModel)
RelationshipsType = TypeVar("RelationshipsType", bound=BaseModel)


class ResourceData(BaseModel):
    """Base model for resource data in relationships."""

    type: str
    id: str


class Relationship(BaseModel):
    """Generic relationship model."""

    data: Optional[Union[ResourceData, List[ResourceData]]] = None
    links: Optional[Dict[str, str]] = None


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


ResourceType = TypeVar("ResourceType", bound="BaseTerraformResource")


class BaseRequest(BaseModel, Generic[ResourceType]):
    """Base model for API request payloads."""

    data: ResourceType


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


def create_project_reference(project_id: str) -> ResourceData:
    return ResourceData(type="projects", id=project_id)


# Explicitly declare exports to avoid pylint unused-import warnings
__all__ = [
    # Pydantic re-exports (used by other model files)
    "BaseModel",
    "ConfigDict",
    "Field",
    "StrictBool",
    "StrictStr",
    # Model classes
    "ResourceData",
    "Relationship",
    "BaseTerraformResource",
    "BaseRequest",
    "TerraformAPIResponse",
    # Utility functions
    "create_workspace_reference",
    "create_configuration_version_reference",
    "create_organization_reference",
    "create_run_reference",
    # Constants
    "HAS_PYDANTIC",
    "AliasChoices",
]
