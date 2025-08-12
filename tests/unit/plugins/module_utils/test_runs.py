# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import sys

from unittest.mock import Mock

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from plugins.module_utils.exceptions import TerraformError
from plugins.module_utils.runs import (
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

    def test_create_run_success(self):
        """Test create_run with successful response."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 201,
            "data": {
                "id": "run-123",
                "type": "runs",
                "attributes": {
                    "status": "pending",
                    "message": "Run created successfully",
                },
            },
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

        result = create_run(mock_client, test_data)

        mock_client.post.assert_called_once_with("/runs", data=test_data)
        assert result["id"] == "run-123"
        assert result["type"] == "runs"
        assert result["attributes"]["status"] == "pending"

    def test_create_run_error_status(self):
        """Test create_run raises TerraformError on non-201 status."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 400,
            "data": {
                "errors": [
                    {
                        "detail": "Invalid request data",
                        "status": "400",
                        "title": "Bad Request",
                    }
                ]
            },
        }

        test_data = {"data": {"type": "runs", "attributes": {"message": "Test run"}}}

        with pytest.raises(TerraformError) as exc_info:
            create_run(mock_client, test_data)

        mock_client.post.assert_called_once_with("/runs", data=test_data)
        assert "400" in str(exc_info.value)

    def test_create_run_empty_data_response(self):
        """Test create_run with empty data in response."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 201,
            "data": None,
        }

        test_data = {"data": {"type": "runs"}}

        result = create_run(mock_client, test_data)

        assert result is None

    def test_create_run_missing_data_key(self):
        """Test create_run when response has no data key."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 201,
        }

        test_data = {"data": {"type": "runs"}}

        result = create_run(mock_client, test_data)

        assert result is None


class TestApplyRun:
    """Test cases for apply_run function."""

    def test_apply_run_success(self):
        """Test apply_run with successful response."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 202,
            "data": {
                "id": "run-123",
                "type": "runs",
                "attributes": {
                    "status": "applying",
                    "message": "Run is being applied",
                },
            },
        }

        run_id = "run-123"
        result = apply_run(mock_client, run_id)

        mock_client.post.assert_called_once_with("/runs/run-123/actions/apply")
        assert result["id"] == "run-123"
        assert result["attributes"]["status"] == "applying"

    def test_apply_run_error_status(self):
        """Test apply_run raises TerraformError on non-202 status."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 404,
            "data": {
                "errors": [
                    {
                        "detail": "Run not found",
                        "status": "404",
                        "title": "Not Found",
                    }
                ]
            },
        }

        run_id = "nonexistent-run"

        with pytest.raises(TerraformError) as exc_info:
            apply_run(mock_client, run_id)

        mock_client.post.assert_called_once_with("/runs/nonexistent-run/actions/apply")
        assert "404" in str(exc_info.value)

    def test_apply_run_empty_run_id(self):
        """Test apply_run with empty run_id."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 202,
            "data": {"id": "run-", "type": "runs"},
        }

        run_id = ""
        result = apply_run(mock_client, run_id)

        mock_client.post.assert_called_once_with("/runs//actions/apply")
        assert result["id"] == "run-"


class TestCancelRun:
    """Test cases for cancel_run function."""

    def test_cancel_run_success(self):
        """Test cancel_run with successful response."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 202,
            "data": {
                "id": "run-123",
                "type": "runs",
                "attributes": {
                    "status": "canceled",
                    "message": "Run has been canceled",
                },
            },
        }

        run_id = "run-123"
        result = cancel_run(mock_client, run_id)

        mock_client.post.assert_called_once_with("/runs/run-123/actions/cancel")
        assert result["id"] == "run-123"
        assert result["attributes"]["status"] == "canceled"

    def test_cancel_run_error_status(self):
        """Test cancel_run raises TerraformError on non-202 status."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 409,
            "data": {
                "errors": [
                    {
                        "detail": "Run cannot be canceled in current state",
                        "status": "409",
                        "title": "Conflict",
                    }
                ]
            },
        }

        run_id = "run-123"

        with pytest.raises(TerraformError) as exc_info:
            cancel_run(mock_client, run_id)

        mock_client.post.assert_called_once_with("/runs/run-123/actions/cancel")
        assert "409" in str(exc_info.value)

    def test_cancel_run_special_characters_in_id(self):
        """Test cancel_run with special characters in run_id."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 202,
            "data": {"id": "run-test-123_abc", "type": "runs"},
        }

        run_id = "run-test-123_abc"
        result = cancel_run(mock_client, run_id)

        mock_client.post.assert_called_once_with("/runs/run-test-123_abc/actions/cancel")
        assert result["id"] == "run-test-123_abc"


