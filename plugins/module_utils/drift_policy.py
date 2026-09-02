# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Single source of attribute-path matching, classification, and the
``plan_guard`` decision.

This module contains no API/transport logic and no Ansible imports. Both
``plan_analyze`` (descriptive classification) and the ``plan_guard``/
``plan_safe`` plugins (the authoritative ``safe_to_refresh`` decision) match
rules against the same canonical target grammar defined here, so the two
features can never silently diverge in what a rule like ``aws_instance.*.
instance_type`` means.

Canonical target grammar:
    * Resource attribute target: ``<module_path>.<type>.<name>.<attr.path>``,
      e.g. ``module.networking.aws_instance.web.tags.role``.
    * Resource address target (attribute-agnostic rules):
      ``<module_path>.<type>.<name>``.
    * Output target: ``output.<name>``.
    Rules are :mod:`fnmatch`-style globs where ``*`` spans dots. A rule on a
    parent path (``*.tags``) also matches child paths (``tags.role``).
"""

from __future__ import annotations

import re
from fnmatch import fnmatchcase
from typing import Any, Dict, List, Optional, Tuple

# Strips a trailing/embedded "[<index>]" from a single path segment.
_INDEX_RE = re.compile(r"\[[^\]]*\]")

_SEVERITY_ORDER = ["blocked", "risky", "safe", "unknown"]

MODES = ["strict", "permissive"]


def _normalize(path: str) -> str:
    """Return ``path`` with list-index segments removed.

    ``ingress[0].cidr_blocks[1]`` -> ``ingress.cidr_blocks``.
    """
    return _INDEX_RE.sub("", path)


def resource_address_target(record: Dict[str, Any]) -> str:
    """Build the canonical, attribute-agnostic address target for a resource.

    ``<module_path>.<type>.<name>``, with the module prefix omitted for
    root-module resources.
    """
    module_address = record.get("module_address")
    resource_type = record.get("type") or ""
    name = record.get("name") or ""
    base = f"{resource_type}.{name}"
    return f"{module_address}.{base}" if module_address else base


def resource_attribute_target(record: Dict[str, Any], attribute_path: str) -> str:
    """Build the canonical attribute target for a single changed attribute path."""
    return f"{resource_address_target(record)}.{_normalize(attribute_path)}"


def output_target(name: str) -> str:
    """Build the canonical target for an output change."""
    return f"output.{name}"


def _matches(target: str, pattern: str) -> bool:
    """Return True if ``target`` matches ``pattern`` or any of its sub-paths.

    ``*`` in the pattern spans dots (fnmatch semantics). A pattern also
    matches deeper paths, so ``*.tags`` matches ``a.b.tags`` and
    ``a.b.tags.Name`` alike (prefix semantics).
    """
    return fnmatchcase(target, pattern) or fnmatchcase(target, f"{pattern}.*")


def compile_rules(rules: Optional[List[str]]) -> List[str]:
    """Normalize a rule list, defaulting to empty (fail-closed)."""
    return list(rules) if rules else []


def first_match(target: str, rules: List[str]) -> Optional[str]:
    """Return the first rule in ``rules`` that matches ``target``, if any."""
    for rule in rules:
        if _matches(target, rule):
            return rule
    return None


def classify(
    changed_attributes: List[str],
    unknown_attributes: List[str],
    safe: Optional[List[str]],
    risky: Optional[List[str]],
    blocked: Optional[List[str]],
    record: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, int], str]:
    """Classify a resource's attribute changes (descriptive, used by ``plan_analyze``).

    Each changed attribute is matched against the classification lists using
    the canonical attribute target (when ``record`` is given) or, for
    backward-compatible bare matching, the raw attribute-name segments.
    Precedence is ``blocked > risky > safe``; an attribute matching none of
    the lists defaults to ``safe``. Computed (unknown) attributes count as
    ``unknown`` and never match any list.

    Args:
        changed_attributes: Concrete changed attribute paths.
        unknown_attributes: Computed (unknown-after-apply) attribute paths.
        safe: Rules for attributes considered safe. Defaults to ``[]``.
        risky: Rules for attributes considered risky. Defaults to ``[]``.
        blocked: Rules for attributes considered blocked. Defaults to ``[]``.
        record: The owning resource record, used to build canonical targets.
            When omitted, rules are matched against the bare attribute path.

    Returns:
        A tuple ``(classification, counts, change_summary)``.
    """
    safe = compile_rules(safe)
    risky = compile_rules(risky)
    blocked = compile_rules(blocked)

    counts = {"blocked": 0, "risky": 0, "safe": 0, "unknown": len(unknown_attributes)}

    for path in changed_attributes:
        target = resource_attribute_target(record, path) if record is not None else _normalize(path)
        if first_match(target, blocked):
            counts["blocked"] += 1
        elif first_match(target, risky):
            counts["risky"] += 1
        else:
            # Explicitly-safe attributes and anything unmatched are benign.
            counts["safe"] += 1

    classification = "safe"
    for category in _SEVERITY_ORDER:
        if counts[category]:
            classification = category
            break

    change_summary = ", ".join(f"{counts[c]} {c}" for c in _SEVERITY_ORDER if counts[c])

    return classification, counts, change_summary


def evaluate(
    analysis: Dict[str, Any],
    allow: Optional[List[str]] = None,
    deny: Optional[List[str]] = None,
    mode: str = "strict",
) -> Dict[str, Any]:
    """Evaluate a ``plan_analyze`` result against allow/deny rules.

    This is the authoritative decision the ``plan_guard`` filter and
    ``plan_safe`` test plugins expose. ``plan_analyze``'s own per-resource
    ``classification`` is descriptive; a resource already classified
    ``blocked`` there is escalated unconditionally here (it cannot be
    overridden by an ``allow`` rule).

    Precedence: ``blocked`` (from the analysis's own classification) >
    ``deny`` match > ``allow`` match > unmatched. A target matching both
    ``allow`` and ``deny`` is denied. In ``strict`` mode (default), an
    unmatched attribute is treated as denied and any computed/unknown
    attribute makes the drift unsafe. In ``permissive`` mode, unmatched and
    unknown attributes do not block; ``blocked``/``deny`` still do.

    Args:
        analysis: A ``plan_analyze`` result (only ``resource_changes`` is
            read; each entry contributes its ``changed_attributes``,
            ``unknown_attributes``, and optional ``classification``).
        allow: Rules for attribute targets acceptable to absorb. Defaults to
            ``[]`` (fail-closed).
        deny: Rules for attribute targets that must never be absorbed;
            always wins over ``allow``. Defaults to ``[]``.
        mode: ``strict`` (default-deny) or ``permissive`` (default-allow).

    Returns:
        A dict with ``safe_to_refresh``, ``mode``, ``summary``, ``allowed``,
        ``denied``, ``blocked``, ``unknown``, and ``reasons``.
    """
    if mode not in MODES:
        raise ValueError(f"Unsupported mode '{mode}'; expected one of {MODES}.")

    allow = compile_rules(allow)
    deny = compile_rules(deny)

    allowed: List[Dict[str, Any]] = []
    denied: List[Dict[str, Any]] = []
    blocked: List[Dict[str, Any]] = []
    unknown: List[Dict[str, Any]] = []
    reasons: List[str] = []

    for entry in analysis.get("resource_changes") or []:
        address = entry.get("address")
        classification = entry.get("classification")

        for attribute in entry.get("changed_attributes") or []:
            target = resource_attribute_target(entry, attribute)
            item = {"address": address, "attribute": attribute}

            if classification == "blocked":
                blocked.append(item)
                reasons.append(f"{attribute} on {address} is classified blocked by plan_analyze")
                continue

            deny_rule = first_match(target, deny)
            if deny_rule is not None:
                denied.append({**item, "rule": deny_rule})
                reasons.append(f"{attribute} on {address} matched deny rule '{deny_rule}'")
                continue

            allow_rule = first_match(target, allow)
            if allow_rule is not None:
                allowed.append({**item, "rule": allow_rule})
            elif mode == "strict":
                denied.append({**item, "rule": None})
                reasons.append(f"{attribute} on {address} is unmatched; strict mode treats it as unsafe")
            else:
                allowed.append({**item, "rule": None})

        for attribute in entry.get("unknown_attributes") or []:
            unknown.append({"address": address, "attribute": attribute})
            if mode == "strict":
                reasons.append(f"{attribute} on {address} is unknown (computed); strict mode treats unknown as unsafe")

    safe_to_refresh = not blocked and not denied and (mode == "permissive" or not unknown)

    return {
        "safe_to_refresh": safe_to_refresh,
        "mode": mode,
        "summary": {
            "allowed": len(allowed),
            "denied": len(denied),
            "blocked": len(blocked),
            "unknown": len(unknown),
        },
        "allowed": allowed,
        "denied": denied,
        "blocked": blocked,
        "unknown": unknown,
        "reasons": reasons,
    }
