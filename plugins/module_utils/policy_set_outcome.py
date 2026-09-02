# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Policy set outcome adapter for pytfe SDK integration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


try:
    # Not re-exported from pytfe.models.__init__ (unlike most model classes,
    # e.g. PolicySetOutcomeListOptions) - import from its submodule directly.
    from pytfe.models.policy_set_outcome import PolicySetOutcome
except ImportError:

    class PolicySetOutcome:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response


def _outcome_matches(outcome: Dict[str, Any], status: Optional[str], enforcement_level: Optional[str]) -> bool:
    """True if at least one result within ``outcome["outcomes"]`` matches the given filters."""
    for result in outcome.get("outcomes") or []:
        if status is not None and result.get("status") != status:
            continue
        if enforcement_level is not None and result.get("enforcement_level") != enforcement_level:
            continue
        return True
    return False


def list_policy_set_outcomes(
    adapter: TerraformClient,
    policy_evaluation_id: str,
    status: Optional[str] = None,
    enforcement_level: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List policy set outcomes for a policy evaluation, optionally filtered client-side."""
    try:
        outcomes = [format_response(o) for o in adapter.client.policy_set_outcomes.list(policy_evaluation_id)]
    except NotFound:
        return []

    if status is None and enforcement_level is None:
        return outcomes
    return [o for o in outcomes if _outcome_matches(o, status, enforcement_level)]


def get_policy_set_outcome(adapter: TerraformClient, policy_set_outcome_id: str) -> Optional[Dict[str, Any]]:
    """Read a single policy set outcome by its ID. Returns None if not found."""
    try:
        raw = adapter.client.policy_set_outcomes.read(policy_set_outcome_id)
    except NotFound:
        return None

    attrs = getattr(raw, "attributes", None)
    if attrs:
        fixed = PolicySetOutcome.model_validate({"id": raw.id, **attrs})
        return format_response(fixed)
    return format_response(raw)
