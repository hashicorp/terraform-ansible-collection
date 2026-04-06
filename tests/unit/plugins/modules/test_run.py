# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import ANY, Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
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


class TestWaitForState:
    """Tests for wait_for_state polling behavior."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run")
    def test_wait_for_state_success(self, mock_get_run):
        mock_adapter = Mock()
        mock_get_run.return_value = {"id": "run-1", "status": "applied"}

        status, data = wait_for_state(mock_adapter, "run-1", timeout=5, polling_interval=1)

        assert status == "success"
        assert data["status"] == "applied"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run")
    def test_wait_for_state_failure(self, mock_get_run):
        mock_adapter = Mock()
        mock_get_run.return_value = {"id": "run-2", "status": "errored"}

        status, data = wait_for_state(mock_adapter, "run-2", timeout=5, polling_interval=1)

        assert status == "failure"
        assert data["status"] == "errored"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.time.sleep")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.time.time")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run")
    def test_wait_for_state_timeout(self, mock_get_run, mock_time, _mock_sleep):
        mock_adapter = Mock()
        mock_get_run.return_value = {"id": "run-3", "status": "pending"}
        mock_time.side_effect = [0, 2, 4, 6]

        status, data = wait_for_state(mock_adapter, "run-3", timeout=5, polling_interval=1)

        assert status == "timeout"
        assert data["status"] == "pending"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run")
    def test_wait_for_state_run_not_found(self, mock_get_run):
        mock_adapter = Mock()
        mock_get_run.return_value = {}

        status, data = wait_for_state(mock_adapter, "run-404", timeout=5, polling_interval=1)

        assert status == "failure"
        assert "not found" in data["error"]


class TestHandlePollingAndResult:
    """Tests for action result shaping with and without polling."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.wait_for_state")
    def test_with_polling_success(self, mock_wait):
        mock_adapter = Mock()
        mock_wait.return_value = ("success", {"id": "run-1", "status": "applied"})

        result = handle_polling_and_result(mock_adapter, {"id": "run-1"}, True)

        assert result["changed"] is True
        assert result["status"] == "applied"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.wait_for_state")
    def test_with_polling_failure(self, mock_wait):
        mock_adapter = Mock()
        mock_wait.return_value = ("failure", {"id": "run-1", "status": "errored"})

        result = handle_polling_and_result(mock_adapter, {"id": "run-1"}, True)

        assert result["failed"] is True
        assert "expected success state" in result["msg"]

    def test_without_polling(self):
        mock_adapter = Mock()

        result = handle_polling_and_result(mock_adapter, {"id": "run-1", "status": "pending"}, False)

        assert result == {"changed": True, "id": "run-1", "status": "pending"}


