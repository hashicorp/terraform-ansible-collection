# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Single source of Terraform plan JSON parsing and sensitive-value masking.

This module contains no API/transport logic and no Ansible imports. It takes a
Terraform plan JSON document (the ``json-output`` shape produced by Terraform
1.x) and derives neutral, provider-agnostic facts: which resources are
affected, which attribute paths changed, which are computed
(unknown-until-apply), and masked before/after values. ``plan_analyze`` and
(eventually) ``view_plan`` both consume this module so plan-parsing semantics
are never duplicated or allowed to diverge.
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

# Value substituted for attributes flagged sensitive when values are included.
SENSITIVE_MASK = ""

# A record whose only action is "no-op" represents no change and is skipped.
_NOOP_ACTIONS = frozenset({"no-op"})

# Terraform plan json-output major version this analyzer targets.
_SUPPORTED_MAJOR_VERSION = 1


def check_format_version(plan_json: Dict[str, Any]) -> Optional[str]:
    """Check the plan JSON's ``format_version`` against the supported schema.

    Terraform's plan ``json-output`` carries a ``format_version`` string. This
    parser targets the 1.x family. Rather than hard-failing on an unrecognized
    major version, return a warning: HashiCorp may add minor versions or
    fields without breaking what we read, so callers should warn and proceed
    best-effort instead of aborting analysis outright.

    Args:
        plan_json: The parsed Terraform plan JSON document.

    Returns:
        A human-readable warning string if ``format_version`` is missing or
        its major version is unrecognized, otherwise ``None``.
    """
    version = plan_json.get("format_version")
    if not version:
        return "Plan JSON is missing 'format_version'; proceeding best-effort."

    major = str(version).split(".", 1)[0]
    try:
        major_int = int(major)
    except ValueError:
        return f"Unrecognized plan format_version '{version}'; proceeding best-effort."

    if major_int != _SUPPORTED_MAJOR_VERSION:
        return f"Plan format_version '{version}' is outside the tested " f"{_SUPPORTED_MAJOR_VERSION}.x family; proceeding best-effort."

    return None


def _diff_paths(before: Any, after: Any, prefix: str, changed: Set[str]) -> None:
    """Recursively collect leaf paths where ``before`` and ``after`` differ.

    A missing side (``None`` on create/delete) is treated as an empty container
    when the other side is a dict/list, so every added or removed leaf is
    reported rather than collapsing to the container root.
    """
    if isinstance(before, dict) or isinstance(after, dict):
        b_map = before if isinstance(before, dict) else {}
        a_map = after if isinstance(after, dict) else {}
        for key in set(b_map) | set(a_map):
            child = f"{prefix}.{key}" if prefix else key
            _diff_paths(b_map.get(key), a_map.get(key), child, changed)
    elif isinstance(before, list) or isinstance(after, list):
        b_list = before if isinstance(before, list) else []
        a_list = after if isinstance(after, list) else []
        for index in range(max(len(b_list), len(a_list))):
            b_item = b_list[index] if index < len(b_list) else None
            a_item = a_list[index] if index < len(a_list) else None
            _diff_paths(b_item, a_item, f"{prefix}[{index}]", changed)
    elif before != after:
        # Scalars, or a type change (dict<->scalar, list<->null, etc.).
        changed.add(prefix)


def _unknown_paths(after_unknown: Any, prefix: str, unknown: Set[str]) -> None:
    """Collect paths marked computed (unknown-after-apply) in ``after_unknown``."""
    if after_unknown is True:
        unknown.add(prefix)
    elif isinstance(after_unknown, dict):
        for key, value in after_unknown.items():
            child = f"{prefix}.{key}" if prefix else key
            _unknown_paths(value, child, unknown)
    elif isinstance(after_unknown, list):
        for index, value in enumerate(after_unknown):
            _unknown_paths(value, f"{prefix}[{index}]", unknown)


def diff_attributes(change: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Compute the changed and unknown attribute paths for a single change block.

    Args:
        change: The ``change`` object of a resource_changes / resource_drift
            record, containing ``before``, ``after``, and ``after_unknown``.

    Returns:
        A tuple ``(changed_attributes, unknown_attributes)`` of sorted, unique
        dotted paths. Paths that are computed (unknown-after-apply) appear only
        in ``unknown_attributes``, never in ``changed_attributes``.
    """
    changed: Set[str] = set()
    unknown: Set[str] = set()

    _diff_paths(change.get("before"), change.get("after"), "", changed)
    _unknown_paths(change.get("after_unknown"), "", unknown)

    # Computed values are reported separately; keep the two sets disjoint.
    changed -= unknown
    changed.discard("")
    unknown.discard("")

    return sorted(changed), sorted(unknown)


def mask_sensitive(value: Any, sensitive: Any) -> Any:
    """Recursively replace sensitive leaves in ``value`` with SENSITIVE_MASK."""
    if sensitive is True:
        return SENSITIVE_MASK
    if isinstance(value, dict) and isinstance(sensitive, dict):
        return {k: mask_sensitive(v, sensitive.get(k, False)) for k, v in value.items()}
    if isinstance(value, list) and isinstance(sensitive, list):
        return [mask_sensitive(item, sensitive[i] if i < len(sensitive) else False) for i, item in enumerate(value)]
    return value


def _record_actions(record: Dict[str, Any]) -> List[str]:
    return (record.get("change") or {}).get("actions") or []


def iter_resource_drift(plan_json: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Yield ``resource_drift`` records, skipping no-op-only entries."""
    for record in plan_json.get("resource_drift") or []:
        if not set(_record_actions(record)) <= _NOOP_ACTIONS:
            yield record


def iter_resource_changes(plan_json: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Yield ``resource_changes`` records, skipping no-op-only entries."""
    for record in plan_json.get("resource_changes") or []:
        if not set(_record_actions(record)) <= _NOOP_ACTIONS:
            yield record


def iter_output_changes(plan_json: Dict[str, Any]) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """Yield ``(name, change)`` output-change pairs, skipping no-op-only entries."""
    for name, change in (plan_json.get("output_changes") or {}).items():
        if not set(change.get("actions") or []) <= _NOOP_ACTIONS:
            yield name, change
