# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


import time

from datetime import datetime

import pytest

from pydantic import ValidationError

from ansible_collections.hashicorp.terraform.plugins.module_utils.models.common import (
    BaseAttributes,
    BaseRelationships,
    Relationship,
    create_configuration_version_reference,
    create_workspace_reference,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.run import (
    RunAttributes,
    RunData,
    RunRelationships,
    RunRequest,
    RunResource,
    RunResponse,
    RunStates,
    create_run_request,
)


class TestRunAttributes:
    """Test cases for RunAttributes model."""

    def test_run_attributes_creation_minimal(self):
        """Test creating RunAttributes with minimal data."""
        attrs = RunAttributes()

        # Should have inherited fields from BaseAttributes
        assert attrs.created_at is None
        assert attrs.updated_at is None
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
                    "variables": {"env": "production", "region": "us-west-2"},
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
                    "variables": {"env": "production", "region": "us-west-2"},
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
                    "variables": {"env": "staging"},
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
                    "variables": {"env": "staging"},
                },
            ),
            # Empty collections
            (
                {
                    "run_message": "Empty collections test",
                    "target_addrs": [],
                    "variables": {},
                },
                {
                    "run_message": "Empty collections test",
                    "target_addrs": [],
                    "variables": {},
                },
            ),
            # Special characters and unicode
            (
                {
                    "run_message": "Test with émojis 🚀 and spëcial chars: @#$%",
                    "target_addrs": ["module.test-with_special.chars"],
                    "variables": {"unicode_key_こんにちは": "unicode_value_世界"},
                },
                {
                    "run_message": "Test with émojis 🚀 and spëcial chars: @#$%",
                    "target_addrs": ["module.test-with_special.chars"],
                    "variables": {"unicode_key_こんにちは": "unicode_value_世界"},
                },
            ),
        ],
    )
    def test_run_attributes_creation_full(self, attribute_values, expected_values):
        """Test creating RunAttributes with various full configurations."""
        now = datetime.now()
        attrs = RunAttributes(created_at=now, updated_at=now, **attribute_values)

        assert attrs.created_at == now
        assert attrs.updated_at == now

        for key, expected_value in expected_values.items():
            actual_value = getattr(attrs, key)
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
                    "is-destroy": True,
                    "target-addrs": ["module.test"],
                    "created-at": "2023-01-01T00:00:00Z",
                    "updated-at": "2023-01-02T00:00:00Z",
                },
                {
                    "run_message": "Test message",
                    "refresh_only": True,
                    "plan_only": False,
                    "auto_apply": True,
                    "save_plan": False,
                    "is_destroy": True,
                    "target_addrs": ["module.test"],
                },
            ),
            # Minimal alias test
            (
                {
                    "message": "Minimal test",
                    "auto-apply": False,
                },
                {
                    "run_message": "Minimal test",
                    "auto_apply": False,
                },
            ),
            # New fields test
            (
                {
                    "message": "Extended test",
                    "replace-addrs": ["module.to_replace"],
                    "allow-empty-apply": True,
                    "allow-config-generation": False,
                    "debugging-mode": True,
                    "terraform-version": "1.5.0",
                },
                {
                    "run_message": "Extended test",
                    "replace_addrs": ["module.to_replace"],
                    "allow_empty_apply": True,
                    "allow_config_generation": False,
                    "debugging_mode": True,
                    "terraform_version": "1.5.0",
                },
            ),
        ],
    )
    def test_run_attributes_field_aliases(self, alias_data, expected_values):
        """Test RunAttributes field aliases with various configurations."""
        attrs = RunAttributes.model_validate(alias_data)

        for field_name, expected_value in expected_values.items():
            actual_value = getattr(attrs, field_name)
            assert actual_value == expected_value, f"Expected {field_name}={expected_value}, got {actual_value}"

        # Check timestamp fields if present
        if "created-at" in alias_data:
            assert attrs.created_at is not None
        if "updated-at" in alias_data:
            assert attrs.updated_at is not None

    @pytest.mark.parametrize(
        "attrs_data,expected_aliases,excluded_fields",
        [
            # Basic serialization test
            (
                {
                    "run_message": "Test message",
                    "refresh_only": True,
                    "auto_apply": True,
                    "is_destroy": False,
                    "target_addrs": ["module.test"],
                },
                {
                    "message": "Test message",
                    "refresh-only": True,
                    "auto-apply": True,
                    "is-destroy": False,
                    "target-addrs": ["module.test"],
                },
                ["refresh_only", "auto_apply", "is_destroy", "target_addrs"],
            ),
            # Extended fields serialization test
            (
                {
                    "run_message": "Extended test",
                    "replace_addrs": ["module.replace"],
                    "allow_empty_apply": True,
                    "debugging_mode": False,
                    "terraform_version": "1.6.0",
                },
                {
                    "message": "Extended test",
                    "replace-addrs": ["module.replace"],
                    "allow-empty-apply": True,
                    "debugging-mode": False,
                    "terraform-version": "1.6.0",
                },
                ["replace_addrs", "allow_empty_apply", "debugging_mode", "terraform_version"],
            ),
        ],
    )
    def test_run_attributes_serialization_with_aliases(self, attrs_data, expected_aliases, excluded_fields):
        """Test RunAttributes serialization uses field aliases with various configurations."""
        attrs = RunAttributes(**attrs_data)
        data = attrs.model_dump(by_alias=True, exclude_unset=True)

        # Check expected aliases are present
        for alias_key, expected_value in expected_aliases.items():
            assert alias_key in data, f"Expected alias '{alias_key}' not found in serialized data"
            assert data[alias_key] == expected_value, f"Expected {alias_key}={expected_value}, got {data[alias_key]}"

        # Check underscore versions are not present
        for field_name in excluded_fields:
            assert field_name not in data, f"Underscore field '{field_name}' should not be in serialized data"

    def test_run_attributes_inheritance(self):
        """Test RunAttributes inherits from BaseAttributes."""
        assert issubclass(RunAttributes, BaseAttributes)

        # Should have BaseAttributes fields
        attrs = RunAttributes()
        assert hasattr(attrs, "created_at")
        assert hasattr(attrs, "updated_at")


