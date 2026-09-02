# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze import (
    main,
)

_PLAN_JSON = {
    "format_version": "1.2",
    "resource_changes": [
        {
            "address": "aws_instance.web",
            "type": "aws_instance",
            "name": "web",
            "provider_name": "registry.terraform.io/hashicorp/aws",
            "mode": "managed",
            "change": {
                "actions": ["update"],
                "before": {"instance_type": "t2.micro"},
                "after": {"instance_type": "t3.small"},
            },
        },
    ],
}


def _base_params(**overrides):
    params = {
        "run_id": None,
        "plan_id": None,
        "plan_json": None,
        "detect_drift": True,
        "include_resource_changes": True,
        "include_output_changes": True,
        "include_values": False,
        "safe_attributes": [],
        "risky_attributes": [],
        "blocked_attributes": [],
        "tfe_token": "test-token",
        "tfe_address": "https://app.terraform.io",
    }
    params.update(overrides)
    return params


class TestPlanAnalyzeModule:
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.get_plan_data")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.AnsibleTerraformModule")
    def test_inline_plan_json_skips_api(self, mock_module_class, mock_get_data, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = _base_params(plan_json=_PLAN_JSON)
        mock_module_class.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_get_data.assert_not_called()
        result = mock_module.exit_args
        assert result["changed"] is False
        assert result["change_count"] == 1
        assert result["resource_changes"][0]["classification"] == "safe"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.get_plan_data")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.AnsibleTerraformModule")
    def test_run_id_fetches_plan(self, mock_module_class, mock_get_data, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = _base_params(run_id="run-123")
        mock_module_class.return_value = mock_module
        mock_get_data.return_value = _PLAN_JSON

        with pytest.raises(SystemExit):
            main()

        mock_get_data.assert_called_once()
        args = mock_get_data.call_args
        assert args.args[1] == "run-123"
        assert args.args[2] is False  # use_plan_id
        assert args.kwargs["include_json_output"] is True
        assert mock_module.exit_args["change_count"] == 1

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.get_plan_data")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.AnsibleTerraformModule")
    def test_plan_id_fetches_plan(self, mock_module_class, mock_get_data, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = _base_params(plan_id="plan-123")
        mock_module_class.return_value = mock_module
        mock_get_data.return_value = _PLAN_JSON

        with pytest.raises(SystemExit):
            main()

        args = mock_get_data.call_args
        assert args.args[1] == "plan-123"
        assert args.args[2] is True  # use_plan_id

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.get_plan_data")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.AnsibleTerraformModule")
    def test_no_json_output_fails(self, mock_module_class, mock_get_data, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = _base_params(plan_id="plan-missing")
        mock_module_class.return_value = mock_module
        mock_get_data.return_value = {}

        with pytest.raises(AssertionError, match="has no JSON output"):
            main()

        assert mock_module.failed is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.get_plan_data")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.AnsibleTerraformModule")
    def test_unsupported_version_warns_and_succeeds(self, mock_module_class, mock_get_data, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = _base_params(plan_json={"format_version": "2.0"})
        mock_module_class.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        assert mock_module.failed is False
        assert any("2.0" in warning for warning in mock_module.warnings)
        assert mock_module.exit_args["resource_changes"] == []

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.get_plan_data")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.plan_analyze.AnsibleTerraformModule")
    def test_custom_blocked_attributes(self, mock_module_class, mock_get_data, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = _base_params(
            plan_json=_PLAN_JSON,
            blocked_attributes=["aws_instance.*.instance_type"],
        )
        mock_module_class.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        assert mock_module.exit_args["resource_changes"][0]["classification"] == "blocked"
        assert mock_module.exit_args["summary"]["blocked"] == 1
