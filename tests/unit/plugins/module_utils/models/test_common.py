# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from datetime import datetime
from typing import Optional

import pytest

from pydantic import ValidationError

from ansible_collections.hashicorp.terraform.plugins.module_utils.models.common import (
    BaseAttributes,
    BaseRelationships,
    BaseRequest,
    BaseTerraformResource,
    Links,
    Relationship,
    ResourceData,
    TerraformAPIResponse,
    create_configuration_version_reference,
    create_organization_reference,
    create_run_reference,
    create_workspace_reference,
)


class TestResourceData:
    """Test cases for ResourceData model."""

    def test_resource_data_creation(self):
        """Test creating ResourceData with valid data."""
        resource = ResourceData(type="workspaces", id="ws-123")

        assert resource.type == "workspaces"
        assert resource.id == "ws-123"

    def test_resource_data_dict_output(self):
        """Test ResourceData dictionary output."""
        resource = ResourceData(type="runs", id="run-456")
        data = resource.model_dump()

        assert data == {"type": "runs", "id": "run-456"}

    def test_resource_data_validation(self):
        """Test ResourceData validation with invalid data."""
        # Test missing required fields
        with pytest.raises(ValidationError):
            ResourceData()

        with pytest.raises(ValidationError):
            ResourceData(type="workspaces")

        with pytest.raises(ValidationError):
            ResourceData(id="ws-123")


class TestRelationship:
    """Test cases for Relationship model."""

    def test_relationship_with_single_data(self):
        """Test Relationship with single ResourceData."""
        data = ResourceData(type="workspaces", id="ws-123")
        relationship = Relationship(data=data)

        assert relationship.data.type == "workspaces"
        assert relationship.data.id == "ws-123"
        assert relationship.links is None

    def test_relationship_with_multiple_data(self):
        """Test Relationship with list of ResourceData."""
        data = [
            ResourceData(type="runs", id="run-1"),
            ResourceData(type="runs", id="run-2"),
        ]
        relationship = Relationship(data=data)

        assert len(relationship.data) == 2
        assert relationship.data[0].id == "run-1"
        assert relationship.data[1].id == "run-2"

    def test_relationship_with_links(self):
        """Test Relationship with links."""
        data = ResourceData(type="workspaces", id="ws-123")
        links = {"self": "/api/v2/workspaces/ws-123"}
        relationship = Relationship(data=data, links=links)

        assert relationship.data.id == "ws-123"
        assert relationship.links["self"] == "/api/v2/workspaces/ws-123"

    def test_relationship_empty(self):
        """Test empty Relationship."""
        relationship = Relationship()

        assert relationship.data is None
        assert relationship.links is None


class TestLinks:
    """Test cases for Links model."""

    def test_links_creation(self):
        """Test creating Links with all fields."""
        links = Links(self="/api/v2/workspaces/ws-123", related="/api/v2/workspaces/ws-123/runs", download="/api/v2/workspaces/ws-123/download")

        assert links.self == "/api/v2/workspaces/ws-123"
        assert links.related == "/api/v2/workspaces/ws-123/runs"
        assert links.download == "/api/v2/workspaces/ws-123/download"

    def test_links_partial(self):
        """Test creating Links with partial fields."""
        links = Links(self="/api/v2/workspaces/ws-123")

        assert links.self == "/api/v2/workspaces/ws-123"
        assert links.related is None
        assert links.download is None

    def test_links_empty(self):
        """Test creating empty Links."""
        links = Links()

        assert links.self is None
        assert links.related is None
        assert links.download is None


