# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.run import (
    apply_run,
    cancel_run,
    create_run,
    discard_run,
    get_run,
    run_events,
    task_stages,
)


class TestCreateRun:
    """Test cases for create_run function."""

    @pytest.mark.parametrize(
        "status,expected_result,should_raise",
        [
            (
                201,
                {
                    "id": "run-123",
                    "type": "runs",
                    "attributes": {"status": "pending", "message": "Run created successfully"},
                },
                False,
            ),
            (400, None, True),
            (422, None, True),
            (500, None, True),
        ],
    )
    def test_create_run_status_codes(self, status, expected_result, should_raise):
        """Test create_run with various status codes."""
        mock_client = Mock()

        if should_raise:
            mock_client.post.return_value = {
                "status": status,
                "data": {
                    "errors": [
                        {
                            "detail": f"Error {status}",
                            "status": str(status),
                            "title": "Error",
                        }
                    ]
                },
            }
        else:
            mock_client.post.return_value = {
                "status": status,
                "data": expected_result,
            }

        test_data = {
            "data": {
                "type": "runs",
                "attributes": {
                    "message": "Test run",
                },
                "relationships": {"workspace": {"data": {"type": "workspaces", "id": "ws-123"}}},
            }
        }

        if should_raise:
            with pytest.raises(TerraformError) as exc_info:
                create_run(mock_client, test_data)
            assert str(status) in str(exc_info.value)
        else:
            result = create_run(mock_client, test_data)
            assert result == expected_result

        mock_client.post.assert_called_once_with("/runs", data=test_data)

    @pytest.mark.parametrize(
        "response_data,expected_result",
        [
            ({"status": 201, "data": None}, None),
            ({"status": 201}, None),
            ({"status": 201, "data": {"id": "run-abc", "type": "runs"}}, {"id": "run-abc", "type": "runs"}),
        ],
    )
    def test_create_run_response_variations(self, response_data, expected_result):
        """Test create_run with various response data structures."""
        mock_client = Mock()
        mock_client.post.return_value = response_data

        test_data = {"data": {"type": "runs"}}
        result = create_run(mock_client, test_data)

        assert result == expected_result


class TestApplyRun:
    """Test cases for apply_run function."""

    @pytest.mark.parametrize(
        "run_id,status,expected_result,should_raise",
        [
            (
                "run-123",
                202,
                {
                    "id": "run-123",
                    "type": "runs",
                    "attributes": {"status": "applying", "message": "Run is being applied"},
                },
                False,
            ),
            ("nonexistent-run", 404, None, True),
            ("run-456", 409, None, True),
            ("", 202, {"id": "run-", "type": "runs"}, False),
            ("run-test-123_abc", 202, {"id": "run-test-123_abc", "type": "runs"}, False),
        ],
    )
    def test_apply_run_scenarios(self, run_id, status, expected_result, should_raise):
        """Test apply_run with various scenarios."""
        mock_client = Mock()

        if should_raise:
            mock_client.post.return_value = {
                "status": status,
                "data": {
                    "errors": [
                        {
                            "detail": f"Error {status}",
                            "status": str(status),
                            "title": "Error",
                        }
                    ]
                },
            }
        else:
            mock_client.post.return_value = {
                "status": status,
                "data": expected_result,
            }

        if should_raise:
            with pytest.raises(TerraformError) as exc_info:
                apply_run(mock_client, run_id)
            assert str(status) in str(exc_info.value)
        else:
            result = apply_run(mock_client, run_id)
            if expected_result:
                assert result["id"] == expected_result["id"]

        mock_client.post.assert_called_once_with(f"/runs/{run_id}/actions/apply")


