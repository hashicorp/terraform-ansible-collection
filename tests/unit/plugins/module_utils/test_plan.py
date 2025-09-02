# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import unittest

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.plan import (
    _get_plan_data,
    _handle_api_response,
    get_plan_json_output,
    get_plan_metadata,
)


# import pytest


class TestHandleApiResponse(unittest.TestCase):
    """Tests for _handle_api_response function."""

    def test_handle_api_response_success_200(self):
        """Test handling successful 200 response."""
        response = {
            "status": 200,
            "data": {"id": "plan-123", "type": "plans"},
        }

        result = _handle_api_response(response)
        self.assertEqual(result, response)

    def test_handle_api_response_not_found_404(self):
        """Test handling 404 not found response."""
        response = {"status": 404, "errors": [{"detail": "Not found"}]}

        result = _handle_api_response(response)
        self.assertEqual(result, {})

    def test_handle_api_response_client_error_400(self):
        """Test handling 400 client error response."""
        response = {
            "status": 400,
            "errors": [{"detail": "Bad request", "code": "INVALID_REQUEST"}],
        }

        with self.assertRaises(TerraformError) as context:
            _handle_api_response(response)

        self.assertEqual(context.exception.args[0], response)

    def test_handle_api_response_unauthorized_401(self):
        """Test handling 401 unauthorized response."""
        response = {
            "status": 401,
            "errors": [{"detail": "Unauthorized", "code": "UNAUTHORIZED"}],
        }

        with self.assertRaises(TerraformError) as context:
            _handle_api_response(response)

        self.assertEqual(context.exception.args[0], response)

    def test_handle_api_response_server_error_500(self):
        """Test handling 500 server error response."""
        response = {
            "status": 500,
            "errors": [{"detail": "Internal server error"}],
        }

        with self.assertRaises(TerraformError) as context:
            _handle_api_response(response)

        self.assertEqual(context.exception.args[0], response)

    def test_handle_api_response_various_error_codes(self):
        """Test handling various error status codes."""
        error_codes = [403, 422, 429, 502, 503]

        for status_code in error_codes:
            with self.subTest(status_code=status_code):
                response = {"status": status_code, "errors": [{"detail": f"Error {status_code}"}]}

                with self.assertRaises(TerraformError) as context:
                    _handle_api_response(response)

                self.assertEqual(context.exception.args[0], response)


class TestGetPlanData(unittest.TestCase):
    """Tests for _get_plan_data function."""

    def setUp(self):
        """Set up common test variables."""
        self.mock_client = Mock()
        self.plan_id = "plan-123abc456def789"
        self.run_id = "run-456def789abc123"

    def test_get_plan_data_with_plan_id_no_suffix(self):
        """Test _get_plan_data with plan ID and no endpoint suffix."""
        expected_response = {
            "status": 200,
            "data": {"id": self.plan_id, "type": "plans"},
        }
        self.mock_client.get.return_value = expected_response

        result = _get_plan_data(self.mock_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, expected_response)
        self.mock_client.get.assert_called_once_with(f"/plans/{self.plan_id}")

    def test_get_plan_data_with_plan_id_with_suffix(self):
        """Test _get_plan_data with plan ID and endpoint suffix."""
        expected_response = {
            "status": 200,
            "data": {"format_version": "1.2", "terraform_version": "1.5.0"},
        }
        self.mock_client.get.return_value = expected_response

        result = _get_plan_data(self.mock_client, self.plan_id, use_plan_id=True, endpoint_suffix="/json-output")

        self.assertEqual(result, expected_response)
        self.mock_client.get.assert_called_once_with(f"/plans/{self.plan_id}/json-output")

    def test_get_plan_data_with_run_id_no_suffix(self):
        """Test _get_plan_data with run ID and no endpoint suffix."""
        expected_response = {
            "status": 200,
            "data": {"id": "plan-789ghi123jkl456", "type": "plans"},
        }
        self.mock_client.get.return_value = expected_response

        result = _get_plan_data(self.mock_client, self.run_id, use_plan_id=False)

        self.assertEqual(result, expected_response)
        self.mock_client.get.assert_called_once_with(f"/runs/{self.run_id}/plan")

    def test_get_plan_data_with_run_id_with_suffix(self):
        """Test _get_plan_data with run ID and endpoint suffix."""
        expected_response = {
            "status": 200,
            "data": {"format_version": "1.2", "terraform_version": "1.5.0"},
        }
        self.mock_client.get.return_value = expected_response

        result = _get_plan_data(self.mock_client, self.run_id, use_plan_id=False, endpoint_suffix="/json-output")

        self.assertEqual(result, expected_response)
        self.mock_client.get.assert_called_once_with(f"/runs/{self.run_id}/plan/json-output")

    def test_get_plan_data_not_found_404(self):
        """Test _get_plan_data when resource is not found."""
        response = {"status": 404, "errors": [{"detail": "Not found"}]}
        self.mock_client.get.return_value = response

        result = _get_plan_data(self.mock_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, {})
        self.mock_client.get.assert_called_once_with(f"/plans/{self.plan_id}")

    def test_get_plan_data_error_response(self):
        """Test _get_plan_data with error response."""
        response = {"status": 500, "errors": [{"detail": "Internal server error"}]}
        self.mock_client.get.return_value = response

        with self.assertRaises(TerraformError) as context:
            _get_plan_data(self.mock_client, self.plan_id, use_plan_id=True)

        self.assertEqual(context.exception.args[0], response)
        self.mock_client.get.assert_called_once_with(f"/plans/{self.plan_id}")