class TestDiscardRun:
    """Test cases for discard_run function."""

    def test_discard_run_success(self):
        """Test discard_run with successful response."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 202,
            "data": {
                "id": "run-123",
                "type": "runs",
                "attributes": {
                    "status": "discarded",
                    "message": "Run has been discarded",
                },
            },
        }

        run_id = "run-123"
        result = discard_run(mock_client, run_id)

        mock_client.post.assert_called_once_with("/runs/run-123/actions/discard")
        assert result["id"] == "run-123"
        assert result["attributes"]["status"] == "discarded"

    def test_discard_run_error_status(self):
        """Test discard_run raises TerraformError on non-202 status."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 422,
            "data": {
                "errors": [
                    {
                        "detail": "Run cannot be discarded",
                        "status": "422",
                        "title": "Unprocessable Entity",
                    }
                ]
            },
        }

        run_id = "run-123"

        with pytest.raises(TerraformError) as exc_info:
            discard_run(mock_client, run_id)

        mock_client.post.assert_called_once_with("/runs/run-123/actions/discard")
        assert "422" in str(exc_info.value)

    def test_discard_run_returns_none_when_data_empty(self):
        """Test discard_run returns None when data is empty."""
        mock_client = Mock()
        mock_client.post.return_value = {
            "status": 202,
            "data": None,
        }

        run_id = "run-123"
        result = discard_run(mock_client, run_id)

        assert result is None


class TestGetRun:
    """Test cases for get_run function."""

    def test_get_run_success(self):
        """Test get_run with successful response."""
        mock_client = Mock()
        mock_client.get.return_value = {
            "status": 200,
            "data": {
                "id": "run-123",
                "type": "runs",
                "attributes": {
                    "status": "planned",
                    "message": "Plan completed successfully",
                    "created-at": "2023-01-01T00:00:00.000Z",
                },
            },
        }

        run_id = "run-123"
        result = get_run(mock_client, run_id)

        mock_client.get.assert_called_once_with("/runs/run-123")
        assert result["id"] == "run-123"
        assert result["type"] == "runs"
        assert result["attributes"]["status"] == "planned"

    def test_get_run_error_status(self):
        """Test get_run raises TerraformError on non-200 status."""
        mock_client = Mock()
        mock_client.get.return_value = {
            "status": 403,
            "data": {
                "errors": [
                    {
                        "detail": "Insufficient permissions",
                        "status": "403",
                        "title": "Forbidden",
                    }
                ]
            },
        }

        run_id = "run-123"

        with pytest.raises(TerraformError) as exc_info:
            get_run(mock_client, run_id)

        mock_client.get.assert_called_once_with("/runs/run-123")
        assert "403" in str(exc_info.value)

    def test_get_run_with_unicode_id(self):
        """Test get_run with Unicode characters in run_id."""
        mock_client = Mock()
        mock_client.get.return_value = {
            "status": 200,
            "data": {
                "id": "run-测试-123",
                "type": "runs",
            },
        }

        run_id = "run-测试-123"
        result = get_run(mock_client, run_id)

        mock_client.get.assert_called_once_with("/runs/run-测试-123")
        assert result["id"] == "run-测试-123"


class TestRunEvents:
    """Test cases for run_events function."""

    def test_run_events_success(self):
        """Test run_events with successful response."""
        mock_client = Mock()
        mock_client.get.return_value = {
            "status": 200,
            "data": [
                {
                    "id": "event-1",
                    "type": "run-events",
                    "attributes": {
                        "action": "created",
                        "created-at": "2023-01-01T00:00:00.000Z",
                    },
                },
                {
                    "id": "event-2",
                    "type": "run-events",
                    "attributes": {
                        "action": "planning",
                        "created-at": "2023-01-01T00:01:00.000Z",
                    },
                },
            ],
        }

        run_id = "run-123"
        result = run_events(mock_client, run_id)

        mock_client.get.assert_called_once_with("/runs/run-123/run-events")
        assert len(result) == 2
        assert result[0]["id"] == "event-1"
        assert result[1]["attributes"]["action"] == "planning"

    def test_run_events_error_status(self):
        """Test run_events raises TerraformError on non-200 status."""
        mock_client = Mock()
        mock_client.get.return_value = {
            "status": 500,
            "data": {
                "errors": [
                    {
                        "detail": "Internal server error",
                        "status": "500",
                        "title": "Internal Server Error",
                    }
                ]
            },
        }

        run_id = "run-123"

        with pytest.raises(TerraformError) as exc_info:
            run_events(mock_client, run_id)

        mock_client.get.assert_called_once_with("/runs/run-123/run-events")
        assert "500" in str(exc_info.value)

    def test_run_events_empty_events_list(self):
        """Test run_events with empty events list."""
        mock_client = Mock()
        mock_client.get.return_value = {
            "status": 200,
            "data": [],
        }

        run_id = "run-123"
        result = run_events(mock_client, run_id)

        assert result == []

    def test_run_events_none_data(self):
        """Test run_events with None data."""
        mock_client = Mock()
        mock_client.get.return_value = {
            "status": 200,
            "data": None,
        }

        run_id = "run-123"
        result = run_events(mock_client, run_id)

        assert result is None


