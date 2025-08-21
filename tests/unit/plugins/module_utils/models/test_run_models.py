# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import time

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.models.common import (
    Relationship,
    create_configuration_version_reference,
    create_workspace_reference,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.run import (
    RunAttributes,
    RunData,
    RunRelationships,
    RunRequest,
    RunStates,
)


class TestRunAttributes:
    """Test cases for RunAttributes model."""

    def test_run_attributes_creation_minimal(self):
        """Test creating RunAttributes with minimal data."""
        attrs = RunAttributes()

        # Should have run-specific fields
        assert attrs.run_message is None
        assert attrs.auto_apply is None

    @pytest.mark.parametrize(
        "attribute_values,expected_values",
        [
            # Full configuration test case 1
            (
                {
                    "run_message": "Test run message",
                    "refresh_only": True,
                    "plan_only": False,
                    "auto_apply": True,
                    "save_plan": False,
                    "is_destroy": False,
                    "target_addrs": ["module.vpc", "module.ec2"],
                    "refresh": True,
                    "variables": [{"key": "env", "value": "production"}, {"key": "region", "value": "us-west-2"}],
                },
                {
                    "run_message": "Test run message",
                    "refresh_only": True,
                    "plan_only": False,
                    "auto_apply": True,
                    "save_plan": False,
                    "is_destroy": False,
                    "target_addrs": ["module.vpc", "module.ec2"],
                    "refresh": True,
                    "variables": [{"key": "env", "value": "production"}, {"key": "region", "value": "us-west-2"}],
                },
            ),
            # Full configuration test case 2 - opposite boolean values
            (
                {
                    "run_message": "Destroy run",
                    "refresh_only": False,
                    "plan_only": True,
                    "auto_apply": False,
                    "save_plan": True,
                    "is_destroy": True,
                    "target_addrs": ["module.database"],
                    "refresh": False,
                    "variables": [{"key": "env", "value": "staging"}],
                },
                {
                    "run_message": "Destroy run",
                    "refresh_only": False,
                    "plan_only": True,
                    "auto_apply": False,
                    "save_plan": True,
                    "is_destroy": True,
                    "target_addrs": ["module.database"],
                    "refresh": False,
                    "variables": [{"key": "env", "value": "staging"}],
                },
            ),
            # Empty collections
            (
                {
                    "run_message": "Empty collections test",
                    "target_addrs": [],
                    "variables": [],
                },
                {
                    "run_message": "Empty collections test",
                    "target_addrs": [],
                    "variables": [],
                },
            ),
            # Special characters and unicode
            (
                {
                    "run_message": "Test with émojis 🚀 and spëcial chars: @#$%",
                    "target_addrs": ["module.test-with_special.chars"],
                    "variables": [{"key": "unicode_key_こんにちは", "value": "unicode_value_世界"}],
                },
                {
                    "run_message": "Test with émojis 🚀 and spëcial chars: @#$%",
                    "target_addrs": ["module.test-with_special.chars"],
                    "variables": [{"key": "unicode_key_こんにちは", "value": "unicode_value_世界"}],
                },
            ),
        ],
    )
    def test_run_attributes_creation_full(self, attribute_values, expected_values):
        """Test creating RunAttributes with various full configurations."""
        attrs = RunAttributes(**attribute_values)

        for key, expected_value in expected_values.items():
            actual_value = getattr(attrs, key)
            if key == "variables" and expected_value is not None and len(expected_value) > 0:
                # For variables, check the structure instead of direct equality
                assert len(actual_value) == len(expected_value), f"Expected {len(expected_value)} variables, got {len(actual_value)}"
                for i, expected_var in enumerate(expected_value):
                    if isinstance(expected_var, dict):
                        assert actual_value[i].key == expected_var["key"], f"Variable {i} key mismatch"
                        assert actual_value[i].value == expected_var["value"], f"Variable {i} value mismatch"
                    else:
                        assert actual_value[i].key == expected_var.key, f"Variable {i} key mismatch"
                        assert actual_value[i].value == expected_var.value, f"Variable {i} value mismatch"
            else:
                assert actual_value == expected_value, f"Expected {key}={expected_value}, got {actual_value}"

    @pytest.mark.parametrize(
        "alias_data,expected_values",
        [
            # Standard alias test
            (
                {
                    "message": "Test message",
                    "refresh-only": True,
                    "plan-only": False,
                    "auto-apply": True,
                    "save-plan": False,
                    "is-destroy": False,
                    "target-addrs": ["module.test"],
                    "replace-addrs": ["module.replace"],
                    "allow-empty-apply": True,
                    "allow-config-generation": False,
                    "debugging-mode": True,
                    "terraform-version": "1.5.0",
                },
                {
                    "run_message": "Test message",
                    "refresh_only": True,
                    "plan_only": False,
                    "auto_apply": True,
                    "save_plan": False,
                    "is_destroy": False,
                    "target_addrs": ["module.test"],
                    "replace_addrs": ["module.replace"],
                    "allow_empty_apply": True,
                    "allow_config_generation": False,
                    "debugging_mode": True,
                    "terraform_version": "1.5.0",
                },
            ),
            # Mixed aliases and direct field names
            (
                {
                    "run_message": "Direct field",  # Direct field name
                    "auto-apply": True,  # Alias
                    "refresh": False,  # Direct field name
                    "variables": [{"key": "test", "value": "value"}],  # Direct field name
                },
                {
                    "run_message": "Direct field",
                    "auto_apply": True,
                    "refresh": False,
                    "variables": [{"key": "test", "value": "value"}],
                },
            ),
            # Only alias fields
            (
                {
                    "message": "Only aliases",
                    "plan-only": True,
                    "terraform-version": "1.4.0",
                },
                {
                    "run_message": "Only aliases",
                    "plan_only": True,
                    "terraform_version": "1.4.0",
                },
            ),
        ],
    )
    def test_run_attributes_field_aliases(self, alias_data, expected_values):
        """Test RunAttributes field aliases work correctly."""
        attrs = RunAttributes.model_validate(alias_data)

        for field_name, expected_value in expected_values.items():
            actual_value = getattr(attrs, field_name)
            if field_name == "variables" and expected_value is not None and len(expected_value) > 0:
                # For variables, check the structure instead of direct equality
                assert len(actual_value) == len(expected_value), f"Expected {len(expected_value)} variables, got {len(actual_value)}"
                for i, expected_var in enumerate(expected_value):
                    if isinstance(expected_var, dict):
                        assert actual_value[i].key == expected_var["key"], f"Variable {i} key mismatch"
                        assert actual_value[i].value == expected_var["value"], f"Variable {i} value mismatch"
                    else:
                        assert actual_value[i].key == expected_var.key, f"Variable {i} key mismatch"
                        assert actual_value[i].value == expected_var.value, f"Variable {i} value mismatch"
            else:
                assert actual_value == expected_value, f"Expected {field_name}={expected_value}, got {actual_value}"

        # Note: created_at and updated_at fields are not part of RunAttributes

    @pytest.mark.parametrize(
        "attrs_data,expected_aliases,excluded_fields",
        [
            # Basic serialization test
            (
                {
                    "run_message": "Test serialization",
                    "auto_apply": True,
                    "plan_only": False,
                    "target_addrs": ["module.test"],
                },
                {
                    "message": "Test serialization",
                    "auto-apply": True,
                    "plan-only": False,
                    "target-addrs": ["module.test"],
                },
                ["refresh", "variables", "save_plan"],  # Fields that should be None/excluded
            ),
            # Full serialization test
            (
                {
                    "run_message": "Full test",
                    "refresh_only": True,
                    "save_plan": True,
                    "is_destroy": False,
                    "terraform_version": "1.5.0",
                    "variables": [{"key": "env", "value": "test"}],
                },
                {
                    "message": "Full test",
                    "refresh-only": True,
                    "save-plan": True,
                    "is-destroy": False,
                    "terraform-version": "1.5.0",
                    "variables": [{"key": "env", "value": "test"}],
                },
                [],
            ),
        ],
    )
    def test_run_attributes_serialization_with_aliases(self, attrs_data, expected_aliases, excluded_fields):
        """Test RunAttributes serialization uses aliases correctly."""
        attrs = RunAttributes(**attrs_data)
        serialized = attrs.model_dump(by_alias=True, exclude_none=True)

        for alias, expected_value in expected_aliases.items():
            assert alias in serialized, f"Alias {alias} should be in serialized output"
            assert serialized[alias] == expected_value, f"Expected {alias}={expected_value}, got {serialized[alias]}"

        for field in excluded_fields:
            # These fields should not be in serialized output when exclude_none=True
            # since they would be None
            field_alias = getattr(RunAttributes.model_fields.get(field, None), "alias", field)
            assert field_alias not in serialized, f"Field {field} (alias: {field_alias}) should not be in output"

    def test_run_attributes_inheritance(self):
        """Test RunAttributes inheritance and structure."""
        attrs = RunAttributes(run_message="Inheritance test")

        # Should have all expected run-specific fields
        expected_fields = [
            "run_message",
            "refresh_only",
            "plan_only",
            "auto_apply",
            "save_plan",
            "is_destroy",
            "target_addrs",
            "replace_addrs",
            "refresh",
            "variables",
            "allow_empty_apply",
            "allow_config_generation",
            "debugging_mode",
            "terraform_version",
        ]

        for field in expected_fields:
            assert hasattr(attrs, field), f"RunAttributes should have field {field}"


class TestRunRelationships:
    """Test cases for RunRelationships model."""

    def test_run_relationships_creation_empty(self):
        """Test creating empty RunRelationships."""
        rels = RunRelationships()

        assert rels.workspace is None
        assert rels.configuration_version is None

    def test_run_relationships_creation_with_workspace(self):
        """Test creating RunRelationships with workspace."""
        workspace_rel = Relationship(data=create_workspace_reference("ws-123"))
        rels = RunRelationships(workspace=workspace_rel)

        assert rels.workspace.data.type == "workspaces"
        assert rels.workspace.data.id == "ws-123"

    def test_run_relationships_creation_full(self):
        """Test creating RunRelationships with all fields."""
        workspace_ref = create_workspace_reference("ws-123")
        config_ref = create_configuration_version_reference("cv-456")

        from ansible_collections.hashicorp.terraform.plugins.module_utils.models.common import ResourceData

        policy_ref = ResourceData(type="policy-checks", id="pc-789")
        events_ref = ResourceData(type="run-events", id="re-101")
        stages_ref = ResourceData(type="task-stages", id="ts-202")

        rels = RunRelationships(
            workspace=Relationship(data=workspace_ref),
            configuration_version=Relationship(data=config_ref),
            policy_checks=Relationship(data=policy_ref),
            run_events=Relationship(data=events_ref),
            task_stages=Relationship(data=stages_ref),
        )

        assert rels.workspace.data.id == "ws-123"
        assert rels.configuration_version.data.id == "cv-456"
        assert rels.policy_checks.data.id == "pc-789"
        assert rels.run_events.data.id == "re-101"
        assert rels.task_stages.data.id == "ts-202"

    def test_run_relationships_field_aliases(self):
        """Test RunRelationships field aliases."""
        data = {
            "workspace": {"data": {"type": "workspaces", "id": "ws-123"}},
            "configuration-version": {"data": {"type": "configuration-versions", "id": "cv-456"}},
            "policy-checks": {"data": {"type": "policy-checks", "id": "pc-101"}},
            "run-events": {"data": {"type": "run-events", "id": "re-202"}},
            "task-stages": {"data": {"type": "task-stages", "id": "ts-303"}},
        }

        rels = RunRelationships.model_validate(data)

        assert rels.workspace.data.id == "ws-123"
        assert rels.configuration_version.data.id == "cv-456"
        assert rels.policy_checks.data.id == "pc-101"
        assert rels.run_events.data.id == "re-202"
        assert rels.task_stages.data.id == "ts-303"

    def test_run_relationships_serialization_with_aliases(self):
        """Test RunRelationships serialization uses field aliases."""
        config_ref = create_configuration_version_reference("cv-456")
        rels = RunRelationships(configuration_version=Relationship(data=config_ref))

        serialized = rels.model_dump(by_alias=True, exclude_none=True)

        assert "configuration-version" in serialized
        assert serialized["configuration-version"]["data"]["id"] == "cv-456"

    def test_run_relationships_inheritance(self):
        """Test RunRelationships inheritance and structure."""
        rels = RunRelationships()

        # Should have expected relationship fields
        expected_fields = ["workspace", "configuration_version", "policy_checks", "run_events", "task_stages"]

        for field in expected_fields:
            assert hasattr(rels, field), f"RunRelationships should have field {field}"


class TestRunData:
    """Test cases for RunData model."""

    def test_run_data_creation_minimal(self):
        """Test creating RunData with minimal configuration."""
        data = RunData()

        assert data.type == "runs"
        assert data.id is None
        assert data.attributes is None
        assert data.relationships is None

    def test_run_data_creation_full(self):
        """Test creating RunData with full configuration."""
        attrs = RunAttributes(run_message="Full test run", auto_apply=True)
        rels = RunRelationships(workspace=Relationship(data=create_workspace_reference("ws-123")))
        data = RunData(id="run-456", attributes=attrs, relationships=rels)

        assert data.id == "run-456"
        assert data.type == "runs"
        assert data.attributes.run_message == "Full test run"
        assert data.attributes.auto_apply is True
        assert data.relationships.workspace.data.id == "ws-123"

    def test_run_data_validation(self):
        """Test RunData validation."""
        # Test that RunData can be created with minimal data since attributes and relationships are optional
        run_data = RunData()
        assert run_data.type == "runs"
        assert run_data.attributes is None
        assert run_data.relationships is None

        # Test with only relationships
        run_data_with_rels = RunData(relationships=RunRelationships())
        assert run_data_with_rels.attributes is None
        assert run_data_with_rels.relationships is not None

        # Test with only attributes
        run_data_with_attrs = RunData(attributes=RunAttributes())
        assert run_data_with_attrs.attributes is not None
        assert run_data_with_attrs.relationships is None

    def test_run_data_type_literal(self):
        """Test RunData type field is literal 'runs'."""
        attrs = RunAttributes()
        rels = RunRelationships()

        data = RunData(attributes=attrs, relationships=rels)
        assert data.type == "runs"

        # Type should be automatically set even if not provided
        data2 = RunData()
        assert data2.type == "runs"


class TestRunRequest:
    """Test cases for RunRequest model."""

    def test_run_request_create_basic(self):
        """Test basic RunRequest creation."""
        request = RunRequest.create(workspace_id="ws-123")

        assert request.data.type == "runs"
        assert request.data.relationships.workspace.data.id == "ws-123"
        assert request.data.relationships.workspace.data.type == "workspaces"

    def test_run_request_create_with_configuration_version(self):
        """Test RunRequest creation with configuration version."""
        request = RunRequest.create(workspace_id="ws-123", configuration_version_id="cv-456")

        assert request.data.relationships.workspace.data.id == "ws-123"
        assert request.data.relationships.configuration_version.data.id == "cv-456"
        assert request.data.relationships.configuration_version.data.type == "configuration-versions"

    def test_run_request_create_with_all_attributes(self):
        """Test RunRequest creation with all attributes."""
        request = RunRequest.create(
            workspace_id="ws-123",
            configuration_version_id="cv-456",
            run_message="Test run with all attributes",
            auto_apply=True,
            plan_only=False,
            variables=[{"key": "env", "value": "test"}, {"key": "region", "value": "us-east-1"}],
        )

        assert request.data.attributes.run_message == "Test run with all attributes"
        assert request.data.attributes.auto_apply is True
        assert request.data.attributes.plan_only is False
        assert len(request.data.attributes.variables) == 2
        assert request.data.attributes.variables[0].key == "env"
        assert request.data.attributes.variables[0].value == "test"
        assert request.data.attributes.variables[1].key == "region"
        assert request.data.attributes.variables[1].value == "us-east-1"

    def test_run_request_serialization(self):
        """Test RunRequest serialization."""
        request = RunRequest.create(workspace_id="ws-serialization-test", run_message="Serialization test")

        serialized = request.model_dump(by_alias=True, exclude_none=True)

        assert "data" in serialized
        assert serialized["data"]["type"] == "runs"
        assert serialized["data"]["attributes"]["message"] == "Serialization test"  # Should use alias
        assert serialized["data"]["relationships"]["workspace"]["data"]["id"] == "ws-serialization-test"

    def test_run_request_without_configuration_version(self):
        """Test RunRequest without configuration version."""
        request = RunRequest.create(workspace_id="ws-no-cv", run_message="No config version")

        assert request.data.relationships.workspace.data.id == "ws-no-cv"
        assert request.data.relationships.configuration_version is None

    def test_run_request_validation_empty_workspace_id(self):
        """Test RunRequest validation with empty workspace ID."""
        # Empty workspace ID should still create valid request
        request = RunRequest.create(workspace_id="")
        assert request.data.relationships.workspace.data.id == ""


class TestRunStates:
    """Test cases for RunStates enum."""

    @pytest.mark.parametrize(
        "state",
        [
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
        ],
    )
    def test_success_states(self, state):
        """Test success states."""
        assert RunStates.is_success_state(state) is True
        assert RunStates.is_failure_state(state) is False
        assert RunStates.is_intermediate_state(state) is False

    @pytest.mark.parametrize("state", ["errored", "policy_soft_failed"])
    def test_failure_states(self, state):
        """Test failure states."""
        assert RunStates.is_failure_state(state) is True
        assert RunStates.is_success_state(state) is False
        assert RunStates.is_intermediate_state(state) is False

    @pytest.mark.parametrize("state", ["plan_queued", "queuing", "planning", "applying"])
    def test_intermediate_states(self, state):
        """Test intermediate states."""
        assert RunStates.is_intermediate_state(state) is True
        assert RunStates.is_success_state(state) is False
        assert RunStates.is_failure_state(state) is False

    @pytest.mark.parametrize("state", ["unknown", "custom_state", "", "pending", "new_future_state", "PLANNED", "applied_with_typo"])
    def test_unknown_states(self, state):
        """Test unknown/invalid states."""
        assert RunStates.is_success_state(state) is False
        assert RunStates.is_failure_state(state) is False
        assert RunStates.is_intermediate_state(state) is False

    def test_state_constants(self):
        """Test state constant lists."""
        # Ensure no duplicates
        assert len(RunStates.SUCCESS_STATES) == len(set(RunStates.SUCCESS_STATES))
        assert len(RunStates.FAILURE_STATES) == len(set(RunStates.FAILURE_STATES))
        assert len(RunStates.INTERMEDIATE_STATES) == len(set(RunStates.INTERMEDIATE_STATES))

        # Ensure no overlap
        all_states = set(RunStates.SUCCESS_STATES + RunStates.FAILURE_STATES + RunStates.INTERMEDIATE_STATES)
        assert len(all_states) == len(RunStates.SUCCESS_STATES) + len(RunStates.FAILURE_STATES) + len(RunStates.INTERMEDIATE_STATES)

    def test_case_sensitivity(self):
        """Test state comparison is case sensitive."""
        assert RunStates.is_success_state("PLANNED") is False  # Should be lowercase
        assert RunStates.is_success_state("planned") is True


class TestRunsModelsEdgeCases:
    """Test edge cases and special scenarios for run models."""

    @pytest.mark.parametrize(
        "list_value,expected",
        [
            (["module.vpc", "module.ec2"], ["module.vpc", "module.ec2"]),
            (["single-module"], ["single-module"]),
            ([], []),
            (None, None),
        ],
    )
    def test_run_attributes_with_list_fields(self, list_value, expected):
        """Test RunAttributes with various list field values."""
        attrs = RunAttributes(target_addrs=list_value)
        assert attrs.target_addrs == expected

    @pytest.mark.parametrize(
        "variables_value,expected_length,expected_first_key,expected_first_value",
        [
            (None, None, None, None),
            ([{"key": "env", "value": "production"}], 1, "env", "production"),
            ([{"key": "complex", "value": "nested_value"}], 1, "complex", "nested_value"),
            ([{"key": "array_value", "value": "1,2,3"}], 1, "array_value", "1,2,3"),
            ([], 0, None, None),
        ],
    )
    def test_run_attributes_with_variables(self, variables_value, expected_length, expected_first_key, expected_first_value):
        """Test RunAttributes with various variable configurations."""
        attrs = RunAttributes(variables=variables_value)
        if expected_length is None:
            assert attrs.variables is None
        elif expected_length == 0:
            assert attrs.variables == []
        else:
            assert len(attrs.variables) == expected_length
            assert attrs.variables[0].key == expected_first_key
            assert attrs.variables[0].value == expected_first_value

    @pytest.mark.parametrize(
        "message",
        [
            "Deploy 🚀 with émojis & spëcial chars: @#$%^&*()",
            "Multi-line\nmessage\nwith\ntabs\t\t",
            "Message with 'single' and \"double\" quotes",
            "Very long message: " + "x" * 1000,
            "",
            'Message with JSON: {"key": "value", "array": [1, 2, 3]}',
        ],
    )
    def test_run_request_with_special_characters_in_message(self, message):
        """Test RunRequest with special characters in message."""
        request = RunRequest.create(workspace_id="ws-special", run_message=message)
        assert request.data.attributes.run_message == message

    @pytest.mark.parametrize(
        "links_config",
        [
            {"self": "/api/v2/runs/run-123"},
            {"self": "/api/v2/runs/run-123", "related": "/api/v2/workspaces/ws-456"},
            {},
            None,
        ],
    )
    def test_run_relationships_with_missing_data(self, links_config):
        """Test RunRelationships with only links and no data."""
        workspace_rel = Relationship(data=None, links=links_config)
        rels = RunRelationships(workspace=workspace_rel)

        assert rels.workspace.data is None
        assert rels.workspace.links == links_config

    def test_run_data_type_immutability(self):
        """Test that RunData type field cannot be overridden."""
        data = RunData()
        assert data.type == "runs"

        # Type should remain 'runs' even if we try to set it differently during creation
        # (This test verifies the Literal type works as expected)
        data_with_explicit_type = RunData(type="runs")
        assert data_with_explicit_type.type == "runs"

    @pytest.mark.parametrize(
        "field_name,test_values",
        [
            ("auto_apply", [True, False, None]),
            ("plan_only", [True, False, None]),
            ("is_destroy", [True, False, None]),
            ("refresh_only", [True, False, None]),
            ("save_plan", [True, False, None]),
            ("refresh", [True, False, None]),
            ("allow_empty_apply", [True, False, None]),
            ("allow_config_generation", [True, False, None]),
            ("debugging_mode", [True, False, None]),
        ],
    )
    def test_run_attributes_boolean_fields(self, field_name, test_values):
        """Test boolean field handling in RunAttributes."""
        for value in test_values:
            attrs = RunAttributes(**{field_name: value})
            assert getattr(attrs, field_name) == value


class TestRunModelsPerformance:
    """Performance and stress tests for run models."""

    def test_run_request_creation_performance(self):
        """Test performance of RunRequest creation."""
        start_time = time.time()

        # Create multiple run requests
        for i in range(100):
            request = RunRequest.create(
                workspace_id=f"ws-{i}",
                configuration_version_id=f"cv-{i}",
                run_message=f"Performance test run {i}",
                variables=[{"key": "index", "value": str(i)}, {"key": "test", "value": "performance"}],
            )
            assert request.data.attributes.run_message == f"Performance test run {i}"

        end_time = time.time()
        duration = end_time - start_time

        # Should complete reasonably quickly (less than 1 second for 100 requests)
        assert duration < 1.0, f"RunRequest creation took too long: {duration} seconds"

    def test_run_attributes_large_data_handling(self):
        """Test RunAttributes with large data structures."""
        # Create large variables list
        large_variables = [{"key": f"var_{i}", "value": f"value_{i}" * 100} for i in range(100)]

        # Create large target addresses list
        large_target_addrs = [f"module.{i}.resource_{j}" for i in range(10) for j in range(10)]

        attrs = RunAttributes(
            run_message="Large data test",
            variables=large_variables,
            target_addrs=large_target_addrs,
        )

        assert len(attrs.variables) == 100
        assert len(attrs.target_addrs) == 100
        assert attrs.run_message == "Large data test"


class TestRunModelsIntegration:
    """Integration tests combining multiple run models."""

    def test_complete_run_workflow_simulation(self):
        """Test complete run workflow using all models together."""
        # Step 1: Create run request
        request = RunRequest.create(
            workspace_id="ws-integration-test",
            configuration_version_id="cv-integration-test",
            run_message="Integration test run",
            auto_apply=False,
            plan_only=True,
        )

        assert request.data.type == "runs"
        assert request.data.attributes.run_message == "Integration test run"
        assert request.data.relationships.workspace.data.id == "ws-integration-test"
        assert request.data.relationships.configuration_version.data.id == "cv-integration-test"

        # Step 2: Simulate API response structure
        response_attrs = RunAttributes(
            run_message="Integration test run",
            auto_apply=False,
            plan_only=True,
        )

        response_rels = RunRelationships(
            workspace=Relationship(data=create_workspace_reference("ws-integration-test")),
            configuration_version=Relationship(data=create_configuration_version_reference("cv-integration-test")),
        )

        # RunResource doesn't exist - using BaseTerraformResource instead
        from ansible_collections.hashicorp.terraform.plugins.module_utils.models.common import BaseTerraformResource

        response_data = BaseTerraformResource[RunAttributes, RunRelationships](
            id="run-integration-response",
            type="runs",
            attributes=response_attrs,
            relationships=response_rels,
        )

        assert response_data.id == "run-integration-response"
        assert response_data.type == "runs"
        assert response_data.attributes.run_message == "Integration test run"

        # Step 3: Test state transitions
        assert RunStates.is_intermediate_state("planning")
        assert RunStates.is_success_state("planned")
        assert not RunStates.is_failure_state("planned")

    @pytest.mark.parametrize(
        "factory_method,workspace_id,expected_type",
        [
            ("create", "ws-factory-1", "runs"),
        ],
    )
    def test_factory_functions_consistency(self, factory_method, workspace_id, expected_type):
        """Test factory method consistency."""
        method = getattr(RunRequest, factory_method)
        result = method(workspace_id=workspace_id)

        assert result.data.type == expected_type
        assert result.data.relationships.workspace.data.id == workspace_id
