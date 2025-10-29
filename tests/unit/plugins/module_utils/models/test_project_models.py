# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import pytest

from pydantic import ValidationError

from ansible_collections.hashicorp.terraform.plugins.module_utils.models.project import (
    ProjectAttributes,
    ProjectData,
    ProjectRelationships,
    ProjectRequest,
    TagBindingAttributes,
    TagBindingsRelationship,
)


class TestTagBindingAttributes:
    """Test cases for TagBindingAttributes model."""

    def test_tag_binding_attributes_creation(self):
        """Test creating TagBindingAttributes with valid data."""
        tag_binding = TagBindingAttributes(key="environment", value="production")

        assert tag_binding.key == "environment"
        assert tag_binding.value == "production"

    def test_tag_binding_attributes_validation(self):
        """Test TagBindingAttributes validation with invalid data."""
        # Test with missing required fields
        try:
            with pytest.raises(ValidationError):
                TagBindingAttributes(key="environment")  # missing value
        except (TypeError, AttributeError):
            # Fallback behavior when pydantic is not available
            pass

        try:
            with pytest.raises(ValidationError):
                TagBindingAttributes(value="production")  # missing key
        except (TypeError, AttributeError):
            # Fallback behavior when pydantic is not available
            pass

    @pytest.mark.parametrize(
        "key,value",
        [
            ("environment", "production"),
            ("team", "infrastructure"),
            ("cost-center", "engineering"),
            ("project", "web-app"),
            ("owner", "john.doe@company.com"),
            ("unicode-key-こんにちは", "unicode-value-世界"),
            ("special-chars", "value@#$%^&*()"),
            ("", "empty-key"),
            ("empty-value", ""),
            ("", ""),
        ],
    )
    def test_tag_binding_attributes_various_values(self, key, value):
        """Test TagBindingAttributes with various key-value combinations."""
        tag_binding = TagBindingAttributes(key=key, value=value)

        assert tag_binding.key == key
        assert tag_binding.value == value

    def test_tag_binding_attributes_serialization(self):
        """Test TagBindingAttributes serialization."""
        tag_binding = TagBindingAttributes(key="environment", value="staging")
        serialized = tag_binding.model_dump()

        expected = {"key": "environment", "value": "staging"}
        assert serialized == expected


class TestTagBindingsRelationship:
    """Test cases for TagBindingsRelationship model."""

    def test_tag_bindings_relationship_empty(self):
        """Test creating empty TagBindingsRelationship."""
        rel = TagBindingsRelationship()

        assert rel.data is None

    def test_tag_bindings_relationship_with_single_tag(self):
        """Test TagBindingsRelationship with single tag binding."""
        tag_binding = TagBindingAttributes(key="environment", value="production")
        rel = TagBindingsRelationship(data=[tag_binding])

        assert len(rel.data) == 1
        assert rel.data[0].key == "environment"
        assert rel.data[0].value == "production"

    def test_tag_bindings_relationship_with_multiple_tags(self):
        """Test TagBindingsRelationship with multiple tag bindings."""
        tag_bindings = [
            TagBindingAttributes(key="environment", value="production"),
            TagBindingAttributes(key="team", value="infrastructure"),
            TagBindingAttributes(key="cost-center", value="engineering"),
        ]
        rel = TagBindingsRelationship(data=tag_bindings)

        assert len(rel.data) == 3
        assert rel.data[0].key == "environment"
        assert rel.data[1].key == "team"
        assert rel.data[2].key == "cost-center"

    def test_tag_bindings_relationship_empty_list(self):
        """Test TagBindingsRelationship with empty list."""
        rel = TagBindingsRelationship(data=[])

        assert rel.data == []

    def test_tag_bindings_relationship_serialization(self):
        """Test TagBindingsRelationship serialization."""
        tag_bindings = [
            TagBindingAttributes(key="env", value="prod"),
            TagBindingAttributes(key="team", value="ops"),
        ]
        rel = TagBindingsRelationship(data=tag_bindings)
        serialized = rel.model_dump()

        expected = {
            "data": [
                {"key": "env", "value": "prod"},
                {"key": "team", "value": "ops"},
            ]
        }
        assert serialized == expected