class TestTaskStages:
    """Test cases for task_stages function."""

    def test_task_stages_success(self):
        """Test task_stages with successful response."""
        mock_client = Mock()
        mock_client.get.return_value = {
            "status": 200,
            "data": [
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
                        "status-timestamps": {
                            "started-at": "2023-01-01T00:02:00.000Z",
                        },
                    },
                },
            ],
        }

        run_id = "run-123"
        result = task_stages(mock_client, run_id)

        mock_client.get.assert_called_once_with("/runs/run-123/task-stages")
        assert len(result) == 2
        assert result[0]["id"] == "task-stage-1"
        assert result[0]["attributes"]["stage"] == "pre_plan"
        assert result[1]["attributes"]["status"] == "running"

    def test_task_stages_error_status(self):
        """Test task_stages raises TerraformError on non-200 status."""
        mock_client = Mock()
        mock_client.get.return_value = {
            "status": 401,
            "data": {
                "errors": [
                    {
                        "detail": "Authentication required",
                        "status": "401",
                        "title": "Unauthorized",
                    }
                ]
            },
        }

        run_id = "run-123"

        with pytest.raises(TerraformError) as exc_info:
            task_stages(mock_client, run_id)

        mock_client.get.assert_called_once_with("/runs/run-123/task-stages")
        assert "401" in str(exc_info.value)

    def test_task_stages_empty_stages_list(self):
        """Test task_stages with empty stages list."""
        mock_client = Mock()
        mock_client.get.return_value = {
            "status": 200,
            "data": [],
        }

        run_id = "run-123"
        result = task_stages(mock_client, run_id)

        assert result == []

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

    def test_all_functions_handle_client_exception(self):
        """Test all functions handle client exceptions gracefully."""
        mock_client = Mock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client.get.side_effect = Exception("Network error")

        run_id = "run-123"
        test_data = {"data": {"type": "runs"}}

        # Test that exceptions from client are propagated
        with pytest.raises(Exception, match="Network error"):
            create_run(mock_client, test_data)

        with pytest.raises(Exception, match="Network error"):
            apply_run(mock_client, run_id)

        with pytest.raises(Exception, match="Network error"):
            cancel_run(mock_client, run_id)

        with pytest.raises(Exception, match="Network error"):
            discard_run(mock_client, run_id)

        with pytest.raises(Exception, match="Network error"):
            get_run(mock_client, run_id)

        with pytest.raises(Exception, match="Network error"):
            run_events(mock_client, run_id)

        with pytest.raises(Exception, match="Network error"):
            task_stages(mock_client, run_id)

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

    def test_functions_with_none_values(self):
        """Test functions handle None values appropriately."""
        mock_client = Mock()

        # Test create_run with None data - it will call client.post() and get a mock response
        mock_client.post.return_value = {"status": 400}
        with pytest.raises(TerraformError):
            create_run(mock_client, None)

        # Test other functions with None run_id - they will format URLs with None
        mock_client.post.return_value = {"status": 400}
        mock_client.get.return_value = {"status": 400}

        with pytest.raises(TerraformError):
            apply_run(mock_client, None)

        with pytest.raises(TerraformError):
            cancel_run(mock_client, None)

        with pytest.raises(TerraformError):
            discard_run(mock_client, None)

        with pytest.raises(TerraformError):
            get_run(mock_client, None)

        with pytest.raises(TerraformError):
            run_events(mock_client, None)

        with pytest.raises(TerraformError):
            task_stages(mock_client, None)

    def test_response_status_edge_cases(self):
        """Test edge cases for status code validation."""
        mock_client = Mock()

        # Test create_run with status 200 instead of 201 (should fail)
        mock_client.post.return_value = {
            "status": 200,
            "data": {"id": "run-123", "type": "runs"},
        }

        test_data = {"data": {"type": "runs"}}
        with pytest.raises(TerraformError):
            create_run(mock_client, test_data)

        # Test apply_run with status 200 instead of 202 (should fail)
        mock_client.post.return_value = {
            "status": 200,
            "data": {"id": "run-123", "type": "runs"},
        }

        with pytest.raises(TerraformError):
            apply_run(mock_client, "run-123")

        # Test get_run with status 201 instead of 200 (should fail)
        mock_client.get.return_value = {
            "status": 201,
            "data": {"id": "run-123", "type": "runs"},
        }

        with pytest.raises(TerraformError):
            get_run(mock_client, "run-123")


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

    def test_error_propagation_consistency(self):
        """Test that all functions consistently handle and propagate errors."""
        mock_client = Mock()
        error_response = {
            "status": 500,
            "data": {"errors": [{"detail": "Server error"}]},
        }

        functions_to_test = [
            (create_run, [{"data": {"type": "runs"}}]),
            (apply_run, ["run-123"]),
            (cancel_run, ["run-123"]),
            (discard_run, ["run-123"]),
            (get_run, ["run-123"]),
            (run_events, ["run-123"]),
            (task_stages, ["run-123"]),
        ]

        for func, args in functions_to_test:
            # Configure mock for this function
            if func == create_run:
                mock_client.post.return_value = error_response
            elif func in [apply_run, cancel_run, discard_run]:
                mock_client.post.return_value = error_response
            else:  # GET functions
                mock_client.get.return_value = error_response

            # Test that TerraformError is raised consistently
            with pytest.raises(TerraformError) as exc_info:
                func(mock_client, *args)

            assert "500" in str(exc_info.value)

            # Reset mock for next iteration
            mock_client.reset_mock()
