# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import unittest

from unittest.mock import Mock

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)

# Import the module under test
from ansible_collections.hashicorp.terraform.plugins.module_utils.plan import (
    get_plan_json_output,
    get_plan_metadata,
)


class TestPlanFunctions(unittest.TestCase):
    """Unit tests for Terraform plan helper functions."""

    def setUp(self):
        """Set up common test variables and mocks."""
        self.mock_tf_client = Mock()
        self.plan_id = "plan-123abc456def789"
        self.run_id = "run-456def789abc123"


class TestGetPlanMetadata(TestPlanFunctions):
    """Tests for get_plan_metadata function."""

    def test_get_plan_metadata_success_with_plan_id(self):
        """Test successful retrieval of plan metadata using plan ID."""
        expected_response = {
            "data": {
                "id": self.plan_id,
                "type": "plans",
                "attributes": {
                    "status": "finished",
                    "has_changes": True,
                    "resource_additions": 1,
                    "resource_changes": 2,
                    "resource_destructions": 0,
                },
            },
            "status": 200,
        }
        self.mock_tf_client.get.return_value = expected_response

        result = get_plan_metadata(self.mock_tf_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, expected_response)
        self.mock_tf_client.get.assert_called_once_with(f"/plans/{self.plan_id}")

    def test_get_plan_metadata_success_with_run_id(self):
        """Test successful retrieval of plan metadata using run ID."""
        expected_response = {
            "data": {
                "id": "plan-789ghi123jkl456",
                "type": "plans",
                "attributes": {
                    "status": "planning",
                    "has_changes": False,
                    "resource_additions": 0,
                    "resource_changes": 0,
                    "resource_destructions": 0,
                },
            },
            "status": 200,
        }
        self.mock_tf_client.get.return_value = expected_response

        result = get_plan_metadata(self.mock_tf_client, self.run_id, use_plan_id=False)

        self.assertEqual(result, expected_response)
        self.mock_tf_client.get.assert_called_once_with(f"/runs/{self.run_id}/plan")

    def test_get_plan_metadata_plan_not_found_404(self):
        """Test get_plan_metadata returns empty dict on 404 (plan not found)."""
        response = {"status": 404}
        self.mock_tf_client.get.return_value = response

        result = get_plan_metadata(self.mock_tf_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, {})
        self.mock_tf_client.get.assert_called_once_with(f"/plans/{self.plan_id}")

    def test_get_plan_metadata_run_not_found_404(self):
        """Test get_plan_metadata returns empty dict on 404 (run not found)."""
        response = {"status": 404}
        self.mock_tf_client.get.return_value = response

        result = get_plan_metadata(self.mock_tf_client, self.run_id, use_plan_id=False)

        self.assertEqual(result, {})
        self.mock_tf_client.get.assert_called_once_with(f"/runs/{self.run_id}/plan")

    def test_get_plan_metadata_failure_raises_error(self):
        """Test get_plan_metadata raises TerraformError on non-200/non-404 status."""
        response = {"status": 500, "error": "Internal server error"}
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(TerraformError):
            get_plan_metadata(self.mock_tf_client, self.plan_id, use_plan_id=True)

    def test_get_plan_metadata_various_failure_statuses(self):
        """Test get_plan_metadata with various non-success status codes."""
        for status_code in [400, 401, 403, 422, 500, 502, 503]:
            with self.subTest(status_code=status_code):
                response = {"status": status_code}
                self.mock_tf_client.get.return_value = response

                with self.assertRaises(TerraformError):
                    get_plan_metadata(self.mock_tf_client, self.plan_id, use_plan_id=True)

    def test_get_plan_metadata_unauthorized_with_plan_id(self):
        """Test get_plan_metadata with 401 unauthorized using plan ID."""
        response = {"status": 401, "error": "Unauthorized"}
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(TerraformError):
            get_plan_metadata(self.mock_tf_client, self.plan_id, use_plan_id=True)

    def test_get_plan_metadata_forbidden_with_run_id(self):
        """Test get_plan_metadata with 403 forbidden using run ID."""
        response = {"status": 403, "error": "Forbidden"}
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(TerraformError):
            get_plan_metadata(self.mock_tf_client, self.run_id, use_plan_id=False)

    def test_get_plan_metadata_with_complex_data_structure(self):
        """Test get_plan_metadata with complex nested data structure."""
        expected_response = {
            "data": {
                "id": self.plan_id,
                "type": "plans",
                "attributes": {
                    "status": "finished",
                    "has_changes": True,
                    "resource_additions": 3,
                    "resource_changes": 1,
                    "resource_destructions": 2,
                    "created_at": "2025-01-15T10:30:00Z",
                    "status_timestamps": {
                        "queued_at": "2025-01-15T10:25:00Z",
                        "pending_at": "2025-01-15T10:26:00Z",
                        "planning_at": "2025-01-15T10:27:00Z",
                        "planned_at": "2025-01-15T10:30:00Z",
                    },
                    "permissions": {
                        "can_update": True,
                        "can_destroy": False,
                    },
                },
                "relationships": {
                    "workspace": {"data": {"id": "ws-123abc", "type": "workspaces"}},
                    "run": {"data": {"id": self.run_id, "type": "runs"}},
                },
            },
            "status": 200,
        }
        self.mock_tf_client.get.return_value = expected_response

        result = get_plan_metadata(self.mock_tf_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, expected_response)