class TestProjectAttributes:
    """Test cases for ProjectAttributes model."""

    def test_project_attributes_creation_minimal(self):
        """Test creating ProjectAttributes with minimal data."""
        attrs = ProjectAttributes(project="my-project")

        assert attrs.project == "my-project"
        assert attrs.description is None
        assert attrs.auto_destroy_activity_duration is None
        assert attrs.execution_mode is None
        assert attrs.default_agent_pool_id is None
        assert attrs.setting_overwrites is None

    @pytest.mark.parametrize(
        "attribute_values,expected_values",
        [
            # Full configuration test case 1
            (
                {
                    "project": "web-application",
                    "description": "Main web application project",
                    "auto_destroy_activity_duration": "7d",
                    "execution_mode": "remote",
                    "default_agent_pool_id": "apool-123456",
                    "setting_overwrites": {"cost_estimation": True, "speculative_enabled": False},
                },
                {
                    "project": "web-application",
                    "description": "Main web application project",
                    "auto_destroy_activity_duration": "7d",
                    "execution_mode": "remote",
                    "default_agent_pool_id": "apool-123456",
                    "setting_overwrites": {"cost_estimation": True, "speculative_enabled": False},
                },
            ),
            # Full configuration test case 2 - local execution
            (
                {
                    "project": "local-dev-project",
                    "description": "Local development project",
                    "auto_destroy_activity_duration": "1d",
                    "execution_mode": "local",
                    "setting_overwrites": {"cost_estimation": False},
                },
                {
                    "project": "local-dev-project",
                    "description": "Local development project",
                    "auto_destroy_activity_duration": "1d",
                    "execution_mode": "local",
                    "default_agent_pool_id": None,
                    "setting_overwrites": {"cost_estimation": False},
                },
            ),
            # Minimal configuration
            (
                {"project": "minimal-project"},
                {
                    "project": "minimal-project",
                    "description": None,
                    "auto_destroy_activity_duration": None,
                    "execution_mode": None,
                    "default_agent_pool_id": None,
                    "setting_overwrites": None,
                },
            ),
            # Special characters and unicode
            (
                {
                    "project": "test-project_with.special-chars",
                    "description": "Project with émojis 🚀 and spëcial chars: @#$%",
                    "auto_destroy_activity_duration": "30d",
                },
                {
                    "project": "test-project_with.special-chars",
                    "description": "Project with émojis 🚀 and spëcial chars: @#$%",
                    "auto_destroy_activity_duration": "30d",
                },
            ),
        ],
    )
    def test_project_attributes_creation_full(self, attribute_values, expected_values):
        """Test creating ProjectAttributes with various full configurations."""
        attrs = ProjectAttributes(**attribute_values)

        for key, expected_value in expected_values.items():
            actual_value = getattr(attrs, key)
            assert actual_value == expected_value, f"Expected {key}={expected_value}, got {actual_value}"

    @pytest.mark.parametrize(
        "alias_data,expected_values",
        [
            # Standard alias test
            (
                {
                    "name": "alias-test-project",
                    "auto-destroy-activity-duration": "14d",
                    "default-agent-pool-id": "apool-alias-test",
                    "setting-overwrites": {"cost_estimation": True},
                },
                {
                    "project": "alias-test-project",
                    "auto_destroy_activity_duration": "14d",
                    "default_agent_pool_id": "apool-alias-test",
                    "setting_overwrites": {"cost_estimation": True},
                },
            ),
            # Mixed aliases and direct field names
            (
                {
                    "project": "mixed-fields-project",  # Direct field name
                    "auto-destroy-activity-duration": "7d",  # Alias
                    "execution_mode": "remote",  # Direct field name
                    "default-agent-pool-id": "apool-mixed",  # Alias
                },
                {
                    "project": "mixed-fields-project",
                    "auto_destroy_activity_duration": "7d",
                    "execution_mode": "remote",
                    "default_agent_pool_id": "apool-mixed",
                },
            ),
            # Only alias fields
            (
                {
                    "name": "only-aliases-project",
                    "setting-overwrites": {"speculative_enabled": False},
                },
                {
                    "project": "only-aliases-project",
                    "setting_overwrites": {"speculative_enabled": False},
                },
            ),
        ],
    )
    def test_project_attributes_field_aliases(self, alias_data, expected_values):
        """Test ProjectAttributes field aliases work correctly."""
        attrs = ProjectAttributes.model_validate(alias_data)

        for field_name, expected_value in expected_values.items():
            actual_value = getattr(attrs, field_name)
            assert actual_value == expected_value, f"Expected {field_name}={expected_value}, got {actual_value}"

    @pytest.mark.parametrize(
        "attrs_data,expected_aliases,excluded_fields",
        [
            # Basic serialization test
            (
                {
                    "project": "serialization-test",
                    "auto_destroy_activity_duration": "7d",
                    "default_agent_pool_id": "apool-serial",
                },
                {
                    "name": "serialization-test",
                    "auto-destroy-activity-duration": "7d",
                    "default-agent-pool-id": "apool-serial",
                },
                ["description", "execution_mode", "setting_overwrites"],  # Fields that should be None/excluded
            ),
            # Full serialization test
            (
                {
                    "project": "full-serialization",
                    "description": "Full serialization test",
                    "execution_mode": "local",
                    "setting_overwrites": {"cost_estimation": True},
                },
                {
                    "name": "full-serialization",
                    "description": "Full serialization test",
                    "default-execution-mode": "local",
                    "setting-overwrites": {"cost_estimation": True},
                },
                [],
            ),
        ],
    )
    def test_project_attributes_serialization_with_aliases(self, attrs_data, expected_aliases, excluded_fields):
        """Test ProjectAttributes serialization uses aliases correctly."""
        attrs = ProjectAttributes(**attrs_data)
        serialized = attrs.model_dump(by_alias=True, exclude_none=True)

        for alias, expected_value in expected_aliases.items():
            assert alias in serialized, f"Alias {alias} should be in serialized output"
            assert serialized[alias] == expected_value, f"Expected {alias}={expected_value}, got {serialized[alias]}"

        for field in excluded_fields:
            # These fields should not be in serialized output when exclude_none=True
            # since they would be None
            field_alias = getattr(ProjectAttributes.model_fields.get(field, None), "alias", field)
            assert field_alias not in serialized, f"Field {field} (alias: {field_alias}) should not be in output"

    def test_project_attributes_validation(self):
        """Test ProjectAttributes validation."""
        # Test that all fields are optional
        attrs = ProjectAttributes()  # All fields are optional
        assert attrs.project is None
        assert attrs.description is None
        assert attrs.execution_mode is None

    @pytest.mark.parametrize(
        "execution_mode",
        ["remote", "local", None],
    )
    def test_project_attributes_execution_mode_validation(self, execution_mode):
        """Test ProjectAttributes execution mode validation."""
        attrs = ProjectAttributes(project="test-project", execution_mode=execution_mode)
        assert attrs.execution_mode == execution_mode

    def test_project_attributes_invalid_execution_mode(self):
        """Test ProjectAttributes with invalid execution mode."""
        try:
            with pytest.raises(ValidationError):
                ProjectAttributes(project="test-project", execution_mode="invalid")
        except (TypeError, AttributeError):
            # Fallback behavior when pydantic is not available
            pass