class TestCancelRun:
    """Test cases for cancel_run function."""

    @pytest.mark.parametrize(
        "run_id,status,expected_result,should_raise",
        [
            (
                "run-123",
                202,
                {
                    "id": "run-123",
                    "type": "runs",
                    "attributes": {"status": "canceled", "message": "Run has been canceled"},
                },
                False,
            ),
            ("run-123", 409, None, True),
            ("run-test-123_abc", 202, {"id": "run-test-123_abc", "type": "runs"}, False),
            ("run-invalid", 404, None, True),
            ("run-forbidden", 403, None, True),
        ],
    )
    def test_cancel_run_scenarios(self, run_id, status, expected_result, should_raise):
        """Test cancel_run with various scenarios."""
        mock_client = Mock()

        if should_raise:
            mock_client.post.return_value = {
                "status": status,
                "data": {
                    "errors": [
                        {
                            "detail": f"Error {status}",
                            "status": str(status),
                            "title": "Error",
                        }
                    ]
                },
            }
        else:
            mock_client.post.return_value = {
                "status": status,
                "data": expected_result,
            }

        if should_raise:
            with pytest.raises(TerraformError) as exc_info:
                cancel_run(mock_client, run_id)
            assert str(status) in str(exc_info.value)
        else:
            result = cancel_run(mock_client, run_id)
            assert result["id"] == expected_result["id"]

        mock_client.post.assert_called_once_with(f"/runs/{run_id}/actions/cancel")


class TestDiscardRun:
    """Test cases for discard_run function."""

    @pytest.mark.parametrize(
        "run_id,status,response_data,expected_result,should_raise",
        [
            (
                "run-123",
                202,
                {
                    "id": "run-123",
                    "type": "runs",
                    "attributes": {"status": "discarded", "message": "Run has been discarded"},
                },
                {
                    "id": "run-123",
                    "type": "runs",
                    "attributes": {"status": "discarded", "message": "Run has been discarded"},
                },
                False,
            ),
            ("run-123", 422, None, None, True),
            ("run-123", 202, None, None, False),  # Empty data case
            ("run-invalid", 404, None, None, True),
            ("run-forbidden", 403, None, None, True),
        ],
    )
    def test_discard_run_scenarios(self, run_id, status, response_data, expected_result, should_raise):
        """Test discard_run with various scenarios."""
        mock_client = Mock()

        if should_raise:
            mock_client.post.return_value = {
                "status": status,
                "data": {
                    "errors": [
                        {
                            "detail": f"Error {status}",
                            "status": str(status),
                            "title": "Error",
                        }
                    ]
                },
            }
        else:
            mock_client.post.return_value = {
                "status": status,
                "data": response_data,
            }

        if should_raise:
            with pytest.raises(TerraformError) as exc_info:
                discard_run(mock_client, run_id)
            assert str(status) in str(exc_info.value)
        else:
            result = discard_run(mock_client, run_id)
            assert result == expected_result

        mock_client.post.assert_called_once_with(f"/runs/{run_id}/actions/discard")


class TestGetRun:
    """Test cases for get_run function."""

    @pytest.mark.parametrize(
        "run_id,status,expected_result,should_raise",
        [
            (
                "run-123",
                200,
                {
                    "id": "run-123",
                    "type": "runs",
                    "attributes": {
                        "status": "planned",
                        "message": "Plan completed successfully",
                        "created-at": "2023-01-01T00:00:00.000Z",
                    },
                },
                False,
            ),
            ("run-123", 403, None, True),
            ("run-123", 404, None, True),
            ("run-unicode-123", 200, {"id": "run-unicode-123", "type": "runs"}, False),
            ("run-special-chars_123", 200, {"id": "run-special-chars_123", "type": "runs"}, False),
        ],
    )
    def test_get_run_scenarios(self, run_id, status, expected_result, should_raise):
        """Test get_run with various scenarios."""
        mock_client = Mock()

        if should_raise:
            mock_client.get.return_value = {
                "status": status,
                "data": {
                    "errors": [
                        {
                            "detail": f"Error {status}",
                            "status": str(status),
                            "title": "Error",
                        }
                    ]
                },
            }
        else:
            mock_client.get.return_value = {
                "status": status,
                "data": expected_result,
            }

        if should_raise:
            with pytest.raises(TerraformError) as exc_info:
                get_run(mock_client, run_id)
            assert str(status) in str(exc_info.value)
        else:
            result = get_run(mock_client, run_id)
            assert result["id"] == expected_result["id"]

        mock_client.get.assert_called_once_with(f"/runs/{run_id}")


