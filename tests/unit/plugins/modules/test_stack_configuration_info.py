# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/stack_configuration_info.py."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.stack_configuration_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.stack_configuration_info"


def _mock_module(params, check_mode=False):
    """Build a mock AnsibleTerraformModule and a mock adapter."""
    mock_module = Mock()
    mock_module.params = params
    mock_module.check_mode = check_mode

    mock_adapter = Mock()
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_adapter)
    mock_context.__exit__ = Mock(return_value=False)
    mock_module.client.return_value = mock_context
    return mock_module, mock_adapter


# ---------------------------------------------------------------------------
# read by ID
# ---------------------------------------------------------------------------


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_configuration")
def test_by_id_success(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module({"stack_configuration_id": "stc-abc123", "stack_id": None})
    mock_module_class.return_value = mock_module
    mock_get.return_value = {"id": "stc-abc123", "status": "completed"}

    main()

    mock_get.assert_called_once_with(mock_adapter, "stc-abc123")
    result = mock_module.exit_json.call_args[1]
    assert result["stack_configuration"]["id"] == "stc-abc123"
    assert result["stack_configuration"]["status"] == "completed"
    assert result["changed"] is False
    assert result["warnings"] == []


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_configuration")
def test_by_id_not_found_fails(mock_get, mock_module_class):
    mock_module = _mock_module({"stack_configuration_id": "stc-x", "stack_id": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.return_value = None

    main()

    mock_module.fail_json.assert_called_once()
    assert "not found" in mock_module.fail_json.call_args[1]["msg"].lower()


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_configuration")
def test_by_id_returns_all_fields(mock_get, mock_module_class):
    mock_module, mock_adapter = _mock_module({"stack_configuration_id": "stc-full", "stack_id": None})
    mock_module_class.return_value = mock_module
    mock_get.return_value = {
        "id": "stc-full",
        "status": "completed",
        "sequence_number": 3,
        "speculative": False,
        "created_at": "2025-01-01T00:00:00+00:00",
        "updated_at": "2025-01-01T00:01:00+00:00",
    }

    main()

    result = mock_module.exit_json.call_args[1]
    assert result["stack_configuration"]["sequence_number"] == 3
    assert result["stack_configuration"]["speculative"] is False
    assert result["stack_configuration"]["status"] == "completed"
    assert result["stack_configuration"]["created_at"] == "2025-01-01T00:00:00+00:00"
    assert result["stack_configuration"]["updated_at"] == "2025-01-01T00:01:00+00:00"
    assert result["changed"] is False
    assert result["warnings"] == []


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.get_stack_configuration")
def test_exception_triggers_fail_json(mock_get, mock_module_class):
    mock_module = _mock_module({"stack_configuration_id": "stc-xyz789", "stack_id": None})[0]
    mock_module_class.return_value = mock_module
    mock_get.side_effect = RuntimeError("unexpected error")

    main()

    mock_module.fail_json.assert_called_once()
    assert "unexpected error" in mock_module.fail_json.call_args[1]["msg"]


# ---------------------------------------------------------------------------
# list by stack_id
# ---------------------------------------------------------------------------

_STC_A = {"id": "stc-111", "status": "completed", "sequence_number": 1}
_STC_B = {"id": "stc-222", "status": "pending", "sequence_number": 2}


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_stack_configurations")
def test_list_by_stack_id_success(mock_list, mock_module_class):
    """Providing only stack_id returns a stack_configurations list."""
    mock_module, mock_adapter = _mock_module({"stack_configuration_id": None, "stack_id": "st-xyz789"})
    mock_module_class.return_value = mock_module
    mock_list.return_value = [_STC_A, _STC_B]

    main()

    mock_list.assert_called_once_with(mock_adapter, "st-xyz789")
    result = mock_module.exit_json.call_args[1]
    assert result["stack_configurations"] == [_STC_A, _STC_B]
    assert result["changed"] is False
    assert result["warnings"] == []


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_stack_configurations")
def test_list_by_stack_id_empty(mock_list, mock_module_class):
    """An empty stack returns an empty list (no error)."""
    mock_module, mock_adapter = _mock_module({"stack_configuration_id": None, "stack_id": "st-xyz789"})
    mock_module_class.return_value = mock_module
    mock_list.return_value = []

    main()

    result = mock_module.exit_json.call_args[1]
    assert result["stack_configurations"] == []
    assert result["changed"] is False


@patch(f"{MODULE_PATH}.AnsibleTerraformModule")
@patch(f"{MODULE_PATH}.list_stack_configurations")
def test_list_exception_triggers_fail_json(mock_list, mock_module_class):
    mock_module = _mock_module({"stack_configuration_id": None, "stack_id": "st-xyz789"})[0]
    mock_module_class.return_value = mock_module
    mock_list.side_effect = RuntimeError("network error")

    main()

    mock_module.fail_json.assert_called_once()
    assert "network error" in mock_module.fail_json.call_args[1]["msg"]


# ---------------------------------------------------------------------------
# argument spec
# ---------------------------------------------------------------------------


def test_argument_spec_declares_required_one_of():
    """Module must declare required_one_of for stack_configuration_id / stack_id."""
    with patch(f"{MODULE_PATH}.AnsibleTerraformModule", side_effect=SystemExit) as mock_cls:
        try:
            main()
        except SystemExit:
            pass

    _args, kwargs = mock_cls.call_args
    roe = kwargs.get("required_one_of", [])
    assert any("stack_configuration_id" in pair and "stack_id" in pair for pair in roe)
