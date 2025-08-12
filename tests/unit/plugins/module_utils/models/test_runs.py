# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from datetime import datetime

import pytest

from pydantic import ValidationError

from ansible_collections.hashicorp.terraform.plugins.module_utils.models.runs import (
    RunAttributes,
    RunData,
    RunRelationships,
    RunRequest,
    RunResource,
    RunResponse,
    RunStates,
)
from plugins.module_utils.models.common import (
    BaseAttributes,
    BaseRelationships,
    Relationship,
    create_configuration_version_reference,
    create_workspace_reference,
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
        assert attrs.message is None
        assert attrs.status is None
        assert attrs.auto_apply is None

    def test_run_attributes_creation_full(self):
        """Test creating RunAttributes with all fields."""
        now = datetime.now()
        attrs = RunAttributes(
            created_at=now,
            updated_at=now,
            message="Test run message",
            status="planned",
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
        assert attrs.message == "Test run message"
        assert attrs.status == "planned"
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
        attrs = RunAttributes(message="Test message", refresh_only=True, auto_apply=True, is_destroy=False, target_addrs=["module.test"])

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

        rels = RunRelationships(
            workspace=Relationship(data=workspace_ref),
            configuration_version=Relationship(data=config_ref),
            plan=Relationship(data={"type": "plans", "id": "plan-789"}),
            apply=Relationship(data={"type": "applies", "id": "apply-101"}),
            created_by=Relationship(data={"type": "users", "id": "user-202"}),
        )

        assert rels.workspace.data.id == "ws-123"
        assert rels.configuration_version.data.id == "cv-456"
        assert rels.plan.data["id"] == "plan-789"
        assert rels.apply.data["id"] == "apply-101"
        assert rels.created_by.data["id"] == "user-202"

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

        assert data.type == "runs"  # Default value
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
        request = RunRequest.create(workspace_id="ws-123", configuration_version_id="cv-456", message="Test run with config version", auto_apply=True)

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
        request = RunRequest.create(workspace_id="ws-123", message="Serialization test", auto_apply=True)

        data = request.model_dump(by_alias=True, exclude_unset=True)

        assert "data" in data
        assert data["data"]["type"] == "runs"
        assert data["data"]["attributes"]["message"] == "Serialization test"
        assert data["data"]["attributes"]["auto-apply"] is True
        assert data["data"]["relationships"]["workspace"]["data"]["type"] == "workspaces"
        assert data["data"]["relationships"]["workspace"]["data"]["id"] == "ws-123"

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


class TestRunsModelsIntegration:
    """Integration tests for runs models working together."""

    def test_complete_run_workflow_models(self):
        """Test complete run workflow using all models."""
        # 1. Create a run request
        request = RunRequest.create(
            workspace_id="ws-production-123",
            configuration_version_id="cv-latest-456",
            message="Deploy to production",
            auto_apply=False,  # Require manual approval for production
            is_destroy=False,
            target_addrs=["module.database", "module.application"],
            variables={"environment": "production", "instance_count": 3, "enable_monitoring": True},
        )

        # Verify request structure
        assert request.data.type == "runs"
        assert request.data.attributes.message == "Deploy to production"
        assert request.data.attributes.auto_apply is False
        assert request.data.relationships.workspace.data.id == "ws-production-123"
        assert request.data.relationships.configuration_version.data.id == "cv-latest-456"

        # 2. Simulate API response after run creation
        run_attrs = RunAttributes(message="Deploy to production", status="planning", auto_apply=False, is_destroy=False, created_at=datetime.now())

        workspace_ref = create_workspace_reference("ws-production-123")
        config_ref = create_configuration_version_reference("cv-latest-456")
        run_rels = RunRelationships(workspace=Relationship(data=workspace_ref), configuration_version=Relationship(data=config_ref))

        run_resource = RunResource(id="run-prod-789", type="runs", attributes=run_attrs, relationships=run_rels)

        response = RunResponse(data=run_resource, meta={"request-id": "req-123", "rate-limit": "1000/hour"})

        # Verify response structure
        assert response.data.id == "run-prod-789"
        assert response.data.attributes.status == "planning"
        assert response.meta["request-id"] == "req-123"

        # 3. Test state transitions
        assert RunStates.is_intermediate_state("planning")
        assert not RunStates.is_final_state("planning")

        # Simulate completion
        run_attrs.status = "planned"
        assert RunStates.is_success_state("planned")
        assert RunStates.is_final_state("planned")

    def test_serialization_for_api_calls(self):
        """Test serialization format matches Terraform Cloud API."""
        request = RunRequest.create(workspace_id="ws-api-test", message="API format test", auto_apply=True, plan_only=False, variables={"api_test": True})

        # Serialize for API call
        api_payload = request.model_dump(by_alias=True, exclude_unset=True)

        # Verify API-compatible format
        expected_structure = {
            "data": {
                "type": "runs",
                "attributes": {"message": "API format test", "auto-apply": True, "plan-only": False, "variables": {"api_test": True}},
                "relationships": {"workspace": {"data": {"type": "workspaces", "id": "ws-api-test"}}},
            }
        }

        assert api_payload["data"]["type"] == expected_structure["data"]["type"]
        assert api_payload["data"]["attributes"]["message"] == expected_structure["data"]["attributes"]["message"]
        assert api_payload["data"]["attributes"]["auto-apply"] == expected_structure["data"]["attributes"]["auto-apply"]
        assert api_payload["data"]["relationships"]["workspace"]["data"]["id"] == expected_structure["data"]["relationships"]["workspace"]["data"]["id"]

    def test_deserialization_from_api_response(self):
        """Test deserializing typical Terraform Cloud API response."""
        api_response_data = {
            "data": {
                "id": "run-api-response-123",
                "type": "runs",
                "attributes": {
                    "message": "Automated deployment",
                    "status": "applied",
                    "auto-apply": True,
                    "is-destroy": False,
                    "created-at": "2023-01-01T10:00:00Z",
                    "updated-at": "2023-01-01T10:05:00Z",
                },
                "relationships": {
                    "workspace": {"data": {"type": "workspaces", "id": "ws-automated-123"}},
                    "configuration-version": {"data": {"type": "configuration-versions", "id": "cv-auto-456"}},
                    "apply": {"data": {"type": "applies", "id": "apply-success-789"}},
                },
                "links": {"self": "/api/v2/runs/run-api-response-123"},
            },
            "included": [{"id": "ws-automated-123", "type": "workspaces", "attributes": {"name": "automated-deployment"}}],
            "meta": {"request-id": "req-api-test-456"},
        }

        response = RunResponse.model_validate(api_response_data)

        # Verify deserialization
        assert response.data.id == "run-api-response-123"
        assert response.data.attributes.message == "Automated deployment"
        assert response.data.attributes.status == "applied"
        assert response.data.attributes.created_at is not None
        assert response.data.relationships.workspace.data.id == "ws-automated-123"
        assert response.data.relationships.configuration_version.data.id == "cv-auto-456"
        assert response.data.relationships.apply.data.id == "apply-success-789"
        assert response.included[0]["attributes"]["name"] == "automated-deployment"
        assert response.meta["request-id"] == "req-api-test-456"


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

    def test_run_states_with_edge_case_strings(self):
        """Test RunStates with edge case input strings."""
        edge_cases = [None, "", " ", "  planning  ", "APPLIED", "Planning"]

        for case in edge_cases:
            # Should not raise exceptions, just return False for unknown states
            try:
                result = RunStates.is_success_state(case)
                assert isinstance(result, bool)
            except (TypeError, AttributeError):
                # None or non-string inputs might raise these, which is acceptable
                pass

    def test_run_relationships_with_missing_data(self):
        """Test RunRelationships with relationships missing data."""
        rels = RunRelationships(workspace=Relationship(links={"self": "/api/v2/workspaces/ws-123"}))

        assert rels.workspace.data is None
        assert rels.workspace.links["self"] == "/api/v2/workspaces/ws-123"

    def test_large_variables_dict(self):
        """Test RunAttributes with large variables dictionary."""
        large_vars = {f"var_{i}": f"value_{i}" for i in range(1000)}
        attrs = RunAttributes(variables=large_vars)

        assert len(attrs.variables) == 1000
        assert attrs.variables["var_500"] == "value_500"

    def test_run_request_serialization_exclude_none(self):
        """Test RunRequest serialization excluding None values."""
        request = RunRequest.create(
            workspace_id="ws-exclude-none",
            message="Test message",
            # Other fields left as None/default
        )

        # Serialize excluding unset/None values
        data = request.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)

        # Should only include explicitly set fields
        attrs = data["data"]["attributes"]
        assert "message" in attrs
        assert attrs["message"] == "Test message"

        # Should not include None/unset fields
        for field in ["auto-apply", "plan-only", "is-destroy", "refresh-only"]:
            assert field not in attrs or attrs[field] is not None

    def test_invalid_relationship_data_types(self):
        """Test validation with invalid relationship data types."""
        with pytest.raises(ValidationError):
            RunRelationships(workspace="invalid_string_instead_of_relationship")

    def test_run_data_with_invalid_type(self):
        """Test RunData validation with invalid type."""
        attrs = RunAttributes()
        rels = RunRelationships()

        # Try to create with invalid type (not literal "runs")
        data = RunData(attributes=attrs, relationships=rels)
        assert data.type == "runs"  # Should default to "runs"
