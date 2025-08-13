# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.runs import (
    get_workspace_id,
    handle_polling_and_result,
    idempotency_check,
    main,
    state_applied,
    state_canceled,
    state_discarded,
    state_present,
    wait_for_state,
)


class EnhancedDummyModule:
    """A mock Ansible module for better inspection in tests."""

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

    def fail_from_exception(self, exception):
        self.failed = True
        self.fail_args = {"msg": str(exception)}
        raise AssertionError(f"fail_from_exception called with: {exception}")

    def exit_json(self, **kwargs):
        self.exit_args = kwargs
        raise SystemExit(kwargs)


class TestWaitForState:
    """Test cases for wait_for_state function."""

    @patch("time.sleep")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run")
    def test_wait_for_state_success(self, mock_get_run, mock_sleep):
        """Test wait_for_state with successful completion."""
        mock_client = Mock()

        # Mock successful run response
        success_response = {"data": {"id": "run-123", "attributes": {"status": "applied"}}}
        mock_get_run.return_value = success_response

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.RunStates") as mock_run_states:
            mock_run_states.is_success_state.return_value = True

            status, response = wait_for_state(mock_client, "run-123")

            assert status == "success"
            assert response == success_response
            mock_get_run.assert_called_with(mock_client, "run-123")

    @patch("time.sleep")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run")
    def test_wait_for_state_failure(self, mock_get_run, mock_sleep):
        """Test wait_for_state with failure state."""
        mock_client = Mock()

        failure_response = {"data": {"id": "run-123", "attributes": {"status": "errored"}}}
        mock_get_run.return_value = failure_response

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.RunStates") as mock_run_states:
            mock_run_states.is_success_state.return_value = False
            mock_run_states.is_failure_state.return_value = True

            status, response = wait_for_state(mock_client, "run-123")

            assert status == "failure"
            assert response == failure_response

    @patch("time.sleep")
    @patch("time.time")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run")
    def test_wait_for_state_timeout(self, mock_get_run, mock_time, mock_sleep):
        """Test wait_for_state with timeout."""
        mock_client = Mock()

        # Mock time progression to trigger timeout after one iteration
        mock_time.side_effect = [0, 30, 60]  # Start at 0, then 30 (within timeout), then 60 (exceeds timeout of 50)

        pending_response = {"data": {"id": "run-123", "attributes": {"status": "pending"}}}
        mock_get_run.return_value = pending_response

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.RunStates") as mock_run_states:
            mock_run_states.is_success_state.return_value = False
            mock_run_states.is_failure_state.return_value = False

            status, response = wait_for_state(mock_client, "run-123", timeout=50)

            assert status == "timeout"
            assert response == pending_response


