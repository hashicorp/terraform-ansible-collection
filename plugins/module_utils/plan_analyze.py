# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Orchestration for the ``plan_analyze`` module.

This module contains no API/transport logic. It combines the shared,
provider-agnostic engines - :mod:`plan_facts` for parsing/masking and
:mod:`drift_policy` for classification - into the ``plan_analyze`` result
shape. Keeping it side-effect free makes it unit-testable without pytfe or a
live organization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils import (
    drift_policy,
    plan_facts,
)


def _analyze_record(
    record: Dict[str, Any],
    source: str,
    safe: Optional[List[str]],
    risky: Optional[List[str]],
    blocked: Optional[List[str]],
    include_values: bool,
) -> Dict[str, Any]:
    """Build a per-resource analysis entry."""
    change = record.get("change") or {}

    changed_attributes, unknown_attributes = plan_facts.diff_attributes(change)
    classification, _counts, change_summary = drift_policy.classify(
        changed_attributes,
        unknown_attributes,
        safe,
        risky,
        blocked,
        record=record,
    )

    entry = {
        "address": record.get("address"),
        "type": record.get("type"),
        "name": record.get("name"),
        "provider_name": record.get("provider_name"),
        "module_address": record.get("module_address"),
        "mode": record.get("mode"),
        "actions": change.get("actions") or [],
        "action_reason": record.get("action_reason"),
        "source": source,
        "changed_attributes": changed_attributes,
        "unknown_attributes": unknown_attributes,
        "classification": classification,
        "change_summary": change_summary,
    }

    if include_values:
        entry["before"] = plan_facts.mask_sensitive(change.get("before"), change.get("before_sensitive"))
        entry["after"] = plan_facts.mask_sensitive(change.get("after"), change.get("after_sensitive"))

    return entry


def _analyze_output(name: str, change: Dict[str, Any], include_values: bool) -> Dict[str, Any]:
    """Build a per-output analysis entry."""
    entry: Dict[str, Any] = {
        "name": name,
        "actions": change.get("actions") or [],
        "sensitive": bool(change.get("after_sensitive") or change.get("before_sensitive")),
    }

    if include_values:
        entry["before"] = plan_facts.mask_sensitive(change.get("before"), change.get("before_sensitive"))
        entry["after"] = plan_facts.mask_sensitive(change.get("after"), change.get("after_sensitive"))

    return entry


def analyze_plan(
    plan_json: Dict[str, Any],
    detect_drift: bool = True,
    include_resource_changes: bool = True,
    include_output_changes: bool = True,
    include_values: bool = False,
    safe_attributes: Optional[List[str]] = None,
    risky_attributes: Optional[List[str]] = None,
    blocked_attributes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Analyze a Terraform plan JSON document into drift/change facts.

    Classification is descriptive only: with no ``safe``/``risky``/
    ``blocked`` rules supplied (the default), every changed attribute is
    classified ``safe`` and computed attributes ``unknown`` - the
    authoritative accept/deny gate is the ``plan_guard`` filter plugin, not
    this module.

    Args:
        plan_json: The parsed Terraform plan ``json-output`` document (1.x).
        detect_drift: Walk ``resource_drift[]`` for out-of-band drift.
        include_resource_changes: Walk ``resource_changes[]`` for planned changes.
        include_output_changes: Analyze ``output_changes``.
        include_values: Include masked ``before``/``after`` values per entry.
        safe_attributes: Rules for attributes considered safe. Defaults to ``[]``.
        risky_attributes: Rules for attributes considered risky. Defaults to ``[]``.
        blocked_attributes: Rules for attributes considered blocked. Defaults to ``[]``.

    Returns:
        A dict with ``has_drift``, ``drift_count``, ``has_changes``,
        ``change_count``, ``resource_changes`` (per-resource entries),
        ``output_changes``, a ``summary`` of classification counts, and
        ``warning`` (a plan-JSON schema warning, or ``None``).
    """
    warning = plan_facts.check_format_version(plan_json)

    entries: List[Dict[str, Any]] = []
    drift_count = 0
    change_count = 0

    if detect_drift:
        for record in plan_facts.iter_resource_drift(plan_json):
            entries.append(_analyze_record(record, "resource_drift", safe_attributes, risky_attributes, blocked_attributes, include_values))
            drift_count += 1

    if include_resource_changes:
        for record in plan_facts.iter_resource_changes(plan_json):
            entries.append(_analyze_record(record, "resource_changes", safe_attributes, risky_attributes, blocked_attributes, include_values))
            change_count += 1

    output_entries: List[Dict[str, Any]] = []
    if include_output_changes:
        for name, change in plan_facts.iter_output_changes(plan_json):
            output_entries.append(_analyze_output(name, change, include_values))

    summary = {"safe": 0, "risky": 0, "blocked": 0, "unknown": 0}
    for entry in entries:
        summary[entry["classification"]] += 1

    return {
        "has_drift": drift_count > 0,
        "drift_count": drift_count,
        "has_changes": change_count > 0,
        "change_count": change_count,
        "resource_changes": entries,
        "output_changes": output_entries,
        "summary": summary,
        "warning": warning,
    }