class TestGetPlanMetadata(unittest.TestCase):
    """Tests for get_plan_metadata function."""

    def setUp(self):
        """Set up common test variables."""
        self.mock_client = Mock()
        self.plan_id = "plan-123abc456def789"
        self.run_id = "run-456def789abc123"

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_metadata_with_plan_id(self, mock_get_plan_data):
        """Test get_plan_metadata with plan ID."""
        expected_response = {
            "status": 200,
            "data": {
                "id": self.plan_id,
                "type": "plans",
                "attributes": {
                    "status": "finished",
                    "has_changes": True,
                    "resource_additions": 2,
                    "resource_changes": 1,
                    "resource_destructions": 0,
                },
            },
        }
        mock_get_plan_data.return_value = expected_response

        result = get_plan_metadata(self.mock_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, expected_response)
        mock_get_plan_data.assert_called_once_with(self.mock_client, self.plan_id, True)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_metadata_with_run_id(self, mock_get_plan_data):
        """Test get_plan_metadata with run ID."""
        expected_response = {
            "status": 200,
            "data": {
                "id": "plan-789ghi123jkl456",
                "type": "plans",
                "attributes": {
                    "status": "planning",
                    "has_changes": False,
                },
            },
        }
        mock_get_plan_data.return_value = expected_response

        result = get_plan_metadata(self.mock_client, self.run_id, use_plan_id=False)

        self.assertEqual(result, expected_response)
        mock_get_plan_data.assert_called_once_with(self.mock_client, self.run_id, False)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_metadata_not_found(self, mock_get_plan_data):
        """Test get_plan_metadata when plan is not found."""
        mock_get_plan_data.return_value = {}

        result = get_plan_metadata(self.mock_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, {})
        mock_get_plan_data.assert_called_once_with(self.mock_client, self.plan_id, True)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_metadata_error(self, mock_get_plan_data):
        """Test get_plan_metadata when an error occurs."""
        mock_get_plan_data.side_effect = TerraformError({"status": 500, "errors": [{"detail": "Server error"}]})

        with self.assertRaises(TerraformError):
            get_plan_metadata(self.mock_client, self.plan_id, use_plan_id=True)

        mock_get_plan_data.assert_called_once_with(self.mock_client, self.plan_id, True)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_metadata_complex_response(self, mock_get_plan_data):
        """Test get_plan_metadata with complex metadata response."""
        expected_response = {
            "status": 200,
            "data": {
                "id": self.plan_id,
                "type": "plans",
                "attributes": {
                    "status": "finished",
                    "has_changes": True,
                    "resource_additions": 3,
                    "resource_changes": 2,
                    "resource_destructions": 1,
                    "created_at": "2025-01-15T10:30:00Z",
                    "status_timestamps": {
                        "queued_at": "2025-01-15T10:25:00Z",
                        "pending_at": "2025-01-15T10:26:00Z",
                        "planning_at": "2025-01-15T10:27:00Z",
                        "planned_at": "2025-01-15T10:30:00Z",
                    },
                    "permissions": {"can_update": True, "can_destroy": False},
                },
                "relationships": {
                    "workspace": {"data": {"id": "ws-123abc", "type": "workspaces"}},
                    "run": {"data": {"id": self.run_id, "type": "runs"}},
                },
            },
        }
        mock_get_plan_data.return_value = expected_response

        result = get_plan_metadata(self.mock_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, expected_response)
        # Verify complex nested structure is preserved
        self.assertIn("status_timestamps", result["data"]["attributes"])
        self.assertIn("permissions", result["data"]["attributes"])
        self.assertIn("relationships", result["data"])


