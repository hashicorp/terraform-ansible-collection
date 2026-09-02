# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/team_token_info.py."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.team_token_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.team_token_info"

# Synthetic token metadata.
_TOKEN_DATA = {"id": "at-abc123", "description": "CI token", "created_at": "2026-05-01T10:00:00Z", "expired_at": None}


def _mock_module(params, check_mode=False):
    mock_module = Mock()
    mock_module.params = params
    mock_module.check_mode = check_mode

    mock_adapter = Mock()
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_adapter)
    mock_context.__exit__ = Mock(return_value=False)
    mock_module.client.return_value = mock_context
    return mock_module, mock_adapter


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_team_token")
def test_by_team_id_success(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module({"team_id": "team-xyz789", "token_id": None})
    mock_module_class.return_value = mock_module
    mock_get.return_value = _TOKEN_DATA

    main()

    mock_get.assert_called_once_with(mock_adapter, "team-xyz789")
    result = mock_module.exit_json.call_args[1]
    assert result["changed"] is False
    assert result["team_token"]["id"] == "at-abc123"


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_team_token")
def test_by_team_id_not_found_fails(mock_get, mock_module_class):
    mock_module = _mock_module({"team_id": "team-missing", "token_id": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_team_token_by_id")
def test_by_token_id_success(mock_get_by_id, mock_module_class):
    mock_module, mock_adapter = _mock_module({"team_id": None, "token_id": "at-abc123"})
    mock_module_class.return_value = mock_module
    mock_get_by_id.return_value = _TOKEN_DATA

    main()

    mock_get_by_id.assert_called_once_with(mock_adapter, "at-abc123")
    result = mock_module.exit_json.call_args[1]
    assert result["changed"] is False
    assert result["team_token"]["id"] == "at-abc123"


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_team_token_by_id")
def test_by_token_id_not_found_fails(mock_get_by_id, mock_module_class):
    mock_module = _mock_module({"team_id": None, "token_id": "at-missing"})[0]
    mock_module_class.return_value = mock_module
    mock_get_by_id.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"]


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_team_token")
def test_check_mode_reads_without_change(mock_get, mock_module_class):
    mock_module, _patch = _mock_module({"team_id": "team-xyz789", "token_id": None}, check_mode=True)
    mock_module_class.return_value = mock_module
    mock_get.return_value = _TOKEN_DATA

    main()

    result = mock_module.exit_json.call_args[1]
    assert result["changed"] is False
    assert result["team_token"]["id"] == "at-abc123"


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_team_token")
def test_unexpected_exception_fails(mock_get, mock_module_class):
    mock_module = _mock_module({"team_id": "team-xyz789", "token_id": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.side_effect = RuntimeError("unexpected")

    main()

    mock_module.fail_json.assert_called_once()
    assert "unexpected" in mock_module.fail_json.call_args[1]["msg"]