class TestRunEvents:
    """Test cases for run_events function."""

    @pytest.mark.parametrize(
        "run_id,status,response_data,expected_result,should_raise",
        [
            (
                "run-123",
                200,
                [
                    {
                        "id": "event-1",
                        "type": "run-events",
                        "attributes": {"action": "created", "created-at": "2023-01-01T00:00:00.000Z"},
                    },
                    {
                        "id": "event-2",
                        "type": "run-events",
                        "attributes": {"action": "planning", "created-at": "2023-01-01T00:01:00.000Z"},
                    },
                ],
                2,
                False,
            ),
            ("run-123", 500, None, None, True),
            ("run-123", 200, [], 0, False),  # Empty events list
            ("run-123", 200, None, None, False),  # None data
            ("run-456", 403, None, None, True),
            ("run-789", 404, None, None, True),
        ],
    )
    def test_run_events_scenarios(self, run_id, status, response_data, expected_result, should_raise):
        """Test run_events with various scenarios."""
        mock_client = Mock()

        if should_raise:
            mock_client.get.return_value = {
                "status": status,
                "data": {
                    "errors": [
                        {
                            "detail": f"Error {status}",
                            "status": str(status),
                            "title": "Error",
                        }
                    ]
                },
            }
        else:
            mock_client.get.return_value = {
                "status": status,
                "data": response_data,
            }

        if should_raise:
            with pytest.raises(TerraformError) as exc_info:
                run_events(mock_client, run_id)
            assert str(status) in str(exc_info.value)
        else:
            result = run_events(mock_client, run_id)
            if expected_result is None:
                assert result is None
            elif isinstance(expected_result, int):
                assert len(result) == expected_result
                if expected_result > 0:
                    assert result[0]["id"] == "event-1"
                    if expected_result > 1:
                        assert result[1]["attributes"]["action"] == "planning"

        mock_client.get.assert_called_once_with(f"/runs/{run_id}/run-events")


class TestTaskStages:
    """Test cases for task_stages function."""

    @pytest.mark.parametrize(
        "run_id,status,response_data,expected_result,should_raise",
        [
            (
                "run-123",
                200,
                [
                    {
                        "id": "task-stage-1",
                        "type": "task-stages",
                        "attributes": {
                            "stage": "pre_plan",
                            "status": "passed",
                            "status-timestamps": {
                                "started-at": "2023-01-01T00:00:00.000Z",
                                "finished-at": "2023-01-01T00:01:00.000Z",
                            },
                        },
                    },
                    {
                        "id": "task-stage-2",
                        "type": "task-stages",
                        "attributes": {
                            "stage": "post_plan",
                            "status": "running",
                            "status-timestamps": {"started-at": "2023-01-01T00:02:00.000Z"},
                        },
                    },
                ],
                2,
                False,
            ),
            ("run-123", 401, None, None, True),
            ("run-123", 200, [], 0, False),  # Empty stages list
            ("run-456", 403, None, None, True),
            ("run-789", 404, None, None, True),
        ],
    )
    def test_task_stages_scenarios(self, run_id, status, response_data, expected_result, should_raise):
        """Test task_stages with various scenarios."""
        mock_client = Mock()

        if should_raise:
            mock_client.get.return_value = {
                "status": status,
                "data": {
                    "errors": [
                        {
                            "detail": f"Error {status}",
                            "status": str(status),
                            "title": "Error",
                        }
                    ]
                },
            }
        else:
            mock_client.get.return_value = {
                "status": status,
                "data": response_data,
            }

        if should_raise:
            with pytest.raises(TerraformError) as exc_info:
                task_stages(mock_client, run_id)
            assert str(status) in str(exc_info.value)
        else:
            result = task_stages(mock_client, run_id)
            if isinstance(expected_result, int):
                assert len(result) == expected_result
                if expected_result > 0:
                    assert result[0]["id"] == "task-stage-1"
                    assert result[0]["attributes"]["stage"] == "pre_plan"
                    if expected_result > 1:
                        assert result[1]["attributes"]["status"] == "running"

        mock_client.get.assert_called_once_with(f"/runs/{run_id}/task-stages")

    def test_task_stages_missing_data_key(self):
        """Test task_stages when response has no data key."""
        mock_client = Mock()
        mock_client.get.return_value = {
            "status": 200,
        }

        run_id = "run-123"
        result = task_stages(mock_client, run_id)

        assert result is None


