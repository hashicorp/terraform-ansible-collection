# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.run import (
    apply_run,
    cancel_run,
    create_run,
    discard_run,
    get_run,
    run_events,
)


class TestCreateRun:
    """Test cases for create_run with SDK adapters."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.RunCreateOptions.model_validate")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.ConfigurationVersion.model_validate")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.Workspace.model_validate")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.format_response")
    def test_create_run_with_workspace_and_configuration_version(
        self,
        mock_format_response,
        mock_safe_api_call,
        mock_workspace_model_validate,
        mock_cv_model_validate,
        mock_run_options_validate,
    ):
        """Test create_run maps IDs to SDK models and formats response."""
        mock_adapter = Mock()
        mock_options = Mock()
        mock_sdk_response = Mock()

        mock_workspace_model_validate.return_value = "workspace-model"
        mock_cv_model_validate.return_value = "config-version-model"
        mock_run_options_validate.return_value = mock_options
        mock_safe_api_call.return_value = mock_sdk_response
        mock_format_response.return_value = {"id": "run-123", "status": "pending"}

        payload = {
            "workspace_id": "ws-123",
            "configuration_version": "cv-123",
            "run_message": "plan run",
            "variables": [{"key": "env", "value": "dev"}],
        }

        result = create_run(mock_adapter, payload)

        assert result == {"id": "run-123", "status": "pending"}
        mock_workspace_model_validate.assert_called_once_with({"id": "ws-123", "type": "workspaces"})
        mock_cv_model_validate.assert_called_once_with({"id": "cv-123", "type": "configuration-versions"})
        mock_run_options_validate.assert_called_once()

        validated_payload = mock_run_options_validate.call_args.args[0]
        assert "workspace_id" not in validated_payload
        assert "configuration_version" in validated_payload
        assert validated_payload["workspace"] == "workspace-model"

        mock_safe_api_call.assert_called_once_with(mock_adapter.client.runs.create, mock_options)
        mock_format_response.assert_called_once_with(mock_sdk_response)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.RunCreateOptions.model_validate")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.format_response")
    def test_create_run_minimal_payload(self, mock_format_response, mock_safe_api_call, mock_run_options_validate):
        """Test create_run handles minimal payload without optional transforms."""
        mock_adapter = Mock()
        mock_options = Mock()
        mock_sdk_response = Mock()

        mock_run_options_validate.return_value = mock_options
        mock_safe_api_call.return_value = mock_sdk_response
        mock_format_response.return_value = {"id": "run-456"}

        payload = {"workspace_id": "ws-456"}

        result = create_run(mock_adapter, payload)

        assert result == {"id": "run-456"}
        mock_run_options_validate.assert_called_once()
        mock_safe_api_call.assert_called_once_with(mock_adapter.client.runs.create, mock_options)


class TestRunActions:
    """Test cases for apply/cancel/discard helpers."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.safe_api_call")
    def test_apply_run(self, mock_safe_api_call):
        """Test apply_run uses SDK runs.apply with options and returns run id."""
        mock_adapter = Mock()

        result = apply_run(mock_adapter, "run-123", comment="apply now")

        assert result == {"data": {"id": "run-123"}}
        mock_safe_api_call.assert_called_once()
        args = mock_safe_api_call.call_args.args
        assert args[0] == mock_adapter.client.runs.apply
        assert args[1] == "run-123"
        assert args[2].comment == "apply now"

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.safe_api_call")
    def test_cancel_run(self, mock_safe_api_call):
        """Test cancel_run uses SDK runs.cancel with options and returns run id."""
        mock_adapter = Mock()

        result = cancel_run(mock_adapter, "run-456", comment="cancel now")

        assert result == {"data": {"id": "run-456"}}
        mock_safe_api_call.assert_called_once()
        args = mock_safe_api_call.call_args.args
        assert args[0] == mock_adapter.client.runs.cancel
        assert args[1] == "run-456"
        assert args[2].comment == "cancel now"

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.safe_api_call")
    def test_discard_run(self, mock_safe_api_call):
        """Test discard_run uses SDK runs.discard with options and returns run id."""
        mock_adapter = Mock()

        result = discard_run(mock_adapter, "run-789", comment="discard now")

        assert result == {"data": {"id": "run-789"}}
        mock_safe_api_call.assert_called_once()
        args = mock_safe_api_call.call_args.args
        assert args[0] == mock_adapter.client.runs.discard
        assert args[1] == "run-789"
        assert args[2].comment == "discard now"


class TestGetRun:
    """Test cases for get_run function with SDK reads."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.format_response")
    def test_get_run_success(self, mock_format_response):
        """Test get_run formats SDK run object."""
        mock_adapter = Mock()
        mock_sdk_run = Mock()

        mock_adapter.client.runs.read.return_value = mock_sdk_run
        mock_format_response.return_value = {"id": "run-abc", "status": "planned"}

        result = get_run(mock_adapter, "run-abc")

        assert result == {"id": "run-abc", "status": "planned"}
        mock_adapter.client.runs.read.assert_called_once_with("run-abc")
        mock_format_response.assert_called_once_with(mock_sdk_run)

    def test_get_run_not_found(self):
        """Test get_run returns empty dict for missing run."""
        mock_adapter = Mock()
        mock_adapter.client.runs.read.side_effect = NotFound("Run not found")

        result = get_run(mock_adapter, "run-missing")

        assert result == {}
        mock_adapter.client.runs.read.assert_called_once_with("run-missing")


class TestRunEvents:
    """Test cases for run_events function with SDK iterator."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.format_response")
    def test_run_events_success(self, mock_format_response):
        """Test run_events formats all SDK event objects from iterator."""
        mock_adapter = Mock()
        mock_event_1 = Mock()
        mock_event_2 = Mock()

        mock_adapter.client.run_events.list.return_value = [mock_event_1, mock_event_2]
        mock_format_response.side_effect = [
            {"id": "event-1", "action": "created"},
            {"id": "event-2", "action": "planning"},
        ]

        result = run_events(mock_adapter, "run-123")

        assert result == [
            {"id": "event-1", "action": "created"},
            {"id": "event-2", "action": "planning"},
        ]
        mock_adapter.client.run_events.list.assert_called_once_with("run-123")
        assert mock_format_response.call_count == 2

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.run.format_response")
    def test_run_events_empty(self, mock_format_response):
        """Test run_events returns empty list for no events."""
        mock_adapter = Mock()
        mock_adapter.client.run_events.list.return_value = []

        result = run_events(mock_adapter, "run-456")

        assert result == []
        mock_adapter.client.run_events.list.assert_called_once_with("run-456")
        mock_format_response.assert_not_called()