class TestRunRelationships:
    """Test cases for RunRelationships model."""

    def test_run_relationships_creation_empty(self):
        """Test creating empty RunRelationships."""
        rels = RunRelationships()

        assert rels.workspace is None
        assert rels.configuration_version is None
        assert rels.plan is None
        assert rels.apply is None
        assert rels.created_by is None
        assert rels.policy_checks is None
        assert rels.run_events is None
        assert rels.task_stages is None

    def test_run_relationships_creation_with_workspace(self):
        """Test creating RunRelationships with workspace."""
        workspace_ref = create_workspace_reference("ws-123")
        workspace_rel = Relationship(data=workspace_ref)

        rels = RunRelationships(workspace=workspace_rel)

        assert rels.workspace.data.type == "workspaces"
        assert rels.workspace.data.id == "ws-123"

    def test_run_relationships_creation_full(self):
        """Test creating RunRelationships with all fields."""
        workspace_ref = create_workspace_reference("ws-123")
        config_ref = create_configuration_version_reference("cv-456")

        from ansible_collections.hashicorp.terraform.plugins.module_utils.models.common import ResourceData

        plan_ref = ResourceData(type="plans", id="plan-789")
        apply_ref = ResourceData(type="applies", id="apply-101")
        user_ref = ResourceData(type="users", id="user-202")

        rels = RunRelationships(
            workspace=Relationship(data=workspace_ref),
            configuration_version=Relationship(data=config_ref),
            plan=Relationship(data=plan_ref),
            apply=Relationship(data=apply_ref),
            created_by=Relationship(data=user_ref),
        )

        assert rels.workspace.data.id == "ws-123"
        assert rels.configuration_version.data.id == "cv-456"
        assert rels.plan.data.id == "plan-789"
        assert rels.apply.data.id == "apply-101"
        assert rels.created_by.data.id == "user-202"

    def test_run_relationships_field_aliases(self):
        """Test RunRelationships field aliases."""
        data = {
            "workspace": {"data": {"type": "workspaces", "id": "ws-123"}},
            "configuration-version": {"data": {"type": "configuration-versions", "id": "cv-456"}},
            "created-by": {"data": {"type": "users", "id": "user-789"}},
            "policy-checks": {"data": {"type": "policy-checks", "id": "pc-101"}},
            "run-events": {"data": {"type": "run-events", "id": "re-202"}},
            "task-stages": {"data": {"type": "task-stages", "id": "ts-303"}},
        }

        rels = RunRelationships.model_validate(data)

        assert rels.workspace.data.id == "ws-123"
        assert rels.configuration_version.data.id == "cv-456"
        assert rels.created_by.data.id == "user-789"
        assert rels.policy_checks.data.id == "pc-101"
        assert rels.run_events.data.id == "re-202"
        assert rels.task_stages.data.id == "ts-303"

    def test_run_relationships_serialization_with_aliases(self):
        """Test RunRelationships serialization uses field aliases."""
        config_ref = create_configuration_version_reference("cv-456")
        rels = RunRelationships(configuration_version=Relationship(data=config_ref))

        data = rels.model_dump(by_alias=True, exclude_unset=True)

        assert "configuration-version" in data
        assert "configuration_version" not in data
        assert data["configuration-version"]["data"]["id"] == "cv-456"

    def test_run_relationships_inheritance(self):
        """Test RunRelationships inherits from BaseRelationships."""
        assert issubclass(RunRelationships, BaseRelationships)