class TestRunsModuleEdgeCases:
    """Test edge cases and error scenarios for runs module."""

    @pytest.mark.parametrize(
        "function_name,args",
        [
            ("create_run", [{"data": {"type": "runs"}}]),
            ("apply_run", ["run-123"]),
            ("cancel_run", ["run-123"]),
            ("discard_run", ["run-123"]),
            ("get_run", ["run-123"]),
            ("run_events", ["run-123"]),
            ("task_stages", ["run-123"]),
        ],
    )
    def test_all_functions_handle_client_exception(self, function_name, args):
        """Test all functions handle client exceptions gracefully."""
        mock_client = Mock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client.get.side_effect = Exception("Network error")

        # Get the function by name
        func = globals()[function_name]

        # Test that exceptions from client are propagated
        with pytest.raises(Exception, match="Network error"):
            func(mock_client, *args)

    def test_terraform_error_with_complex_response(self):
        """Test TerraformError with complex error response."""
        mock_client = Mock()
        complex_error_response = {
            "status": 422,
            "data": {
                "errors": [
                    {
                        "detail": "Workspace is locked",
                        "status": "422",
                        "title": "Unprocessable Entity",
                        "source": {"pointer": "/data/attributes/workspace"},
                    }
                ],
                "meta": {
                    "request-id": "req-123",
                    "timestamp": "2023-01-01T00:00:00.000Z",
                },
            },
        }
        mock_client.post.return_value = complex_error_response

        run_id = "run-123"

        with pytest.raises(TerraformError) as exc_info:
            apply_run(mock_client, run_id)

        # Verify the entire response is included in the error
        error_str = str(exc_info.value)
        assert "422" in error_str
        assert "Workspace is locked" in error_str

    @pytest.mark.parametrize(
        "function_name,args,method_type",
        [
            ("create_run", [None], "post"),
            ("apply_run", [None], "post"),
            ("cancel_run", [None], "post"),
            ("discard_run", [None], "post"),
            ("get_run", [None], "get"),
            ("run_events", [None], "get"),
            ("task_stages", [None], "get"),
        ],
    )
    def test_functions_with_none_values(self, function_name, args, method_type):
        """Test functions handle None values appropriately."""
        mock_client = Mock()

        # Set up mock to return error status
        if method_type == "post":
            mock_client.post.return_value = {"status": 400}
        else:
            mock_client.get.return_value = {"status": 400}

        # Get the function by name
        func = globals()[function_name]

        with pytest.raises(TerraformError):
            func(mock_client, *args)

    @pytest.mark.parametrize(
        "function_name,args,method_type,wrong_status,expected_status",
        [
            ("create_run", [{"data": {"type": "runs"}}], "post", 200, 201),
            ("apply_run", ["run-123"], "post", 200, 202),
            ("cancel_run", ["run-123"], "post", 200, 202),
            ("discard_run", ["run-123"], "post", 200, 202),
            ("get_run", ["run-123"], "get", 201, 200),
            ("run_events", ["run-123"], "get", 201, 200),
            ("task_stages", ["run-123"], "get", 201, 200),
        ],
    )
    def test_response_status_edge_cases(self, function_name, args, method_type, wrong_status, expected_status):
        """Test edge cases for status code validation."""
        mock_client = Mock()

        response = {
            "status": wrong_status,
            "data": {"id": "run-123", "type": "runs"},
        }

        if method_type == "post":
            mock_client.post.return_value = response
        else:
            mock_client.get.return_value = response

        # Get the function by name
        func = globals()[function_name]

        with pytest.raises(TerraformError):
            func(mock_client, *args)


