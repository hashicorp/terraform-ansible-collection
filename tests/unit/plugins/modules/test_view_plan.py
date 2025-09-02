# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import unittest

from unittest.mock import ANY, Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import (
    SENSITIVE_MASK,
    _convert_actions_to_readable_string,
    _create_sensitive_output_values,
    _get_change_indicator_text,
    _has_output_changes,
    _mask_sensitive_object,
    main,
)


class TestViewPlanModule:
    """Unit tests for view_plan module."""

    def test_main_with_plan_id_diff_format_success(self):
        """Test main function with plan_id parameter in diff format success case."""
        params = {
            "plan_id": "plan-123abc456def789",
            "run_id": None,
            "output_format": "diff",
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
                            "before_sensitive": {},
                            "after_sensitive": {},
                        },
                    },
                ],
                "resource_drift": [],
                "output_changes": {},
                "applyable": True,
                "complete": True,
                "errored": False,
            },
            "status": 200,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output",
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            mock_module.exit_json.side_effect = SystemExit({"changed": True})

            with pytest.raises(SystemExit):
                main()

            mock_get_metadata.assert_called_once_with(ANY, "plan-123abc456def789", True)
            mock_get_json.assert_called_once_with(ANY, "plan-123abc456def789", True)

            call_args = mock_module.exit_json.call_args[1]
            expected_keys = {"changed", "diff"}
            assert set(call_args.keys()) == expected_keys
            assert call_args["changed"] is True
            assert isinstance(call_args["diff"], list)

            mock_module.fail_json.assert_not_called()

    def test_main_with_run_id_json_format_success(self):
        """Test main function with run_id parameter in json format success case."""
        params = {
            "plan_id": None,
            "run_id": "run-456def789abc123",
            "output_format": "json",
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
                "resource_drift": [],
                "output_changes": {},
                "applyable": False,
                "complete": True,
                "errored": False,
            },
            "status": 200,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output",
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            mock_module.exit_json.side_effect = SystemExit({"changed": False})

            with pytest.raises(SystemExit):
                main()

            mock_get_metadata.assert_called_once_with(ANY, "run-456def789abc123", False)
            mock_get_json.assert_called_once_with(ANY, "run-456def789abc123", False)

            call_args = mock_module.exit_json.call_args[1]
            expected_keys = {"metadata", "json_output"}
            assert set(call_args.keys()) == expected_keys
            assert call_args["metadata"] == metadata_response["data"]
            assert call_args["json_output"] == json_output_response["data"]

            mock_module.fail_json.assert_not_called()

    def test_main_plan_not_found_with_plan_id(self):
        """Test main function when plan is not found using plan_id."""
        params = {
            "plan_id": "plan-nonexistent123",
            "run_id": None,
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output",
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_module.fail_json.side_effect = SystemExit({"failed": True})

            mock_get_metadata.return_value = {}
            mock_get_json.return_value = {}

            with pytest.raises(SystemExit):
                main()

            mock_module.fail_json.assert_called_once_with(msg="Plan with ID 'plan-nonexistent123' was not found.")
            mock_module.exit_json.assert_not_called()

    def test_main_plan_not_found_with_run_id(self):
        """Test main function when plan is not found using run_id."""
        params = {
            "plan_id": None,
            "run_id": "run-nonexistent456",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output",
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_module.fail_json.side_effect = SystemExit({"failed": True})

            mock_get_metadata.return_value = {}
            mock_get_json.return_value = {}

            with pytest.raises(SystemExit):
                main()

            mock_module.fail_json.assert_called_once_with(msg="Plan for run with ID 'run-nonexistent456' was not found.")

            mock_module.exit_json.assert_not_called()

            mock_get_metadata.assert_called_once_with(ANY, "run-nonexistent456", False)
            mock_get_json.assert_called_once_with(ANY, "run-nonexistent456", False)

    def test_main_no_changes_diff_format(self):
        """Test main function when there are no changes in diff format."""
        params = {
            "plan_id": "plan-nochanges123",
            "run_id": None,
            "output_format": "diff",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        metadata_response = {
            "data": {
                "id": "plan-nochanges123",
                "type": "plans",
                "attributes": {
                    "status": "finished",
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
                "resource_drift": [],
                "output_changes": {},
                "applyable": False,
                "complete": True,
                "errored": False,
            },
            "status": 200,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output",
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            mock_module.exit_json.side_effect = SystemExit({"changed": False})

            with pytest.raises(SystemExit):
                main()

            call_args = mock_module.exit_json.call_args[1]

            expected_keys = {"diff", "msg"}
            assert set(call_args.keys()) == expected_keys
            assert call_args["msg"] == "No changes. Your infrastructure matches the configuration."
            assert len(call_args["diff"]) == 0

            mock_module.fail_json.assert_not_called()

    def test_main_with_resource_changes_and_drift(self):
        """Test main function with both resource changes and drift."""
        params = {
            "plan_id": "plan-complex123",
            "run_id": None,
            "output_format": "diff",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        metadata_response = {
            "data": {
                "id": "plan-complex123",
                "type": "plans",
                "attributes": {
                    "status": "finished",
                    "has_changes": True,
                    "resource_additions": 1,
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
                        "change": {
                            "actions": ["create"],
                            "before": None,
                            "after": {"ami": "ami-12345", "instance_type": "t2.micro"},
                            "before_sensitive": {},
                            "after_sensitive": {},
                        },
                    },
                ],
                "resource_drift": [
                    {
                        "address": "aws_instance.drift",
                        "change": {
                            "actions": ["update"],
                            "before": {"ami": "ami-old"},
                            "after": {"ami": "ami-new"},
                            "before_sensitive": {},
                            "after_sensitive": {},
                        },
                    },
                ],
                "output_changes": {
                    "instance_ip": {
                        "actions": ["create"],
                        "before": None,
                        "after": "192.168.1.1",
                        "before_sensitive": False,
                        "after_sensitive": False,
                    },
                },
            },
            "status": 200,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output",
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            mock_module.exit_json.side_effect = SystemExit({"changed": True})

            with pytest.raises(SystemExit):
                main()

            call_args = mock_module.exit_json.call_args[1]
            assert call_args["changed"] is True
            assert len(call_args["diff"]) > 0

            mock_module.fail_json.assert_not_called()

    def test_main_with_sensitive_values(self):
        """Test main function with sensitive values in diff format."""
        params = {
            "plan_id": "plan-sensitive123",
            "run_id": None,
            "output_format": "diff",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        metadata_response = {
            "data": {
                "id": "plan-sensitive123",
                "type": "plans",
                "attributes": {"status": "finished", "has_changes": True},
            },
            "status": 200,
        }

        json_output_response = {
            "data": {
                "resource_changes": [
                    {
                        "address": "aws_instance.web",
                        "change": {
                            "actions": ["create"],
                            "before": None,
                            "after": {"password": "secret123", "username": "admin"},
                            "before_sensitive": {},
                            "after_sensitive": {"password": True},
                        },
                    },
                ],
                "resource_drift": [],
                "output_changes": {},
            },
            "status": 200,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output",
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            mock_module.exit_json.side_effect = SystemExit({"changed": True})

            with pytest.raises(SystemExit):
                main()

            call_args = mock_module.exit_json.call_args[1]
            assert call_args["changed"] is True
            assert len(call_args["diff"]) > 0

            mock_module.fail_json.assert_not_called()

    def test_main_exception_handling(self):
        """Test main function exception handling."""
        params = {
            "plan_id": "plan-exception123",
            "run_id": None,
            "output_format": "diff",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient",
        ) as mock_client_class, patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output",
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_client_class.side_effect = Exception("Connection failed")

            main()

            mock_module.fail_json.assert_called_once_with(msg="Connection failed")

            mock_module.exit_json.assert_not_called()

            mock_get_metadata.assert_not_called()
            mock_get_json.assert_not_called()

    def test_main_replacement_actions(self):
        """Test main function with replacement actions."""
        params = {
            "plan_id": "plan-replace123",
            "run_id": None,
            "output_format": "diff",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        metadata_response = {
            "data": {
                "id": "plan-replace123",
                "attributes": {"status": "finished", "has_changes": True},
            },
        }

        json_output_response = {
            "data": {
                "resource_changes": [
                    {
                        "address": "aws_instance.web",
                        "change": {
                            "actions": ["delete", "create"],
                            "before": {"ami": "ami-old", "instance_type": "t2.micro"},
                            "after": {"ami": "ami-new", "instance_type": "t2.micro"},
                            "before_sensitive": {},
                            "after_sensitive": {},
                        },
                    },
                ],
                "resource_drift": [],
                "output_changes": {},
            },
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output",
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            mock_module.exit_json.side_effect = SystemExit({"changed": True})

            with pytest.raises(SystemExit):
                main()

            call_args = mock_module.exit_json.call_args[1]
            assert call_args["changed"] is True
            assert len(call_args["diff"]) > 0

    def test_main_noop_actions(self):
        """Test main function with no-op actions."""
        params = {
            "plan_id": "plan-noop123",
            "run_id": None,
            "output_format": "diff",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        metadata_response = {
            "data": {
                "id": "plan-noop123",
                "attributes": {"status": "finished", "has_changes": False},
            },
        }

        json_output_response = {
            "data": {
                "resource_changes": [
                    {
                        "address": "aws_instance.web",
                        "change": {
                            "actions": ["no-op"],
                            "before": {"ami": "ami-123", "instance_type": "t2.micro"},
                            "after": {"ami": "ami-123", "instance_type": "t2.micro"},
                            "before_sensitive": {},
                            "after_sensitive": {},
                        },
                    },
                ],
                "resource_drift": [],
                "output_changes": {},
            },
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output",
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = metadata_response
            mock_get_json.return_value = json_output_response

            mock_module.exit_json.side_effect = SystemExit({"changed": False})

            with pytest.raises(SystemExit):
                main()

            call_args = mock_module.exit_json.call_args[1]

            expected_keys = {"diff", "msg"}
            assert set(call_args.keys()) == expected_keys
            assert call_args["msg"] == "No changes. Your infrastructure matches the configuration."

    def test_module_argument_spec(self):
        """Test that the module has correct argument specification."""
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class:
            mock_module = Mock()
            mock_module.params = {
                "plan_id": "plan-test123",
                "run_id": None,
                "output_format": "diff",
                "tf_token": "test-token",
                "tf_hostname": "app.terraform.io",
            }
            mock_module_class.return_value = mock_module

            with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient"), patch(
                "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata",
            ) as mock_get_metadata, patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output") as mock_get_json:

                mock_get_metadata.return_value = {"data": {"attributes": {"status": "finished"}}}
                mock_get_json.return_value = {"data": {"resource_changes": [], "resource_drift": [], "output_changes": {}}}

                mock_module.exit_json.side_effect = SystemExit({"changed": False})

                with pytest.raises(SystemExit):
                    main()

                expected_argument_spec = {
                    "plan_id": {"type": "str", "aliases": ["id"]},
                    "run_id": {"type": "str"},
                    "output_format": {"type": "str", "choices": ["diff", "json"], "default": "diff"},
                }

                call_args = mock_module_class.call_args
                actual_argument_spec = call_args[1]["argument_spec"]

                assert actual_argument_spec == expected_argument_spec

                assert call_args[1]["mutually_exclusive"] == [["plan_id", "run_id"]]
                assert call_args[1]["required_one_of"] == [["plan_id", "run_id"]]
                assert call_args[1]["supports_check_mode"] is True

                mock_module.exit_json.assert_called_once()
                mock_module.fail_json.assert_not_called()

                mock_get_metadata.assert_called_once()
                mock_get_json.assert_called_once()


class TestHelperFunctions:
    """Unit tests for helper functions."""

    def test_mask_sensitive_object_dict(self):
        """Test masking sensitive values in a dictionary."""
        data = {"username": "john", "password": "secret123", "config": {"api_key": "key123"}}
        sensitive_flags = {"password": True, "config": {"api_key": True}}

        result = _mask_sensitive_object(data, sensitive_flags)

        expected = {"username": "john", "password": SENSITIVE_MASK, "config": {"api_key": SENSITIVE_MASK}}
        assert result == expected

    def test_mask_sensitive_object_list(self):
        """Test masking sensitive values in a list."""
        data = ["value1", "value2", "value3"]
        sensitive_flags = {}

        result = _mask_sensitive_object(data, sensitive_flags)

        assert result == data

    def test_mask_sensitive_object_simple_value(self):
        """Test masking a simple value."""
        data = "simple_value"
        sensitive_flags = {}

        result = _mask_sensitive_object(data, sensitive_flags)

        assert result == data

    def test_get_change_indicator_text_not_sensitive(self):
        """Test change indicator when values are not sensitive."""
        before_text, after_text = _get_change_indicator_text("old", "new", False, False)

        assert before_text is None
        assert after_text is None

    def test_get_change_indicator_text_sensitive_changed(self):
        """Test change indicator when sensitive values changed."""
        before_text, after_text = _get_change_indicator_text("old", "new", True, True)

        assert before_text == "<sensitive> changed from"
        assert after_text == "<sensitive> changed to"

    def test_get_change_indicator_text_sensitive_unchanged(self):
        """Test change indicator when sensitive values unchanged."""
        before_text, after_text = _get_change_indicator_text("same", "same", True, True)

        assert before_text == SENSITIVE_MASK
        assert after_text == SENSITIVE_MASK

    def test_convert_actions_to_readable_string(self):
        """Test converting action lists to readable strings."""
        # Test single actions
        assert _convert_actions_to_readable_string(["create"]) == "created"
        assert _convert_actions_to_readable_string(["update"]) == "updated"
        assert _convert_actions_to_readable_string(["delete"]) == "destroyed"
        assert _convert_actions_to_readable_string(["read"]) == "read"

        # Test replacement actions
        assert _convert_actions_to_readable_string(["delete", "create"]) == "replaced"
        assert _convert_actions_to_readable_string(["create", "delete"]) == "replaced"

        # Test complex update actions
        assert _convert_actions_to_readable_string(["update", "create"]) == "updated (create, update)"

        # Test empty list
        assert _convert_actions_to_readable_string([]) == "no-op"

        # Test unknown action
        assert _convert_actions_to_readable_string(["unknown"]) == "unknown"

    def test_has_output_changes(self):
        """Test checking for output changes."""
        # No-op action
        change_noop = {"actions": ["no-op"], "before": "value", "after": "value"}
        assert _has_output_changes(change_noop) is False

        # Actual change
        change_real = {"actions": ["update"], "before": "old", "after": "new"}
        assert _has_output_changes(change_real) is True

        # Same values
        change_same = {"actions": ["update"], "before": "value", "after": "value"}
        assert _has_output_changes(change_same) is False

    def test_create_sensitive_output_values(self):
        """Test creating sensitive output values."""
        # Non-sensitive values
        change = {"before": "old", "after": "new", "before_sensitive": False, "after_sensitive": False}
        before_val, after_val = _create_sensitive_output_values(change)
        assert before_val == "old"
        assert after_val == "new"

        # Sensitive values
        change_sensitive = {"before": "old", "after": "new", "before_sensitive": True, "after_sensitive": True}
        before_val, after_val = _create_sensitive_output_values(change_sensitive)
        assert before_val == "<sensitive> changed from"
        assert after_val == "<sensitive> changed to"

    def test_mask_sensitive_object_nested_dict(self):
        """Test masking nested sensitive values in dictionaries."""
        data = {
            "database": {"password": "secret", "host": "localhost"},
            "api_key": "key123",
            "tags": {"Environment": "prod"},
        }
        sensitive_flags = {"database": {"password": True}, "api_key": True}

        result = _mask_sensitive_object(data, sensitive_flags)

        expected = {
            "database": {"password": SENSITIVE_MASK, "host": "localhost"},
            "api_key": SENSITIVE_MASK,
            "tags": {"Environment": "prod"},
        }
        assert result == expected

    def test_mask_sensitive_object_mixed_types(self):
        """Test masking with mixed data types."""
        data = {
            "string_val": "test",
            "dict_val": {"key": "value"},
            "list_val": ["item1", "item2"],
            "null_val": None,
        }
        sensitive_flags = {"string_val": True, "dict_val": {"key": True}}

        result = _mask_sensitive_object(data, sensitive_flags)

        expected = {
            "string_val": SENSITIVE_MASK,
            "dict_val": {"key": SENSITIVE_MASK},
            "list_val": ["item1", "item2"],
            "null_val": None,
        }
        assert result == expected

    def test_convert_actions_edge_cases(self):
        """Test edge cases for action conversion."""
        # Multiple actions that aren't replacements
        assert "updated" in _convert_actions_to_readable_string(["update", "read"])

        # Single action mapping
        assert _convert_actions_to_readable_string(["delete"]) == "destroyed"

        # Multiple mixed actions
        result = _convert_actions_to_readable_string(["create", "update", "read"])
        assert "updated" in result and "(" in result

    def test_sensitive_output_values_edge_cases(self):
        """Test edge cases for sensitive output values."""
        # Only before is sensitive
        change = {"before": "old", "after": "new", "before_sensitive": True, "after_sensitive": False}
        before_val, after_val = _create_sensitive_output_values(change)
        assert before_val == "<sensitive> changed from"
        assert after_val == "new"

        # Only after is sensitive
        change = {"before": "old", "after": "new", "before_sensitive": False, "after_sensitive": True}
        before_val, after_val = _create_sensitive_output_values(change)
        assert before_val == "old"
        assert after_val == "<sensitive> changed to"

        # Missing values
        change = {"before": None, "after": "new", "before_sensitive": False, "after_sensitive": False}
        before_val, after_val = _create_sensitive_output_values(change)
        assert before_val is None
        assert after_val == "new"

    def test_create_unified_resources_changes_only(self):
        """Test unifying resources with changes only."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _create_unified_resources

        resource_changes = [
            {
                "address": "aws_instance.web",
                "change": {"actions": ["create"], "before": None, "after": {"ami": "ami-123"}},
            },
        ]
        resource_drift = []

        result = _create_unified_resources(resource_changes, resource_drift)

        assert len(result) == 1
        assert result[0].address == "aws_instance.web"
        assert result[0].resource_changes is not None
        assert result[0].resource_drift is None
        assert result[0].has_drift is False

    def test_create_unified_resources_drift_only(self):
        """Test unifying resources with drift only."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _create_unified_resources

        resource_changes = []
        resource_drift = [
            {
                "address": "aws_instance.drift",
                "change": {"actions": ["update"], "before": {"ami": "old"}, "after": {"ami": "new"}},
            },
        ]

        result = _create_unified_resources(resource_changes, resource_drift)

        assert len(result) == 1
        assert result[0].address == "aws_instance.drift"
        assert result[0].resource_changes is None
        assert result[0].resource_drift is not None
        assert result[0].has_drift is True

    def test_create_unified_resources_both(self):
        """Test unifying resources with both changes and drift."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _create_unified_resources

        resource_changes = [
            {
                "address": "aws_instance.both",
                "change": {"actions": ["update"], "before": {"size": "small"}, "after": {"size": "large"}},
            },
        ]
        resource_drift = [
            {
                "address": "aws_instance.both",
                "change": {"actions": ["update"], "before": {"ami": "old"}, "after": {"ami": "new"}},
            },
        ]

        result = _create_unified_resources(resource_changes, resource_drift)

        assert len(result) == 1
        assert result[0].address == "aws_instance.both"
        assert result[0].resource_changes is not None
        assert result[0].resource_drift is not None
        assert result[0].has_drift is True

    def test_determine_primary_item_and_scenario_changes_with_actions(self):
        """Test scenario determination for changes with actions."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import (
            ResourceData,
            _determine_primary_item_and_scenario,
        )

        changes_item = {
            "change": {"actions": ["create"], "before": None, "after": {"ami": "ami-123"}},
        }
        resource_data = ResourceData(
            address="aws_instance.web",
            resource_changes=changes_item,
            resource_drift=None,
            has_drift=False,
        )

        item, scenario = _determine_primary_item_and_scenario(resource_data)

        assert item == changes_item
        assert scenario == "changes_with_actions"

    def test_determine_primary_item_and_scenario_drift_only(self):
        """Test scenario determination for drift only."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import (
            ResourceData,
            _determine_primary_item_and_scenario,
        )

        drift_item = {
            "change": {"actions": ["update"], "before": {"ami": "old"}, "after": {"ami": "new"}},
        }
        resource_data = ResourceData(
            address="aws_instance.drift",
            resource_changes=None,
            resource_drift=drift_item,
            has_drift=True,
        )

        item, scenario = _determine_primary_item_and_scenario(resource_data)

        assert item == drift_item
        assert scenario == "drift_only"

    def test_determine_primary_item_no_actions(self):
        """Test scenario determination with no meaningful actions."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import (
            ResourceData,
            _determine_primary_item_and_scenario,
        )

        changes_item = {
            "change": {"actions": ["no-op"], "before": {"ami": "ami-123"}, "after": {"ami": "ami-123"}},
        }
        resource_data = ResourceData(
            address="aws_instance.noop",
            resource_changes=changes_item,
            resource_drift=None,
            has_drift=False,
        )

        item, scenario = _determine_primary_item_and_scenario(resource_data)

        assert item is None
        assert scenario is None

    def test_create_diff_headers_drift_only(self):
        """Test header creation for drift-only scenario."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _create_diff_headers

        headers = _create_diff_headers(
            "drift_only",
            "aws_instance.drift",
            "i-123456789",
            "updated",
            True,
            {"change": {"actions": ["update"]}},
        )

        assert "Resource changed outside Terraform" in headers["before_header"]
        assert "Drift detected" in headers["after_header"]
        assert "aws_instance.drift" in headers["after_header"]
        assert "(ID=i-123456789)" in headers["after_header"]

    def test_create_diff_headers_changes_with_drift(self):
        """Test header creation for changes with drift scenario."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _create_diff_headers

        headers = _create_diff_headers(
            "changes_with_actions",
            "aws_instance.web",
            "i-987654321",
            "created",
            True,
            {"change": {"actions": ["update"]}},
        )

        assert "Resource changed outside Terraform" in headers["before_header"]
        assert "will be created" in headers["after_header"]
        assert "Changes to apply" in headers["after_header"]

    def test_update_changed_sensitive_values_complex(self):
        """Test complex sensitive value updates."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _update_changed_sensitive_values

        before_obj = {"password": "<sensitive>", "username": "admin", "config": {"api_key": "<sensitive>"}}
        after_obj = {"password": "<sensitive>", "username": "admin", "config": {"api_key": "<sensitive>"}}
        before_sensitive = {"password": True, "config": {"api_key": True}}
        after_sensitive = {"password": True, "config": {"api_key": True}}
        before_raw = {"password": "old_secret", "username": "admin", "config": {"api_key": "old_key"}}
        after_raw = {"password": "new_secret", "username": "admin", "config": {"api_key": "new_key"}}

        result_before, result_after = _update_changed_sensitive_values(
            before_obj,
            after_obj,
            before_sensitive,
            after_sensitive,
            before_raw,
            after_raw,
        )

        # Check that changed sensitive values show indicators
        assert result_before["password"] == "<sensitive> changed from"
        assert result_after["password"] == "<sensitive> changed to"
        assert result_before["config"]["api_key"] == "<sensitive> changed from"
        assert result_after["config"]["api_key"] == "<sensitive> changed to"
        # Non-sensitive unchanged values remain the same
        assert result_before["username"] == "admin"
        assert result_after["username"] == "admin"

    def test_mask_sensitive_values_in_objects_integration(self):
        """Test the main sensitive masking function."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _mask_sensitive_values_in_objects

        before_obj = {"password": "old_secret", "username": "admin"}
        after_obj = {"password": "new_secret", "username": "admin"}
        before_sensitive = {"password": True}
        after_sensitive = {"password": True}

        masked_before, masked_after = _mask_sensitive_values_in_objects(
            before_obj,
            after_obj,
            before_sensitive,
            after_sensitive,
        )

        # Should show change indicators for changed sensitive values
        assert masked_before["password"] == "<sensitive> changed from"
        assert masked_after["password"] == "<sensitive> changed to"
        # Non-sensitive values should remain unchanged
        assert masked_before["username"] == "admin"
        assert masked_after["username"] == "admin"

    def test_create_diff_entry_complete(self):
        """Test complete diff entry creation."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import (
            ResourceData,
            _create_diff_entry,
        )

        changes_item = {
            "change": {
                "actions": ["create"],
                "before": None,
                "after": {"ami": "ami-123", "instance_type": "t2.micro", "id": "i-123456"},
                "before_sensitive": {},
                "after_sensitive": {},
            },
        }

        resource_data = ResourceData(
            address="aws_instance.web",
            resource_changes=changes_item,
            resource_drift=None,
            has_drift=False,
        )

        result = _create_diff_entry(resource_data)

        assert result is not None
        assert result["before"] is None
        assert result["after"] == {"ami": "ami-123", "instance_type": "t2.micro", "id": "i-123456"}
        assert "after_header" in result
        assert "will be created" in result["after_header"]
        assert "aws_instance.web" in result["after_header"]

    def test_get_diff_sequences_integration(self):
        """Test the main diff sequence extraction function."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _get_diff_sequences

        json_output_data = {
            "resource_changes": [
                {
                    "address": "aws_instance.web",
                    "change": {
                        "actions": ["create"],
                        "before": None,
                        "after": {"ami": "ami-123"},
                        "before_sensitive": {},
                        "after_sensitive": {},
                    },
                },
            ],
            "resource_drift": [
                {
                    "address": "aws_instance.drift",
                    "change": {
                        "actions": ["update"],
                        "before": {"ami": "old"},
                        "after": {"ami": "new"},
                        "before_sensitive": {},
                        "after_sensitive": {},
                    },
                },
            ],
            "output_changes": {
                "instance_ip": {
                    "actions": ["create"],
                    "before": None,
                    "after": "192.168.1.1",
                    "before_sensitive": False,
                    "after_sensitive": False,
                },
            },
        }

        diffs = _get_diff_sequences(json_output_data)

        assert len(diffs) >= 2

        for diff in diffs:
            assert "before" in diff or "after" in diff
            if "after_header" in diff:
                assert isinstance(diff["after_header"], str)

    def test_process_output_changes_sensitive(self):
        """Test output changes with sensitive values."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _process_output_changes

        output_changes = {
            "db_password": {
                "actions": ["create"],
                "before": None,
                "after": "secret123",
                "before_sensitive": False,
                "after_sensitive": True,
            },
            "instance_ip": {
                "actions": ["update"],
                "before": "1.1.1.1",
                "after": "2.2.2.2",
                "before_sensitive": False,
                "after_sensitive": False,
            },
        }

        diffs = _process_output_changes(output_changes)

        assert len(diffs) == 2

        sensitive_diff = next(d for d in diffs if "db_password" in str(d))
        assert "db_password" in sensitive_diff["after"]

        normal_diff = next(d for d in diffs if "instance_ip" in str(d))
        assert normal_diff["before"]["instance_ip"] == "1.1.1.1"
        assert normal_diff["after"]["instance_ip"] == "2.2.2.2"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_resource_data(self):
        """Test handling of empty resource data."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _get_diff_sequences

        json_output_data = {
            "resource_changes": [],
            "resource_drift": [],
            "output_changes": {},
        }

        diffs = _get_diff_sequences(json_output_data)
        assert diffs == []

    def test_malformed_change_data(self):
        """Test handling of malformed change data."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import ResourceData, _create_diff_entry

        malformed_item = {"address": "aws_instance.bad"}

        resource_data = ResourceData(
            address="aws_instance.bad",
            resource_changes=malformed_item,
            resource_drift=None,
            has_drift=False,
        )

        result = _create_diff_entry(resource_data)
        assert result is None

    def test_nested_sensitive_structures(self):
        """Test deeply nested sensitive structures."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _mask_sensitive_object

        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "secret": "value",
                        "normal": "value",
                    },
                },
            },
        }

        sensitive_flags = {
            "level1": {
                "level2": {
                    "level3": {
                        "secret": True,
                    },
                },
            },
        }

        result = _mask_sensitive_object(data, sensitive_flags)

        assert result["level1"]["level2"]["level3"]["secret"] == "<sensitive>"
        assert result["level1"]["level2"]["level3"]["normal"] == "value"


class TestFixedMainTests:
    """Corrected versions of problematic main tests."""

    def test_main_with_plan_id_diff_format_fixed(self):
        """Fixed version of main test with proper mock setup."""
        params = {
            "plan_id": "plan-123abc456def789",
            "run_id": None,
            "output_format": "diff",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata") as mock_get_metadata, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output",
        ) as mock_get_json:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_get_metadata.return_value = {"data": {"attributes": {"status": "finished"}}}
            mock_get_json.return_value = {
                "data": {
                    "resource_changes": [
                        {
                            "address": "aws_instance.web",
                            "change": {
                                "actions": ["create"],
                                "before": None,
                                "after": {"ami": "ami-123"},
                                "before_sensitive": {},
                                "after_sensitive": {},
                            },
                        },
                    ],
                    "resource_drift": [],
                    "output_changes": {},
                },
            }

            captured_result = {}

            def capture_exit(**kwargs):
                captured_result.update(kwargs)
                raise SystemExit(0)

            mock_module.exit_json.side_effect = capture_exit

            with pytest.raises(SystemExit):
                main()

            assert captured_result["changed"] is True
            assert "diff" in captured_result
            assert len(captured_result["diff"]) > 0

            mock_module.fail_json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