class TestRunData:
    """Test cases for RunData model."""

    def test_run_data_creation_minimal(self):
        """Test creating RunData with minimal required fields."""
        attrs = RunAttributes(run_message="Test run")
        rels = RunRelationships()

        data = RunData(attributes=attrs, relationships=rels)

        assert data.type == "runs"
        assert data.attributes.run_message == "Test run"
        assert data.relationships is not None

    def test_run_data_creation_full(self):
        """Test creating RunData with full configuration."""
        attrs = RunAttributes(run_message="Full test run", auto_apply=True, is_destroy=False)

        workspace_ref = create_workspace_reference("ws-123")
        rels = RunRelationships(workspace=Relationship(data=workspace_ref))

        data = RunData(attributes=attrs, relationships=rels, type="runs")

        assert data.type == "runs"
        assert data.attributes.run_message == "Full test run"
        assert data.attributes.auto_apply is True
        assert data.relationships.workspace.data.id == "ws-123"

    def test_run_data_validation(self):
        """Test RunData validation."""
        # Missing required attributes
        with pytest.raises(ValidationError):
            RunData(relationships=RunRelationships())

        # Missing required relationships
        with pytest.raises(ValidationError):
            RunData(attributes=RunAttributes())

    def test_run_data_type_literal(self):
        """Test RunData type field is literal 'runs'."""
        attrs = RunAttributes()
        rels = RunRelationships()

        # Should accept "runs"
        data = RunData(attributes=attrs, relationships=rels, type="runs")
        assert data.type == "runs"

        # Should default to "runs"
        data2 = RunData(attributes=attrs, relationships=rels)
        assert data2.type == "runs"


