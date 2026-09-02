# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/stack_configuration.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.stack_configuration import (
    _desired_payload,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.stack_configuration"


class TestDesiredPayload:
    def test_includes_all_supplied_keys(self):
        params = {
            "stack_id": "st-xyz789",
            "source": "fetch",
            "speculative_enabled": True,
            "destroy_all": True,
            "selected_deployments": ["dep-a"],
        }
        payload = _desired_payload(params)
        assert payload == {
            "source": "fetch",
            "speculative_enabled": True,
            "destroy_all": True,
            "selected_deployments": ["dep-a"],
        }

    def test_excludes_none_values(self):
        params = {
            "stack_id": "st-xyz789",
            "source": "manual",
            "speculative_enabled": False,
            "destroy_all": False,
            "selected_deployments": None,
        }
        payload = _desired_payload(params)
        assert "selected_deployments" not in payload
        assert payload["speculative_enabled"] is False
        assert payload["destroy_all"] is False
        assert payload["source"] == "manual"

    def test_stack_id_not_in_payload(self):
        params = {"stack_id": "st-xyz789", "speculative_enabled": True, "source": "manual"}
        payload = _desired_payload(params)
        assert "stack_id" not in payload

    def test_empty_params_returns_only_source_default(self):
        params = {}
        payload = _desired_payload(params)
        # Neither source nor create options keys are in an empty dict
        assert payload == {}


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_success(self, adapter):
        params = {
            "stack_id": "st-xyz789",
            "source": "manual",
            "speculative_enabled": False,
            "destroy_all": False,
            "selected_deployments": None,
        }
        expected = {"id": "stc-1", "status": "pending"}
        with patch(f"{MODULE_PATH}.create_stack_configuration", return_value=expected) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[0][0] is adapter
        assert call_args[0][1] == "st-xyz789"
        assert result["changed"] is True
        assert result["id"] == "stc-1"
        assert result["status"] == "pending"

    def test_create_check_mode(self, adapter):
        params = {
            "stack_id": "st-xyz789",
            "source": "manual",
            "speculative_enabled": False,
        }
        with patch(f"{MODULE_PATH}.create_stack_configuration") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]
        assert "st-xyz789" in result["msg"]

    def test_missing_stack_id_raises(self, adapter):
        params = {"stack_id": None, "source": "manual"}
        with pytest.raises(ValueError, match="stack_id"):
            state_present(adapter, params, check_mode=False)

    def test_missing_stack_id_empty_string_raises(self, adapter):
        params = {"stack_id": "", "source": "manual"}
        with pytest.raises(ValueError, match="stack_id"):
            state_present(adapter, params, check_mode=False)

    def test_create_with_fetch_source(self, adapter):
        params = {
            "stack_id": "st-xyz789",
            "source": "fetch",
            "speculative_enabled": False,
            "destroy_all": False,
            "selected_deployments": None,
        }
        expected = {"id": "stc-vcs-1", "status": "pending"}
        with patch(f"{MODULE_PATH}.create_stack_configuration", return_value=expected) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once()
        passed_data = mock_create.call_args[0][2]
        assert passed_data.get("source") == "fetch"
        assert result["changed"] is True
        assert result["id"] == "stc-vcs-1"

    def test_create_with_speculative_enabled(self, adapter):
        params = {
            "stack_id": "st-xyz789",
            "source": "manual",
            "speculative_enabled": True,
            "destroy_all": False,
            "selected_deployments": None,
        }
        expected = {"id": "stc-spec", "status": "pending", "speculative": True}
        with patch(f"{MODULE_PATH}.create_stack_configuration", return_value=expected) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        assert result["changed"] is True
        passed_data = mock_create.call_args[0][2]
        assert passed_data.get("speculative_enabled") is True

    def test_create_with_selected_deployments(self, adapter):
        params = {
            "stack_id": "st-xyz789",
            "source": "manual",
            "speculative_enabled": False,
            "destroy_all": False,
            "selected_deployments": ["dep-a", "dep-b"],
        }
        expected = {"id": "stc-sel", "status": "pending"}
        with patch(f"{MODULE_PATH}.create_stack_configuration", return_value=expected) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        passed_data = mock_create.call_args[0][2]
        assert passed_data.get("selected_deployments") == ["dep-a", "dep-b"]
        assert result["changed"] is True

    def test_create_check_mode_with_fetch_source(self, adapter):
        params = {"stack_id": "st-xyz789", "source": "fetch"}
        with patch(f"{MODULE_PATH}.create_stack_configuration") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_create_returns_all_api_fields(self, adapter):
        params = {
            "stack_id": "st-xyz789",
            "source": "manual",
            "speculative_enabled": False,
            "destroy_all": False,
            "selected_deployments": None,
        }
        expected = {
            "id": "stc-full",
            "status": "completed",
            "sequence_number": 5,
            "speculative": False,
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:01:00+00:00",
        }
        with patch(f"{MODULE_PATH}.create_stack_configuration", return_value=expected):
            result = state_present(adapter, params, check_mode=False)
        assert result["id"] == "stc-full"
        assert result["status"] == "completed"
        assert result["sequence_number"] == 5
        assert result["speculative"] is False
        assert result["created_at"] == "2025-01-01T00:00:00+00:00"
        assert result["updated_at"] == "2025-01-01T00:01:00+00:00"
        assert result["changed"] is True