class TestGetPlanJsonOutput(TestPlanFunctions):
    """Tests for get_plan_json_output function."""

    def test_get_plan_json_output_success_with_plan_id(self):
        """Test successful retrieval of plan JSON output using plan ID."""
        expected_response = {
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "planned_values": {
                    "root_module": {
                        "resources": [
                            {
                                "address": "aws_instance.example",
                                "mode": "managed",
                                "type": "aws_instance",
                                "name": "example",
                                "values": {
                                    "ami": "ami-0c02fb55956c7d316",
                                    "instance_type": "t2.micro",
                                },
                            }
                        ]
                    }
                },
                "resource_changes": [
                    {
                        "address": "aws_instance.example",
                        "mode": "managed",
                        "type": "aws_instance",
                        "name": "example",
                        "change": {
                            "actions": ["create"],
                            "before": None,
                            "after": {
                                "ami": "ami-0c02fb55956c7d316",
                                "instance_type": "t2.micro",
                            },
                        },
                    }
                ],
                "applyable": True,
                "complete": True,
                "errored": False,
            },
            "status": 200,
        }
        self.mock_tf_client.get.return_value = expected_response

        result = get_plan_json_output(self.mock_tf_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, expected_response)
        self.mock_tf_client.get.assert_called_once_with(f"/plans/{self.plan_id}/json-output")

    def test_get_plan_json_output_success_with_run_id(self):
        """Test successful retrieval of plan JSON output using run ID."""
        expected_response = {
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
                    }
                ],
                "applyable": True,
                "complete": True,
                "errored": False,
            },
            "status": 200,
        }
        self.mock_tf_client.get.return_value = expected_response

        result = get_plan_json_output(self.mock_tf_client, self.run_id, use_plan_id=False)

        self.assertEqual(result, expected_response)
        self.mock_tf_client.get.assert_called_once_with(f"/runs/{self.run_id}/plan/json-output")

    def test_get_plan_json_output_plan_not_found_404(self):
        """Test get_plan_json_output returns empty dict on 404 (plan JSON not found)."""
        response = {"status": 404}
        self.mock_tf_client.get.return_value = response

        result = get_plan_json_output(self.mock_tf_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, {})
        self.mock_tf_client.get.assert_called_once_with(f"/plans/{self.plan_id}/json-output")

    def test_get_plan_json_output_run_not_found_404(self):
        """Test get_plan_json_output returns empty dict on 404 (run JSON not found)."""
        response = {"status": 404}
        self.mock_tf_client.get.return_value = response

        result = get_plan_json_output(self.mock_tf_client, self.run_id, use_plan_id=False)

        self.assertEqual(result, {})
        self.mock_tf_client.get.assert_called_once_with(f"/runs/{self.run_id}/plan/json-output")

    def test_get_plan_json_output_failure_raises_error(self):
        """Test get_plan_json_output raises TerraformError on non-200/non-404 status."""
        response = {"status": 500, "error": "Internal server error"}
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(TerraformError):
            get_plan_json_output(self.mock_tf_client, self.plan_id, use_plan_id=True)

    def test_get_plan_json_output_various_failure_statuses(self):
        """Test get_plan_json_output with various non-success status codes."""
        for status_code in [400, 401, 403, 422, 500, 502, 503]:
            with self.subTest(status_code=status_code):
                response = {"status": status_code}
                self.mock_tf_client.get.return_value = response

                with self.assertRaises(TerraformError):
                    get_plan_json_output(self.mock_tf_client, self.plan_id, use_plan_id=True)

    def test_get_plan_json_output_with_no_changes(self):
        """Test get_plan_json_output when plan has no changes."""
        expected_response = {
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [],
                "planned_values": {"root_module": {"resources": []}},
                "applyable": False,
                "complete": True,
                "errored": False,
            },
            "status": 200,
        }
        self.mock_tf_client.get.return_value = expected_response

        result = get_plan_json_output(self.mock_tf_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, expected_response)

    def test_get_plan_json_output_with_error_state(self):
        """Test get_plan_json_output when plan is in error state."""
        expected_response = {
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [],
                "applyable": False,
                "complete": False,
                "errored": True,
                "error_details": {
                    "message": "Configuration error",
                    "code": "INVALID_CONFIG",
                },
            },
            "status": 200,
        }
        self.mock_tf_client.get.return_value = expected_response

        result = get_plan_json_output(self.mock_tf_client, self.run_id, use_plan_id=False)

        self.assertEqual(result, expected_response)

    def test_get_plan_json_output_with_complex_resource_changes(self):
        """Test get_plan_json_output with complex resource changes."""
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
                            "after": {
                                "ami": "ami-12345",
                                "instance_type": "t3.micro",
                                "tags": {"Name": "web-server-1"},
                            },
                            "after_unknown": {
                                "id": True,
                                "arn": True,
                                "public_ip": True,
                            },
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
                                    }
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
                        },
                    },
                    {
                        "address": "aws_instance.old",
                        "mode": "managed",
                        "type": "aws_instance",
                        "name": "old",
                        "change": {
                            "actions": ["delete"],
                            "before": {
                                "ami": "ami-old123",
                                "instance_type": "t2.micro",
                            },
                            "after": None,
                        },
                    },
                ],
                "planned_values": {
                    "root_module": {
                        "resources": [
                            {
                                "address": "aws_instance.web[0]",
                                "mode": "managed",
                                "type": "aws_instance",
                                "name": "web",
                                "index": 0,
                                "values": {
                                    "ami": "ami-12345",
                                    "instance_type": "t3.micro",
                                },
                            }
                        ]
                    }
                },
                "applyable": True,
                "complete": True,
                "errored": False,
            },
            "status": 200,
        }
        self.mock_tf_client.get.return_value = expected_response

        result = get_plan_json_output(self.mock_tf_client, self.plan_id, use_plan_id=True)

        self.assertEqual(result, expected_response)


if __name__ == "__main__":
    unittest.main()
