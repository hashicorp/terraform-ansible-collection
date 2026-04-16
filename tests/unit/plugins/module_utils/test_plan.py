# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest
from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.plan import (
    get_plan_data,
)


class TestPlanFunctions:
    """Tests for plan helper functions with SDK adapters."""

    @pytest.fixture
    def mock_tf_client(self):
        """Provide a mock TerraformClient adapter for tests."""
        return Mock()

    @pytest.fixture
    def plan_id(self):
        """Provide a sample plan ID."""
        return "plan-123abc456def789"

    @pytest.fixture
    def run_id(self):
        """Provide a sample run ID."""
        return "run-456def789abc123"

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan.format_response")
    def test_get_plan_data_plan_id_metadata_success(self, mock_format_response, mock_tf_client, plan_id):
        """Test metadata retrieval by plan_id using SDK plans.read."""
        sdk_plan = Mock()
        formatted_plan = {"id": plan_id, "status": "finished", "has_changes": True}

        mock_tf_client.client.plans.read.return_value = sdk_plan
        mock_format_response.return_value = formatted_plan

        result = get_plan_data(mock_tf_client, plan_id, use_plan_id=True, include_json_output=False)

        assert result == formatted_plan
        mock_tf_client.client.plans.read.assert_called_once_with(plan_id)
        mock_tf_client.client.plans.read_json_output.assert_not_called()
        mock_format_response.assert_called_once_with(sdk_plan)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan.format_response")
    def test_get_plan_data_plan_id_json_output_model_success(self, mock_format_response, mock_tf_client, plan_id):
        """Test JSON output retrieval by plan_id when SDK returns a model object."""
        sdk_json_output = Mock()
        formatted_json = {"format_version": "1.2", "resource_changes": []}

        mock_tf_client.client.plans.read_json_output.return_value = sdk_json_output
        mock_format_response.return_value = formatted_json

        result = get_plan_data(mock_tf_client, plan_id, use_plan_id=True, include_json_output=True)

        assert result == formatted_json
        mock_tf_client.client.plans.read_json_output.assert_called_once_with(plan_id)
        mock_tf_client.client.plans.read.assert_not_called()
        mock_format_response.assert_called_once_with(sdk_json_output)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan.format_response")
    def test_get_plan_data_plan_id_json_output_dict_passthrough(self, mock_format_response, mock_tf_client, plan_id):
        """Test JSON output retrieval returns dict as-is without formatting."""
        json_output = {
            "format_version": "1.2",
            "terraform_version": "1.5.0",
            "resource_changes": [{"address": "null_resource.test", "change": {"actions": ["create"]}}],
        }
        mock_tf_client.client.plans.read_json_output.return_value = json_output

        result = get_plan_data(mock_tf_client, plan_id, use_plan_id=True, include_json_output=True)

        assert result == json_output
        mock_tf_client.client.plans.read_json_output.assert_called_once_with(plan_id)
        mock_format_response.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan.get_run")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan.format_response")
    def test_get_plan_data_run_id_metadata_success(self, mock_format_response, mock_get_run, mock_tf_client, run_id):
        """Test metadata retrieval by run_id resolves plan id then reads plan."""
        resolved_plan_id = "plan-resolved123"
        sdk_plan = Mock()
        formatted_plan = {"id": resolved_plan_id, "status": "finished"}

        mock_get_run.return_value = {"id": run_id, "plan": {"id": resolved_plan_id}}
        mock_tf_client.client.plans.read.return_value = sdk_plan
        mock_format_response.return_value = formatted_plan

        result = get_plan_data(mock_tf_client, run_id, use_plan_id=False, include_json_output=False)

        assert result == formatted_plan
        mock_get_run.assert_called_once_with(mock_tf_client, run_id)
        mock_tf_client.client.plans.read.assert_called_once_with(resolved_plan_id)
        mock_format_response.assert_called_once_with(sdk_plan)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan.get_run")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan.format_response")
    def test_get_plan_data_run_id_json_success(self, mock_format_response, mock_get_run, mock_tf_client, run_id):
        """Test JSON retrieval by run_id resolves plan id then reads json output."""
        resolved_plan_id = "plan-resolved456"
        sdk_json = Mock()
        formatted_json = {"format_version": "1.2", "resource_changes": []}

        mock_get_run.return_value = {"id": run_id, "plan": {"id": resolved_plan_id}}
        mock_tf_client.client.plans.read_json_output.return_value = sdk_json
        mock_format_response.return_value = formatted_json

        result = get_plan_data(mock_tf_client, run_id, use_plan_id=False, include_json_output=True)

        assert result == formatted_json
        mock_get_run.assert_called_once_with(mock_tf_client, run_id)
        mock_tf_client.client.plans.read_json_output.assert_called_once_with(resolved_plan_id)
        mock_format_response.assert_called_once_with(sdk_json)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan.get_run")
    def test_get_plan_data_run_id_not_found_raises(self, mock_get_run, mock_tf_client, run_id):
        """Test run_id path raises TerraformError when run does not exist."""
        mock_get_run.return_value = {}

        with pytest.raises(TerraformError, match=f"Run with ID {run_id} not found"):
            get_plan_data(mock_tf_client, run_id, use_plan_id=False)

        mock_tf_client.client.plans.read.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan.get_run")
    @pytest.mark.parametrize(
        "run_response", [{"id": "run-abc"}, {"id": "run-abc", "plan": None}, {"id": "run-abc", "plan": {}}, {"id": "run-abc", "plan": {"type": "plans"}}]
    )
    def test_get_plan_data_run_id_without_associated_plan_raises(self, mock_get_run, mock_tf_client, run_response):
        """Test run_id path raises TerraformError when run has no associated plan id."""
        run_id = "run-abc"
        mock_get_run.return_value = run_response

        with pytest.raises(TerraformError, match=f"Run with ID {run_id} does not have an associated plan"):
            get_plan_data(mock_tf_client, run_id, use_plan_id=False)

        mock_tf_client.client.plans.read.assert_not_called()

    @pytest.mark.parametrize("include_json_output", [False, True])
    def test_get_plan_data_plan_not_found_returns_empty_dict(self, mock_tf_client, plan_id, include_json_output):
        """Test plan read returns empty dict when SDK raises NotFound."""
        if include_json_output:
            mock_tf_client.client.plans.read_json_output.side_effect = NotFound("not found")
        else:
            mock_tf_client.client.plans.read.side_effect = NotFound("not found")

        result = get_plan_data(mock_tf_client, plan_id, use_plan_id=True, include_json_output=include_json_output)

        assert result == {}

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan.format_response")
    def test_get_plan_data_unexpected_exception_bubbles(self, mock_format_response, mock_tf_client, plan_id):
        """Test non-NotFound exceptions are propagated to caller."""
        mock_tf_client.client.plans.read.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            get_plan_data(mock_tf_client, plan_id, use_plan_id=True)

        mock_format_response.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.plan.format_response")
    def test_get_plan_data_default_parameter_reads_metadata(self, mock_format_response, mock_tf_client, plan_id):
        """Test include_json_output defaults to metadata path."""
        sdk_plan = Mock()
        formatted = {"id": plan_id, "status": "finished"}

        mock_tf_client.client.plans.read.return_value = sdk_plan
        mock_format_response.return_value = formatted

        result = get_plan_data(mock_tf_client, plan_id, use_plan_id=True)

        assert result == formatted
        mock_tf_client.client.plans.read.assert_called_once_with(plan_id)
        mock_tf_client.client.plans.read_json_output.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
