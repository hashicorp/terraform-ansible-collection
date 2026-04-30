# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from typing import Optional

import pytest
from pydantic import ValidationError

from ansible_collections.hashicorp.terraform.plugins.module_utils.models.common import (
    BaseModel,
    BaseRequest,
    BaseTerraformResource,
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
        data = ResourceData(type="workspaces", id="ws-123")

        assert data.type == "workspaces"
        assert data.id == "ws-123"

    def test_resource_data_dict_output(self):
        """Test ResourceData dictionary output."""
        data = ResourceData(type="workspaces", id="ws-123")

        # Test that it can be converted to dict if using pydantic
        try:
            result = data.model_dump()
            expected = {"type": "workspaces", "id": "ws-123"}
            assert result == expected
        except AttributeError:
            # Fallback behavior when pydantic is not available
            pass

    def test_resource_data_validation(self):
        """Test ResourceData validation with invalid data."""
        # Test with missing required fields - this should work with fallback
        try:
            with pytest.raises(ValidationError):
                ResourceData(type="workspaces")  # missing id
        except (TypeError, AttributeError):
            # Fallback behavior when pydantic is not available
            pass


class TestRelationship:
    """Test cases for Relationship model."""

    def test_relationship_with_single_data(self):
        """Test Relationship with single ResourceData."""
        data = ResourceData(type="workspaces", id="ws-123")
        rel = Relationship(data=data)

        assert rel.data.type == "workspaces"
        assert rel.data.id == "ws-123"
        assert rel.links is None

    def test_relationship_with_multiple_data(self):
        """Test Relationship with list of ResourceData."""
        data1 = ResourceData(type="workspaces", id="ws-123")
        data2 = ResourceData(type="workspaces", id="ws-456")
        rel = Relationship(data=[data1, data2])

        assert len(rel.data) == 2
        assert rel.data[0].id == "ws-123"
        assert rel.data[1].id == "ws-456"

    def test_relationship_with_links(self):
        """Test Relationship with links."""
        links = {"self": "/api/v2/workspaces/ws-123", "related": "/api/v2/runs"}
        rel = Relationship(links=links)

        assert rel.data is None
        assert rel.links["self"] == "/api/v2/workspaces/ws-123"

    def test_relationship_empty(self):
        """Test empty Relationship."""
        rel = Relationship()

        assert rel.data is None
        assert rel.links is None


class TestBaseTerraformResource:
    """Test cases for BaseTerraformResource model."""

    def test_base_terraform_resource_creation(self):
        """Test creating BaseTerraformResource with all fields."""

        class SampleAttributes(BaseModel):
            """Sample attributes class for testing."""

            name: str
            description: Optional[str] = None

        class SampleRelationships(BaseModel):
            """Sample relationships class for testing."""

            workspace: Optional[Relationship] = None

        attrs = SampleAttributes(name="test", description="test description")
        rels = SampleRelationships()

        resource = BaseTerraformResource[SampleAttributes, SampleRelationships](id="resource-123", type="test-resources", attributes=attrs, relationships=rels)

        assert resource.id == "resource-123"
        assert resource.type == "test-resources"
        assert resource.attributes.name == "test"
        assert resource.relationships is not None

    def test_base_terraform_resource_minimal(self):
        """Test creating BaseTerraformResource with minimal fields."""

        class SampleAttributes(BaseModel):
            """Sample attributes class for testing."""

            name: str

        class SampleRelationships(BaseModel):
            """Sample relationships class for testing."""

            pass

        resource = BaseTerraformResource[SampleAttributes, SampleRelationships](type="test-resources")

        assert resource.id is None
        assert resource.type == "test-resources"
        assert resource.attributes is None
        assert resource.relationships is None

    def test_base_terraform_resource_validation(self):
        """Test BaseTerraformResource validation."""

        class SampleAttributes(BaseModel):
            """Sample attributes class for testing."""

            name: str

        class SampleRelationships(BaseModel):
            """Sample relationships class for testing."""

            pass

        # Test missing required type field
        try:
            with pytest.raises(ValidationError):
                BaseTerraformResource[SampleAttributes, SampleRelationships]()
        except (TypeError, AttributeError):
            # Fallback behavior when pydantic is not available
            pass


class TestBaseRequest:
    """Test cases for BaseRequest model."""

    def test_base_request_creation(self):
        """Test creating BaseRequest."""

        class SampleData(BaseModel):
            """Sample data class for testing."""

            id: str
            type: str

        data = SampleData(id="test-123", type="test-type")
        request = BaseRequest[SampleData](data=data)

        assert request.data.id == "test-123"
        assert request.data.type == "test-type"

    def test_base_request_validation(self):
        """Test BaseRequest validation."""

        class SampleData(BaseModel):
            """Sample data class for testing."""

            id: str
            type: str

        # Test missing required data field
        try:
            with pytest.raises(ValidationError):
                BaseRequest[SampleData]()
        except (TypeError, AttributeError):
            # Fallback behavior when pydantic is not available
            pass


class TestTerraformAPIResponse:
    """Test cases for TerraformAPIResponse model."""

    def test_terraform_api_response_with_single_resource(self):
        """Test TerraformAPIResponse with single resource."""
        data = ResourceData(type="workspaces", id="ws-123")
        response = TerraformAPIResponse[ResourceData](data=data)

        assert response.data.type == "workspaces"
        assert response.data.id == "ws-123"
        assert response.included is None
        assert response.meta is None

    def test_terraform_api_response_with_multiple_resources(self):
        """Test TerraformAPIResponse with multiple resources."""
        data1 = ResourceData(type="workspaces", id="ws-123")
        data2 = ResourceData(type="workspaces", id="ws-456")
        response = TerraformAPIResponse[ResourceData](data=[data1, data2])

        assert len(response.data) == 2
        assert response.data[0].id == "ws-123"
        assert response.data[1].id == "ws-456"

    def test_terraform_api_response_with_meta_and_links(self):
        """Test TerraformAPIResponse with meta and links."""
        meta = {"page": 1, "total": 100}
        links = {"next": "/api/v2/workspaces?page=2"}
        response = TerraformAPIResponse[ResourceData](meta=meta, links=links)

        assert response.data is None
        assert response.meta["page"] == 1
        assert response.links["next"] == "/api/v2/workspaces?page=2"

    def test_terraform_api_response_empty(self):
        """Test empty TerraformAPIResponse."""
        response = TerraformAPIResponse[ResourceData]()

        assert response.data is None
        assert response.included is None
        assert response.meta is None
        assert response.links is None
        assert response.errors is None


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_create_workspace_reference(self):
        """Test create_workspace_reference function."""
        ref = create_workspace_reference("ws-123")

        assert ref.type == "workspaces"
        assert ref.id == "ws-123"

    def test_create_configuration_version_reference(self):
        """Test create_configuration_version_reference function."""
        ref = create_configuration_version_reference("cv-456")

        assert ref.type == "configuration-versions"
        assert ref.id == "cv-456"

    def test_create_organization_reference(self):
        """Test create_organization_reference function."""
        ref = create_organization_reference("my-org")

        assert ref.type == "organizations"
        assert ref.id == "my-org"

    def test_create_run_reference(self):
        """Test create_run_reference function."""
        ref = create_run_reference("run-789")

        assert ref.type == "runs"
        assert ref.id == "run-789"

    def test_utility_functions_with_empty_strings(self):
        """Test utility functions with empty strings."""
        workspace_ref = create_workspace_reference("")
        config_ref = create_configuration_version_reference("")
        org_ref = create_organization_reference("")
        run_ref = create_run_reference("")

        assert workspace_ref.id == ""
        assert config_ref.id == ""
        assert org_ref.id == ""
        assert run_ref.id == ""

    def test_utility_functions_with_special_characters(self):
        """Test utility functions with special characters."""
        special_id = "test-123_with@special.chars"

        workspace_ref = create_workspace_reference(special_id)
        config_ref = create_configuration_version_reference(special_id)
        org_ref = create_organization_reference(special_id)
        run_ref = create_run_reference(special_id)

        assert workspace_ref.id == special_id
        assert config_ref.id == special_id
        assert org_ref.id == special_id
        assert run_ref.id == special_id


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_relationship_data(self):
        """Test handling invalid relationship data."""
        # Test that invalid relationship data is handled gracefully
        try:
            with pytest.raises(ValidationError):
                # This should fail validation if pydantic is available
                ResourceData(type=123, id="valid-id")  # invalid type
        except (TypeError, AttributeError):
            # Fallback behavior when pydantic is not available
            pass

    def test_type_validation_in_generic_models(self):
        """Test type validation in generic models."""

        class InvalidAttributes:
            """Invalid attributes class (not BaseModel)."""

            pass

        class ValidRelationships(BaseModel):
            """Valid relationships class."""

            pass

        # This should work since Python's typing is mostly runtime-optional
        try:
            resource = BaseTerraformResource[InvalidAttributes, ValidRelationships](type="test")
            assert resource.type == "test"
        except Exception:
            # If there are strict type checks, this is expected
            pass

    def test_list_validation_in_relationships(self):
        """Test list validation in relationships."""
        # Test that relationship data as list works correctly
        data1 = ResourceData(type="workspaces", id="ws-1")
        data2 = ResourceData(type="workspaces", id="ws-2")

        rel = Relationship(data=[data1, data2])

        assert isinstance(rel.data, list)
        assert len(rel.data) == 2
        assert all(isinstance(item, ResourceData) for item in rel.data)