class TestRunsModuleIntegration:
    """Integration-style tests for runs module functions."""

    def test_complete_run_workflow(self):
        """Test a complete workflow using multiple runs functions."""
        mock_client = Mock()

        # Mock responses for a complete workflow
        create_response = {
            "status": 201,
            "data": {
                "id": "run-workflow-123",
                "type": "runs",
                "attributes": {"status": "pending"},
            },
        }

        get_response = {
            "status": 200,
            "data": {
                "id": "run-workflow-123",
                "type": "runs",
                "attributes": {"status": "planned"},
            },
        }

        apply_response = {
            "status": 202,
            "data": {
                "id": "run-workflow-123",
                "type": "runs",
                "attributes": {"status": "applying"},
            },
        }

        events_response = {
            "status": 200,
            "data": [
                {
                    "id": "event-1",
                    "type": "run-events",
                    "attributes": {"action": "created"},
                }
            ],
        }

        tasks_response = {
            "status": 200,
            "data": [
                {
                    "id": "task-1",
                    "type": "task-stages",
                    "attributes": {"stage": "pre_plan", "status": "passed"},
                }
            ],
        }

        # Configure mock responses in order
        mock_client.post.side_effect = [create_response, apply_response]
        mock_client.get.side_effect = [get_response, events_response, tasks_response]

        # Execute workflow
        test_data = {"data": {"type": "runs", "attributes": {"message": "Test"}}}

        # 1. Create run
        created_run = create_run(mock_client, test_data)
        assert created_run["id"] == "run-workflow-123"
        assert created_run["attributes"]["status"] == "pending"

        # 2. Get run details
        run_details = get_run(mock_client, "run-workflow-123")
        assert run_details["attributes"]["status"] == "planned"

        # 3. Apply run
        applied_run = apply_run(mock_client, "run-workflow-123")
        assert applied_run["attributes"]["status"] == "applying"

        # 4. Get run events
        events = run_events(mock_client, "run-workflow-123")
        assert len(events) == 1
        assert events[0]["attributes"]["action"] == "created"

        # 5. Get task stages
        tasks = task_stages(mock_client, "run-workflow-123")
        assert len(tasks) == 1
        assert tasks[0]["attributes"]["stage"] == "pre_plan"

        # Verify all expected calls were made
        assert mock_client.post.call_count == 2
        assert mock_client.get.call_count == 3

    @pytest.mark.parametrize(
        "function_name,args,method_type",
        [
            ("create_run", [{"data": {"type": "runs"}}], "post"),
            ("apply_run", ["run-123"], "post"),
            ("cancel_run", ["run-123"], "post"),
            ("discard_run", ["run-123"], "post"),
            ("get_run", ["run-123"], "get"),
            ("run_events", ["run-123"], "get"),
            ("task_stages", ["run-123"], "get"),
        ],
    )
    def test_error_propagation_consistency(self, function_name, args, method_type):
        """Test that all functions consistently handle and propagate errors."""
        mock_client = Mock()
        error_response = {
            "status": 500,
            "data": {"errors": [{"detail": "Server error"}]},
        }

        # Configure mock for this function
        if method_type == "post":
            mock_client.post.return_value = error_response
        else:
            mock_client.get.return_value = error_response

        # Get the function by name
        func = globals()[function_name]

        # Test that TerraformError is raised consistently
        with pytest.raises(TerraformError) as exc_info:
            func(mock_client, *args)

        assert "500" in str(exc_info.value)