class TestRunRequest:
    """Test cases for RunRequest model."""

    def test_run_request_create_basic(self):
        """Test RunRequest.create with basic parameters."""
        request = RunRequest.create(workspace_id="ws-123", run_message="Test run")

        assert request.data.type == "runs"
        assert request.data.attributes.run_message == "Test run"
        assert request.data.relationships.workspace.data.type == "workspaces"
        assert request.data.relationships.workspace.data.id == "ws-123"

    def test_run_request_create_with_configuration_version(self):
        """Test RunRequest.create with configuration version."""
        request = RunRequest.create(
            workspace_id="ws-123",
            configuration_version_id="cv-456",
            run_message="Test run with config version",
            auto_apply=True,
        )

        assert request.data.attributes.run_message == "Test run with config version"
        assert request.data.attributes.auto_apply is True
        assert request.data.relationships.workspace.data.id == "ws-123"
        assert request.data.relationships.configuration_version.data.type == "configuration-versions"
        assert request.data.relationships.configuration_version.data.id == "cv-456"

    def test_run_request_create_with_all_attributes(self):
        """Test RunRequest.create with all possible attributes."""
        request = RunRequest.create(
            workspace_id="ws-123",
            run_message="Complete test run",
            auto_apply=True,
            plan_only=False,
            save_plan=True,
            is_destroy=False,
            refresh_only=False,
            refresh=True,
            target_addrs=["module.vpc", "module.security"],
            variables={"environment": "test", "debug": True},
        )

        attrs = request.data.attributes
        assert attrs.run_message == "Complete test run"
        assert attrs.auto_apply is True
        assert attrs.plan_only is False
        assert attrs.save_plan is True
        assert attrs.is_destroy is False
        assert attrs.refresh_only is False
        assert attrs.refresh is True
        assert attrs.target_addrs == ["module.vpc", "module.security"]
        assert attrs.variables == {"environment": "test", "debug": True}

    def test_run_request_serialization(self):
        """Test RunRequest serialization for API calls."""
        request = RunRequest.create(workspace_id="ws-123", run_message="Serialization test", auto_apply=True)

        # Test serialization with exclude_unset to get clean API payload
        data = request.model_dump(by_alias=True, exclude_unset=True)
        assert "data" in data
        assert data["data"]["attributes"]["message"] == "Serialization test"
        assert data["data"]["attributes"]["auto-apply"] is True
        assert data["data"]["relationships"]["workspace"]["data"]["type"] == "workspaces"
        assert data["data"]["relationships"]["workspace"]["data"]["id"] == "ws-123"

        # Test serialization without exclude_unset to verify type field is present
        full_data = request.model_dump(by_alias=True)
        assert full_data["data"]["type"] == "runs"

    def test_run_request_without_configuration_version(self):
        """Test RunRequest.create without configuration version."""
        request = RunRequest.create(workspace_id="ws-456")

        assert request.data.relationships.workspace.data.id == "ws-456"
        assert request.data.relationships.configuration_version is None

    def test_run_request_validation_empty_workspace_id(self):
        """Test RunRequest.create validation with empty workspace_id."""
        # Should still work with empty string (validation at API level)
        request = RunRequest.create(workspace_id="")
        assert request.data.relationships.workspace.data.id == ""