class TestGetPlanJsonOutput(unittest.TestCase):
    """Tests for get_plan_json_output function."""

    def setUp(self):
        """Set up common test variables."""
        self.mock_client = Mock()
        self.plan_id = "plan-123abc456def789"
        self.run_id = "run-456def789abc123"

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_json_output_with_plan_id(self, mock_get_plan_data):
        """Test get_plan_json_output with plan ID."""
        expected_response = {
            "status": 200,
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [
                    {
                        "address": "aws_instance.example",
                        "mode": "managed",
                        "type": "aws_instance",
                        "name": "example",
                        "change": {
                            "actions": ["create"],
                            "before": None,
                            "after": {"ami": "ami-0c02fb55956c7d316", "instance_type": "t2.micro"},
                        },
                    },
                ],
                "planned_values": {
                    "root_module": {
                        "resources": [
                            {
                                "address": "aws_instance.example",
                                "mode": "managed",
                                "type": "aws_instance",
                                "name": "example",
                                "values": {"ami": "ami-0c02fb55956c7d316", "instance_type": "t2.micro"},
                            },
                        ],
                    },
                },
                "applyable": True,
                "complete": True,
                "errored": False,
            },
        }
        mock_get_plan_data.return_value = expected_response

        result = get_plan_json_output(self.mock_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, expected_response)
        mock_get_plan_data.assert_called_once_with(self.mock_client, self.plan_id, True, "/json-output")

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_json_output_with_run_id(self, mock_get_plan_data):
        """Test get_plan_json_output with run ID."""
        expected_response = {
            "status": 200,
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [
                    {
                        "address": "aws_s3_bucket.example",
                        "mode": "managed",
                        "type": "aws_s3_bucket",
                        "name": "example",
                        "change": {
                            "actions": ["update"],
                            "before": {"versioning": {"enabled": False}},
                            "after": {"versioning": {"enabled": True}},
                        },
                    },
                ],
                "applyable": True,
                "complete": True,
                "errored": False,
            },
        }
        mock_get_plan_data.return_value = expected_response

        result = get_plan_json_output(self.mock_client, self.run_id, use_plan_id=False)

        self.assertEqual(result, expected_response)
        mock_get_plan_data.assert_called_once_with(self.mock_client, self.run_id, False, "/json-output")

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_json_output_not_found(self, mock_get_plan_data):
        """Test get_plan_json_output when JSON output is not found."""
        mock_get_plan_data.return_value = {}

        result = get_plan_json_output(self.mock_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, {})
        mock_get_plan_data.assert_called_once_with(self.mock_client, self.plan_id, True, "/json-output")

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_json_output_error(self, mock_get_plan_data):
        """Test get_plan_json_output when an error occurs."""
        mock_get_plan_data.side_effect = TerraformError({"status": 401, "errors": [{"detail": "Unauthorized"}]})

        with self.assertRaises(TerraformError):
            get_plan_json_output(self.mock_client, self.plan_id, use_plan_id=True)

        mock_get_plan_data.assert_called_once_with(self.mock_client, self.plan_id, True, "/json-output")

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_json_output_no_changes(self, mock_get_plan_data):
        """Test get_plan_json_output when plan has no changes."""
        expected_response = {
            "status": 200,
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [],
                "planned_values": {"root_module": {"resources": []}},
                "applyable": False,
                "complete": True,
                "errored": False,
            },
        }
        mock_get_plan_data.return_value = expected_response

        result = get_plan_json_output(self.mock_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, expected_response)
        mock_get_plan_data.assert_called_once_with(self.mock_client, self.plan_id, True, "/json-output")

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_json_output_error_state(self, mock_get_plan_data):
        """Test get_plan_json_output when plan is in error state."""
        expected_response = {
            "status": 200,
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [],
                "applyable": False,
                "complete": False,
                "errored": True,
                "error_details": {"message": "Configuration error", "code": "INVALID_CONFIG"},
            },
        }
        mock_get_plan_data.return_value = expected_response

        result = get_plan_json_output(self.mock_client, self.run_id, use_plan_id=False)

        self.assertEqual(result, expected_response)
        mock_get_plan_data.assert_called_once_with(self.mock_client, self.run_id, False, "/json-output")

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan._get_plan_data")
    def test_get_plan_json_output_complex_resource_changes(self, mock_get_plan_data):
        """Test get_plan_json_output with complex resource changes."""
        expected_response = {
            "status": 200,
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
                            "after": {
                                "ami": "ami-12345",
                                "instance_type": "t3.micro",
                                "tags": {"Name": "web-server-1"},
                            },
                            "after_unknown": {"id": True, "arn": True, "public_ip": True},
                            "before_sensitive": {},
                            "after_sensitive": {"tags": {"Name": False}},
                        },
                    },
                    {
                        "address": "aws_security_group.web",
                        "mode": "managed",
                        "type": "aws_security_group",
                        "name": "web",
                        "change": {
                            "actions": ["update"],
                            "before": {
                                "ingress": [
                                    {
                                        "from_port": 80,
                                        "to_port": 80,
                                        "protocol": "tcp",
                                        "cidr_blocks": ["0.0.0.0/0"],
                                    },
                                ],
                            },
                            "after": {
                                "ingress": [
                                    {
                                        "from_port": 80,
                                        "to_port": 80,
                                        "protocol": "tcp",
                                        "cidr_blocks": ["10.0.0.0/8"],
                                    },
                                    {
                                        "from_port": 443,
                                        "to_port": 443,
                                        "protocol": "tcp",
                                        "cidr_blocks": ["10.0.0.0/8"],
                                    },
                                ],
                            },
                            "before_sensitive": {},
                            "after_sensitive": {},
                        },
                    },
                    {
                        "address": "aws_instance.old",
                        "mode": "managed",
                        "type": "aws_instance",
                        "name": "old",
                        "change": {
                            "actions": ["delete"],
                            "before": {"ami": "ami-old123", "instance_type": "t2.micro"},
                            "after": None,
                            "before_sensitive": {},
                            "after_sensitive": {},
                        },
                    },
                ],
                "resource_drift": [
                    {
                        "address": "aws_instance.drift_resource",
                        "mode": "managed",
                        "type": "aws_instance",
                        "name": "drift_resource",
                        "change": {
                            "actions": ["update"],
                            "before": {"tags": {"Environment": "dev"}},
                            "after": {"tags": {"Environment": "prod"}},
                            "before_sensitive": {},
                            "after_sensitive": {},
                        },
                    },
                ],
                "output_changes": {
                    "instance_ip": {
                        "actions": ["create"],
                        "before": None,
                        "after": "192.168.1.100",
                        "before_sensitive": False,
                        "after_sensitive": False,
                    },
                    "database_password": {
                        "actions": ["update"],
                        "before": "old_password",
                        "after": "new_password",
                        "before_sensitive": True,
                        "after_sensitive": True,
                    },
                },
                "planned_values": {
                    "root_module": {
                        "resources": [
                            {
                                "address": "aws_instance.web[0]",
                                "mode": "managed",
                                "type": "aws_instance",
                                "name": "web",
                                "index": 0,
                                "values": {"ami": "ami-12345", "instance_type": "t3.micro"},
                            },
                        ],
                    },
                },
                "applyable": True,
                "complete": True,
                "errored": False,
            },
        }
        mock_get_plan_data.return_value = expected_response

        result = get_plan_json_output(self.mock_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, expected_response)
        mock_get_plan_data.assert_called_once_with(self.mock_client, self.plan_id, True, "/json-output")

        # Verify complex data structure is preserved
        self.assertGreater(len(result["data"]["resource_changes"]), 1)
        self.assertIn("after_unknown", result["data"]["resource_changes"][0]["change"])
        self.assertIn("resource_drift", result["data"])
        self.assertIn("output_changes", result["data"])
        self.assertIn("planned_values", result["data"])