class TestBaseAttributes:
    """Test cases for BaseAttributes model."""

    def test_base_attributes_with_timestamps(self):
        """Test BaseAttributes with timestamp fields."""
        now = datetime.now()
        attrs = BaseAttributes(created_at=now, updated_at=now)

        assert attrs.created_at == now
        assert attrs.updated_at == now

    def test_base_attributes_with_aliases(self):
        """Test BaseAttributes with field aliases."""
        now = datetime.now()
        data = {"created-at": now.isoformat(), "updated-at": now.isoformat()}
        attrs = BaseAttributes.model_validate(data)

        assert attrs.created_at is not None
        assert attrs.updated_at is not None

    def test_base_attributes_empty(self):
        """Test empty BaseAttributes."""
        attrs = BaseAttributes()

        assert attrs.created_at is None
        assert attrs.updated_at is None

    def test_base_attributes_serialization_with_aliases(self):
        """Test BaseAttributes serialization uses aliases."""
        now = datetime.now()
        attrs = BaseAttributes(created_at=now, updated_at=now)
        data = attrs.model_dump(by_alias=True, exclude_unset=True)

        assert "created-at" in data
        assert "updated-at" in data
        assert "created_at" not in data
        assert "updated_at" not in data


class TestBaseRelationships:
    """Test cases for BaseRelationships model."""

    def test_base_relationships_creation(self):
        """Test creating BaseRelationships."""
        relationships = BaseRelationships()
        assert relationships is not None

    def test_base_relationships_extra_fields(self):
        """Test BaseRelationships allows extra fields."""
        data = {"workspace": {"data": {"type": "workspaces", "id": "ws-123"}}, "custom_field": {"data": {"type": "custom", "id": "custom-123"}}}
        relationships = BaseRelationships.model_validate(data)

        # Should not raise validation error due to extra="allow"
        assert relationships is not None


class SampleAttributes(BaseAttributes):
    """Sample attributes class for testing."""

    name: str
    description: Optional[str] = None


class SampleRelationships(BaseRelationships):
    """Sample relationships class for testing."""

    workspace: Optional[Relationship] = None
    organization: Optional[Relationship] = None


class TestBaseTerraformResource:
    """Test cases for BaseTerraformResource model."""

    def test_base_terraform_resource_creation(self):
        """Test creating BaseTerraformResource with all fields."""
        attributes = SampleAttributes(name="test-resource")
        relationships = SampleRelationships()
        links = Links(self="/api/v2/test/123")

        resource = BaseTerraformResource[SampleAttributes, SampleRelationships](
            id="test-123", type="test-resources", attributes=attributes, relationships=relationships, links=links
        )

        assert resource.id == "test-123"
        assert resource.type == "test-resources"
        assert resource.attributes.name == "test-resource"
        assert resource.relationships is not None
        assert resource.links.self == "/api/v2/test/123"

    def test_base_terraform_resource_minimal(self):
        """Test creating BaseTerraformResource with minimal fields."""
        resource = BaseTerraformResource[SampleAttributes, SampleRelationships](type="test-resources")

        assert resource.id is None
        assert resource.type == "test-resources"
        assert resource.attributes is None
        assert resource.relationships is None
        assert resource.links is None

    def test_base_terraform_resource_validation(self):
        """Test BaseTerraformResource validation."""
        # Type is required
        with pytest.raises(ValidationError):
            BaseTerraformResource[SampleAttributes, SampleRelationships]()


class SampleData(BaseAttributes):
    """Sample data for testing BaseRequest."""

    action: str


class TestBaseRequest:
    """Test cases for BaseRequest model."""

    def test_base_request_creation(self):
        """Test creating BaseRequest."""
        data = SampleData(action="create")
        request = BaseRequest[SampleData](data=data)

        assert request.data.action == "create"

    def test_base_request_validation(self):
        """Test BaseRequest validation."""
        # Data is required
        with pytest.raises(ValidationError):
            BaseRequest[SampleData]()

    def test_base_request_config(self):
        """Test BaseRequest configuration."""
        # Test that populate_by_name is enabled
        data = SampleData(action="test")
        request = BaseRequest[SampleData](data=data)

        # Should be able to serialize using field names
        serialized = request.model_dump(by_alias=True)
        assert "data" in serialized