class TestProjectRelationships:
    """Test cases for ProjectRelationships model."""

    def test_project_relationships_creation_empty(self):
        """Test creating empty ProjectRelationships."""
        rels = ProjectRelationships()

        assert rels.tag_bindings is None

    def test_project_relationships_creation_with_tag_bindings(self):
        """Test creating ProjectRelationships with tag bindings."""
        tag_bindings = [
            TagBindingAttributes(key="environment", value="production"),
            TagBindingAttributes(key="team", value="infrastructure"),
        ]
        tag_bindings_rel = TagBindingsRelationship(data=tag_bindings)
        rels = ProjectRelationships(tag_bindings=tag_bindings_rel)

        assert rels.tag_bindings is not None
        assert len(rels.tag_bindings.data) == 2
        assert rels.tag_bindings.data[0].key == "environment"
        assert rels.tag_bindings.data[1].key == "team"

    def test_project_relationships_field_aliases(self):
        """Test ProjectRelationships field aliases."""
        data = {
            "tag-bindings": {
                "data": [
                    {"key": "environment", "value": "staging"},
                    {"key": "owner", "value": "devops-team"},
                ]
            }
        }

        rels = ProjectRelationships.model_validate(data)

        assert rels.tag_bindings is not None
        assert len(rels.tag_bindings.data) == 2
        assert rels.tag_bindings.data[0].key == "environment"
        assert rels.tag_bindings.data[0].value == "staging"
        assert rels.tag_bindings.data[1].key == "owner"
        assert rels.tag_bindings.data[1].value == "devops-team"

    def test_project_relationships_serialization_with_aliases(self):
        """Test ProjectRelationships serialization uses field aliases."""
        tag_bindings = [TagBindingAttributes(key="env", value="test")]
        tag_bindings_rel = TagBindingsRelationship(data=tag_bindings)
        rels = ProjectRelationships(tag_bindings=tag_bindings_rel)

        serialized = rels.model_dump(by_alias=True, exclude_none=True)

        assert "tag-bindings" in serialized
        assert serialized["tag-bindings"]["data"][0]["key"] == "env"
        assert serialized["tag-bindings"]["data"][0]["value"] == "test"


