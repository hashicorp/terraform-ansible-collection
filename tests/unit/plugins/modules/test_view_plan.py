# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import unittest

from unittest.mock import ANY, Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import (
    SENSITIVE_MASK,
    _convert_actions_to_readable_string,
    _create_sensitive_output_values,
    _get_change_indicator_text,
    _has_output_changes,
    _mask_sensitive_object,
    main,
)


class TestViewPlanModule(unittest.TestCase):
    """Unit tests for view_plan module."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule")
    def test_main_with_plan_id_diff_format_success(self, mock_module_class, mock_client_class, mock_get_metadata, mock_get_json):
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

        mock_module = Mock()
        mock_module.params = params
        mock_module_class.return_value = mock_module
        mock_get_metadata.return_value = metadata_response
        mock_get_json.return_value = json_output_response

        mock_module.exit_json.side_effect = SystemExit({"changed": True})

        with self.assertRaises(SystemExit):
            main()

        mock_get_metadata.assert_called_once_with(ANY, "plan-123abc456def789", True)
        mock_get_json.assert_called_once_with(ANY, "plan-123abc456def789", True)

        call_args = mock_module.exit_json.call_args[1]
        expected_keys = {"changed", "diff"}
        self.assertEqual(set(call_args.keys()), expected_keys)
        self.assertTrue(call_args["changed"])
        self.assertIsInstance(call_args["diff"], list)

        mock_module.fail_json.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule")
    def test_main_with_run_id_json_format_success(self, mock_module_class, mock_client_class, mock_get_metadata, mock_get_json):
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

        mock_module = Mock()
        mock_module.params = params
        mock_module_class.return_value = mock_module
        mock_get_metadata.return_value = metadata_response
        mock_get_json.return_value = json_output_response

        mock_module.exit_json.side_effect = SystemExit({"changed": False})

        with self.assertRaises(SystemExit):
            main()

        mock_get_metadata.assert_called_once_with(ANY, "run-456def789abc123", False)
        mock_get_json.assert_called_once_with(ANY, "run-456def789abc123", False)

        call_args = mock_module.exit_json.call_args[1]
        expected_keys = {"metadata", "json_output"}
        self.assertEqual(set(call_args.keys()), expected_keys)
        self.assertEqual(call_args["metadata"], metadata_response["data"])
        self.assertEqual(call_args["json_output"], json_output_response["data"])

        mock_module.fail_json.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule")
    def test_main_plan_not_found_with_plan_id(self, mock_module_class, mock_client_class, mock_get_metadata, mock_get_json):
        """Test main function when plan is not found using plan_id."""
        params = {
            "plan_id": "plan-nonexistent123",
            "run_id": None,
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        mock_module = Mock()
        mock_module.params = params
        mock_module_class.return_value = mock_module
        mock_module.fail_json.side_effect = SystemExit({"failed": True})
        mock_get_metadata.return_value = {}
        mock_get_json.return_value = {}

        with self.assertRaises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once_with(msg="Plan with ID 'plan-nonexistent123' was not found.")
        mock_module.exit_json.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule")
    def test_main_plan_not_found_with_run_id(self, mock_module_class, mock_client_class, mock_get_metadata, mock_get_json):
        """Test main function when plan is not found using run_id."""
        params = {
            "plan_id": None,
            "run_id": "run-nonexistent456",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        mock_module = Mock()
        mock_module.params = params
        mock_module_class.return_value = mock_module
        mock_module.fail_json.side_effect = SystemExit({"failed": True})
        mock_get_metadata.return_value = {}
        mock_get_json.return_value = {}

        with self.assertRaises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once_with(msg="Plan for run with ID 'run-nonexistent456' was not found.")
        mock_module.exit_json.assert_not_called()
        mock_get_metadata.assert_called_once_with(ANY, "run-nonexistent456", False)
        mock_get_json.assert_called_once_with(ANY, "run-nonexistent456", False)

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule")
    def test_main_no_changes_diff_format(self, mock_module_class, mock_client_class, mock_get_metadata, mock_get_json):
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

        mock_module = Mock()
        mock_module.params = params
        mock_module_class.return_value = mock_module
        mock_get_metadata.return_value = metadata_response
        mock_get_json.return_value = json_output_response
        mock_module.exit_json.side_effect = SystemExit({"changed": False})

        with self.assertRaises(SystemExit):
            main()

        call_args = mock_module.exit_json.call_args[1]
        expected_keys = {"diff", "msg"}
        self.assertEqual(set(call_args.keys()), expected_keys)
        self.assertEqual(call_args["msg"], "No changes. Your infrastructure matches the configuration.")
        self.assertEqual(len(call_args["diff"]), 0)

        mock_module.fail_json.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule")
    def test_main_exception_handling(self, mock_module_class, mock_client_class):
        """Test main function exception handling."""
        params = {
            "plan_id": "plan-exception123",
            "run_id": None,
            "output_format": "diff",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        mock_module = Mock()
        mock_module.params = params
        mock_module_class.return_value = mock_module
        mock_client_class.side_effect = Exception("Connection failed")

        main()

        mock_module.fail_json.assert_called_once_with(msg="Connection failed")
        mock_module.exit_json.assert_not_called()


class TestHelperFunctions(unittest.TestCase):
    """Unit tests for helper functions."""

    def test_mask_sensitive_object_dict(self):
        """Test masking sensitive values in a dictionary."""
        data = {"username": "john", "password": "secret123", "config": {"api_key": "key123"}}
        sensitive_flags = {"password": True, "config": {"api_key": True}}

        result = _mask_sensitive_object(data, sensitive_flags)

        expected = {"username": "john", "password": SENSITIVE_MASK, "config": {"api_key": SENSITIVE_MASK}}
        self.assertEqual(result, expected)

    def test_mask_sensitive_object_list(self):
        """Test masking sensitive values in a list."""
        data = ["value1", "value2", "value3"]
        sensitive_flags = {}

        result = _mask_sensitive_object(data, sensitive_flags)

        self.assertEqual(result, data)

    def test_mask_sensitive_object_simple_value(self):
        """Test masking a simple value."""
        data = "simple_value"
        sensitive_flags = {}

        result = _mask_sensitive_object(data, sensitive_flags)

        self.assertEqual(result, data)

    def test_get_change_indicator_text_not_sensitive(self):
        """Test change indicator when values are not sensitive."""
        before_text, after_text = _get_change_indicator_text("old", "new", False, False)

        self.assertIsNone(before_text)
        self.assertIsNone(after_text)

    def test_get_change_indicator_text_sensitive_changed(self):
        """Test change indicator when sensitive values changed."""
        before_text, after_text = _get_change_indicator_text("old", "new", True, True)

        self.assertEqual(before_text, "<sensitive> changed from")
        self.assertEqual(after_text, "<sensitive> changed to")

    def test_get_change_indicator_text_sensitive_unchanged(self):
        """Test change indicator when sensitive values unchanged."""
        before_text, after_text = _get_change_indicator_text("same", "same", True, True)

        self.assertEqual(before_text, SENSITIVE_MASK)
        self.assertEqual(after_text, SENSITIVE_MASK)

    def test_convert_actions_to_readable_string(self):
        """Test converting action lists to readable strings."""
        # Test single actions
        self.assertEqual(_convert_actions_to_readable_string(["create"]), "created")
        self.assertEqual(_convert_actions_to_readable_string(["update"]), "updated")
        self.assertEqual(_convert_actions_to_readable_string(["delete"]), "destroyed")
        self.assertEqual(_convert_actions_to_readable_string(["read"]), "read")

        # Test replacement actions
        self.assertEqual(_convert_actions_to_readable_string(["delete", "create"]), "replaced")
        self.assertEqual(_convert_actions_to_readable_string(["create", "delete"]), "replaced")

        # Test complex update actions
        self.assertEqual(_convert_actions_to_readable_string(["update", "create"]), "updated (create, update)")

        # Test empty list
        self.assertEqual(_convert_actions_to_readable_string([]), "no-op")

        # Test unknown action
        self.assertEqual(_convert_actions_to_readable_string(["unknown"]), "unknown")

    def test_has_output_changes(self):
        """Test checking for output changes."""
        # No-op action
        change_noop = {"actions": ["no-op"], "before": "value", "after": "value"}
        self.assertFalse(_has_output_changes(change_noop))

        # Actual change
        change_real = {"actions": ["update"], "before": "old", "after": "new"}
        self.assertTrue(_has_output_changes(change_real))

        # Same values
        change_same = {"actions": ["update"], "before": "value", "after": "value"}
        self.assertFalse(_has_output_changes(change_same))

    def test_create_sensitive_output_values(self):
        """Test creating sensitive output values."""
        # Non-sensitive values
        change = {"before": "old", "after": "new", "before_sensitive": False, "after_sensitive": False}
        before_val, after_val = _create_sensitive_output_values(change)
        self.assertEqual(before_val, "old")
        self.assertEqual(after_val, "new")

        # Sensitive values
        change_sensitive = {"before": "old", "after": "new", "before_sensitive": True, "after_sensitive": True}
        before_val, after_val = _create_sensitive_output_values(change_sensitive)
        self.assertEqual(before_val, "<sensitive> changed from")
        self.assertEqual(after_val, "<sensitive> changed to")


if __name__ == "__main__":
    unittest.main()