class TestTerraformAPIResponse:
    """Test cases for TerraformAPIResponse model."""

    def test_terraform_api_response_with_single_resource(self):
        """Test TerraformAPIResponse with single resource."""
        resource = BaseTerraformResource[SampleAttributes, SampleRelationships](id="test-123", type="test-resources")
        response = TerraformAPIResponse[BaseTerraformResource[SampleAttributes, SampleRelationships]](data=resource)

        assert response.data.id == "test-123"
        assert response.data.type == "test-resources"

    def test_terraform_api_response_with_multiple_resources(self):
        """Test TerraformAPIResponse with multiple resources."""
        resources = [
            BaseTerraformResource[SampleAttributes, SampleRelationships](id="test-1", type="test-resources"),
            BaseTerraformResource[SampleAttributes, SampleRelationships](id="test-2", type="test-resources"),
        ]
        response = TerraformAPIResponse[BaseTerraformResource[SampleAttributes, SampleRelationships]](data=resources)

        assert len(response.data) == 2
        assert response.data[0].id == "test-1"
        assert response.data[1].id == "test-2"

    def test_terraform_api_response_with_meta_and_links(self):
        """Test TerraformAPIResponse with meta and links."""
        response = TerraformAPIResponse[BaseTerraformResource[SampleAttributes, SampleRelationships]](
            data=None, meta={"total": 100, "page": 1}, links={"next": "/api/v2/test?page=2"}
        )

        assert response.data is None
        assert response.meta["total"] == 100
        assert response.links["next"] == "/api/v2/test?page=2"

    def test_terraform_api_response_with_errors(self):
        """Test TerraformAPIResponse with errors."""
        errors = [{"detail": "Resource not found", "status": "404"}, {"detail": "Validation failed", "status": "422"}]
        response = TerraformAPIResponse[BaseTerraformResource[SampleAttributes, SampleRelationships]](errors=errors)

        assert len(response.errors) == 2
        assert response.errors[0]["detail"] == "Resource not found"
        assert response.errors[1]["status"] == "422"

    def test_terraform_api_response_empty(self):
        """Test empty TerraformAPIResponse."""
        response = TerraformAPIResponse[BaseTerraformResource[SampleAttributes, SampleRelationships]]()

        assert response.data is None
        assert response.included is None
        assert response.meta is None
        assert response.links is None
        assert response.errors is None


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_create_workspace_reference(self):
        """Test create_workspace_reference function."""
        ref = create_workspace_reference("ws-12345")

        assert ref.type == "workspaces"
        assert ref.id == "ws-12345"

    def test_create_configuration_version_reference(self):
        """Test create_configuration_version_reference function."""
        ref = create_configuration_version_reference("cv-67890")

        assert ref.type == "configuration-versions"
        assert ref.id == "cv-67890"

    def test_create_organization_reference(self):
        """Test create_organization_reference function."""
        ref = create_organization_reference("my-org")

        assert ref.type == "organizations"
        assert ref.id == "my-org"

    def test_create_run_reference(self):
        """Test create_run_reference function."""
        ref = create_run_reference("run-abcdef")

        assert ref.type == "runs"
        assert ref.id == "run-abcdef"

    def test_utility_functions_with_empty_strings(self):
        """Test utility functions with empty strings."""
        # Should still work with empty strings
        ref = create_workspace_reference("")
        assert ref.type == "workspaces"
        assert ref.id == ""

    def test_utility_functions_with_special_characters(self):
        """Test utility functions with special characters."""
        ref = create_workspace_reference("ws-test_123-abc")
        assert ref.type == "workspaces"
        assert ref.id == "ws-test_123-abc"


