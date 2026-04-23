# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Gate a Terraform run on policy outcomes before applying it.

This action plugin is an orchestrator built on top of the collection's
pytfe-backed module_utils. It does not issue its own HTTP calls.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import time

from ansible.plugins.action import ActionBase

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.policy_check import (
    list_policy_checks,
    summarize_policy_checks,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.run import apply_run, get_run

# Run states in which `apply` is a valid operation.
APPLIABLE_STATUSES = {"planned", "cost_estimated", "policy_checked", "post_plan_completed", "confirmed"}
# Run states that are already final.
FINAL_STATUSES = {"applied", "errored", "canceled", "discarded", "planned_and_finished"}


class ActionModule(ActionBase):

    _VALID_ARGS = frozenset(
        (
            "run_id",
            "require_policy_pass",
            "allow_advisory_failures",
            "wait",
            "timeout",
            "poll_interval",
            "auto_apply_when_eligible",
            "comment",
            "tfe_token",
            "tfe_address",
            "tfe_timeout",
            "tfe_verify_tls",
            "tf_token",
            "tf_hostname",
        )
    )

    def _fail(self, result, msg, **extra):
        result.update({"failed": True, "changed": False, "msg": msg, **extra})
        return result

    def _wait_for_appliable(self, adapter, run_id, timeout, poll_interval):
        """Poll the run until it is appliable, final, or the timeout elapses."""
        deadline = time.time() + timeout
        run = get_run(adapter, run_id)
        while run and run.get("status") not in APPLIABLE_STATUSES | FINAL_STATUSES and time.time() < deadline:
            time.sleep(poll_interval)
            run = get_run(adapter, run_id)
        return run

    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars) or {}
        args = self._task.args or {}

        run_id = args.get("run_id")
        if not run_id:
            return self._fail(result, "'run_id' is required.")

        require_policy_pass = bool(args.get("require_policy_pass", True))
        allow_advisory_failures = bool(args.get("allow_advisory_failures", True))
        wait = bool(args.get("wait", False))
        timeout = int(args.get("timeout", 600))
        poll_interval = int(args.get("poll_interval", 10))
        auto_apply_when_eligible = bool(args.get("auto_apply_when_eligible", True))
        comment = args.get("comment")

        gates = {
            "run_status_before": None,
            "run_status_after": None,
            "policy_summary": None,
            "applied": False,
            "skipped_reason": None,
        }

        try:
            with TerraformClient.from_mapping(args) as adapter:
                run = get_run(adapter, run_id)
                if not run:
                    return self._fail(result, f"Run {run_id} not found.", gates=gates)
                gates["run_status_before"] = run.get("status")

                if run.get("status") in FINAL_STATUSES:
                    gates["skipped_reason"] = f"Run already in final state '{run.get('status')}'"
                    result.update({"changed": False, "gates": gates, "run": run})
                    return result

                if wait and run.get("status") not in APPLIABLE_STATUSES:
                    run = self._wait_for_appliable(adapter, run_id, timeout, poll_interval) or run
                    gates["run_status_before"] = run.get("status")

                if run.get("status") not in APPLIABLE_STATUSES:
                    gates["skipped_reason"] = f"Run status {run.get('status')!r} is not appliable"
                    result.update({"changed": False, "gates": gates, "run": run})
                    return result

                checks = list_policy_checks(adapter, run_id)
                summary = summarize_policy_checks(checks)
                gates["policy_summary"] = summary

                if require_policy_pass:
                    if summary["mandatory_failed"]:
                        return self._fail(result, f"Mandatory policy checks failed on run {run_id}.", gates=gates, policy_checks=checks)
                    if summary["advisory_failed"] and not allow_advisory_failures:
                        return self._fail(result, f"Advisory policy checks failed on run {run_id}.", gates=gates, policy_checks=checks)

                if not auto_apply_when_eligible:
                    gates["skipped_reason"] = "auto_apply_when_eligible=false"
                    result.update({"changed": False, "gates": gates, "run": run, "policy_checks": checks})
                    return result

                apply_run(adapter, run_id, comment=comment)
                gates["applied"] = True
                run_after = get_run(adapter, run_id) or run
                gates["run_status_after"] = run_after.get("status")

                result.update({"changed": True, "gates": gates, "run": run_after, "policy_checks": checks})
                return result

        except Exception as e:
            return self._fail(result, f"promote_run failed: {e}", gates=gates)