class TestRunStates:
    """Test cases for RunStates utility class."""

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
        """Test success state recognition for all success states."""
        assert RunStates.is_success_state(state), f"State '{state}' should be success state"
        assert not RunStates.is_failure_state(state), f"State '{state}' should not be failure state"
        assert not RunStates.is_intermediate_state(state), f"State '{state}' should not be intermediate state"
        assert RunStates.is_final_state(state), f"State '{state}' should be final state"

    @pytest.mark.parametrize(
        "state",
        [
            "errored",
            "policy_soft_failed",
        ],
    )
    def test_failure_states(self, state):
        """Test failure state recognition for all failure states."""
        assert RunStates.is_failure_state(state), f"State '{state}' should be failure state"
        assert not RunStates.is_success_state(state), f"State '{state}' should not be success state"
        assert not RunStates.is_intermediate_state(state), f"State '{state}' should not be intermediate state"
        assert RunStates.is_final_state(state), f"State '{state}' should be final state"

    @pytest.mark.parametrize(
        "state",
        [
            "plan_queued",
            "queuing",
            "planning",
            "applying",
        ],
    )
    def test_intermediate_states(self, state):
        """Test intermediate state recognition for all intermediate states."""
        assert RunStates.is_intermediate_state(state), f"State '{state}' should be intermediate state"
        assert not RunStates.is_success_state(state), f"State '{state}' should not be success state"
        assert not RunStates.is_failure_state(state), f"State '{state}' should not be failure state"
        assert not RunStates.is_final_state(state), f"State '{state}' should not be final state"

    @pytest.mark.parametrize(
        "state",
        [
            "unknown",
            "custom_state",
            "",
            "pending",
            "new_future_state",
            "PLANNED",  # Case sensitivity test
            "applied_with_typo",
        ],
    )
    def test_unknown_states(self, state):
        """Test unknown state handling for various unknown states."""
        assert not RunStates.is_success_state(state), f"Unknown state '{state}' should not be success"
        assert not RunStates.is_failure_state(state), f"Unknown state '{state}' should not be failure"
        assert not RunStates.is_intermediate_state(state), f"Unknown state '{state}' should not be intermediate"
        assert not RunStates.is_final_state(state), f"Unknown state '{state}' should not be final"

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
        """Test state recognition is case sensitive."""
        assert RunStates.is_success_state("applied")
        assert not RunStates.is_success_state("Applied")
        assert not RunStates.is_success_state("APPLIED")


class TestRunResourceAndResponse:
    """Test cases for RunResource and RunResponse type aliases."""

    def test_run_resource_creation(self):
        """Test creating RunResource (type alias)."""
        attrs = RunAttributes(run_message="Test resource")
        rels = RunRelationships()

        resource = RunResource(id="run-123", type="runs", attributes=attrs, relationships=rels)

        assert resource.id == "run-123"
        assert resource.type == "runs"
        assert resource.attributes.run_message == "Test resource"

    def test_run_response_creation(self):
        """Test creating RunResponse (type alias)."""
        attrs = RunAttributes(run_message="Test response")
        rels = RunRelationships()

        resource = RunResource(id="run-456", type="runs", attributes=attrs, relationships=rels)

        response = RunResponse(data=resource)

        assert response.data.id == "run-456"
        assert response.data.attributes.run_message == "Test response"

    def test_run_response_with_multiple_resources(self):
        """Test RunResponse with multiple resources."""
        resources = []
        for i in range(3):
            attrs = RunAttributes(run_message=f"Test run {i}")
            rels = RunRelationships()
            resources.append(RunResource(id=f"run-{i}", type="runs", attributes=attrs, relationships=rels))

        response = RunResponse(data=resources)

        assert len(response.data) == 3
        assert response.data[0].id == "run-0"
        assert response.data[1].attributes.run_message == "Test run 1"
        assert response.data[2].id == "run-2"


class TestCreateRunRequest:
    """Test cases for create_run_request factory function."""

    def test_create_run_request_basic(self):
        """Test create_run_request with basic parameters."""
        request = create_run_request(workspace_id="ws-123", run_message="Factory test")

        assert request.data.type == "runs"
        assert request.data.attributes.run_message == "Factory test"
        assert request.data.relationships.workspace.data.id == "ws-123"

    def test_create_run_request_with_all_params(self):
        """Test create_run_request with all parameters."""
        request = create_run_request(
            workspace_id="ws-123",
            configuration_version_id="cv-456",
            run_message="Complete factory test",
            auto_apply=True,
            plan_only=False,
            save_plan=True,
            is_destroy=False,
            refresh_only=False,
            refresh=True,
            target_addrs=["module.test"],
            variables={"test": True},
        )

        attrs = request.data.attributes
        assert attrs.run_message == "Complete factory test"
        assert attrs.auto_apply is True
        assert attrs.plan_only is False
        assert attrs.save_plan is True
        assert attrs.is_destroy is False
        assert attrs.refresh_only is False
        assert attrs.refresh is True
        assert attrs.target_addrs == ["module.test"]
        assert attrs.variables == {"test": True}

        assert request.data.relationships.workspace.data.id == "ws-123"
        assert request.data.relationships.configuration_version.data.id == "cv-456"


class TestRunsModelsEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.parametrize(
        "list_value,expected",
        [
            ([], []),
            (["module.single"], ["module.single"]),
            (["module.a", "module.b", "module.c"], ["module.a", "module.b", "module.c"]),
            (None, None),
        ],
    )
    def test_run_attributes_with_list_fields(self, list_value, expected):
        """Test RunAttributes with various list field configurations."""
        attrs = RunAttributes(
            target_addrs=list_value,
            replace_addrs=list_value,
        )
        assert attrs.target_addrs == expected
        assert attrs.replace_addrs == expected

    @pytest.mark.parametrize(
        "variables_value,expected",
        [
            (None, None),
            ({}, {}),
            ({"key": "value"}, {"key": "value"}),
            ({"env": "prod", "debug": True, "count": 42}, {"env": "prod", "debug": True, "count": 42}),
            ({"unicode_こんにちは": "value_世界"}, {"unicode_こんにちは": "value_世界"}),
        ],
    )
    def test_run_attributes_with_variables(self, variables_value, expected):
        """Test RunAttributes with various variable configurations."""
        attrs = RunAttributes(variables=variables_value)
        assert attrs.variables == expected

    @pytest.mark.parametrize(
        "special_message",
        [
            "Deploy 🚀 with émojis & spëcial chars: @#$%^&*()",
            "Multi-line\nmessage\nwith\ntabs\t\t",
            "Message with 'single' and \"double\" quotes",
            "Very long message: " + "x" * 1000,
            "",  # Empty message
            'Message with JSON: {"key": "value", "array": [1, 2, 3]}',
        ],
    )
    def test_run_request_with_special_characters_in_message(self, special_message):
        """Test RunRequest with various special characters and edge cases in message."""
        request = RunRequest.create(workspace_id="ws-special", run_message=special_message)
        assert request.data.attributes.run_message == special_message

    @pytest.mark.parametrize(
        "links_config",
        [
            {"self": "/api/v2/workspaces/ws-123"},
            {"related": "/api/v2/workspaces/ws-123/runs"},
            {"custom": "/custom/endpoint"},
            {},  # Empty links
        ],
    )
    def test_run_relationships_with_missing_data(self, links_config):
        """Test RunRelationships with various link configurations but missing data."""
        rels = RunRelationships(workspace=Relationship(links=links_config))

        assert rels.workspace.data is None
        assert rels.workspace.links == links_config

        for key, value in links_config.items():
            assert rels.workspace.links[key] == value

    def test_run_data_type_immutability(self):
        """Test RunData type field behavior and immutability."""
        attrs = RunAttributes()
        rels = RunRelationships()

        # Type should default to "runs"
        data = RunData(attributes=attrs, relationships=rels)
        assert data.type == "runs"

        # Type should be literal "runs" even if explicitly set
        data_explicit = RunData(attributes=attrs, relationships=rels, type="runs")
        assert data_explicit.type == "runs"

    @pytest.mark.parametrize(
        "boolean_field,test_values",
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
    def test_run_attributes_boolean_fields(self, boolean_field, test_values):
        """Test RunAttributes boolean fields with various values."""
        for value in test_values:
            attrs = RunAttributes(**{boolean_field: value})
            assert getattr(attrs, boolean_field) == value


class TestRunModelsPerformance:
    """Test performance characteristics of run models."""

    def test_run_request_creation_performance(self):
        """Test performance of RunRequest creation with large data."""
        start_time = time.time()

        # Create many run requests
        requests = []
        for i in range(100):
            request = RunRequest.create(
                workspace_id=f"ws-{i}",
                run_message=f"Performance test run {i}",
                auto_apply=i % 2 == 0,
                target_addrs=[f"module.test_{j}" for j in range(10)],
                variables={f"var_{j}": f"value_{j}" for j in range(5)},
            )
            requests.append(request)

        end_time = time.time()

        assert len(requests) == 100
        # Should complete in reasonable time (less than 2 seconds)
        assert (end_time - start_time) < 2.0

        # Verify some random requests
        assert requests[0].data.attributes.run_message == "Performance test run 0"
        assert requests[50].data.relationships.workspace.data.id == "ws-50"

    def test_run_attributes_large_data_handling(self):
        """Test RunAttributes with large data sets."""
        # Large target addresses list
        large_target_addrs = [f"module.target_{i}" for i in range(1000)]

        # Large variables dictionary
        large_variables = {f"var_{i}": f"value_{i}" * 10 for i in range(100)}

        start_time = time.time()

        attrs = RunAttributes(
            run_message="Large data test",
            target_addrs=large_target_addrs,
            variables=large_variables,
        )

        # Test serialization
        data = attrs.model_dump(by_alias=True)

        end_time = time.time()

        assert len(attrs.target_addrs) == 1000
        assert len(attrs.variables) == 100
        assert data["target-addrs"] == large_target_addrs
        assert data["variables"] == large_variables

        # Should complete in reasonable time
        assert (end_time - start_time) < 1.0


class TestRunModelsIntegration:
    """Integration tests for run models working together."""

    def test_complete_run_workflow_simulation(self):
        """Test a complete run workflow with all models working together."""
        # Step 1: Create a run request
        request = RunRequest.create(
            workspace_id="ws-integration-test",
            configuration_version_id="cv-integration-test",
            run_message="Integration test run",
            auto_apply=False,
            plan_only=True,
            target_addrs=["module.vpc", "module.security_group"],
            variables={"environment": "test", "region": "us-east-1"},
        )

        # Verify request structure
        assert request.data.type == "runs"
        assert request.data.attributes.run_message == "Integration test run"
        assert request.data.relationships.workspace.data.id == "ws-integration-test"
        assert request.data.relationships.configuration_version.data.id == "cv-integration-test"

        # Step 2: Simulate API response structure
        response_attrs = RunAttributes(
            run_message="Integration test run",
            auto_apply=False,
            plan_only=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        response_rels = RunRelationships(
            workspace=Relationship(data=create_workspace_reference("ws-integration-test")),
            configuration_version=Relationship(data=create_configuration_version_reference("cv-integration-test")),
        )

        run_resource = RunResource(
            id="run-integration-test",
            type="runs",
            attributes=response_attrs,
            relationships=response_rels,
        )

        # Step 3: Test state transitions
        states_to_test = ["plan_queued", "planning", "planned"]
        for state in states_to_test:
            if RunStates.is_intermediate_state(state):
                assert not RunStates.is_final_state(state)
            elif RunStates.is_success_state(state):
                assert RunStates.is_final_state(state)

        # Verify final response structure
        assert run_resource.id == "run-integration-test"
        assert run_resource.attributes.run_message == "Integration test run"
        assert run_resource.relationships.workspace.data.type == "workspaces"

    @pytest.mark.parametrize(
        "factory_function,workspace_id,expected_type",
        [
            (RunRequest.create, "ws-factory-1", "runs"),
            (create_run_request, "ws-factory-2", "runs"),
        ],
    )
    def test_factory_functions_consistency(self, factory_function, workspace_id, expected_type):
        """Test that different factory functions produce consistent results."""
        request1 = factory_function(
            workspace_id=workspace_id,
            message="Factory test",
            auto_apply=True,
        )

        request2 = factory_function(
            workspace_id=workspace_id,
            run_message="Factory test",  # Alternative parameter name
            auto_apply=True,
        )

        # Both should produce valid requests
        assert request1.data.type == expected_type
        assert request2.data.type == expected_type
        assert request1.data.relationships.workspace.data.id == workspace_id
        assert request2.data.relationships.workspace.data.id == workspace_id