class TestIntegrationScenarios(unittest.TestCase):
    """Integration-style tests for plan utility functions working together."""

    def setUp(self):
        """Set up common test variables."""
        self.mock_client = Mock()
        self.plan_id = "plan-integration-test"
        self.run_id = "run-integration-test"

    def test_full_plan_retrieval_workflow_with_plan_id(self):
        """Test complete workflow of retrieving plan metadata and JSON output using plan ID."""
        # Mock metadata response
        metadata_response = {
            "status": 200,
            "data": {
                "id": self.plan_id,
                "type": "plans",
                "attributes": {
                    "status": "finished",
                    "has_changes": True,
                    "resource_additions": 1,
                    "resource_changes": 0,
                    "resource_destructions": 0,
                },
            },
        }

        # Mock JSON output response
        json_output_response = {
            "status": 200,
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [
                    {
                        "address": "aws_instance.test",
                        "change": {
                            "actions": ["create"],
                            "before": None,
                            "after": {"ami": "ami-test123"},
                        },
                    },
                ],
                "applyable": True,
                "complete": True,
                "errored": False,
            },
        }

        # Set up mock responses for different endpoints
        def mock_get_side_effect(path):
            if path == f"/plans/{self.plan_id}":
                return metadata_response
            elif path == f"/plans/{self.plan_id}/json-output":
                return json_output_response
            else:
                return {"status": 404}

        self.mock_client.get.side_effect = mock_get_side_effect

        # Test metadata retrieval
        metadata_result = get_plan_metadata(self.mock_client, self.plan_id, use_plan_id=True)
        self.assertEqual(metadata_result, metadata_response)

        # Test JSON output retrieval
        json_output_result = get_plan_json_output(self.mock_client, self.plan_id, use_plan_id=True)
        self.assertEqual(json_output_result, json_output_response)

        # Verify both endpoints were called
        expected_calls = [
            unittest.mock.call(f"/plans/{self.plan_id}"),
            unittest.mock.call(f"/plans/{self.plan_id}/json-output"),
        ]
        self.mock_client.get.assert_has_calls(expected_calls)

    def test_full_plan_retrieval_workflow_with_run_id(self):
        """Test complete workflow of retrieving plan metadata and JSON output using run ID."""
        # Mock metadata response
        metadata_response = {
            "status": 200,
            "data": {
                "id": "plan-from-run",
                "type": "plans",
                "attributes": {
                    "status": "planning",
                    "has_changes": False,
                },
            },
        }

        # Mock JSON output response
        json_output_response = {
            "status": 200,
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [],
                "applyable": False,
                "complete": True,
                "errored": False,
            },
        }

        # Set up mock responses for different endpoints
        def mock_get_side_effect(path):
            if path == f"/runs/{self.run_id}/plan":
                return metadata_response
            elif path == f"/runs/{self.run_id}/plan/json-output":
                return json_output_response
            else:
                return {"status": 404}

        self.mock_client.get.side_effect = mock_get_side_effect

        # Test metadata retrieval
        metadata_result = get_plan_metadata(self.mock_client, self.run_id, use_plan_id=False)
        self.assertEqual(metadata_result, metadata_response)

        # Test JSON output retrieval
        json_output_result = get_plan_json_output(self.mock_client, self.run_id, use_plan_id=False)
        self.assertEqual(json_output_result, json_output_response)

        # Verify both endpoints were called
        expected_calls = [
            unittest.mock.call(f"/runs/{self.run_id}/plan"),
            unittest.mock.call(f"/runs/{self.run_id}/plan/json-output"),
        ]
        self.mock_client.get.assert_has_calls(expected_calls)

    def test_partial_failure_scenarios(self):
        """Test scenarios where one API call succeeds and another fails."""

        # Scenario 1: Metadata succeeds, JSON output fails
        def mock_get_scenario_1(path):
            if path == f"/plans/{self.plan_id}":
                return {"status": 200, "data": {"id": self.plan_id}}
            elif path == f"/plans/{self.plan_id}/json-output":
                return {"status": 500, "errors": [{"detail": "Server error"}]}
            else:
                return {"status": 404}

        self.mock_client.get.side_effect = mock_get_scenario_1

        # Metadata should succeed
        metadata_result = get_plan_metadata(self.mock_client, self.plan_id, use_plan_id=True)
        self.assertEqual(metadata_result["status"], 200)

        # JSON output should raise an exception
        with self.assertRaises(TerraformError):
            get_plan_json_output(self.mock_client, self.plan_id, use_plan_id=True)

        # Reset mock for next scenario
        self.mock_client.reset_mock()

        # Scenario 2: Metadata fails, JSON output would succeed
        def mock_get_scenario_2(path):
            if path == f"/plans/{self.plan_id}":
                return {"status": 403, "errors": [{"detail": "Forbidden"}]}
            elif path == f"/plans/{self.plan_id}/json-output":
                return {"status": 200, "data": {"format_version": "1.2"}}
            else:
                return {"status": 404}

        self.mock_client.get.side_effect = mock_get_scenario_2

        # Metadata should raise an exception
        with self.assertRaises(TerraformError):
            get_plan_metadata(self.mock_client, self.plan_id, use_plan_id=True)

    def test_consistent_not_found_handling(self):
        """Test that both functions handle 404 responses consistently."""
        # Both endpoints return 404
        self.mock_client.get.return_value = {"status": 404}

        # Both functions should return empty dict for 404
        metadata_result = get_plan_metadata(self.mock_client, self.plan_id, use_plan_id=True)
        json_output_result = get_plan_json_output(self.mock_client, self.plan_id, use_plan_id=True)

        self.assertEqual(metadata_result, {})
        self.assertEqual(json_output_result, {})

        # Verify both endpoints were called
        expected_calls = [
            unittest.mock.call(f"/plans/{self.plan_id}"),
            unittest.mock.call(f"/plans/{self.plan_id}/json-output"),
        ]
        self.mock_client.get.assert_has_calls(expected_calls)


