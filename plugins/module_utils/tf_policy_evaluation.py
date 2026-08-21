# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Adapter for tf-policy evaluations and set outcomes.

Wraps ``client.tf_policy_evaluations`` and ``client.tf_policy_set_outcomes``
(``/api/v2/runs/{run_id}/tf-policy-evaluations``,
``/api/v2/tf-policy-evaluations/{id}``,
``/api/v2/tf-policy-evaluations/{id}/tf-policy-set-outcomes``,
``/api/v2/tf-policy-set-outcomes/{id}``). tf-policy is HCP Terraform's native
policy-as-code engine (distinct from the Sentinel/OPA policy-check flow
covered by ``plugins/module_utils/policy_check.py`` /
``plugins/module_utils/policy_evaluation.py``) - evaluations are produced by
Terraform runs, never created directly, so this adapter is read-only except
for the single override action.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        TfPolicyEvaluationListOptions,
        TfPolicyEvaluationOverrideOptions,
        TfPolicySetOutcomeListOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    TfPolicyEvaluationListOptions = None  # type: ignore[assignment]
    TfPolicyEvaluationOverrideOptions = None  # type: ignore[assignment]
    TfPolicySetOutcomeListOptions = None  # type: ignore[assignment]


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_evaluations(adapter: TerraformClient, run_id: str) -> List[Dict[str, Any]]:
    """List tf-policy evaluations for a run. Returns [] on NotFound."""
    try:
        return [format_response(e) for e in adapter.client.tf_policy_evaluations.list(run_id)]
    except NotFound:
        return []


def get_evaluation(adapter: TerraformClient, evaluation_id: str, include_outcomes: bool = False) -> Optional[Dict[str, Any]]:
    """Read a single tf-policy evaluation by ID. Returns None if not found.

    When ``include_outcomes`` is true, sideloads the evaluation's
    ``tf_policy_set_outcomes`` relationship in the same request.
    """
    try:
        opts = TfPolicyEvaluationListOptions(include="tf_policy_set_outcomes" if include_outcomes else None)
        return format_response(adapter.client.tf_policy_evaluations.read(evaluation_id, options=opts))
    except NotFound:
        return None


def list_set_outcomes(
    adapter: TerraformClient,
    evaluation_id: str,
    filter_status: Optional[str] = None,
    filter_enforcement_level: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List tf-policy set outcomes for an evaluation, optionally filtered.

    Returns [] on NotFound.
    """
    try:
        opts = TfPolicySetOutcomeListOptions(
            filter_status=filter_status,
            filter_enforcement_level=filter_enforcement_level,
        )
        return [format_response(o) for o in adapter.client.tf_policy_evaluations.list_set_outcomes(evaluation_id, options=opts)]
    except NotFound:
        return []


def get_set_outcome(adapter: TerraformClient, outcome_id: str) -> Optional[Dict[str, Any]]:
    """Read a single tf-policy set outcome by ID. Returns None if not found."""
    try:
        return format_response(adapter.client.tf_policy_set_outcomes.read(outcome_id))
    except NotFound:
        return None


def override_evaluation(adapter: TerraformClient, evaluation_id: str, comment: Optional[str] = None) -> Dict[str, Any]:
    """Override a tf-policy evaluation that is in awaiting_override status."""
    options = TfPolicyEvaluationOverrideOptions(comment=comment)
    response = safe_api_call(
        adapter.client.tf_policy_evaluations.override,
        evaluation_id,
        options,
        error_context=f"Failed to override tf-policy evaluation {evaluation_id}",
    )
    return format_response(response)
