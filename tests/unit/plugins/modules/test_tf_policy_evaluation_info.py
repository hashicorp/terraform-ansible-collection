# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the tf_policy_evaluation_info module."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.tf_policy_evaluation_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.tf_policy_evaluation_info"


def _mock_module(params):
    mock_module = Mock()
    mock_module.params = params
    mock_adapter = Mock()
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_adapter)
    mock_context.__exit__ = Mock(return_value=False)
    mock_module.client.return_value = mock_context
    return mock_module, mock_adapter


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_evaluations")
def test_list_by_run_id(mock_list, mock_module_class):
    mock_module, mock_adapter = _mock_module({"run_id": "run-1", "evaluation_id": None, "include_outcomes": False, "filter": None})
    mock_module_class.return_value = mock_module
    mock_list.return_value = [{"id": "tfpeval-1", "status": "passed"}]

    main()

    mock_list.assert_called_once_with(mock_adapter, "run-1")
    result = mock_module.exit_json.call_args[1]
    assert result["evaluations"] == [{"id": "tfpeval-1", "status": "passed"}]
    assert result["changed"] is False
    assert "evaluation" not in result


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_evaluation")
def test_read_by_evaluation_id(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module({"run_id": None, "evaluation_id": "tfpeval-1", "include_outcomes": False, "filter": None})
    mock_module_class.return_value = mock_module
    mock_get.return_value = {"id": "tfpeval-1", "status": "awaiting_override"}

    main()

    mock_get.assert_called_once_with(mock_adapter, "tfpeval-1", include_outcomes=False)
    result = mock_module.exit_json.call_args[1]
    assert result["evaluation"] == {"id": "tfpeval-1", "status": "awaiting_override"}
    assert "evaluations" not in result


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_evaluation")
def test_read_by_evaluation_id_not_found_fails(mock_get, mock_module_class):
    mock_module, _mock_adapter = _mock_module({"run_id": None, "evaluation_id": "tfpeval-missing", "include_outcomes": False, "filter": None})
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_set_outcomes")
@patch(f"{MODULE_PATH}.list_evaluations")
def test_include_outcomes_attaches_set_outcomes_per_evaluation(mock_list, mock_list_outcomes, mock_module_class):
    mock_module, mock_adapter = _mock_module({"run_id": "run-1", "evaluation_id": None, "include_outcomes": True, "filter": None})
    mock_module_class.return_value = mock_module
    mock_list.return_value = [{"id": "tfpeval-1", "status": "awaiting_override"}]
    mock_list_outcomes.return_value = [{"id": "tfpsout-1", "policy_set_name": "baseline"}]

    main()

    mock_list_outcomes.assert_called_once_with(mock_adapter, "tfpeval-1", filter_status=None, filter_enforcement_level=None)
    result = mock_module.exit_json.call_args[1]
    assert result["evaluations"][0]["set_outcomes"] == [{"id": "tfpsout-1", "policy_set_name": "baseline"}]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_set_outcomes")
@patch(f"{MODULE_PATH}.list_evaluations")
def test_filter_forwarded_to_list_set_outcomes(mock_list, mock_list_outcomes, mock_module_class):
    mock_module, mock_adapter = _mock_module(
        {
            "run_id": "run-1",
            "evaluation_id": None,
            "include_outcomes": True,
            "filter": {"status": "failed", "enforcement_level": "mandatory_overridable"},
        }
    )
    mock_module_class.return_value = mock_module
    mock_list.return_value = [{"id": "tfpeval-1"}]
    mock_list_outcomes.return_value = []

    main()

    mock_list_outcomes.assert_called_once_with(mock_adapter, "tfpeval-1", filter_status="failed", filter_enforcement_level="mandatory_overridable")


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_evaluations")
def test_argument_spec(mock_list, mock_module_class):
    mock_module, _mock_adapter = _mock_module({"run_id": "run-1", "evaluation_id": None, "include_outcomes": False, "filter": None})
    mock_module_class.return_value = mock_module
    mock_list.return_value = []

    main()

    call_kwargs = mock_module_class.call_args[1]
    assert call_kwargs["required_one_of"] == [("run_id", "evaluation_id")]
    assert call_kwargs["mutually_exclusive"] == [("run_id", "evaluation_id")]
    assert call_kwargs["supports_check_mode"] is True
    argument_spec = call_kwargs["argument_spec"]
    assert argument_spec["include_outcomes"]["default"] is False
    assert set(argument_spec["filter"]["options"].keys()) == {"status", "enforcement_level"}
