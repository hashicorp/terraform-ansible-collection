# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import unittest

from unittest.mock import ANY, patch

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


class EnhancedDummyModule:
    """Enhanced mock Ansible module for detailed test inspection and control."""

    def __init__(self, params=None):
        self.params = params or {}
        self.failed = False
        self.exit_args = None
        self.fail_args = None
        self.check_mode = False

    def fail_json(self, **kwargs):
        self.failed = True
        self.fail_args = kwargs
        raise AssertionError(kwargs.get("msg", "fail_json called with no message"))

    def exit_json(self, **kwargs):
        self.exit_args = kwargs
        raise SystemExit(kwargs)


class TestViewPlanModule:
    """Unit tests for view_plan module main function."""

    @pytest.mark.parametrize(
        "params,metadata_response,json_response,expected_keys,expected_changed",
        [
            (
                {
                    "plan_id": "plan-123abc456def789",
                    "run_id": None,
                    "output_format": "diff",
                    "tf_token": "test-token",
                    "tf_hostname": "app.terraform.io",
                },
                {
                    "data": {
                        "id": "plan-123abc456def789",
                        "type": "plans",
                        "attributes": {"status": "finished", "has_changes": True},
                    },
                },
                {
                    "data": {
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
                        "resource_drift": [],
                        "output_changes": {},
                    },
                },
                {"changed", "diff"},
                True,
            ),
            (
                {
                    "plan_id": None,
                    "run_id": "run-456def789abc123",
                    "output_format": "json",
                    "tf_token": "test-token",
                    "tf_hostname": "app.terraform.io",
                },
                {"data": {"id": "plan-789", "attributes": {"status": "planning"}}},
                {"data": {"resource_changes": [], "resource_drift": [], "output_changes": {}}},
                {"metadata", "json_output"},
                None,
            ),
            (
                {
                    "plan_id": "plan-nochanges123",
                    "run_id": None,
                    "output_format": "diff",
                    "tf_token": "test-token",
                    "tf_hostname": "app.terraform.io",
                },
                {"data": {"id": "plan-nochanges123", "attributes": {"status": "finished"}}},
                {"data": {"resource_changes": [], "resource_drift": [], "output_changes": {}}},
                {"diff", "msg"},
                None,
            ),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule")
    def test_main_success_scenarios(
        self,
        mock_module_class,
        mock_client,
        mock_get_metadata,
        mock_get_json,
        params,
        metadata_response,
        json_response,
        expected_keys,
        expected_changed,
    ):
        """Test main function with various success scenarios."""
        mock_module = EnhancedDummyModule(params)
        mock_module_class.return_value = mock_module

        mock_get_metadata.return_value = metadata_response
        mock_get_json.return_value = json_response

        with pytest.raises(SystemExit):
            main()

        call_args = mock_module.exit_args
        assert set(call_args.keys()) == expected_keys

        if expected_changed is not None:
            assert call_args["changed"] is expected_changed

        if "msg" in expected_keys:
            assert call_args["msg"] == "No changes. Your infrastructure matches the configuration."

        assert not mock_module.failed

    @pytest.mark.parametrize(
        "plan_id,run_id,use_plan_id,expected_msg",
        [
            ("plan-nonexistent123", None, True, "Plan with ID 'plan-nonexistent123' was not found."),
            (None, "run-nonexistent456", False, "Plan for run with ID 'run-nonexistent456' was not found."),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule")
    def test_main_plan_not_found(
        self,
        mock_module_class,
        mock_client,
        mock_get_metadata,
        mock_get_json,
        plan_id,
        run_id,
        use_plan_id,
        expected_msg,
    ):
        """Test main function when plan is not found."""
        params = {
            "plan_id": plan_id,
            "run_id": run_id,
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        mock_module = EnhancedDummyModule(params)
        mock_module_class.return_value = mock_module

        mock_get_metadata.return_value = {}
        mock_get_json.return_value = {}

        with pytest.raises(AssertionError) as exc_info:
            main()

        assert expected_msg in str(exc_info.value)
        assert mock_module.failed
        assert mock_module.fail_args["msg"] == expected_msg

        identifier = plan_id if use_plan_id else run_id
        mock_get_metadata.assert_called_once_with(ANY, identifier, use_plan_id)

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule")
    def test_main_exception_handling(self, mock_module_class, mock_client_class):
        """Test main function exception handling."""
        params = {"plan_id": "plan-exception123", "run_id": None, "tf_token": "test-token"}

        mock_module = EnhancedDummyModule(params)
        mock_module_class.return_value = mock_module

        mock_client_class.side_effect = Exception("Connection failed")

        with pytest.raises(AssertionError) as exc_info:
            main()

        assert "Connection failed" in str(exc_info.value)
        assert mock_module.failed
        assert mock_module.fail_args["msg"] == "Connection failed"

    @pytest.mark.parametrize(
        "scenario,json_data,expected_diff_count",
        [
            (
                "changes_and_drift",
                {
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
                3,
            ),
            (
                "sensitive_values",
                {
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
                1,
            ),
            (
                "replacement_actions",
                {
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
                1,
            ),
            (
                "noop_actions",
                {
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
                0,
            ),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule")
    def test_main_complex_scenarios(
        self,
        mock_module_class,
        mock_client,
        mock_get_metadata,
        mock_get_json,
        scenario,
        json_data,
        expected_diff_count,
    ):
        """Test main function with complex data scenarios."""
        params = {
            "plan_id": f"plan-{scenario}123",
            "run_id": None,
            "output_format": "diff",
            "tf_token": "test-token",
            "tf_hostname": "app.terraform.io",
        }

        mock_module = EnhancedDummyModule(params)
        mock_module_class.return_value = mock_module

        metadata_response = {"data": {"id": f"plan-{scenario}123", "attributes": {"status": "finished"}}}
        json_output_response = {"data": json_data}

        mock_get_metadata.return_value = metadata_response
        mock_get_json.return_value = json_output_response

        with pytest.raises(SystemExit):
            main()

        call_args = mock_module.exit_args

        if expected_diff_count > 0:
            assert call_args["changed"] is True
            assert len(call_args["diff"]) >= expected_diff_count
        else:
            assert "msg" in call_args
            assert call_args["msg"] == "No changes. Your infrastructure matches the configuration."

        assert not mock_module.failed

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.AnsibleTerraformModule")
    def test_module_argument_spec(self, mock_module_class):
        """Test that the module has correct argument specification."""
        mock_module = EnhancedDummyModule(
            {
                "plan_id": "plan-test123",
                "run_id": None,
                "output_format": "diff",
                "tf_token": "test-token",
                "tf_hostname": "app.terraform.io",
            },
        )
        mock_module_class.return_value = mock_module

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.TerraformClient"), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_metadata",
        ) as mock_get_metadata, patch("ansible_collections.hashicorp.terraform.plugins.modules.view_plan.get_plan_json_output") as mock_get_json:

            mock_get_metadata.return_value = {"data": {"attributes": {"status": "finished"}}}
            mock_get_json.return_value = {"data": {"resource_changes": [], "resource_drift": [], "output_changes": {}}}

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


class TestHelperFunctions:
    """Unit tests for helper functions."""

    @pytest.mark.parametrize(
        "data,sensitive_flags,expected",
        [
            (
                {"username": "john", "password": "secret123", "config": {"api_key": "key123"}},
                {"password": True, "config": {"api_key": True}},
                {"username": "john", "password": SENSITIVE_MASK, "config": {"api_key": SENSITIVE_MASK}},
            ),
            (
                {
                    "database": {"password": "secret", "host": "localhost"},
                    "api_key": "key123",
                    "tags": {"Environment": "prod"},
                },
                {"database": {"password": True}, "api_key": True},
                {
                    "database": {"password": SENSITIVE_MASK, "host": "localhost"},
                    "api_key": SENSITIVE_MASK,
                    "tags": {"Environment": "prod"},
                },
            ),
            (
                {
                    "string_val": "test",
                    "dict_val": {"key": "value"},
                    "list_val": ["item1", "item2"],
                    "null_val": None,
                },
                {"string_val": True, "dict_val": {"key": True}},
                {
                    "string_val": SENSITIVE_MASK,
                    "dict_val": {"key": SENSITIVE_MASK},
                    "list_val": ["item1", "item2"],
                    "null_val": None,
                },
            ),
        ],
    )
    def test_mask_sensitive_object(self, data, sensitive_flags, expected):
        """Test masking sensitive values in objects."""
        result = _mask_sensitive_object(data, sensitive_flags)
        assert result == expected

    @pytest.mark.parametrize(
        "before_raw,after_raw,is_before_sensitive,is_after_sensitive,expected_before,expected_after",
        [
            ("old", "new", False, False, None, None),
            ("old", "new", True, True, "<sensitive> changed from", "<sensitive> changed to"),
            ("same", "same", True, True, SENSITIVE_MASK, SENSITIVE_MASK),
            ("old", "new", True, False, "<sensitive> changed from", "<sensitive> changed to"),
            ("old", "new", False, True, "<sensitive> changed from", "<sensitive> changed to"),
        ],
    )
    def test_get_change_indicator_text(self, before_raw, after_raw, is_before_sensitive, is_after_sensitive, expected_before, expected_after):
        """Test change indicator text generation."""
        before_text, after_text = _get_change_indicator_text(before_raw, after_raw, is_before_sensitive, is_after_sensitive)
        assert before_text == expected_before
        assert after_text == expected_after

    @pytest.mark.parametrize(
        "actions,expected",
        [
            (["create"], "created"),
            (["update"], "updated"),
            (["delete"], "destroyed"),
            (["read"], "read"),
            (["delete", "create"], "replaced"),
            (["create", "delete"], "replaced"),
            (["update", "create"], "updated (create, update)"),
            ([], "no-op"),
            (["unknown"], "unknown"),
        ],
    )
    def test_convert_actions_to_readable_string(self, actions, expected):
        """Test converting action lists to readable strings."""
        result = _convert_actions_to_readable_string(actions)
        assert result == expected

    @pytest.mark.parametrize(
        "change,expected_result",
        [
            ({"actions": ["no-op"], "before": "value", "after": "value"}, False),
            ({"actions": ["update"], "before": "old", "after": "new"}, True),
            ({"actions": ["update"], "before": "value", "after": "value"}, False),
            ({"actions": ["create"], "before": None, "after": "new"}, True),
        ],
    )
    def test_has_output_changes(self, change, expected_result):
        """Test checking for output changes."""
        result = _has_output_changes(change)
        assert result == expected_result

    @pytest.mark.parametrize(
        "change,expected_before,expected_after",
        [
            (
                {"before": "old", "after": "new", "before_sensitive": False, "after_sensitive": False},
                "old",
                "new",
            ),
            (
                {"before": "old", "after": "new", "before_sensitive": True, "after_sensitive": True},
                "<sensitive> changed from",
                "<sensitive> changed to",
            ),
            (
                {"before": "old", "after": "new", "before_sensitive": True, "after_sensitive": False},
                "<sensitive> changed from",
                "new",
            ),
            (
                {"before": "old", "after": "new", "before_sensitive": False, "after_sensitive": True},
                "old",
                "<sensitive> changed to",
            ),
            (
                {"before": None, "after": "new", "before_sensitive": False, "after_sensitive": False},
                None,
                "new",
            ),
        ],
    )
    def test_create_sensitive_output_values(self, change, expected_before, expected_after):
        """Test creating sensitive output values."""
        before_val, after_val = _create_sensitive_output_values(change)
        assert before_val == expected_before
        assert after_val == expected_after

    def test_create_unified_resources_complex_scenarios(self):
        """Test unified resource processing with various combinations."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _create_unified_resources

        # Test changes only
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
        assert result[0].has_drift is False

        resource_changes = []
        resource_drift = [
            {
                "address": "aws_instance.drift",
                "change": {"actions": ["update"], "before": {"ami": "old"}, "after": {"ami": "new"}},
            },
        ]

        result = _create_unified_resources(resource_changes, resource_drift)
        assert len(result) == 1
        assert result[0].has_drift is True

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
        assert result[0].resource_changes is not None
        assert result[0].resource_drift is not None
        assert result[0].has_drift is True

    def test_diff_processing_integration(self):
        """Test complete diff processing workflow."""
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

    def test_sensitive_value_processing_complex(self):
        """Test complex sensitive value processing scenarios."""
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

        assert result_before["password"] == "<sensitive> changed from"
        assert result_after["password"] == "<sensitive> changed to"
        assert result_before["config"]["api_key"] == "<sensitive> changed from"
        assert result_after["config"]["api_key"] == "<sensitive> changed to"
        assert result_before["username"] == "admin"
        assert result_after["username"] == "admin"


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
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import ViewPlanResourceData, _create_diff_entry

        malformed_item = {"address": "aws_instance.bad"}

        resource_data = ViewPlanResourceData(
            address="aws_instance.bad",
            resource_changes=malformed_item,
            resource_drift=None,
            has_drift=False,
        )

        result = _create_diff_entry(resource_data)
        assert result is None

    def test_nested_sensitive_structures(self):
        """Test deeply nested sensitive structures."""
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

    def test_output_changes_with_sensitive_values(self):
        """Test output changes processing with sensitive values."""
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

    @pytest.mark.parametrize(
        "scenario_type,address,resource_id,action_type,has_drift,expected_contains",
        [
            ("drift_only", "aws_instance.drift", "i-123456789", "updated", True, ["Resource changed outside Terraform", "Drift detected"]),
            ("changes_with_actions", "aws_instance.web", "i-987654321", "created", True, ["Resource changed outside Terraform", "will be created"]),
            ("changes_with_actions", "aws_instance.simple", "", "updated", False, ["will be updated"]),
        ],
    )
    def test_diff_headers_creation(self, scenario_type, address, resource_id, action_type, has_drift, expected_contains):
        """Test diff header creation for various scenarios."""
        from ansible_collections.hashicorp.terraform.plugins.modules.view_plan import _create_diff_headers

        drift_item = {"change": {"actions": ["update"]}} if has_drift else None

        headers = _create_diff_headers(
            scenario_type,
            address,
            resource_id,
            action_type,
            has_drift,
            drift_item,
        )

        for expected_text in expected_contains:
            found = any(expected_text in header for header in headers.values())
            assert found, f"Expected '{expected_text}' not found in headers: {headers}"


if __name__ == "__main__":
    unittest.main()
