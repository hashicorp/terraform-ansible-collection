# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Helpers for Sentinel policy checks on runs."""

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response

HARD_FAIL_STATUSES = {"hard_failed", "errored"}
SOFT_FAIL_STATUSES = {"soft_failed"}
PASS_STATUSES = {"passed", "overridden"}


def list_policy_checks(adapter: TerraformClient, run_id: str) -> List[Dict[str, Any]]:
    """List policy checks associated with a run."""
    try:
        return [format_response(pc) for pc in adapter.client.policy_checks.list(run_id)]
    except NotFound:
        return []


def get_policy_check(adapter: TerraformClient, policy_check_id: str) -> Optional[Dict[str, Any]]:
    """Read a single policy check by ID."""
    try:
        return format_response(adapter.client.policy_checks.read(policy_check_id))
    except NotFound:
        return None


def summarize_policy_checks(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate pass/fail counts and overall verdict from a list of checks.

    ``hard_failed`` and ``errored`` are treated as mandatory failures.
    ``soft_failed`` is treated as an advisory failure.
    An empty check list is reported as passed (nothing to gate on).
    """
    summary = {
        "total": len(checks),
        "passed": 0,
        "soft_failed": 0,
        "hard_failed": 0,
        "mandatory_failed": False,
        "advisory_failed": False,
        "all_passed": True,
    }
    for c in checks:
        status = c.get("status")
        if status in PASS_STATUSES:
            summary["passed"] += 1
        elif status in SOFT_FAIL_STATUSES:
            summary["soft_failed"] += 1
            summary["advisory_failed"] = True
            summary["all_passed"] = False
        elif status in HARD_FAIL_STATUSES:
            summary["hard_failed"] += 1
            summary["mandatory_failed"] = True
            summary["all_passed"] = False
        else:
            # pending/queued/etc. — we don't count it as passed
            summary["all_passed"] = False
    return summary