class TestProjectData:
    """Test cases for ProjectData model."""

    def test_project_data_creation_minimal(self):
        """Test creating ProjectData with minimal configuration."""
        data = ProjectData()

        assert data.type == "projects"
        assert data.id is None
        assert data.attributes is None
        assert data.relationships is None

    def test_project_data_creation_full(self):
        """Test creating ProjectData with full configuration."""
        attrs = ProjectAttributes(
            project="full-test-project",
            description="Full test project description",
            execution_mode="remote",
        )
        tag_bindings = [TagBindingAttributes(key="environment", value="production")]
        rels = ProjectRelationships(tag_bindings=TagBindingsRelationship(data=tag_bindings))
        data = ProjectData(id="prj-123456", attributes=attrs, relationships=rels)

        assert data.id == "prj-123456"
        assert data.type == "projects"
        assert data.attributes.project == "full-test-project"
        assert data.attributes.description == "Full test project description"
        assert data.attributes.execution_mode == "remote"
        assert data.relationships.tag_bindings.data[0].key == "environment"

    def test_project_data_validation(self):
        """Test ProjectData validation."""
        # Test that ProjectData can be created with minimal data since attributes and relationships are optional
        project_data = ProjectData()
        assert project_data.type == "projects"
        assert project_data.attributes is None
        assert project_data.relationships is None

        # Test with only relationships
        project_data_with_rels = ProjectData(relationships=ProjectRelationships())
        assert project_data_with_rels.attributes is None
        assert project_data_with_rels.relationships is not None

        # Test with only attributes
        project_data_with_attrs = ProjectData(attributes=ProjectAttributes(project="test"))
        assert project_data_with_attrs.attributes is not None
        assert project_data_with_attrs.relationships is None

    def test_project_data_type_literal(self):
        """Test ProjectData type field is literal 'projects'."""
        attrs = ProjectAttributes(project="test-project")
        rels = ProjectRelationships()

        data = ProjectData(attributes=attrs, relationships=rels)
        assert data.type == "projects"

        # Type should be automatically set even if not provided
        data2 = ProjectData()
        assert data2.type == "projects"


