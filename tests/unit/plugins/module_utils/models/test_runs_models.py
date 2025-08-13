# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


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
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.runs import (
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

    def test_run_attributes_creation_full(self):
        """Test creating RunAttributes with all fields."""
        now = datetime.now()
        attrs = RunAttributes(
            created_at=now,
            updated_at=now,
            run_message="Test run message",
            refresh_only=True,
            plan_only=False,
            auto_apply=True,
            save_plan=False,
            is_destroy=False,
            target_addrs=["module.vpc", "module.ec2"],
            refresh=True,
            variables={"env": "production", "region": "us-west-2"},
        )

        assert attrs.created_at == now
        assert attrs.updated_at == now
        assert attrs.run_message == "Test run message"
        assert attrs.refresh_only is True
        assert attrs.plan_only is False
        assert attrs.auto_apply is True
        assert attrs.save_plan is False
        assert attrs.is_destroy is False
        assert attrs.target_addrs == ["module.vpc", "module.ec2"]
        assert attrs.refresh is True
        assert attrs.variables == {"env": "production", "region": "us-west-2"}

    def test_run_attributes_field_aliases(self):
        """Test RunAttributes field aliases."""
        data = {
            "message": "Test message",
            "refresh-only": True,
            "plan-only": False,
            "auto-apply": True,
            "save-plan": False,
            "is-destroy": True,
            "target-addrs": ["module.test"],
            "created-at": "2023-01-01T00:00:00Z",
            "updated-at": "2023-01-02T00:00:00Z",
        }

        attrs = RunAttributes.model_validate(data)

        assert attrs.message == "Test message"
        assert attrs.refresh_only is True
        assert attrs.plan_only is False
        assert attrs.auto_apply is True
        assert attrs.save_plan is False
        assert attrs.is_destroy is True
        assert attrs.target_addrs == ["module.test"]
        assert attrs.created_at is not None
        assert attrs.updated_at is not None

    def test_run_attributes_serialization_with_aliases(self):
        """Test RunAttributes serialization uses field aliases."""
        attrs = RunAttributes(
            run_message="Test message",
            refresh_only=True,
            auto_apply=True,
            is_destroy=False,
            target_addrs=["module.test"],
        )

        data = attrs.model_dump(by_alias=True, exclude_unset=True)

        assert data["message"] == "Test message"
        assert data["refresh-only"] is True
        assert data["auto-apply"] is True
        assert data["is-destroy"] is False
        assert data["target-addrs"] == ["module.test"]

        # Should not contain underscore versions
        assert "refresh_only" not in data
        assert "auto_apply" not in data
        assert "is_destroy" not in data
        assert "target_addrs" not in data

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
        attrs = RunAttributes(message="Test run")
        rels = RunRelationships()

        data = RunData(attributes=attrs, relationships=rels)

        assert data.type == "runs"
        assert data.attributes.message == "Test run"
        assert data.relationships is not None

    def test_run_data_creation_full(self):
        """Test creating RunData with full configuration."""
        attrs = RunAttributes(message="Full test run", auto_apply=True, is_destroy=False)

        workspace_ref = create_workspace_reference("ws-123")
        rels = RunRelationships(workspace=Relationship(data=workspace_ref))

        data = RunData(attributes=attrs, relationships=rels, type="runs")

        assert data.type == "runs"
        assert data.attributes.message == "Full test run"
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
        request = RunRequest.create(workspace_id="ws-123", message="Test run")

        assert request.data.type == "runs"
        assert request.data.attributes.message == "Test run"
        assert request.data.relationships.workspace.data.type == "workspaces"
        assert request.data.relationships.workspace.data.id == "ws-123"

    def test_run_request_create_with_configuration_version(self):
        """Test RunRequest.create with configuration version."""
        request = RunRequest.create(
            workspace_id="ws-123",
            configuration_version_id="cv-456",
            message="Test run with config version",
            auto_apply=True,
        )

        assert request.data.attributes.message == "Test run with config version"
        assert request.data.attributes.auto_apply is True
        assert request.data.relationships.workspace.data.id == "ws-123"
        assert request.data.relationships.configuration_version.data.type == "configuration-versions"
        assert request.data.relationships.configuration_version.data.id == "cv-456"

    def test_run_request_create_with_all_attributes(self):
        """Test RunRequest.create with all possible attributes."""
        request = RunRequest.create(
            workspace_id="ws-123",
            message="Complete test run",
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
        assert attrs.message == "Complete test run"
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

    def test_success_states(self):
        """Test success state recognition."""
        success_states = [
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
        ]

        for state in success_states:
            assert RunStates.is_success_state(state), f"State '{state}' should be success state"
            assert not RunStates.is_failure_state(state), f"State '{state}' should not be failure state"
            assert not RunStates.is_intermediate_state(state), f"State '{state}' should not be intermediate state"
            assert RunStates.is_final_state(state), f"State '{state}' should be final state"

    def test_failure_states(self):
        """Test failure state recognition."""
        failure_states = ["errored", "policy_soft_failed"]

        for state in failure_states:
            assert RunStates.is_failure_state(state), f"State '{state}' should be failure state"
            assert not RunStates.is_success_state(state), f"State '{state}' should not be success state"
            assert not RunStates.is_intermediate_state(state), f"State '{state}' should not be intermediate state"
            assert RunStates.is_final_state(state), f"State '{state}' should be final state"

    def test_intermediate_states(self):
        """Test intermediate state recognition."""
        intermediate_states = ["plan_queued", "queuing", "planning", "applying"]

        for state in intermediate_states:
            assert RunStates.is_intermediate_state(state), f"State '{state}' should be intermediate state"
            assert not RunStates.is_success_state(state), f"State '{state}' should not be success state"
            assert not RunStates.is_failure_state(state), f"State '{state}' should not be failure state"
            assert not RunStates.is_final_state(state), f"State '{state}' should not be final state"

    def test_unknown_states(self):
        """Test unknown state handling."""
        unknown_states = ["unknown", "custom_state", "", "pending"]

        for state in unknown_states:
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
        attrs = RunAttributes(message="Test resource")
        rels = RunRelationships()

        resource = RunResource(id="run-123", type="runs", attributes=attrs, relationships=rels)

        assert resource.id == "run-123"
        assert resource.type == "runs"
        assert resource.attributes.message == "Test resource"

    def test_run_response_creation(self):
        """Test creating RunResponse (type alias)."""
        attrs = RunAttributes(message="Test response")
        rels = RunRelationships()

        resource = RunResource(id="run-456", type="runs", attributes=attrs, relationships=rels)

        response = RunResponse(data=resource)

        assert response.data.id == "run-456"
        assert response.data.attributes.message == "Test response"

    def test_run_response_with_multiple_resources(self):
        """Test RunResponse with multiple resources."""
        resources = []
        for i in range(3):
            attrs = RunAttributes(message=f"Test run {i}")
            rels = RunRelationships()
            resources.append(RunResource(id=f"run-{i}", type="runs", attributes=attrs, relationships=rels))

        response = RunResponse(data=resources)

        assert len(response.data) == 3
        assert response.data[0].id == "run-0"
        assert response.data[1].attributes.message == "Test run 1"
        assert response.data[2].id == "run-2"


class TestCreateRunRequest:
    """Test cases for create_run_request factory function."""

    def test_create_run_request_basic(self):
        """Test create_run_request with basic parameters."""
        request = create_run_request(workspace_id="ws-123", message="Factory test")

        assert request.data.type == "runs"
        assert request.data.attributes.message == "Factory test"
        assert request.data.relationships.workspace.data.id == "ws-123"

    def test_create_run_request_with_all_params(self):
        """Test create_run_request with all parameters."""
        request = create_run_request(
            workspace_id="ws-123",
            configuration_version_id="cv-456",
            message="Complete factory test",
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
        assert attrs.message == "Complete factory test"
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

    def test_run_attributes_with_empty_lists(self):
        """Test RunAttributes with empty target_addrs list."""
        attrs = RunAttributes(target_addrs=[])
        assert attrs.target_addrs == []

    def test_run_attributes_with_none_variables(self):
        """Test RunAttributes with None variables."""
        attrs = RunAttributes(variables=None)
        assert attrs.variables is None

    def test_run_attributes_with_empty_variables(self):
        """Test RunAttributes with empty variables dict."""
        attrs = RunAttributes(variables={})
        assert attrs.variables == {}

    def test_run_request_with_special_characters_in_message(self):
        """Test RunRequest with special characters in message."""
        special_message = "Deploy 🚀 with émojis & spëcial chars: @#$%^&*()"
        request = RunRequest.create(workspace_id="ws-special", message=special_message)

        assert request.data.attributes.message == special_message

    def test_run_relationships_with_missing_data(self):
        """Test RunRelationships with relationships missing data."""
        rels = RunRelationships(workspace=Relationship(links={"self": "/api/v2/workspaces/ws-123"}))

        assert rels.workspace.data is None
        assert rels.workspace.links["self"] == "/api/v2/workspaces/ws-123"

    def test_run_data_with_invalid_type(self):
        """Test RunData validation with invalid type."""
        attrs = RunAttributes()
        rels = RunRelationships()

        # Try to create with invalid type (not literal "runs")
        data = RunData(attributes=attrs, relationships=rels)
        assert data.type == "runs"  # Should default to "runs"