class TestCommonModelsIntegration:
    """Integration tests for common models working together."""

    def test_complex_terraform_resource_structure(self):
        """Test complex Terraform resource with all components."""
        # Create attributes
        attributes = SampleAttributes(name="test-workspace", description="A test workspace")

        # Create relationships
        org_ref = create_organization_reference("my-org")
        relationships = SampleRelationships(organization=Relationship(data=org_ref))

        # Create links
        links = Links(self="/api/v2/workspaces/ws-123", related="/api/v2/workspaces/ws-123/runs")

        # Create resource
        resource = BaseTerraformResource[SampleAttributes, SampleRelationships](
            id="ws-123", type="workspaces", attributes=attributes, relationships=relationships, links=links
        )

        # Create API response
        response = TerraformAPIResponse[BaseTerraformResource[SampleAttributes, SampleRelationships]](data=resource, meta={"request-id": "req-123"})

        # Verify the complete structure
        assert response.data.id == "ws-123"
        assert response.data.attributes.name == "test-workspace"
        assert response.data.relationships.organization.data.type == "organizations"
        assert response.data.relationships.organization.data.id == "my-org"
        assert response.data.links.self == "/api/v2/workspaces/ws-123"
        assert response.meta["request-id"] == "req-123"

    def test_serialization_with_aliases(self):
        """Test complete serialization with field aliases."""
        now = datetime.now()
        attributes = SampleAttributes(name="test-resource", created_at=now, updated_at=now)

        resource = BaseTerraformResource[SampleAttributes, SampleRelationships](type="test-resources", attributes=attributes)

        # Serialize with aliases
        data = resource.model_dump(by_alias=True, exclude_unset=True)

        assert data["type"] == "test-resources"
        assert data["attributes"]["name"] == "test-resource"
        assert "created-at" in data["attributes"]
        assert "updated-at" in data["attributes"]
        assert "created_at" not in data["attributes"]

    def test_deserialization_from_api_response(self):
        """Test deserializing from typical API response format."""
        api_data = {
            "data": {
                "id": "ws-123",
                "type": "workspaces",
                "attributes": {"name": "my-workspace", "created-at": "2023-01-01T00:00:00Z", "updated-at": "2023-01-02T00:00:00Z"},
                "relationships": {"organization": {"data": {"type": "organizations", "id": "org-123"}}},
                "links": {"self": "/api/v2/workspaces/ws-123"},
            },
            "meta": {"request-id": "req-456"},
        }

        response = TerraformAPIResponse[BaseTerraformResource[SampleAttributes, SampleRelationships]].model_validate(api_data)

        assert response.data.id == "ws-123"
        assert response.data.attributes.name == "my-workspace"
        assert response.data.attributes.created_at is not None
        assert response.data.relationships.organization.data.id == "org-123"
        assert response.meta["request-id"] == "req-456"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_relationship_data(self):
        """Test handling invalid relationship data."""
        # Test with invalid data structure
        with pytest.raises(ValidationError):
            Relationship(data={"invalid": "structure"})

    def test_type_validation_in_generic_models(self):
        """Test type validation in generic models."""
        # Test with wrong attribute type
        with pytest.raises(ValidationError):
            BaseTerraformResource[SampleAttributes, SampleRelationships](type="test", attributes="invalid_type")  # Should be SampleAttributes instance

    def test_nested_validation_errors(self):
        """Test nested validation errors propagate correctly."""
        with pytest.raises(ValidationError):
            TerraformAPIResponse[BaseTerraformResource[SampleAttributes, SampleRelationships]](
                data=BaseTerraformResource[SampleAttributes, SampleRelationships](
                    # Missing required 'type' field
                    attributes=SampleAttributes(name="test")
                )
            )

    def test_list_validation_in_relationships(self):
        """Test list validation in relationships."""
        # Valid list
        valid_data = [ResourceData(type="runs", id="run-1"), ResourceData(type="runs", id="run-2")]
        relationship = Relationship(data=valid_data)
        assert len(relationship.data) == 2

        # Invalid list item
        with pytest.raises(ValidationError):
            Relationship(data=[ResourceData(type="runs", id="run-1"), {"invalid": "item"}])
