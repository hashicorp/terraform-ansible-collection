# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the policy_evaluation_info module."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.policy_evaluation_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.policy_evaluation_info"


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_policy_evaluations")
def test_list_for_task_stage(mock_list, mock_module_class):
    mock_module = Mock()
    mock_module.params = {"task_stage_id": "ts-1"}
    mock_adapter = Mock()
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_adapter)
    mock_context.__exit__ = Mock(return_value=False)
    mock_module.client.return_value = mock_context
    mock_module_class.return_value = mock_module
    mock_list.return_value = [{"id": "poleval-1", "status": "passed"}]

    main()

    mock_list.assert_called_once_with(mock_adapter, "ts-1")
    result = mock_module.exit_json.call_args[1]
    assert result["policy_evaluations"] == [{"id": "poleval-1", "status": "passed"}]
    assert result["changed"] is False
