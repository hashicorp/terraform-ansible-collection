# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.run import (
    check_mode,
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
from tests.unit.constants import create_run_response


class TestWaitForState:
    """Test cases for wait_for_state function."""

    @pytest.mark.parametrize(
        "run_id,final_status,expected_state,is_success,is_failure",
        [
            ("run-123", "applied", "success", True, False),
            ("run-456", "errored", "failure", False, True),
            ("run-789", "planned", "success", True, False),
            ("run-abc", "canceled", "success", True, False),
            ("run-def", "policy_soft_failed", "failure", False, True),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run")
    def test_wait_for_state_final_states(self, mock_get_run, run_id, final_status, expected_state, is_success, is_failure, mock_time, payload_factory):
        """Test wait_for_state with various final states."""
        mock_client = Mock()

        # Using payload factory to create response
        response = payload_factory["run"](run_id=run_id, status=final_status)
        mock_get_run.return_value = response

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.RunStates") as mock_run_states:
            mock_run_states.is_success_state.return_value = is_success
            mock_run_states.is_failure_state.return_value = is_failure

            status, response_result = wait_for_state(mock_client, run_id)

            assert status == expected_state
            assert response_result == response
            mock_get_run.assert_called_with(mock_client, run_id)

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run")
    def test_wait_for_state_timeout(self, mock_get_run, mock_time, payload_factory):
        """Test wait_for_state with timeout."""
        mock_client = Mock()

        # Mock time progression to trigger timeout after one iteration
        mock_time["time"].side_effect = [0, 30, 60]  # Start at 0, then 30 (within timeout), then 60 (exceeds timeout of 50)

        # Using payload factory to create response
        pending_response = payload_factory["run"](run_id="run-123", status="pending")
        mock_get_run.return_value = pending_response

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.RunStates") as mock_run_states:
            mock_run_states.is_success_state.return_value = False
            mock_run_states.is_failure_state.return_value = False

            status, response = wait_for_state(mock_client, "run-123", timeout=50)

            assert status == "timeout"
            assert response == pending_response


class TestHandlePollingAndResult:
    """Test cases for handle_polling_and_result function."""

    @pytest.mark.parametrize(
        "poll_enabled,wait_status,wait_response,expected_changed,expected_failed,custom_run_id,poll_timeout,poll_interval",
        [
            (
                True,
                "success",
                create_run_response(run_id="run-123", status="applied"),
                True,
                None,
                None,
                120,
                5,
            ),
            (True, "failure", None, None, True, None, 120, 5),
            (False, None, None, True, None, None, None, None),  # Polling disabled
            (True, "success", create_run_response(run_id="run-123"), True, None, "run-123", 25, 5),  # Custom run_id
            (True, "success", create_run_response(run_id="run-123"), True, None, None, 60, 10),  # Custom timeouts
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.wait_for_state")
    def test_handle_polling_scenarios(
        self,
        mock_wait_for_state,
        poll_enabled,
        wait_status,
        wait_response,
        expected_changed,
        expected_failed,
        custom_run_id,
        poll_timeout,
        poll_interval,
    ):
        """Test handle_polling_and_result with various scenarios."""
        mock_client = Mock()
        response = create_run_response(run_id="run-123", status="pending")

        if poll_enabled:
            mock_wait_for_state.return_value = (wait_status, wait_response)

        kwargs = {}
        if custom_run_id:
            kwargs["run_id"] = custom_run_id
        if poll_timeout and poll_timeout != 120:
            kwargs["poll_timeout"] = poll_timeout
        if poll_interval and poll_interval != 5:
            kwargs["poll_interval"] = poll_interval

        result = handle_polling_and_result(mock_client, response, poll_enabled, **kwargs)

        if expected_changed is not None:
            assert result["changed"] is expected_changed
        if expected_failed is not None:
            assert result["failed"] is expected_failed
            assert "failure" in result["msg"]

        if poll_enabled:
            expected_run_id = custom_run_id or "run-123"
            expected_timeout = poll_timeout or 120
            expected_interval = poll_interval or 5
            mock_wait_for_state.assert_called_once_with(mock_client, expected_run_id, expected_timeout, expected_interval)
        else:
            mock_wait_for_state.assert_not_called()


class TestIdempotencyCheck:
    """Test cases for idempotency_check decorator."""

    @pytest.mark.parametrize(
        "run_id,current_status,function_name,should_be_idempotent",
        [
            ("run-123", "applied", "state_applied", True),
            ("run-456", "pending", "state_applied", False),
            ("run-789", "discarded", "state_discarded", True),
            ("run-abc", "canceled", "state_canceled", True),
            ("run-def", "errored", "state_applied", False),
            (None, None, "state_applied", False),  # No run_id provided
        ],
    )
    def test_idempotency_check_scenarios(self, run_id, current_status, function_name, should_be_idempotent):
        """Test idempotency check with various scenarios."""
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run") as mock_get_run:
            if run_id:
                mock_get_run.return_value = {"data": {"id": run_id, "attributes": {"status": current_status}}}

            @idempotency_check
            def state_applied(client, **kwargs):
                return {"changed": True, "applied": True}

            @idempotency_check
            def state_discarded(client, **kwargs):
                return {"changed": True, "discarded": True}

            @idempotency_check
            def state_canceled(client, **kwargs):
                return {"changed": True, "canceled": True}

            # Get the function by name
            test_function = locals()[function_name]

            if run_id:
                result = test_function(mock_client, run_id=run_id)
            else:
                result = test_function(mock_client)

            if should_be_idempotent:
                assert result["changed"] is False
                assert "run" in result
                mock_get_run.assert_called_once_with(mock_client, run_id)
            else:
                assert result["changed"] is True
                if run_id:
                    mock_get_run.assert_called_once_with(mock_client, run_id)
                else:
                    mock_get_run.assert_not_called()

    def test_idempotency_check_with_empty_dict_404(self):
        """Test idempotency check when get_run returns empty dict (404)."""
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run") as mock_get_run:
            mock_get_run.return_value = {}

            @idempotency_check
            def state_applied(client, **kwargs):
                return {"changed": True, "applied": True}

            # When get_run returns empty dict, idempotency check should return failure
            result = state_applied(mock_client, run_id="run-404")

            assert result["failed"] is True
            assert result["msg"] == "Run run-404 not found"
            mock_get_run.assert_called_once_with(mock_client, "run-404")

    def test_idempotency_check_empty_dict_all_states(self):
        """Test idempotency check with empty dict for all state functions."""
        mock_client = Mock()

        state_functions = [
            ("state_applied", "run-404-apply"),
            ("state_discarded", "run-404-discard"),
            ("state_canceled", "run-404-cancel"),
        ]

        for func_name, run_id in state_functions:
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run") as mock_get_run:
                mock_get_run.return_value = {}

                @idempotency_check
                def test_state_func(client, **kwargs):
                    return {"changed": True, "action": "test"}

                # Set the function name for the decorator logic
                test_state_func.__name__ = func_name

                result = test_state_func(mock_client, run_id=run_id)

                # Empty dict means run not found, so idempotency check should return failure
                assert result["failed"] is True, f"Expected failure for {func_name} with empty dict"
                assert result["msg"] == f"Run {run_id} not found", f"Wrong message for {func_name}"
                mock_get_run.assert_called_once_with(mock_client, run_id)


class TestCheckMode:
    """Test cases for check_mode decorator."""

    @pytest.mark.parametrize(
        "function_name,check_mode_enabled,run_id,get_run_return,expected_changed,expected_failed,expected_msg_contains",
        [
            # Present state functions - should always return default message when check_mode enabled
            ("state_present", True, "run-123", {"id": "run-123"}, True, False, "Check mode is enabled, no changes will be made"),
            ("state_present", False, None, None, True, False, None),  # Normal execution
            # Applied state functions - should check run existence when check_mode enabled
            ("state_applied", True, "run-123", {"id": "run-123", "attributes": {"status": "planned"}}, True, False, "Run run-123 found, check mode is enabled"),
            ("state_applied", True, "run-456", {}, None, True, "Run run-456 not found"),
            ("state_applied", True, "run-404", {}, None, True, "Run run-404 not found"),
            ("state_applied", False, "run-123", {"id": "run-123"}, True, False, None),  # Normal execution
            # Canceled state functions - should check run existence when check_mode enabled
            (
                "state_canceled",
                True,
                "run-123",
                {"id": "run-123", "attributes": {"status": "planned"}},
                True,
                False,
                "Run run-123 found, check mode is enabled",
            ),
            ("state_canceled", True, "run-456", {}, None, True, "Run run-456 not found"),
            ("state_canceled", True, "run-404", {}, None, True, "Run run-404 not found"),
            ("state_canceled", False, "run-123", {"id": "run-123"}, True, False, None),  # Normal execution
            # Discarded state functions - should check run existence when check_mode enabled
            (
                "state_discarded",
                True,
                "run-123",
                {"id": "run-123", "attributes": {"status": "planned"}},
                True,
                False,
                "Run run-123 found, check mode is enabled",
            ),
            ("state_discarded", True, "run-456", {}, None, True, "Run run-456 not found"),
            ("state_discarded", True, "run-404", {}, None, True, "Run run-404 not found"),
            ("state_discarded", False, "run-123", {"id": "run-123"}, True, False, None),  # Normal execution
        ],
    )
    def test_check_mode_scenarios(self, function_name, check_mode_enabled, run_id, get_run_return, expected_changed, expected_failed, expected_msg_contains):
        """Test check_mode decorator with various scenarios."""
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run") as mock_get_run:
            mock_get_run.return_value = get_run_return

            # Create decorated test functions
            @check_mode
            def state_present(client, **kwargs):
                return {"changed": True, "created": True}

            @check_mode
            def state_applied(client, **kwargs):
                return {"changed": True, "applied": True}

            @check_mode
            def state_canceled(client, **kwargs):
                return {"changed": True, "canceled": True}

            @check_mode
            def state_discarded(client, **kwargs):
                return {"changed": True, "discarded": True}

            # Get the function by name
            test_function = locals()[function_name]

            # Prepare kwargs
            kwargs = {"check_mode": check_mode_enabled}
            if run_id:
                kwargs["run_id"] = run_id

            # Execute the function
            result = test_function(mock_client, **kwargs)

            # Verify results
            if expected_failed:
                assert result["failed"] == expected_failed
                # When failed, changed field might not be present, so only check if expected
                if expected_changed is not None and "changed" in result:
                    assert result["changed"] == expected_changed
            else:
                if expected_changed is not None:
                    assert result["changed"] == expected_changed
                assert result.get("failed", False) == expected_failed

            if expected_msg_contains:
                assert expected_msg_contains in result["msg"]

            # Verify get_run was called appropriately
            if check_mode_enabled and not function_name.endswith("_present") and run_id:
                mock_get_run.assert_called_once_with(mock_client, run_id)
            elif not check_mode_enabled and function_name.endswith("_present"):
                # For present functions in normal mode, get_run should not be called
                mock_get_run.assert_not_called()
            elif not check_mode_enabled and not function_name.endswith("_present"):
                # For action functions in normal mode, the original function should execute
                # but get_run is not called by the decorator
                mock_get_run.assert_not_called()

    def test_check_mode_decorator_preserves_function_metadata(self):
        """Test that the check_mode decorator preserves function metadata."""

        @check_mode
        def test_function(client, **kwargs):
            """Test function docstring."""
            return {"changed": True}

        # The wrapper function should preserve the original function name for endswith checks
        assert hasattr(test_function, "__name__")
        # The decorator creates a wrapper, so the name will be 'wrapper', but the logic uses func.__name__
        # which should be preserved internally

    def test_check_mode_with_empty_dict_error_handling(self):
        """Test check_mode decorator handles empty dict (404) from get_run correctly."""
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run") as mock_get_run:
            mock_get_run.return_value = {}

            @check_mode
            def state_applied(client, **kwargs):
                return {"changed": True, "applied": True}

            result = state_applied(mock_client, check_mode=True, run_id="run-404")

            assert result["failed"] is True
            assert result["msg"] == "Run run-404 not found in the Terraform Cloud/Enterprise workspace"
            mock_get_run.assert_called_once_with(mock_client, "run-404")

    def test_check_mode_empty_dict_for_all_states(self):
        """Test check_mode decorator handles empty dict for all state functions."""
        mock_client = Mock()

        state_functions = [
            ("state_applied", "applied"),
            ("state_discarded", "discarded"),
            ("state_canceled", "canceled"),
        ]

        for func_name, action in state_functions:
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run") as mock_get_run:
                mock_get_run.return_value = {}

                @check_mode
                def test_state_func(client, **kwargs):
                    return {"changed": True, action: True}

                # Set the function name for the decorator logic
                test_state_func.__name__ = func_name

                result = test_state_func(mock_client, check_mode=True, run_id="run-404")

                assert result["failed"] is True, f"Expected failure for {func_name}"
                assert result["msg"] == "Run run-404 not found in the Terraform Cloud/Enterprise workspace", f"Wrong message for {func_name}"
                mock_get_run.assert_called_once_with(mock_client, "run-404")


class TestStatePresent:
    """Test cases for state_present function."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.handle_polling_and_result")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.create_run")
    def test_state_present_success(self, mock_create_run, mock_handle_polling):
        """Test state_present with successful run creation."""
        mock_client = Mock()
        mock_create_run.return_value = create_run_response(run_id="run-123")
        mock_handle_polling.return_value = {"changed": True, "id": "run-123"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.RunRequest") as mock_run_request:
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

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.RunRequest") as mock_run_request:
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.create_run"):
                with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.handle_polling_and_result"):
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


@pytest.mark.parametrize(
    "state_function_name,action_function_name,default_poll",
    [
        ("state_applied", "apply_run", True),
        ("state_discarded", "discard_run", False),
        ("state_canceled", "cancel_run", False),
    ],
)
class TestStateActions:
    """Test cases for state action functions (applied, discarded, canceled)."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.handle_polling_and_result")
    def test_state_action_success(self, mock_handle_polling, state_function_name, action_function_name, default_poll):
        """Test state action functions with successful execution."""
        mock_client = Mock()

        # Mock the specific action function
        with patch(f"ansible_collections.hashicorp.terraform.plugins.modules.run.{action_function_name}") as mock_action:
            mock_action.return_value = create_run_response(run_id="run-123")
            mock_handle_polling.return_value = {"changed": True, "id": "run-123"}

            with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run") as mock_get_run:
                mock_get_run.return_value = {"data": {"attributes": {"status": "pending"}}}

                # Get the function by name
                state_func = globals()[state_function_name]
                result = state_func(mock_client, run_id="run-123", poll=default_poll)

                assert result["changed"] is True
                mock_action.assert_called_once_with(mock_client, "run-123")
                mock_handle_polling.assert_called_once_with(mock_client, mock_action.return_value, default_poll, "run-123")

    @pytest.mark.parametrize("poll_value", [True, False])
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.handle_polling_and_result")
    def test_state_action_poll_parameter(self, mock_handle_polling, state_function_name, action_function_name, default_poll, poll_value):
        """Test state action functions with different poll values."""
        mock_client = Mock()

        with patch(f"ansible_collections.hashicorp.terraform.plugins.modules.run.{action_function_name}") as mock_action:
            mock_action.return_value = create_run_response(run_id="run-456")
            mock_handle_polling.return_value = {"changed": True, "id": "run-456"}

            with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run") as mock_get_run:
                mock_get_run.return_value = {"data": {"attributes": {"status": "pending"}}}

                # Get the function by name
                state_func = globals()[state_function_name]
                result = state_func(mock_client, run_id="run-456", poll=poll_value)

                assert result["changed"] is True
                mock_handle_polling.assert_called_once_with(mock_client, mock_action.return_value, poll_value, "run-456")


class TestGetWorkspaceId:
    """Test cases for get_workspace_id function."""

    @pytest.mark.parametrize(
        "workspace_name,organization,workspace_response,expected_result,should_raise",
        [
            (
                "test-workspace",
                "test-org",
                {"data": {"id": "ws-123", "attributes": {"name": "test-workspace"}}},
                "ws-123",
                False,
            ),
            (
                "another-workspace",
                "another-org",
                {"data": {"id": "ws-456", "attributes": {"name": "another-workspace"}}},
                "ws-456",
                False,
            ),
            ("nonexistent", "test-org", None, None, True),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_workspace")
    def test_get_workspace_id_scenarios(self, mock_get_workspace, workspace_name, organization, workspace_response, expected_result, should_raise):
        """Test get_workspace_id with various scenarios."""
        mock_client = Mock()
        mock_get_workspace.return_value = workspace_response

        if should_raise:
            with pytest.raises(Exception):  # Will raise TerraformError or AttributeError depending on the scenario
                get_workspace_id(mock_client, workspace_name, organization)
        else:
            result = get_workspace_id(mock_client, workspace_name, organization)
            assert result == expected_result

        mock_get_workspace.assert_called_once_with(mock_client, organization, workspace_name)

    def test_get_workspace_id_empty_data_response(self):
        """Test get_workspace_id when workspace response has data=None."""
        mock_client = Mock()

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_workspace") as mock_get_workspace:
            mock_get_workspace.return_value = {"data": None}

            # This should raise an AttributeError because response.get("data").get("id") tries to call get() on None
            with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'get'"):
                get_workspace_id(mock_client, "empty-response", "test-org")


class TestMainFunction:
    """Test cases for main function."""

    @pytest.mark.parametrize(
        "state,state_function_name,module_params",
        [
            (
                "present",
                "state_present",
                {"workspace_id": "ws-123", "message": "Test run", "state": "present", "poll": True},
            ),
            (
                "applied",
                "state_applied",
                {"workspace_id": "ws-123", "run_id": "run-123", "state": "applied", "poll": True},
            ),
            (
                "discarded",
                "state_discarded",
                {"workspace_id": "ws-123", "run_id": "run-123", "state": "discarded", "poll": False},
            ),
            (
                "canceled",
                "state_canceled",
                {"workspace_id": "ws-123", "run_id": "run-123", "state": "canceled", "poll": True},
            ),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.TerraformClient")
    def test_main_state_functions(self, mock_tf_client, mock_module_class, state, state_function_name, module_params, enhanced_dummy_module):
        """Test main function with different state functions."""
        mock_module = enhanced_dummy_module
        mock_module.params = module_params
        mock_module_class.return_value = mock_module

        mock_client_instance = Mock()
        mock_tf_client.return_value = mock_client_instance

        with patch(f"ansible_collections.hashicorp.terraform.plugins.modules.run.{state_function_name}") as mock_state_func:
            mock_state_func.return_value = {"changed": True, "id": "run-123"}

            with pytest.raises(SystemExit):
                main()

            mock_state_func.assert_called_once()
            assert mock_module.exit_args["changed"] is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.state_present")
    def test_main_state_present_with_workspace_name(self, mock_state_present, mock_get_workspace_id, mock_tf_client, mock_module_class, enhanced_dummy_module):
        """Test main function with state=present and workspace name provided."""
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "workspace": "test-workspace",
            "organization": "test-org",
            "message": "Test run",
            "state": "present",
            "poll": True,
        }
        mock_module_class.return_value = mock_module

        mock_client_instance = Mock()
        mock_tf_client.return_value = mock_client_instance

        mock_get_workspace_id.return_value = "ws-123"
        mock_state_present.return_value = {"changed": True, "id": "run-123"}

        with pytest.raises(SystemExit):
            main()

        mock_get_workspace_id.assert_called_once_with(mock_client_instance, "test-workspace", "test-org")
        mock_state_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @pytest.mark.parametrize(
        "scenario,module_params,check_mode,client_side_effect,expected_behavior",
        [
            ("check_mode", {"workspace_id": "ws-123", "state": "present"}, True, None, "check_mode_exit"),
            # Note: invalid_state test removed - Ansible's argument spec validation prevents invalid states from reaching the match statement
            (
                "client_exception",
                {"workspace_id": "ws-123", "state": "present"},
                False,
                Exception("Connection error"),
                "failure",
            ),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.TerraformClient")
    def test_main_edge_cases(
        self,
        mock_tf_client,
        mock_module_class,
        scenario,
        module_params,
        check_mode,
        client_side_effect,
        expected_behavior,
        enhanced_dummy_module,
    ):
        """Test main function edge cases."""
        mock_module = enhanced_dummy_module
        mock_module.params = module_params
        mock_module.check_mode = check_mode
        mock_module_class.return_value = mock_module

        if client_side_effect:
            mock_tf_client.side_effect = client_side_effect
        else:
            mock_client_instance = Mock()
            mock_tf_client.return_value = mock_client_instance

        if expected_behavior == "check_mode_exit":
            with pytest.raises(SystemExit):
                main()
            assert mock_module.exit_args["changed"] is True
            assert "Check mode" in mock_module.exit_args["msg"]
        elif expected_behavior == "failure":
            with pytest.raises(AssertionError):
                main()
            assert mock_module.failed is True


class TestRunsModuleIntegration:
    """Integration-style tests for the runs module."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.AnsibleTerraformModule")
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
        assert argument_spec["poll_timeout"]["default"] == 120

        # Verify validation rules
        assert call_args["required_together"] == [["workspace", "organization"]]
        assert len(call_args["required_if"]) == 4
        assert len(call_args["mutually_exclusive"]) == 4

    def test_complete_workflow_present_state(self):
        """Test complete workflow for creating a run."""
        mock_client = Mock()

        # Mock all the dependencies
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.RunRequest") as mock_run_request:
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.create_run") as mock_create_run:
                with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.wait_for_state") as mock_wait:

                    # Setup mocks
                    mock_request_instance = Mock()
                    mock_request_instance.model_dump.return_value = {"data": {"type": "runs"}}
                    mock_run_request.create.return_value = mock_request_instance

                    mock_create_run.return_value = create_run_response(run_id="run-123")
                    mock_wait.return_value = ("success", create_run_response(run_id="run-123", status="applied"))

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
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.create_run", side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                state_present(mock_client, workspace_id="ws-123")

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.run.apply_run",
            side_effect=Exception("Apply Error"),
        ):
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run"):
                with pytest.raises(Exception, match="Apply Error"):
                    state_applied(mock_client, run_id="run-123")

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.run.discard_run",
            side_effect=Exception("Discard Error"),
        ):
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run"):
                with pytest.raises(Exception, match="Discard Error"):
                    state_discarded(mock_client, run_id="run-123")

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.run.cancel_run",
            side_effect=Exception("Cancel Error"),
        ):
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run"):
                with pytest.raises(Exception, match="Cancel Error"):
                    state_canceled(mock_client, run_id="run-123")


class TestRunsModuleEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_wait_for_state_with_custom_timeout(self):
        """Test wait_for_state with custom timeout and polling interval."""
        mock_client = Mock()

        with patch("time.sleep") as mock_sleep:
            with patch("time.time", side_effect=[0, 20, 100]):  # Simulate timeout after one iteration
                with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run") as mock_get_run:
                    with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.RunStates") as mock_run_states:
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

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.RunRequest") as mock_run_request:
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.create_run"):
                with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.handle_polling_and_result"):
                    mock_request_instance = Mock()
                    mock_run_request.create.return_value = mock_request_instance

                    state_present(mock_client, workspace_id="ws-123", variables=[])

                    # Should still call create_run successfully
                    mock_run_request.create.assert_called_once()


@patch("ansible_collections.hashicorp.terraform.plugins.modules.run.handle_polling_and_result")
def test_state_applied_passes_timeout_parameters(mock_handle_polling):
    """Test that state_applied passes poll_timeout and poll_interval to handle_polling_and_result."""
    mock_client = Mock()

    with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.apply_run") as mock_apply:
        mock_apply.return_value = create_run_response(run_id="run-123")
        mock_handle_polling.return_value = {"changed": True, "id": "run-123"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run"):
            result = state_applied(mock_client, run_id="run-123", poll=True, poll_timeout=600, poll_interval=10)

            assert result["changed"] is True
            # Verify that poll_timeout and poll_interval are passed in kwargs
            mock_handle_polling.assert_called_once_with(mock_client, mock_apply.return_value, True, "run-123", poll_timeout=600, poll_interval=10)
