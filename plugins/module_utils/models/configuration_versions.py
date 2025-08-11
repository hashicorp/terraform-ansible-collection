
from typing import Dict, List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field, StrictBool

from .common import (
    BaseAttributes,
    BaseRelationships,
    BaseRequest,
    BaseTerraformResource,
    Relationship,
    TerraformAPIResponse,
)


class ConfigurationVersionAttributes(BaseAttributes):
    """Attributes for configuration version resources."""
    auto_queue_runs: Optional[StrictBool] = Field(None, alias="auto-queue-runs")
    speculative: Optional[StrictBool] = None
    provisional: Optional[StrictBool] = None
    status: Optional[Literal["pending", "fetching", "uploaded", "errored", "archived"]] = None
    error: Optional[str] = None
    error_message: Optional[str] = Field(None, alias="error-message")
    source: Optional[Literal[
        "tfe-api", "tfe-ui", "tfe-cli", "github",
        "gitlab", "bitbucket", "ado", "terraform-cloud-operator"
    ]] = None
    upload_url: Optional[str] = Field(None, alias="upload-url")
    status_timestamps: Optional[Dict[str, datetime]] = Field(None, alias="status-timestamps")
    changed_files: Optional[List[str]] = Field(None, alias="changed-files")


class ConfigurationVersionRelationships(BaseRelationships):
    """Relationships for configuration version resources."""
    ingress_attributes: Optional[Relationship] = Field(default=None, alias="ingress-attributes")


class ConfigurationVersionData(BaseModel):
    """Model for configuration version data."""
    type: Literal["configuration-versions"] = "configuration-versions"
    attributes: Optional[ConfigurationVersionAttributes] = None
    relationships: Optional[ConfigurationVersionRelationships] = None


class ConfigurationVersionRequest(BaseRequest[ConfigurationVersionData]):
    """Model for configuration version API requests."""

    @classmethod
    def create(
        cls,
        auto_queue_runs: bool = True,
        speculative: bool = False,
        provisional: bool = False,
        **attributes
    ) -> "ConfigurationVersionRequest":
        """
        Create a ConfigurationVersionRequest with simplified interface.

        Args:
            auto_queue_runs: Whether to auto-queue runs
            speculative: Whether this is a speculative configuration
            provisional: Whether this is provisional
            **attributes: Additional configuration version attributes

        Returns:
            A complete ConfigurationVersionRequest
        """
        # Use alias for auto_queue_runs to match the field definition
        attributes_dict = {
            "auto-queue-runs": auto_queue_runs,
            "speculative": speculative,
            "provisional": provisional,
            **attributes
        }
        config_attrs = ConfigurationVersionAttributes(**attributes_dict)

        relationships = ConfigurationVersionRelationships()

        return cls(
            data=ConfigurationVersionData(
                attributes=config_attrs,
                relationships=relationships
            )
        )


ConfigurationVersionResource = BaseTerraformResource[ConfigurationVersionAttributes, ConfigurationVersionRelationships]
ConfigurationVersionResponse = TerraformAPIResponse[ConfigurationVersionResource]


class ConfigurationVersionStates:
    """Data class containing configuration version state definitions."""

    PENDING_STATES = ["pending", "fetching"]
    SUCCESS_STATES = ["uploaded"]
    FAILURE_STATES = ["errored"]
    ARCHIVED_STATES = ["archived"]

    @classmethod
    def is_pending_state(cls, state: str) -> bool:
        """Check if the given state is a pending state."""
        return state in cls.PENDING_STATES

    @classmethod
    def is_success_state(cls, state: str) -> bool:
        """Check if the given state is a success state."""
        return state in cls.SUCCESS_STATES

    @classmethod
    def is_failure_state(cls, state: str) -> bool:
        """Check if the given state is a failure state."""
        return state in cls.FAILURE_STATES

    @classmethod
    def is_archived_state(cls, state: str) -> bool:
        """Check if the given state is an archived state."""
        return state in cls.ARCHIVED_STATES

    @classmethod
    def is_final_state(cls, state: str) -> bool:
        """Check if the given state is a final state (success, failure, or archived)."""
        return (cls.is_success_state(state) or
                cls.is_failure_state(state) or
                cls.is_archived_state(state))
