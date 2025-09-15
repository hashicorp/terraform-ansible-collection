# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.plan import (
    get_plan_data,
)


class TestPlanFunctions:
    """Tests for Terraform plan helper functions."""

    @pytest.fixture
    def mock_tf_client(self):
        """Provide a mock TerraformClient for tests."""
        return Mock()

    @pytest.fixture
    def plan_id(self):
        """Provide a sample plan ID."""
        return "plan-123abc456def789"

    @pytest.fixture
    def run_id(self):
        """Provide a sample run ID."""
        return "run-456def789abc123"

    @pytest.mark.parametrize(
        "include_json_output,use_plan_id,resource_id,expected_endpoint_suffix",
        [
            (False, True, "plan-123", ""),
            (False, False, "run-456", "/plan"),
            (True, True, "plan-123", "/json-output"),
            (True, False, "run-456", "/plan/json-output"),
        ],
    )
    def test_get_plan_data_success(self, mock_tf_client, include_json_output, use_plan_id, resource_id, expected_endpoint_suffix):
        """Test successful retrieval for both metadata and JSON output using get_plan_data."""
        expected_response = {
            "data": (
                {
                    "id": "plan-789" if not use_plan_id else resource_id,
                    "type": "plans",
                    "attributes": {"status": "finished", "has_changes": True},
                }
                if not include_json_output
                else {
                    "format_version": "1.2",
                    "terraform_version": "1.5.0",
                    "resource_changes": [{"address": "aws_instance.test", "change": {"actions": ["create"]}}],
                    "applyable": True,
                    "complete": True,
                    "errored": False,
                }
            ),
            "status": 200,
        }

        mock_tf_client.get.return_value = expected_response

        result = get_plan_data(mock_tf_client, resource_id, use_plan_id=use_plan_id, include_json_output=include_json_output)

        assert result == expected_response
        if use_plan_id:
            expected_endpoint = f"/plans/{resource_id}{expected_endpoint_suffix}"
        else:
            expected_endpoint = f"/runs/{resource_id}{expected_endpoint_suffix}"
        mock_tf_client.get.assert_called_once_with(expected_endpoint)

    @pytest.mark.parametrize(
        "use_plan_id,include_json_output",
        [
            (True, False),
            (False, False),
            (True, True),
            (False, True),
        ],
    )
    def test_get_plan_data_not_found_404(self, mock_tf_client, use_plan_id, include_json_output):
        """Test get_plan_data returns empty dict on 404."""
        mock_tf_client.get.return_value = {"status": 404}

        result = get_plan_data(mock_tf_client, "resource-123", use_plan_id=use_plan_id, include_json_output=include_json_output)

        assert result == {}

    @pytest.mark.parametrize(
        "status_code,include_json_output",
        [
            (400, False),
            (500, True),
            (401, False),
            (503, True),
        ],
    )
    def test_get_plan_data_failure_statuses(self, mock_tf_client, plan_id, status_code, include_json_output):
        """Test get_plan_data raises TerraformError on non-success status codes."""
        response = {"status": status_code}
        mock_tf_client.get.return_value = response

        with pytest.raises(TerraformError) as exc_info:
            get_plan_data(mock_tf_client, plan_id, use_plan_id=True, include_json_output=include_json_output)

        assert exc_info.value.args[0] == response

    def test_get_plan_data_metadata_complex_structure(self, mock_tf_client, plan_id, run_id):
        """Test get_plan_data for metadata with complex nested data structure."""
        expected_response = {
            "data": {
                "id": plan_id,
                "type": "plans",
                "attributes": {
                    "status": "finished",
                    "has_changes": True,
                    "resource_additions": 3,
                    "resource_changes": 1,
                    "resource_destructions": 2,
                    "status_timestamps": {
                        "queued_at": "2025-01-15T10:25:00Z",
                        "planned_at": "2025-01-15T10:30:00Z",
                    },
                    "permissions": {"can_update": True, "can_destroy": False},
                },
                "relationships": {
                    "workspace": {"data": {"id": "ws-123abc", "type": "workspaces"}},
                    "run": {"data": {"id": run_id, "type": "runs"}},
                },
            },
            "status": 200,
        }
        mock_tf_client.get.return_value = expected_response

        result = get_plan_data(mock_tf_client, plan_id, use_plan_id=True, include_json_output=False)

        assert result == expected_response
        assert "status_timestamps" in result["data"]["attributes"]
        assert "permissions" in result["data"]["attributes"]
        assert "relationships" in result["data"]

    def test_get_plan_data_json_output_complex_changes(self, mock_tf_client, plan_id):
        """Test get_plan_data for JSON output with complex resource changes."""
        expected_response = {
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [
                    {
                        "address": "aws_instance.web[0]",
                        "mode": "managed",
                        "type": "aws_instance",
                        "name": "web",
                        "index": 0,
                        "change": {
                            "actions": ["create"],
                            "before": None,
                            "after": {"ami": "ami-12345", "instance_type": "t3.micro"},
                            "after_unknown": {"id": True, "public_ip": True},
                        },
                    },
                    {
                        "address": "aws_instance.old",
                        "change": {"actions": ["delete"], "before": {"ami": "ami-old"}, "after": None},
                    },
                ],
                "planned_values": {
                    "root_module": {
                        "resources": [
                            {"address": "aws_instance.web[0]", "values": {"ami": "ami-12345"}},
                        ],
                    },
                },
                "applyable": True,
                "complete": True,
                "errored": False,
            },
            "status": 200,
        }
        mock_tf_client.get.return_value = expected_response

        result = get_plan_data(mock_tf_client, plan_id, use_plan_id=True, include_json_output=True)

        assert result == expected_response
        assert len(result["data"]["resource_changes"]) > 1
        assert "after_unknown" in result["data"]["resource_changes"][0]["change"]
        assert "planned_values" in result["data"]

    @pytest.mark.parametrize(
        "plan_status,applyable,complete,errored",
        [
            ("finished", True, True, False),
            ("planning", False, False, False),
            ("errored", False, False, True),
        ],
    )
    def test_get_plan_data_json_output_various_states(self, mock_tf_client, plan_id, plan_status, applyable, complete, errored):
        """Test get_plan_data JSON output with various plan states."""
        expected_response = {
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [],
                "applyable": applyable,
                "complete": complete,
                "errored": errored,
            },
            "status": 200,
        }
        mock_tf_client.get.return_value = expected_response

        result = get_plan_data(mock_tf_client, plan_id, use_plan_id=True, include_json_output=True)

        assert result["data"]["applyable"] == applyable
        assert result["data"]["complete"] == complete
        assert result["data"]["errored"] == errored

    @pytest.mark.parametrize(
        "exception_type,include_json_output",
        [
            (Exception, False),
            (Exception, True),
            (ConnectionError, False),
            (TimeoutError, True),
        ],
    )
    def test_get_plan_data_client_exceptions(self, mock_tf_client, exception_type, include_json_output):
        """Test get_plan_data handles client exceptions."""
        mock_tf_client.get.side_effect = exception_type("Network error")

        with pytest.raises(exception_type, match="Network error"):
            get_plan_data(mock_tf_client, "plan-123", use_plan_id=True, include_json_output=include_json_output)

    def test_get_plan_data_consistency(self, mock_tf_client):
        """Test that metadata and JSON output are consistent for the same plan."""
        plan_id = "plan-consistent123"

        def mock_get_response(endpoint):
            if endpoint.endswith("/json-output"):
                return {
                    "data": {
                        "resource_changes": [
                            {"address": "aws_instance.new1", "change": {"actions": ["create"]}},
                            {"address": "aws_instance.existing", "change": {"actions": ["update"]}},
                        ],
                        "applyable": True,
                    },
                    "status": 200,
                }
            else:
                return {
                    "data": {
                        "attributes": {
                            "has_changes": True,
                            "resource_additions": 1,
                            "resource_changes": 1,
                        },
                    },
                    "status": 200,
                }

        mock_tf_client.get.side_effect = mock_get_response

        metadata = get_plan_data(mock_tf_client, plan_id, use_plan_id=True, include_json_output=False)
        json_output = get_plan_data(mock_tf_client, plan_id, use_plan_id=True, include_json_output=True)

        assert metadata["data"]["attributes"]["has_changes"] == json_output["data"]["applyable"]
        creates = len([rc for rc in json_output["data"]["resource_changes"] if rc["change"]["actions"] == ["create"]])
        updates = len([rc for rc in json_output["data"]["resource_changes"] if rc["change"]["actions"] == ["update"]])
        assert metadata["data"]["attributes"]["resource_additions"] == creates
        assert metadata["data"]["attributes"]["resource_changes"] == updates

    def test_get_plan_data_default_parameter(self, mock_tf_client):
        """Test that get_plan_data defaults to metadata when include_json_output is not specified."""
        plan_id = "plan-default-test"
        metadata_response = {
            "data": {"id": plan_id, "attributes": {"status": "finished"}},
            "status": 200,
        }
        mock_tf_client.get.return_value = metadata_response

        result = get_plan_data(mock_tf_client, plan_id, use_plan_id=True)
        assert result == metadata_response
        mock_tf_client.get.assert_called_with(f"/plans/{plan_id}")

        mock_tf_client.reset_mock()
        mock_tf_client.get.return_value = metadata_response

        result_explicit = get_plan_data(mock_tf_client, plan_id, use_plan_id=True, include_json_output=False)
        assert result_explicit == metadata_response
        mock_tf_client.get.assert_called_with(f"/plans/{plan_id}")

    def test_get_plan_data_endpoint_construction(self, mock_tf_client):
        """Test that get_plan_data constructs correct endpoints for all scenarios."""
        plan_id = "plan-endpoint-test"
        run_id = "run-endpoint-test"

        test_cases = [
            (True, False, plan_id, f"/plans/{plan_id}"),
            (True, True, plan_id, f"/plans/{plan_id}/json-output"),
            (False, False, run_id, f"/runs/{run_id}/plan"),
            (False, True, run_id, f"/runs/{run_id}/plan/json-output"),
        ]

        mock_tf_client.get.return_value = {"status": 200, "data": {}}

        for use_plan_id, include_json_output, identifier, expected_endpoint in test_cases:
            mock_tf_client.reset_mock()
            get_plan_data(mock_tf_client, identifier, use_plan_id, include_json_output)
            mock_tf_client.get.assert_called_once_with(expected_endpoint)

    def test_get_plan_data_response_handling(self, mock_tf_client):
        """Test that get_plan_data properly handles different response scenarios."""
        plan_id = "plan-response-test"

        success_response = {"status": 200, "data": {"id": plan_id}}
        mock_tf_client.get.return_value = success_response
        result = get_plan_data(mock_tf_client, plan_id, use_plan_id=True)
        assert result == success_response

        mock_tf_client.get.return_value = {"status": 404}
        result = get_plan_data(mock_tf_client, plan_id, use_plan_id=True)
        assert result == {}

        error_response = {"status": 500, "error": "Internal server error"}
        mock_tf_client.get.return_value = error_response
        with pytest.raises(TerraformError) as exc_info:
            get_plan_data(mock_tf_client, plan_id, use_plan_id=True)
        assert exc_info.value.args[0] == error_response


if __name__ == "__main__":
    pytest.main([__file__])