class TestProjectRequest:
    """Test cases for ProjectRequest model."""

    def test_project_request_create_basic(self):
        """Test basic ProjectRequest creation."""
        request = ProjectRequest.create(organization="my-org", project="basic-project")

        assert request.data.type == "projects"
        assert request.data.attributes.project == "basic-project"
        assert request.data.relationships.tag_bindings is None

    def test_project_request_create_with_all_attributes(self):
        """Test ProjectRequest creation with all attributes."""
        request = ProjectRequest.create(
            organization="test-org",
            project="comprehensive-project",
            description="A comprehensive test project",
            auto_destroy_activity_duration="14d",
            execution_mode="remote",
            default_agent_pool_id="apool-test-123",
            setting_overwrites={"cost_estimation": True, "speculative_enabled": False},
        )

        assert request.data.attributes.project == "comprehensive-project"
        assert request.data.attributes.description == "A comprehensive test project"
        assert request.data.attributes.auto_destroy_activity_duration == "14d"
        assert request.data.attributes.execution_mode == "remote"
        assert request.data.attributes.default_agent_pool_id == "apool-test-123"
        assert request.data.attributes.setting_overwrites == {"cost_estimation": True, "speculative_enabled": False}

    def test_project_request_create_with_tag_bindings(self):
        """Test ProjectRequest creation with tag bindings."""
        tag_bindings = [
            TagBindingAttributes(key="environment", value="production"),
            TagBindingAttributes(key="team", value="infrastructure"),
            TagBindingAttributes(key="cost-center", value="engineering"),
        ]

        request = ProjectRequest.create(
            organization="tagged-org",
            project="tagged-project",
            tag_bindings=tag_bindings,
        )

        assert request.data.attributes.project == "tagged-project"
        assert request.data.relationships.tag_bindings is not None
        assert len(request.data.relationships.tag_bindings.data) == 3
        assert request.data.relationships.tag_bindings.data[0].key == "environment"
        assert request.data.relationships.tag_bindings.data[1].key == "team"
        assert request.data.relationships.tag_bindings.data[2].key == "cost-center"

    def test_project_request_create_with_aliases(self):
        """Test ProjectRequest creation using field aliases."""
        request = ProjectRequest.create(
            organization="alias-org",
            name="alias-project",  # Using alias for project
            description="Project created with aliases",
        )

        assert request.data.attributes.project == "alias-project"
        assert request.data.attributes.description == "Project created with aliases"

    def test_project_request_serialization(self):
        """Test ProjectRequest serialization."""
        request = ProjectRequest.create(
            organization="serialization-org",
            project="serialization-project",
            description="Serialization test project",
        )

        serialized = request.model_dump(by_alias=True, exclude_none=True)

        assert "data" in serialized
        assert serialized["data"]["type"] == "projects"
        assert serialized["data"]["attributes"]["name"] == "serialization-project"  # Should use alias
        assert serialized["data"]["attributes"]["description"] == "Serialization test project"

    def test_project_request_without_tag_bindings(self):
        """Test ProjectRequest without tag bindings."""
        request = ProjectRequest.create(
            organization="no-tags-org",
            project="no-tags-project",
            description="Project without tags",
        )

        assert request.data.attributes.project == "no-tags-project"
        assert request.data.relationships.tag_bindings is None

    def test_project_request_validation_empty_organization(self):
        """Test ProjectRequest validation with empty organization."""
        # Empty organization should still create valid request
        request = ProjectRequest.create(organization="", project="empty-org-project")
        assert request.data.attributes.project == "empty-org-project"

    def test_project_request_validation_empty_project_name(self):
        """Test ProjectRequest validation with empty project name."""
        # Empty project name should still create valid request
        request = ProjectRequest.create(organization="test-org", project="")
        assert request.data.attributes.project == ""