class TestHandlePollingAndResult:
    """Test cases for handle_polling_and_result function."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.wait_for_state")
    def test_handle_polling_success(self, mock_wait_for_state):
        """Test handle_polling_and_result with successful polling."""
        mock_client = Mock()
        response = {"data": {"id": "run-123", "attributes": {"status": "applied"}}}

        mock_wait_for_state.return_value = ("success", {"data": {"id": "run-123", "attributes": {"status": "applied"}}})

        result = handle_polling_and_result(mock_client, response, True)

        assert result["changed"] is True
        assert result["id"] == "run-123"
        mock_wait_for_state.assert_called_once_with(mock_client, "run-123", 25, 5)

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.wait_for_state")
    def test_handle_polling_failure(self, mock_wait_for_state):
        """Test handle_polling_and_result with polling failure."""
        mock_client = Mock()
        response = {"data": {"id": "run-123"}}

        mock_wait_for_state.return_value = ("failure", None)

        result = handle_polling_and_result(mock_client, response, True)

        assert result["failed"] is True
        assert "failure" in result["msg"]

    def test_handle_polling_disabled(self):
        """Test handle_polling_and_result with polling disabled."""
        mock_client = Mock()
        response = {"data": {"id": "run-123", "attributes": {"status": "pending"}}}

        result = handle_polling_and_result(mock_client, response, False)

        assert result["changed"] is True
        assert result["id"] == "run-123"
        assert result["attributes"]["status"] == "pending"

    def test_handle_polling_with_custom_run_id(self):
        """Test handle_polling_and_result with custom run_id parameter."""
        mock_client = Mock()
        response = {"data": {"id": "run-456"}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.wait_for_state") as mock_wait:
            mock_wait.return_value = ("success", {"data": {"id": "run-123"}})

            result = handle_polling_and_result(mock_client, response, True, run_id="run-123")

            mock_wait.assert_called_once_with(mock_client, "run-123", 25, 5)

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.wait_for_state")
    def test_handle_polling_with_custom_timeouts(self, mock_wait_for_state):
        """Test handle_polling_and_result with custom poll_timeout and poll_interval."""
        mock_client = Mock()
        response = {"data": {"id": "run-123"}}

        mock_wait_for_state.return_value = ("success", {"data": {"id": "run-123"}})

        result = handle_polling_and_result(mock_client, response, True, poll_timeout=60, poll_interval=10)

        assert result["changed"] is True
        mock_wait_for_state.assert_called_once_with(mock_client, "run-123", 60, 10)


class TestIdempotencyCheck:
    """Test cases for idempotency_check decorator."""

    def test_idempotency_check_already_in_state(self):
        """Test idempotency check when run is already in desired state."""
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run") as mock_get_run:
            mock_get_run.return_value = {"data": {"id": "run-123", "attributes": {"status": "applied"}}}

            @idempotency_check
            def state_applied(client, **kwargs):
                return {"changed": True, "new_state": True}

            result = state_applied(mock_client, run_id="run-123")

            assert result["changed"] is False
            assert "run" in result
            mock_get_run.assert_called_once_with(mock_client, "run-123")

    def test_idempotency_check_needs_change(self):
        """Test idempotency check when run needs to change state."""
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run") as mock_get_run:
            mock_get_run.return_value = {"data": {"id": "run-123", "attributes": {"status": "pending"}}}

            @idempotency_check
            def state_applied(client, **kwargs):
                return {"changed": True, "new_state": True}

            result = state_applied(mock_client, run_id="run-123")

            assert result["changed"] is True
            assert result["new_state"] is True

    def test_idempotency_check_no_run_id(self):
        """Test idempotency check when no run_id is provided."""
        mock_client = Mock()

        @idempotency_check
        def state_applied(client, **kwargs):
            return {"changed": True, "new_state": True}

        result = state_applied(mock_client)

        assert result["changed"] is True
        assert result["new_state"] is True


class TestStatePresent:
    """Test cases for state_present function."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.handle_polling_and_result")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.create_run")
    def test_state_present_success(self, mock_create_run, mock_handle_polling):
        """Test state_present with successful run creation."""
        mock_client = Mock()
        mock_create_run.return_value = {"data": {"id": "run-123"}}
        mock_handle_polling.return_value = {"changed": True, "id": "run-123"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.RunRequest") as mock_run_request:
            mock_request_instance = Mock()
            mock_request_instance.model_dump.return_value = {"data": {"type": "runs"}}
            mock_run_request.create.return_value = mock_request_instance

            result = state_present(
                mock_client,
                workspace_id="ws-123",
                message="Test run",
                tf_hostname="app.terraform.io",
                tf_token="token",
                state="present",
                organization="test-org",
                workspace="test-ws",
            )

            assert result["changed"] is True
            assert result["id"] == "run-123"
            mock_create_run.assert_called_once()
            mock_handle_polling.assert_called_once()

    def test_state_present_filters_params(self):
        """Test state_present properly filters out unwanted parameters."""
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.RunRequest") as mock_run_request:
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.create_run"):
                with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.handle_polling_and_result"):
                    mock_request_instance = Mock()
                    mock_run_request.create.return_value = mock_request_instance

                    state_present(
                        mock_client,
                        workspace_id="ws-123",
                        tf_hostname="app.terraform.io",  # Should be filtered
                        tf_token="token",  # Should be filtered
                        state="present",  # Should be filtered
                        organization="test-org",  # Should be filtered
                        workspace="test-ws",  # Should be filtered
                        message="Test run",  # Should be kept
                    )

                    # Verify that filtered params are not passed to RunRequest.create
                    call_args = mock_run_request.create.call_args
                    assert "tf_hostname" not in call_args[1]
                    assert "tf_token" not in call_args[1]
                    assert "state" not in call_args[1]
                    assert "organization" not in call_args[1]
                    assert "workspace" not in call_args[1]
                    assert call_args[1]["workspace_id"] == "ws-123"


class TestStateApplied:
    """Test cases for state_applied function."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.handle_polling_and_result")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.apply_run")
    def test_state_applied_success(self, mock_apply_run, mock_handle_polling):
        """Test state_applied with successful run application."""
        mock_client = Mock()
        mock_apply_run.return_value = {"data": {"id": "run-123"}}
        mock_handle_polling.return_value = {"changed": True, "id": "run-123"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run") as mock_get_run:
            mock_get_run.return_value = {"data": {"attributes": {"status": "pending"}}}

            result = state_applied(mock_client, run_id="run-123", poll=True)

            assert result["changed"] is True
            mock_apply_run.assert_called_once_with(mock_client, "run-123")
            mock_handle_polling.assert_called_once_with(mock_client, mock_apply_run.return_value, True, "run-123")


class TestStateDiscarded:
    """Test cases for state_discarded function."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.handle_polling_and_result")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.discard_run")
    def test_state_discarded_success(self, mock_discard_run, mock_handle_polling):
        """Test state_discarded with successful run discard."""
        mock_client = Mock()
        mock_discard_run.return_value = {"data": {"id": "run-123"}}
        mock_handle_polling.return_value = {"changed": True, "id": "run-123"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run") as mock_get_run:
            mock_get_run.return_value = {"data": {"attributes": {"status": "pending"}}}

            result = state_discarded(mock_client, run_id="run-123", poll=False)

            assert result["changed"] is True
            mock_discard_run.assert_called_once_with(mock_client, "run-123")
            mock_handle_polling.assert_called_once_with(mock_client, mock_discard_run.return_value, False, "run-123")


class TestStateCanceled:
    """Test cases for state_canceled function."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.handle_polling_and_result")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.cancel_run")
    def test_state_canceled_success(self, mock_cancel_run, mock_handle_polling):
        """Test state_canceled with successful run cancellation."""
        mock_client = Mock()
        mock_cancel_run.return_value = {"data": {"id": "run-123"}}
        mock_handle_polling.return_value = {"changed": True, "id": "run-123"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run") as mock_get_run:
            mock_get_run.return_value = {"data": {"attributes": {"status": "pending"}}}

            result = state_canceled(mock_client, run_id="run-123")

            assert result["changed"] is True
            mock_cancel_run.assert_called_once_with(mock_client, "run-123")
            mock_handle_polling.assert_called_once_with(mock_client, mock_cancel_run.return_value, False, "run-123")


class TestGetWorkspaceId:
    """Test cases for get_workspace_id function."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_workspace")
    def test_get_workspace_id_success(self, mock_get_workspace):
        """Test get_workspace_id with successful workspace retrieval."""
        mock_client = Mock()
        mock_get_workspace.return_value = {"data": {"id": "ws-123", "attributes": {"name": "test-workspace"}}}

        result = get_workspace_id(mock_client, "test-workspace", "test-org")

        assert result == "ws-123"
        mock_get_workspace.assert_called_once_with(mock_client, "test-org", "test-workspace")

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_workspace")
    def test_get_workspace_id_not_found(self, mock_get_workspace):
        """Test get_workspace_id when workspace is not found."""
        mock_client = Mock()
        mock_get_workspace.return_value = None

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.TerraformError") as mock_error:
            mock_error.side_effect = Exception("Workspace not found")

            with pytest.raises(Exception, match="Workspace not found"):
                get_workspace_id(mock_client, "nonexistent", "test-org")


