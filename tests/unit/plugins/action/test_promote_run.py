# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import MagicMock, Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.action.promote_run import ActionModule

MOD = "ansible_collections.hashicorp.terraform.plugins.action.promote_run"


def _make_action(args):
    task = Mock(args=args)
    task.async_val = 0
    action = ActionModule(
        task=task,
        connection=Mock(),
        play_context=Mock(),
        loader=Mock(),
        templar=Mock(),
        shared_loader_obj=Mock(),
    )
    return action


@pytest.fixture
def patched_client():
    with patch(f"{MOD}.TerraformClient") as mock_class:
        mock_client = Mock()
        ctx = MagicMock()
        ctx.__enter__.return_value = mock_client
        ctx.__exit__.return_value = False
        mock_class.from_mapping.return_value = ctx
        yield mock_client, mock_class


class TestPromoteRun:

    def test_missing_run_id(self):
        action = _make_action({})
        result = action.run()
        assert result["failed"] is True
        assert "run_id" in result["msg"]

    @patch(f"{MOD}.get_run")
    def test_run_not_found(self, mock_get, patched_client):
        mock_get.return_value = None
        action = _make_action({"run_id": "run-missing"})
        result = action.run()
        assert result["failed"] is True
        assert "not found" in result["msg"]

    @patch(f"{MOD}.get_run")
    def test_already_final(self, mock_get, patched_client):
        mock_get.return_value = {"id": "run-1", "status": "applied"}
        action = _make_action({"run_id": "run-1"})
        result = action.run()
        assert result["changed"] is False
        assert "final state" in result["gates"]["skipped_reason"]
        assert result["gates"]["run_status_after"] == "applied"

    @patch(f"{MOD}.apply_run")
    @patch(f"{MOD}.get_run")
    def test_plan_only_policy_soft_failure_is_final(self, mock_get, mock_apply, patched_client):
        mock_get.return_value = {"id": "run-1", "status": "policy_soft_failed", "plan_only": True}

        result = _make_action({"run_id": "run-1", "wait": True}).run()

        assert result["changed"] is False
        assert result["gates"]["run_status_after"] == "policy_soft_failed"
        assert "final state" in result["gates"]["skipped_reason"]
        mock_apply.assert_not_called()

    @patch(f"{MOD}.apply_run")
    @patch(f"{MOD}.get_run")
    def test_confirmed_is_not_appliable_without_capability_data(self, mock_get, mock_apply, patched_client):
        mock_get.return_value = {"id": "run-1", "status": "confirmed"}

        result = _make_action({"run_id": "run-1"}).run()

        assert result["changed"] is False
        assert "not appliable" in result["gates"]["skipped_reason"]
        mock_apply.assert_not_called()

    @patch(f"{MOD}.get_run")
    def test_not_appliable_without_wait(self, mock_get, patched_client):
        mock_get.return_value = {"id": "run-1", "status": "pending"}
        action = _make_action({"run_id": "run-1"})
        result = action.run()
        assert result["changed"] is False
        assert "not appliable" in result["gates"]["skipped_reason"]

    @patch(f"{MOD}.apply_run")
    @patch(f"{MOD}.summarize_policy_checks")
    @patch(f"{MOD}.list_policy_checks")
    @patch(f"{MOD}.get_run")
    def test_happy_path_applies(self, mock_get, mock_list, mock_summarize, mock_apply, patched_client):
        mock_get.side_effect = [
            {"id": "run-1", "status": "planned"},
            {"id": "run-1", "status": "applied"},
        ]
        mock_list.return_value = []
        mock_summarize.return_value = {
            "total": 0,
            "passed": 0,
            "soft_failed": 0,
            "hard_failed": 0,
            "mandatory_failed": False,
            "advisory_failed": False,
            "all_passed": True,
        }
        action = _make_action({"run_id": "run-1", "comment": "go"})
        result = action.run()
        assert result["changed"] is True
        assert result["gates"]["applied"] is True
        assert result["gates"]["run_status_after"] == "applied"
        mock_apply.assert_called_once()

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}.apply_run")
    @patch(f"{MOD}.summarize_policy_checks")
    @patch(f"{MOD}.list_policy_checks")
    @patch(f"{MOD}.get_run")
    def test_wait_covers_post_apply_completion(self, mock_get, mock_list, mock_summarize, mock_apply, _mock_sleep, patched_client):
        mock_get.side_effect = [
            {"id": "run-1", "status": "planned"},
            {"id": "run-1", "status": "applying"},
            {"id": "run-1", "status": "applied"},
        ]
        mock_list.return_value = []
        mock_summarize.return_value = {"mandatory_failed": False, "advisory_failed": False}

        result = _make_action({"run_id": "run-1", "wait": True, "poll_interval": 0}).run()

        assert result["changed"] is True
        assert result["gates"]["run_status_after"] == "applied"
        assert mock_get.call_count == 3
        mock_apply.assert_called_once()

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}.apply_run")
    @patch(f"{MOD}.summarize_policy_checks")
    @patch(f"{MOD}.list_policy_checks")
    @patch(f"{MOD}.get_run")
    def test_wait_does_not_treat_transient_planned_as_confirmable(
        self,
        mock_get,
        mock_list,
        mock_summarize,
        mock_apply,
        _mock_sleep,
        patched_client,
    ):
        mock_get.side_effect = [
            {"id": "run-1", "status": "planned", "actions": {"is_confirmable": False}},
            {"id": "run-1", "status": "policy_checked", "actions": {"is_confirmable": True}},
            {"id": "run-1", "status": "applied", "actions": {"is_confirmable": False}},
        ]
        mock_list.return_value = [{"id": "polchk-1", "status": "passed"}]
        mock_summarize.return_value = {"mandatory_failed": False, "advisory_failed": False}

        result = _make_action({"run_id": "run-1", "wait": True, "poll_interval": 0}).run()

        assert result["gates"]["run_status_before"] == "policy_checked"
        assert result["gates"]["run_status_after"] == "applied"
        mock_apply.assert_called_once()

    @patch(f"{MOD}.apply_run")
    @patch(f"{MOD}.summarize_policy_checks")
    @patch(f"{MOD}.list_policy_checks")
    @patch(f"{MOD}.get_run")
    def test_saved_plan_is_appliable(self, mock_get, mock_list, mock_summarize, mock_apply, patched_client):
        mock_get.side_effect = [
            {"id": "run-1", "status": "planned_and_saved"},
            {"id": "run-1", "status": "applied"},
        ]
        mock_list.return_value = []
        mock_summarize.return_value = {"mandatory_failed": False, "advisory_failed": False}

        result = _make_action({"run_id": "run-1"}).run()

        assert result["changed"] is True
        mock_apply.assert_called_once()

    @patch(f"{MOD}.apply_run")
    @patch(f"{MOD}.summarize_policy_checks")
    @patch(f"{MOD}.list_policy_checks")
    @patch(f"{MOD}.get_run")
    def test_wait_reports_failed_final_state_after_apply(self, mock_get, mock_list, mock_summarize, mock_apply, patched_client):
        mock_get.side_effect = [
            {"id": "run-1", "status": "planned"},
            {"id": "run-1", "status": "errored"},
        ]
        mock_list.return_value = []
        mock_summarize.return_value = {"mandatory_failed": False, "advisory_failed": False}

        result = _make_action({"run_id": "run-1", "wait": True}).run()

        assert result["failed"] is True
        assert result["changed"] is True
        assert result["gates"]["applied"] is True
        assert result["gates"]["run_status_after"] == "errored"
        mock_apply.assert_called_once()

    @patch(f"{MOD}.summarize_policy_checks")
    @patch(f"{MOD}.list_policy_checks")
    @patch(f"{MOD}.get_run")
    def test_mandatory_fail_blocks(self, mock_get, mock_list, mock_summarize, patched_client):
        mock_get.return_value = {"id": "run-1", "status": "policy_checked"}
        mock_list.return_value = [{"id": "polchk-1", "status": "hard_failed"}]
        mock_summarize.return_value = {"mandatory_failed": True, "advisory_failed": False}
        action = _make_action({"run_id": "run-1"})
        result = action.run()
        assert result["failed"] is True
        assert "Mandatory policy" in result["msg"]

    @patch(f"{MOD}.summarize_policy_checks")
    @patch(f"{MOD}.list_policy_checks")
    @patch(f"{MOD}.get_run")
    def test_advisory_fail_blocks_when_disallowed(self, mock_get, mock_list, mock_summarize, patched_client):
        mock_get.return_value = {"id": "run-1", "status": "policy_checked"}
        mock_list.return_value = []
        mock_summarize.return_value = {"mandatory_failed": False, "advisory_failed": True}
        action = _make_action({"run_id": "run-1", "allow_advisory_failures": False})
        result = action.run()
        assert result["failed"] is True
        assert "Advisory policy" in result["msg"]

    @patch(f"{MOD}.apply_run")
    @patch(f"{MOD}.summarize_policy_checks")
    @patch(f"{MOD}.list_policy_checks")
    @patch(f"{MOD}.get_run")
    def test_auto_apply_false_skips(self, mock_get, mock_list, mock_summarize, mock_apply, patched_client):
        mock_get.return_value = {"id": "run-1", "status": "planned"}
        mock_list.return_value = []
        mock_summarize.return_value = {"mandatory_failed": False, "advisory_failed": False}
        action = _make_action({"run_id": "run-1", "auto_apply_when_eligible": False})
        result = action.run()
        assert result["changed"] is False
        assert result["gates"]["applied"] is False
        mock_apply.assert_not_called()