class TestDecorators:
    """Tests for check_mode and idempotency decorators."""

    def test_check_mode_present_short_circuit(self):
        @check_mode
        def state_present(adapter, **kwargs):
            return {"changed": False}

        result = state_present(Mock(), check_mode=True)

        assert result["changed"] is True
        assert "Check mode" in result["msg"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run")
    def test_check_mode_action_run_not_found(self, mock_get_run):
        mock_get_run.return_value = {}

        @check_mode
        def state_applied(adapter, **kwargs):
            return {"changed": True}

        result = state_applied(Mock(), check_mode=True, run_id="run-404")

        assert result["failed"] is True
        assert "not found" in result["msg"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run")
    def test_check_mode_action_run_found(self, mock_get_run):
        mock_get_run.return_value = {"id": "run-1", "status": "planned"}

        @check_mode
        def state_applied(adapter, **kwargs):
            return {"changed": True}

        result = state_applied(Mock(), check_mode=True, run_id="run-1")

        assert result["changed"] is True
        assert "found" in result["msg"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run")
    def test_idempotency_short_circuit(self, mock_get_run):
        mock_get_run.return_value = {"id": "run-1", "status": "applied"}

        @idempotency_check
        def state_applied(adapter, **kwargs):
            return {"changed": True}

        result = state_applied(Mock(), run_id="run-1")

        assert result["changed"] is False
        assert result["run"]["status"] == "applied"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_run")
    def test_idempotency_run_not_found(self, mock_get_run):
        mock_get_run.return_value = {}

        @idempotency_check
        def state_applied(adapter, **kwargs):
            return {"changed": True}

        result = state_applied(Mock(), run_id="run-404")

        assert result["failed"] is True
        assert "not found" in result["msg"]


class TestStateHandlers:
    """Tests for state_* handler functions."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.handle_polling_and_result")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.create_run")
    def test_state_present_filters_params(self, mock_create_run, mock_handle):
        mock_adapter = Mock()
        mock_create_run.return_value = {"id": "run-1"}
        mock_handle.return_value = {"changed": True, "id": "run-1"}

        result = state_present(
            mock_adapter,
            workspace_id="ws-1",
            run_message="test",
            state="present",
            organization="org-1",
            workspace="ws-name",
            poll=True,
            poll_timeout=10,
            poll_interval=1,
            tfe_token="secret",
            check_mode=False,
        )

        assert result["changed"] is True
        call_kwargs = mock_create_run.call_args.kwargs["data"]
        assert "organization" not in call_kwargs
        assert "workspace" not in call_kwargs
        assert "tfe_token" not in call_kwargs
        assert call_kwargs["poll"] is True
        assert call_kwargs["workspace_id"] == "ws-1"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.handle_polling_and_result")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.apply_run")
    def test_state_applied(self, mock_apply_run, mock_handle):
        mock_apply_run.return_value = {"data": {"id": "run-1"}}
        mock_handle.return_value = {"changed": True, "id": "run-1"}

        result = state_applied(Mock(), run_id="run-1", poll=True, run_message="apply")

        assert result["changed"] is True
        mock_apply_run.assert_called_once_with(ANY, "run-1", comment="apply")

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.handle_polling_and_result")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.discard_run")
    def test_state_discarded(self, mock_discard_run, mock_handle):
        mock_discard_run.return_value = {"data": {"id": "run-2"}}
        mock_handle.return_value = {"changed": True, "id": "run-2"}

        result = state_discarded(Mock(), run_id="run-2", poll=False, run_message="discard")

        assert result["changed"] is True
        mock_discard_run.assert_called_once_with(ANY, "run-2", comment="discard")

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.handle_polling_and_result")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.cancel_run")
    def test_state_canceled(self, mock_cancel_run, mock_handle):
        mock_cancel_run.return_value = {"data": {"id": "run-3"}}
        mock_handle.return_value = {"changed": True, "id": "run-3"}

        result = state_canceled(Mock(), run_id="run-3", poll=True, run_message="cancel")

        assert result["changed"] is True
        mock_cancel_run.assert_called_once_with(ANY, "run-3", comment="cancel")


class TestWorkspaceLookup:
    """Tests for workspace id lookup helper."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_workspace")
    def test_get_workspace_id_success(self, mock_get_workspace):
        mock_get_workspace.return_value = {"id": "ws-123"}

        workspace_id = get_workspace_id(Mock(), "workspace-a", "org-a")

        assert workspace_id == "ws-123"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_workspace")
    def test_get_workspace_id_not_found(self, mock_get_workspace):
        mock_get_workspace.return_value = None

        with pytest.raises(TerraformError):
            get_workspace_id(Mock(), "workspace-a", "org-a")


class TestMain:
    """Tests for module main flow and wiring."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.state_present")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.get_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.AnsibleTerraformModule")
    def test_main_present_with_workspace_lookup(self, mock_module_class, mock_tf_client, mock_get_workspace_id, mock_state_present, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "workspace": "ws-name",
            "workspace_id": None,
            "organization": "org-a",
            "state": "present",
            "poll": True,
            "poll_interval": 5,
            "poll_timeout": 120,
            "comment": None,
            "tfe_token": "token",
            "tfe_address": "https://app.terraform.io",
        }
        mock_module.check_mode = False
        mock_module_class.return_value = mock_module

        mock_adapter = Mock()
        mock_tf_client.return_value = mock_adapter
        mock_get_workspace_id.return_value = "ws-123"
        mock_state_present.return_value = {"changed": True, "id": "run-1"}

        with pytest.raises(SystemExit):
            main()

        mock_get_workspace_id.assert_called_once_with(mock_adapter, "ws-name", "org-a")
        assert mock_module.exit_args["changed"] is True
        assert mock_module.exit_args["id"] == "run-1"
        mock_adapter.cleanup.assert_called_once()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.state_applied")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.AnsibleTerraformModule")
    def test_main_applied_state(self, mock_module_class, mock_tf_client, mock_state_applied, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "state": "applied",
            "run_id": "run-1",
            "poll": True,
            "poll_interval": 5,
            "poll_timeout": 120,
            "comment": "apply",
            "workspace": None,
            "workspace_id": None,
            "organization": None,
            "tfe_token": "token",
            "tfe_address": "https://app.terraform.io",
        }
        mock_module.check_mode = False
        mock_module_class.return_value = mock_module

        mock_adapter = Mock()
        mock_tf_client.return_value = mock_adapter
        mock_state_applied.return_value = {"changed": True, "status": "applied"}

        with pytest.raises(SystemExit):
            main()

        assert mock_module.exit_args["changed"] is True
        assert mock_module.exit_args["status"] == "applied"
        mock_adapter.cleanup.assert_called_once()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run.AnsibleTerraformModule")
    def test_main_exception_uses_fail_json(self, mock_module_class, mock_tf_client, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "state": "present",
            "workspace": "ws-name",
            "workspace_id": "ws-123",
            "organization": "org-a",
            "poll": True,
            "poll_interval": 5,
            "poll_timeout": 120,
            "comment": None,
            "tfe_token": "token",
            "tfe_address": "https://app.terraform.io",
        }
        mock_module.check_mode = False
        mock_module_class.return_value = mock_module

        mock_tf_client.side_effect = Exception("client init failed")

        with pytest.raises(AssertionError):
            main()

        assert "client init failed" in mock_module.fail_args["msg"]
