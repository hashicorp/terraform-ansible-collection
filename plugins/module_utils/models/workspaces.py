from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, StrictBool, StrictStr

from .common import (
    BaseAttributes,
    BaseRelationships,
    BaseRequest,
    BaseTerraformResource,
    Relationship,
    TerraformAPIResponse,
    create_organization_reference,
)


class WorkspaceAttributes(BaseAttributes):
    """Attributes for workspace resources."""
    name: Optional[StrictStr] = None
    description: Optional[StrictStr] = None
    auto_apply: Optional[StrictBool] = Field(None, alias="auto-apply")
    working_directory: Optional[StrictStr] = Field(None, alias="working-directory")
    terraform_version: Optional[StrictStr] = Field(None, alias="terraform-version")
    execution_mode: Optional[Literal["remote", "local", "agent"]] = Field(None, alias="execution-mode")
    environment: Optional[Dict[str, str]] = None
    locked: Optional[StrictBool] = None
    queue_all_runs: Optional[StrictBool] = Field(None, alias="queue-all-runs")
    speculative_enabled: Optional[StrictBool] = Field(None, alias="speculative-enabled")
    structured_run_output_enabled: Optional[StrictBool] = Field(None, alias="structured-run-output-enabled")
    file_triggers_enabled: Optional[StrictBool] = Field(None, alias="file-triggers-enabled")
    trigger_prefixes: Optional[List[str]] = Field(None, alias="trigger-prefixes")
    vcs_repo: Optional[Dict[str, Any]] = Field(None, alias="vcs-repo")
    resource_count: Optional[int] = Field(None, alias="resource-count")
    apply_duration_average: Optional[int] = Field(None, alias="apply-duration-average")
    plan_duration_average: Optional[int] = Field(None, alias="plan-duration-average")
    policy_check_failures: Optional[int] = Field(None, alias="policy-check-failures")
    run_failures: Optional[int] = Field(None, alias="run-failures")
    workspace_kpis_runs_count: Optional[int] = Field(None, alias="workspace-kpis-runs-count")


class WorkspaceRelationships(BaseRelationships):
    """Relationships for workspace resources."""
    organization: Optional[Relationship] = None
    current_run: Optional[Relationship] = Field(default=None, alias="current-run")
    current_state_version: Optional[Relationship] = Field(default=None, alias="current-state-version")
    current_configuration_version: Optional[Relationship] = Field(default=None, alias="current-configuration-version")
    agent_pool: Optional[Relationship] = Field(default=None, alias="agent-pool")
    ssh_key: Optional[Relationship] = Field(default=None, alias="ssh-key")


class WorkspaceData(BaseModel):
    """Model for workspace data."""
    type: Literal["workspaces"] = "workspaces"
    attributes: Optional[WorkspaceAttributes] = None
    relationships: Optional[WorkspaceRelationships] = None


class WorkspaceRequest(BaseRequest[WorkspaceData]):
    """Model for workspace API requests."""

    @classmethod
    def create(
        cls,
        name: str,
        organization_name: Optional[str] = None,
        **attributes
    ) -> "WorkspaceRequest":
        """
        Create a WorkspaceRequest with simplified interface.

        Args:
            name: Workspace name
            organization_name: Organization name (if needed for relationships)
            **attributes: Additional workspace attributes

        Returns:
            A complete WorkspaceRequest
        """
        workspace_attrs = WorkspaceAttributes(name=name, **attributes)
        relationships = None

        if organization_name:
            relationships = WorkspaceRelationships()
            relationships.organization = Relationship(
                data=create_organization_reference(organization_name)
            )

        return cls(
            data=WorkspaceData(
                attributes=workspace_attrs,
                relationships=relationships
            )
        )


# Type aliases for convenience
WorkspaceResource = BaseTerraformResource[WorkspaceAttributes, WorkspaceRelationships]
WorkspaceResponse = TerraformAPIResponse[WorkspaceResource]