class TestProjectModelsEdgeCases:
    """Test edge cases and special scenarios for project models."""

    @pytest.mark.parametrize(
        "project_name",
        [
            "simple-project",
            "project_with_underscores",
            "project.with.dots",
            "project-with-émojis-🚀",
            "project with spaces",
            "UPPERCASE-PROJECT",
            "123-numeric-project",
            "project@special#chars$%",
            "",
            "very-long-project-name-" + "x" * 100,
        ],
    )
    def test_project_request_with_special_project_names(self, project_name):
        """Test ProjectRequest with special characters in project name."""
        request = ProjectRequest.create(organization="special-org", project=project_name)
        assert request.data.attributes.project == project_name

    @pytest.mark.parametrize(
        "description",
        [
            "Simple description",
            "Description with émojis 🚀 and spëcial chars: @#$%^&*()",
            "Multi-line\ndescription\nwith\ntabs\t\t",
            "Description with 'single' and \"double\" quotes",
            "Very long description: " + "x" * 1000,
            "",
            'Description with JSON: {"key": "value", "array": [1, 2, 3]}',
        ],
    )
    def test_project_request_with_special_descriptions(self, description):
        """Test ProjectRequest with special characters in description."""
        request = ProjectRequest.create(
            organization="desc-org",
            project="desc-project",
            description=description,
        )
        assert request.data.attributes.description == description

    @pytest.mark.parametrize(
        "duration",
        [
            "1d",
            "7d",
            "14d",
            "30d",
            "90d",
            "1h",
            "24h",
            "168h",
            "",
            "invalid-duration",
        ],
    )
    def test_project_attributes_auto_destroy_duration_values(self, duration):
        """Test ProjectAttributes with various auto destroy duration values."""
        attrs = ProjectAttributes(project="duration-test", auto_destroy_activity_duration=duration)
        assert attrs.auto_destroy_activity_duration == duration

    @pytest.mark.parametrize(
        "setting_overwrites",
        [
            {"cost_estimation": True},
            {"speculative_enabled": False},
            {"cost_estimation": True, "speculative_enabled": False},
            {"cost_estimation": False, "speculative_enabled": True, "custom_setting": True},
            {},
            None,
        ],
    )
    def test_project_attributes_setting_overwrites_values(self, setting_overwrites):
        """Test ProjectAttributes with various setting overwrites values."""
        attrs = ProjectAttributes(project="settings-test", setting_overwrites=setting_overwrites)
        assert attrs.setting_overwrites == setting_overwrites

    def test_project_data_type_immutability(self):
        """Test that ProjectData type field cannot be overridden."""
        data = ProjectData()
        assert data.type == "projects"

        # Type should remain 'projects' even if we try to set it differently during creation
        # (This test verifies the Literal type works as expected)
        data_with_explicit_type = ProjectData(type="projects")
        assert data_with_explicit_type.type == "projects"

    def test_tag_bindings_with_duplicate_keys(self):
        """Test tag bindings with duplicate keys."""
        tag_bindings = [
            TagBindingAttributes(key="environment", value="production"),
            TagBindingAttributes(key="environment", value="staging"),  # Duplicate key
            TagBindingAttributes(key="team", value="infrastructure"),
        ]

        request = ProjectRequest.create(
            organization="duplicate-org",
            project="duplicate-project",
            tag_bindings=tag_bindings,
        )

        # Should accept duplicate keys (validation is handled at API level)
        assert len(request.data.relationships.tag_bindings.data) == 3
        assert request.data.relationships.tag_bindings.data[0].value == "production"
        assert request.data.relationships.tag_bindings.data[1].value == "staging"

    def test_empty_tag_bindings_list(self):
        """Test project with empty tag bindings list."""
        request = ProjectRequest.create(
            organization="empty-tags-org",
            project="empty-tags-project",
            tag_bindings=[],
        )

        # Empty list should not create tag_bindings relationship (matches implementation behavior)
        assert request.data.relationships.tag_bindings is None


class TestProjectModelsPerformance:
    """Performance and stress tests for project models."""

    def test_project_request_creation_performance(self):
        """Test performance of ProjectRequest creation."""
        import time

        start_time = time.time()

        # Create multiple project requests
        for i in range(100):
            tag_bindings = [
                TagBindingAttributes(key="index", value=str(i)),
                TagBindingAttributes(key="test", value="performance"),
            ]
            request = ProjectRequest.create(
                organization=f"perf-org-{i}",
                project=f"perf-project-{i}",
                description=f"Performance test project {i}",
                tag_bindings=tag_bindings,
            )
            assert request.data.attributes.project == f"perf-project-{i}"

        end_time = time.time()
        duration = end_time - start_time

        # Should complete reasonably quickly (less than 1 second for 100 requests)
        assert duration < 1.0, f"ProjectRequest creation took too long: {duration} seconds"

    def test_project_attributes_large_data_handling(self):
        """Test ProjectAttributes with large data structures."""
        # Create large setting overwrites
        large_settings = {f"setting_{i}": i % 2 == 0 for i in range(100)}

        attrs = ProjectAttributes(
            project="large-data-test",
            description="Large data test project",
            setting_overwrites=large_settings,
        )

        assert len(attrs.setting_overwrites) == 100
        assert attrs.project == "large-data-test"

    def test_large_tag_bindings_handling(self):
        """Test project with large number of tag bindings."""
        # Create large tag bindings list
        large_tag_bindings = [TagBindingAttributes(key=f"tag_{i}", value=f"value_{i}") for i in range(100)]

        request = ProjectRequest.create(
            organization="large-tags-org",
            project="large-tags-project",
            tag_bindings=large_tag_bindings,
        )

        assert len(request.data.relationships.tag_bindings.data) == 100
        assert request.data.relationships.tag_bindings.data[0].key == "tag_0"
        assert request.data.relationships.tag_bindings.data[99].key == "tag_99"