class TestErrorHandlingEdgeCases(unittest.TestCase):
    """Tests for edge cases in error handling."""

    def setUp(self):
        """Set up common test variables."""
        self.mock_client = Mock()

    def test_handle_api_response_missing_status(self):
        """Test handling response with missing status field."""
        response = {"data": {"id": "plan-123"}}  # Missing status

        # Should handle gracefully - missing status key will cause KeyError
        with self.assertRaises(KeyError):
            _handle_api_response(response)

    def test_handle_api_response_none_response(self):
        """Test handling None response."""
        with self.assertRaises((AttributeError, TypeError)):
            _handle_api_response(None)

    def test_handle_api_response_empty_response(self):
        """Test handling empty response."""
        response = {}

        with self.assertRaises(KeyError):
            _handle_api_response(response)

    def test_get_plan_data_client_exception(self):
        """Test _get_plan_data when client raises an exception."""
        self.mock_client.get.side_effect = Exception("Network error")

        with self.assertRaises(Exception) as context:
            _get_plan_data(self.mock_client, "plan-123", use_plan_id=True)

        self.assertEqual(str(context.exception), "Network error")

    def test_plan_functions_with_client_exception(self):
        """Test plan functions when client raises an exception."""
        self.mock_client.get.side_effect = ConnectionError("Connection failed")

        with self.assertRaises(ConnectionError):
            get_plan_metadata(self.mock_client, "plan-123", use_plan_id=True)

        with self.assertRaises(ConnectionError):
            get_plan_json_output(self.mock_client, "plan-123", use_plan_id=True)

    def test_unicode_handling_in_responses(self):
        """Test handling of unicode characters in API responses."""
        unicode_response = {
            "status": 200,
            "data": {
                "id": "plan-unicode-测试",
                "attributes": {
                    "description": "Plan with unicode: 测试 🚀 café",
                    "status": "finished",
                },
            },
        }

        result = _handle_api_response(unicode_response)
        self.assertEqual(result, unicode_response)

        # Verify unicode content is preserved
        self.assertIn("测试 🚀 café", result["data"]["attributes"]["description"])
        self.assertIn("plan-unicode-测试", result["data"]["id"])

    def test_large_response_handling(self):
        """Test handling of large response payloads."""
        # Create a large response with many resource changes
        large_resource_changes = []
        for i in range(1000):
            large_resource_changes.append(
                {
                    "address": f"aws_instance.large_{i}",
                    "change": {
                        "actions": ["create"],
                        "before": None,
                        "after": {"ami": f"ami-{i:06d}", "instance_type": "t2.micro"},
                    },
                },
            )

        large_response = {
            "status": 200,
            "data": {
                "format_version": "1.2",
                "resource_changes": large_resource_changes,
                "applyable": True,
                "complete": True,
                "errored": False,
            },
        }

        result = _handle_api_response(large_response)
        self.assertEqual(result, large_response)
        self.assertEqual(len(result["data"]["resource_changes"]), 1000)


if __name__ == "__main__":
    unittest.main()