class TestMainFunction:
    """Test cases for main function."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.state_present")
    def test_main_state_present_with_workspace_id(self, mock_state_present, mock_tf_client, mock_module_class):
        """Test main function with state=present and workspace_id provided."""
        mock_module = EnhancedDummyModule({"workspace_id": "ws-123", "message": "Test run", "state": "present", "poll": True})
        mock_module_class.return_value = mock_module

        mock_client_instance = Mock()
        mock_tf_client.return_value = mock_client_instance

        mock_state_present.return_value = {"changed": True, "id": "run-123"}

        with pytest.raises(SystemExit):
            main()

        mock_state_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.state_present")
    def test_main_state_present_with_workspace_name(self, mock_state_present, mock_get_workspace_id, mock_tf_client, mock_module_class):
        """Test main function with state=present and workspace name provided."""
        mock_module = EnhancedDummyModule({"workspace": "test-workspace", "organization": "test-org", "message": "Test run", "state": "present", "poll": True})
        mock_module_class.return_value = mock_module

        mock_client_instance = Mock()
        mock_tf_client.return_value = mock_client_instance

        mock_get_workspace_id.return_value = "ws-123"
        mock_state_present.return_value = {"changed": True, "id": "run-123"}

        with pytest.raises(SystemExit):
            main()

        mock_get_workspace_id.assert_called_once_with(mock_client_instance, "test-org", "test-workspace")
        mock_state_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.state_applied")
    def test_main_state_applied(self, mock_state_applied, mock_tf_client, mock_module_class):
        """Test main function with state=applied."""
        mock_module = EnhancedDummyModule({"workspace_id": "ws-123", "run_id": "run-123", "state": "applied", "poll": True})
        mock_module_class.return_value = mock_module

        mock_client_instance = Mock()
        mock_tf_client.return_value = mock_client_instance

        mock_state_applied.return_value = {"changed": True, "id": "run-123"}

        with pytest.raises(SystemExit):
            main()

        mock_state_applied.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.state_discarded")
    def test_main_state_discarded(self, mock_state_discarded, mock_tf_client, mock_module_class):
        """Test main function with state=discarded."""
        mock_module = EnhancedDummyModule({"workspace_id": "ws-123", "run_id": "run-123", "state": "discarded", "poll": False})
        mock_module_class.return_value = mock_module

        mock_client_instance = Mock()
        mock_tf_client.return_value = mock_client_instance

        mock_state_discarded.return_value = {"changed": True, "id": "run-123"}

        with pytest.raises(SystemExit):
            main()

        mock_state_discarded.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.state_canceled")
    def test_main_state_canceled(self, mock_state_canceled, mock_tf_client, mock_module_class):
        """Test main function with state=canceled."""
        mock_module = EnhancedDummyModule({"workspace_id": "ws-123", "run_id": "run-123", "state": "canceled", "poll": True})
        mock_module_class.return_value = mock_module

        mock_client_instance = Mock()
        mock_tf_client.return_value = mock_client_instance

        mock_state_canceled.return_value = {"changed": True, "id": "run-123"}

        with pytest.raises(SystemExit):
            main()

        mock_state_canceled.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.TerraformClient")
    def test_main_check_mode(self, mock_tf_client, mock_module_class):
        """Test main function in check mode."""
        mock_module = EnhancedDummyModule(
            {
                "workspace_id": "ws-123",
                "state": "present",
            }
        )
        mock_module.check_mode = True
        mock_module_class.return_value = mock_module

        mock_client_instance = Mock()
        mock_tf_client.return_value = mock_client_instance

        with pytest.raises(SystemExit):
            main()

        assert mock_module.exit_args["changed"] is True
        assert "Check mode" in mock_module.exit_args["msg"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.TerraformClient")
    def test_main_invalid_state(self, mock_tf_client, mock_module_class):
        """Test main function with invalid state."""
        mock_module = EnhancedDummyModule(
            {
                "workspace_id": "ws-123",
                "state": "invalid_state",
            }
        )
        mock_module_class.return_value = mock_module

        mock_client_instance = Mock()
        mock_tf_client.return_value = mock_client_instance

        with pytest.raises(AssertionError):
            main()

        assert mock_module.failed is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.TerraformClient")
    def test_main_exception_handling(self, mock_tf_client, mock_module_class):
        """Test main function exception handling."""
        mock_module = EnhancedDummyModule(
            {
                "workspace_id": "ws-123",
                "state": "present",
            }
        )
        mock_module_class.return_value = mock_module

        # Make TerraformClient constructor raise an exception
        mock_tf_client.side_effect = Exception("Connection error")

        with pytest.raises(AssertionError):
            main()

        assert mock_module.failed is True


class TestRunsModuleIntegration:
    """Integration-style tests for the runs module."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.AnsibleTerraformModule")
    def test_argument_spec_validation(self, mock_module_class):
        """Test that argument spec is properly configured."""
        main()

        # Get the call arguments to AnsibleTerraformModule
        call_args = mock_module_class.call_args[1]
        argument_spec = call_args["argument_spec"]

        # Verify all expected parameters are present
        expected_params = [
            "workspace_id",
            "workspace",
            "organization",
            "poll",
            "poll_interval",
            "poll_timeout",
            "configuration_version",
            "run_message",
            "auto_apply",
            "save_plan",
            "variables",
            "plan_only",
            "is_destroy",
            "target_addrs",
            "state",
            "run_id",
        ]

        for param in expected_params:
            assert param in argument_spec

        # Verify specific configurations
        assert argument_spec["state"]["choices"] == ["present", "applied", "discarded", "canceled"]
        assert argument_spec["state"]["default"] == "present"
        assert argument_spec["poll"]["default"] is True
        assert argument_spec["poll_interval"]["default"] == 5
        assert argument_spec["poll_timeout"]["default"] == 25

        # Verify validation rules
        assert call_args["required_together"] == [["workspace", "organization"]]
        assert len(call_args["required_if"]) == 4
        assert len(call_args["mutually_exclusive"]) == 4

    def test_complete_workflow_present_state(self):
        """Test complete workflow for creating a run."""
        mock_client = Mock()

        # Mock all the dependencies
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.RunRequest") as mock_run_request:
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.create_run") as mock_create_run:
                with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.wait_for_state") as mock_wait:

                    # Setup mocks
                    mock_request_instance = Mock()
                    mock_request_instance.model_dump.return_value = {"data": {"type": "runs"}}
                    mock_run_request.create.return_value = mock_request_instance

                    mock_create_run.return_value = {"data": {"id": "run-123"}}
                    mock_wait.return_value = ("success", {"data": {"id": "run-123", "status": "applied"}})

                    # Execute the workflow
                    result = state_present(mock_client, workspace_id="ws-123", message="Test run", auto_apply=True, poll=True)

                    # Verify the complete flow
                    assert result["changed"] is True
                    mock_run_request.create.assert_called_once()
                    mock_create_run.assert_called_once()
                    mock_wait.assert_called_once()

    def test_error_handling_consistency(self):
        """Test that all state functions handle errors consistently."""
        mock_client = Mock()

        # Test that all state functions can handle exceptions from their dependencies
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.create_run", side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                state_present(mock_client, workspace_id="ws-123")

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.apply_run", side_effect=Exception("Apply Error")):
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run"):
                with pytest.raises(Exception, match="Apply Error"):
                    state_applied(mock_client, run_id="run-123")

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.discard_run", side_effect=Exception("Discard Error")):
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run"):
                with pytest.raises(Exception, match="Discard Error"):
                    state_discarded(mock_client, run_id="run-123")

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.cancel_run", side_effect=Exception("Cancel Error")):
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run"):
                with pytest.raises(Exception, match="Cancel Error"):
                    state_canceled(mock_client, run_id="run-123")


class TestRunsModuleEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_wait_for_state_with_custom_timeout(self):
        """Test wait_for_state with custom timeout and polling interval."""
        mock_client = Mock()

        with patch("time.sleep") as mock_sleep:
            with patch("time.time", side_effect=[0, 20, 100]):  # Simulate timeout after one iteration
                with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.get_run") as mock_get_run:
                    with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.RunStates") as mock_run_states:
                        mock_get_run.return_value = {"data": {"attributes": {"status": "pending"}}}
                        mock_run_states.is_success_state.return_value = False
                        mock_run_states.is_failure_state.return_value = False

                        status, response = wait_for_state(mock_client, "run-123", timeout=30, polling_interval=10)

                        assert status == "timeout"

    def test_handle_polling_with_missing_run_id(self):
        """Test handle_polling_and_result when response has no run ID."""
        mock_client = Mock()
        response = {"data": {}}  # No ID field

        result = handle_polling_and_result(mock_client, response, False)

        assert result["changed"] is True
        # Should not attempt polling without run_id

    def test_state_present_with_empty_variables(self):
        """Test state_present with empty variables list."""
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.RunRequest") as mock_run_request:
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.create_run"):
                with patch("ansible_collections.hashicorp.terraform.plugins.modules.runs.handle_polling_and_result"):
                    mock_request_instance = Mock()
                    mock_run_request.create.return_value = mock_request_instance

                    state_present(mock_client, workspace_id="ws-123", variables=[])

                    # Should still call create_run successfully
                    mock_run_request.create.assert_called_once()