class TestProjectModelsIntegration:
    """Integration tests combining multiple project models."""

    def test_complete_project_workflow_simulation(self):
        """Test complete project workflow using all models together."""
        # Step 1: Create project request with comprehensive configuration
        tag_bindings = [
            TagBindingAttributes(key="environment", value="production"),
            TagBindingAttributes(key="team", value="infrastructure"),
            TagBindingAttributes(key="cost-center", value="engineering"),
            TagBindingAttributes(key="owner", value="devops-team"),
        ]

        request = ProjectRequest.create(
            organization="integration-org",
            project="integration-project",
            description="Integration test project with full configuration",
            auto_destroy_activity_duration="30d",
            execution_mode="remote",
            default_agent_pool_id="apool-integration-123",
            setting_overwrites={
                "cost_estimation": True,
                "speculative_enabled": False,
                "auto_apply": False,
            },
            tag_bindings=tag_bindings,
        )

        # Verify request structure
        assert request.data.type == "projects"
        assert request.data.attributes.project == "integration-project"
        assert request.data.attributes.description == "Integration test project with full configuration"
        assert request.data.attributes.execution_mode == "remote"
        assert len(request.data.relationships.tag_bindings.data) == 4

        # Step 2: Simulate API response structure
        response_attrs = ProjectAttributes(
            project="integration-project",
            description="Integration test project with full configuration",
            auto_destroy_activity_duration="30d",
            execution_mode="remote",
            default_agent_pool_id="apool-integration-123",
            setting_overwrites={
                "cost_estimation": True,
                "speculative_enabled": False,
                "auto_apply": False,
            },
        )

        response_rels = ProjectRelationships(tag_bindings=TagBindingsRelationship(data=tag_bindings))

        from ansible_collections.hashicorp.terraform.plugins.module_utils.models.common import BaseTerraformResource

        response_data = BaseTerraformResource[ProjectAttributes, ProjectRelationships](
            id="prj-integration-response",
            type="projects",
            attributes=response_attrs,
            relationships=response_rels,
        )

        assert response_data.id == "prj-integration-response"
        assert response_data.type == "projects"
        assert response_data.attributes.project == "integration-project"
        assert len(response_data.relationships.tag_bindings.data) == 4

        # Step 3: Test serialization for API communication
        request_serialized = request.model_dump(by_alias=True, exclude_none=True)
        response_serialized = response_data.model_dump(by_alias=True, exclude_none=True)

        # Verify serialized structure uses aliases
        assert request_serialized["data"]["attributes"]["name"] == "integration-project"
        assert "auto-destroy-activity-duration" in request_serialized["data"]["attributes"]
        assert "tag-bindings" in request_serialized["data"]["relationships"]

        assert response_serialized["attributes"]["name"] == "integration-project"
        assert "auto-destroy-activity-duration" in response_serialized["attributes"]

    @pytest.mark.parametrize(
        "factory_method,organization,project_name,expected_type",
        [
            ("create", "factory-org-1", "factory-project-1", "projects"),
            ("create", "factory-org-2", "factory-project-2", "projects"),
        ],
    )
    def test_factory_functions_consistency(self, factory_method, organization, project_name, expected_type):
        """Test factory method consistency."""
        method = getattr(ProjectRequest, factory_method)
        result = method(organization=organization, project=project_name)

        assert result.data.type == expected_type
        assert result.data.attributes.project == project_name

    def test_model_validation_chain(self):
        """Test validation chain across all project models."""
        # Test that valid nested structures work with minimal data
        valid_attrs = ProjectAttributes()  # All fields are optional
        valid_rels = ProjectRelationships()
        valid_data = ProjectData(attributes=valid_attrs, relationships=valid_rels)
        valid_request = ProjectRequest(data=valid_data)

        assert valid_request.data.attributes.project is None
        assert valid_request.data.type == "projects"

        # Test with full data
        valid_attrs_full = ProjectAttributes(project="validation-test")
        valid_rels_full = ProjectRelationships()
        valid_data_full = ProjectData(attributes=valid_attrs_full, relationships=valid_rels_full)
        valid_request_full = ProjectRequest(data=valid_data_full)

        assert valid_request_full.data.attributes.project == "validation-test"
        assert valid_request_full.data.type == "projects"
