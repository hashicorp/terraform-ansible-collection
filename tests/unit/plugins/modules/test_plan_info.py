# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import unittest

from unittest.mock import ANY, Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.plan_info import main


class TestPlanInfoModule:
    """Unit tests for plan_info module."""

    def test_main_with_plan_id_success(self):
        """Test main function with plan_id parameter success case."""
        params = {
            "plan_id": "plan-123abc456def789",
            "run_id": None,
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        metadata_response = {
            "data": {
                "id": "plan-123abc456def789",
                "type": "plans",
                "attributes": {
                    "status": "finished",
                    "has_changes": True,
                    "resource_additions": 2,
                    "resource_changes": 1,
                    "resource_destructions": 0,
                },
            },
            "status": 200,
        }

        json_output_response = {
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [
                    {
                        "address": "aws_instance.web",
                        "mode": "managed",
                        "type": "aws_instance",
                        "name": "web",
                        "change": {
                            "actions": ["create"],
                            "before": None,
                            "after": {
                                "ami": "ami-12345",
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

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_json_output"
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            # Mock exit_json to raise SystemExit to simulate module exit
            mock_module.exit_json.side_effect = SystemExit({"changed": False})

            with pytest.raises(SystemExit):
                main()

            # Verify the plan utility functions were called correctly
            mock_get_metadata.assert_called_once_with(ANY, "plan-123abc456def789", True)
            mock_get_json.assert_called_once_with(ANY, "plan-123abc456def789", True)

            # Verify exit_json was called with the correct result
            expected_result = {
                "changed": False,
                "metadata": metadata_response["data"],
                "json_output": json_output_response["data"],
                "plan_status": "finished",
            }
            mock_module.exit_json.assert_called_once_with(**expected_result)

    def test_main_with_run_id_success(self):
        """Test main function with run_id parameter success case."""
        params = {
            "plan_id": None,
            "run_id": "run-456def789abc123",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        metadata_response = {
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

        json_output_response = {
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [],
                "applyable": False,
                "complete": True,
                "errored": False,
            },
            "status": 200,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_json_output"
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            # Mock exit_json to raise SystemExit to simulate module exit
            mock_module.exit_json.side_effect = SystemExit({"changed": False})

            with pytest.raises(SystemExit):
                main()

            # Verify the plan utility functions were called correctly
            mock_get_metadata.assert_called_once_with(ANY, "run-456def789abc123", False)
            mock_get_json.assert_called_once_with(ANY, "run-456def789abc123", False)

            # Verify exit_json was called with the correct result
            expected_result = {
                "changed": False,
                "metadata": metadata_response["data"],
                "json_output": json_output_response["data"],
                "plan_status": "planning",
            }
            mock_module.exit_json.assert_called_once_with(**expected_result)

    def test_main_plan_not_found_with_plan_id(self):
        """Test main function when plan is not found using plan_id."""
        params = {
            "plan_id": "plan-nonexistent123",
            "run_id": None,
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_json_output"
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            # Mock plan not found (empty response)
            mock_get_metadata.return_value = {}
            mock_get_json.return_value = {}

            main()

            # Should call fail_json with appropriate error message
            mock_module.fail_json.assert_called_once()
            call_args = mock_module.fail_json.call_args[1]  # kwargs
            assert "Plan with ID 'plan-nonexistent123' was not found." in call_args["msg"]

    def test_main_plan_not_found_with_run_id(self):
        """Test main function when plan is not found using run_id."""
        params = {
            "plan_id": None,
            "run_id": "run-nonexistent456",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_json_output"
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            # Mock plan not found (empty response)
            mock_get_metadata.return_value = {}
            mock_get_json.return_value = {}

            main()

            # Should call fail_json with appropriate error message
            mock_module.fail_json.assert_called_once()
            call_args = mock_module.fail_json.call_args[1]
            assert "Plan for run with ID 'run-nonexistent456' was not found." in call_args["msg"]

    def test_main_with_error_status_plan(self):
        """Test main function with a plan in error status."""
        params = {
            "plan_id": "plan-error123",
            "run_id": None,
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        metadata_response = {
            "data": {
                "id": "plan-error123",
                "type": "plans",
                "attributes": {
                    "status": "errored",
                    "has_changes": False,
                    "resource_additions": 0,
                    "resource_changes": 0,
                    "resource_destructions": 0,
                },
            },
            "status": 200,
        }

        json_output_response = {
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [],
                "applyable": False,
                "complete": False,
                "errored": True,
                "error_details": {
                    "message": "Configuration validation failed",
                    "code": "VALIDATION_ERROR",
                },
            },
            "status": 200,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_json_output"
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            # Mock exit_json to raise SystemExit to simulate module exit
            mock_module.exit_json.side_effect = SystemExit({"changed": False})

            with pytest.raises(SystemExit):
                main()

            # Verify exit_json was called with the correct error status
            expected_result = {
                "changed": False,
                "metadata": metadata_response["data"],
                "json_output": json_output_response["data"],
                "plan_status": "errored",
            }
            mock_module.exit_json.assert_called_once_with(**expected_result)

    def test_main_exception_handling(self):
        """Test main function exception handling."""
        params = {
            "plan_id": "plan-exception123",
            "run_id": None,
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformClient"
        ) as mock_client_class:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            # Mock TerraformClient to raise an exception
            mock_client_class.side_effect = Exception("Connection failed")

            main()

            # Should call fail_json with the exception message
            mock_module.fail_json.assert_called_once()
            call_args = mock_module.fail_json.call_args[1]
            assert "Connection failed" in call_args["msg"]

    def test_main_with_missing_status_in_metadata(self):
        """Test main function when status is missing from metadata."""
        params = {
            "plan_id": "plan-nostatus123",
            "run_id": None,
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        metadata_response = {
            "data": {
                "id": "plan-nostatus123",
                "type": "plans",
                "attributes": {
                    "has_changes": True,
                    "resource_additions": 1,
                    "resource_changes": 0,
                    "resource_destructions": 0,
                    # Missing status field
                },
            },
            "status": 200,
        }

        json_output_response = {
            "data": {
                "format_version": "1.2",
                "terraform_version": "1.5.0",
                "resource_changes": [],
                "applyable": True,
                "complete": True,
                "errored": False,
            },
            "status": 200,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_json_output"
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            # Mock exit_json to raise SystemExit to simulate module exit
            mock_module.exit_json.side_effect = SystemExit({"changed": False})

            with pytest.raises(SystemExit):
                main()

            # Verify exit_json was called with "unknown" status
            expected_result = {
                "changed": False,
                "metadata": metadata_response["data"],
                "json_output": json_output_response["data"],
                "plan_status": "unknown",
            }
            mock_module.exit_json.assert_called_once_with(**expected_result)

    def test_main_with_complex_plan_data(self):
        """Test main function with complex plan data including multiple resource changes."""
        params = {
            "run_id": "run-complex789",
            "plan_id": None,
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        metadata_response = {
            "data": {
                "id": "plan-complex789",
                "type": "plans",
                "attributes": {
                    "status": "finished",
                    "has_changes": True,
                    "resource_additions": 2,
                    "resource_changes": 3,
                    "resource_destructions": 1,
                    "created_at": "2025-01-15T10:30:00Z",
                    "status_timestamps": {
                        "queued_at": "2025-01-15T10:25:00Z",
                        "pending_at": "2025-01-15T10:26:00Z",
                        "planning_at": "2025-01-15T10:27:00Z",
                        "planned_at": "2025-01-15T10:30:00Z",
                    },
                },
                "relationships": {
                    "workspace": {"data": {"id": "ws-123abc", "type": "workspaces"}},
                    "run": {"data": {"id": "run-complex789", "type": "runs"}},
                },
            },
            "status": 200,
        }

        json_output_response = {
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
                        },
                    },
                    {
                        "address": "aws_security_group.web",
                        "mode": "managed",
                        "type": "aws_security_group",
                        "name": "web",
                        "change": {
                            "actions": ["update"],
                            "before": {"ingress": [{"from_port": 80, "to_port": 80}]},
                            "after": {"ingress": [{"from_port": 80, "to_port": 80}, {"from_port": 443, "to_port": 443}]},
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
                                "values": {"ami": "ami-12345", "instance_type": "t3.micro"},
                            }
                        ]
                    }
                },
                "applyable": True,
                "complete": True,
                "errored": False,
                "timestamp": "2025-01-15T10:30:00Z",
            },
            "status": 200,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_json_output"
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            # Mock exit_json to raise SystemExit to simulate module exit
            mock_module.exit_json.side_effect = SystemExit({"changed": False})

            with pytest.raises(SystemExit):
                main()

            # Verify the plan utility functions were called correctly with run_id
            mock_get_metadata.assert_called_once_with(ANY, "run-complex789", False)
            mock_get_json.assert_called_once_with(ANY, "run-complex789", False)

            # Verify exit_json was called with the complex data
            expected_result = {
                "changed": False,
                "metadata": metadata_response["data"],
                "json_output": json_output_response["data"],
                "plan_status": "finished",
            }
            mock_module.exit_json.assert_called_once_with(**expected_result)

    def test_module_argument_spec(self):
        """Test that the module has correct argument specification."""
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformModule") as mock_module_class:
            mock_module = Mock()
            mock_module.params = {
                "plan_id": "plan-test123",
                "run_id": None,
                "tf_token": "test-token",
                "tf_hostname": "app.terraform.io",
            }
            mock_module_class.return_value = mock_module

            # Mock the plan utility functions to avoid actual API calls
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.TerraformClient"), patch(
                "ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_metadata"
            ) as mock_get_metadata, patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_info.get_plan_json_output") as mock_get_json:

                mock_get_metadata.return_value = {"data": {"attributes": {"status": "finished"}}}
                mock_get_json.return_value = {"data": {}}

                # Mock exit_json to raise SystemExit to simulate module exit
                mock_module.exit_json.side_effect = SystemExit({"changed": False})

                with pytest.raises(SystemExit):
                    main()

                # Verify TerraformModule was called with correct argument spec
                expected_argument_spec = {
                    "plan_id": {"type": "str", "aliases": ["id"]},
                    "run_id": {"type": "str"},
                }

                call_args = mock_module_class.call_args
                actual_argument_spec = call_args[1]["argument_spec"]

                assert actual_argument_spec == expected_argument_spec

                # Verify mutually exclusive and requires_one_of settings
                assert call_args[1]["mutually_exclusive"] == [["plan_id", "run_id"]]
                assert call_args[1]["requires_one_of"] == [["plan_id", "run_id"]]
                assert call_args[1]["supports_check_mode"] is True


if __name__ == "__main__":
    unittest.main()
