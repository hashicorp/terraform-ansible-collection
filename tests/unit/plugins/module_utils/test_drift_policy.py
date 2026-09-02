# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.drift_policy import (
    _matches,
    _normalize,
    classify,
    evaluate,
    output_target,
    resource_address_target,
    resource_attribute_target,
)


class TestNormalize:
    def test_strips_single_index(self):
        assert _normalize("ingress[0].cidr_blocks") == "ingress.cidr_blocks"

    def test_strips_multiple_indices(self):
        assert _normalize("ingress[1].cidr_blocks[0]") == "ingress.cidr_blocks"

    def test_no_index_unchanged(self):
        assert _normalize("instance_type") == "instance_type"


class TestCanonicalTargets:
    def test_root_module_resource_address(self):
        record = {"type": "aws_instance", "name": "web", "module_address": None}
        assert resource_address_target(record) == "aws_instance.web"

    def test_nested_module_resource_address(self):
        record = {"type": "aws_instance", "name": "web", "module_address": "module.networking"}
        assert resource_address_target(record) == "module.networking.aws_instance.web"

    def test_attribute_target_root_module(self):
        record = {"type": "aws_instance", "name": "web", "module_address": None}
        assert resource_attribute_target(record, "tags.role") == "aws_instance.web.tags.role"

    def test_attribute_target_strips_indices(self):
        record = {"type": "aws_security_group", "name": "app", "module_address": None}
        assert resource_attribute_target(record, "ingress[0].from_port") == "aws_security_group.app.ingress.from_port"

    def test_attribute_target_nested_module(self):
        record = {"type": "aws_instance", "name": "web", "module_address": "module.networking"}
        assert resource_attribute_target(record, "tags.role") == "module.networking.aws_instance.web.tags.role"

    def test_output_target(self):
        assert output_target("endpoint") == "output.endpoint"


class TestMatches:
    def test_exact(self):
        assert _matches("aws_instance.web.instance_type", "aws_instance.web.instance_type")

    def test_type_scoped_wildcard(self):
        assert _matches("aws_instance.web.instance_type", "aws_instance.*.instance_type")

    def test_resource_type_wildcard(self):
        assert _matches("aws_iam_policy.admin.arn", "aws_iam_policy.*")

    def test_module_scoped_wildcard(self):
        assert _matches("module.networking.aws_instance.web.tags.role", "module.networking.*")

    def test_prefix_semantics_matches_child_path(self):
        assert _matches("aws_instance.web.tags.role", "*.tags")

    def test_prefix_semantics_exact_match(self):
        assert _matches("aws_instance.web.tags", "*.tags")

    def test_non_match(self):
        assert not _matches("aws_instance.web.ami", "aws_instance.*.instance_type")


class TestClassify:
    def _record(self):
        return {"type": "aws_instance", "name": "web", "module_address": None}

    def test_no_rules_defaults_to_safe(self):
        classification, counts, _summary = classify(["instance_type", "tags.role"], [], None, None, None, record=self._record())
        assert classification == "safe"
        assert counts == {"blocked": 0, "risky": 0, "safe": 2, "unknown": 0}

    def test_blocked_precedence(self):
        classification, counts, _summary = classify(
            ["ami", "instance_type"],
            [],
            safe=[],
            risky=["*.instance_type"],
            blocked=["*.ami"],
            record=self._record(),
        )
        assert classification == "blocked"
        assert counts["blocked"] == 1
        assert counts["risky"] == 1

    def test_risky_matches_type_scoped_rule(self):
        classification, counts, _summary = classify(
            ["instance_type"],
            [],
            safe=[],
            risky=["aws_instance.*.instance_type"],
            blocked=[],
            record=self._record(),
        )
        assert classification == "risky"
        assert counts["risky"] == 1

    def test_only_unknown(self):
        classification, counts, summary = classify([], ["private_dns"], [], [], [], record=self._record())
        assert classification == "unknown"
        assert summary == "1 unknown"

    def test_list_index_path_matches_type_scoped_rule(self):
        record = {"type": "aws_security_group", "name": "app", "module_address": None}
        classification, _counts, _summary = classify(
            ["ingress[0].from_port"],
            [],
            safe=[],
            risky=["aws_security_group.*.ingress"],
            blocked=[],
            record=record,
        )
        assert classification == "risky"

    def test_bare_matching_without_record(self):
        # Backward-compatible bare-path matching when no record is supplied.
        classification, counts, _summary = classify(["instance_type"], [], [], ["instance_type"], [])
        assert classification == "risky"
        assert counts["risky"] == 1


def _analysis(*entries):
    """Build a minimal plan_analyze-shaped dict.

    Each argument is a tuple ``(record_overrides, changed_attributes, unknown_attributes)``.
    """
    resource_changes = []
    for overrides, changed, unknown in entries:
        entry = {
            "address": overrides.get("address"),
            "type": overrides.get("type", "aws_instance"),
            "name": overrides.get("name", "web"),
            "module_address": overrides.get("module_address"),
            "classification": overrides.get("classification"),
            "changed_attributes": changed,
            "unknown_attributes": unknown,
        }
        resource_changes.append(entry)
    return {"resource_changes": resource_changes}


class TestEvaluate:
    def test_empty_analysis_is_safe(self):
        decision = evaluate({}, allow=[], deny=[], mode="strict")
        assert decision["safe_to_refresh"] is True
        assert decision["summary"] == {"allowed": 0, "denied": 0, "blocked": 0, "unknown": 0}

    def test_allow_makes_safe_in_strict_mode(self):
        analysis = _analysis(({"address": "aws_instance.web"}, ["tags.role"], []))
        decision = evaluate(analysis, allow=["*.tags"], deny=[], mode="strict")
        assert decision["safe_to_refresh"] is True
        assert decision["summary"]["allowed"] == 1

    def test_deny_wins_over_allow(self):
        analysis = _analysis(({"address": "aws_instance.web"}, ["instance_type"], []))
        decision = evaluate(
            analysis,
            allow=["aws_instance.*.instance_type"],
            deny=["aws_instance.*.instance_type"],
            mode="permissive",
        )
        assert decision["safe_to_refresh"] is False
        assert decision["summary"]["denied"] == 1
        assert decision["denied"][0]["rule"] == "aws_instance.*.instance_type"

    def test_strict_unmatched_is_denied(self):
        analysis = _analysis(({"address": "aws_instance.web"}, ["ami"], []))
        decision = evaluate(analysis, allow=[], deny=[], mode="strict")
        assert decision["safe_to_refresh"] is False
        assert decision["summary"]["denied"] == 1
        assert decision["denied"][0]["rule"] is None

    def test_permissive_unmatched_is_allowed(self):
        analysis = _analysis(({"address": "aws_instance.web"}, ["ami"], []))
        decision = evaluate(analysis, allow=[], deny=[], mode="permissive")
        assert decision["safe_to_refresh"] is True
        assert decision["summary"]["allowed"] == 1

    def test_strict_unknown_blocks(self):
        analysis = _analysis(({"address": "aws_instance.web"}, [], ["private_dns"]))
        decision = evaluate(analysis, allow=[], deny=[], mode="strict")
        assert decision["safe_to_refresh"] is False
        assert decision["summary"]["unknown"] == 1

    def test_permissive_unknown_does_not_block(self):
        analysis = _analysis(({"address": "aws_instance.web"}, [], ["private_dns"]))
        decision = evaluate(analysis, allow=[], deny=[], mode="permissive")
        assert decision["safe_to_refresh"] is True
        assert decision["summary"]["unknown"] == 1

    def test_blocked_classification_is_unconditional(self):
        analysis = _analysis(({"address": "aws_iam_policy.admin", "type": "aws_iam_policy", "classification": "blocked"}, ["policy"], []))
        decision = evaluate(analysis, allow=["*"], deny=[], mode="permissive")
        assert decision["safe_to_refresh"] is False
        assert decision["summary"]["blocked"] == 1

    def test_mixed_verdict(self):
        analysis = _analysis(
            ({"address": "aws_instance.ec2"}, ["tags.role"], []),
            ({"address": "aws_instance.web"}, ["instance_type"], []),
        )
        decision = evaluate(
            analysis,
            allow=["*.tags"],
            deny=["aws_instance.*.instance_type"],
            mode="strict",
        )
        assert decision["safe_to_refresh"] is False
        assert decision["summary"] == {"allowed": 1, "denied": 1, "blocked": 0, "unknown": 0}

    def test_reasons_populated(self):
        analysis = _analysis(({"address": "aws_iam_policy.admin", "type": "aws_iam_policy"}, ["policy"], []))
        decision = evaluate(analysis, allow=[], deny=["aws_iam_policy.*"], mode="strict")
        assert any("matched deny rule" in reason for reason in decision["reasons"])

    def test_index_paths_match_type_scoped_allow_rule(self):
        analysis = _analysis(
            ({"address": "aws_security_group.ec2_sg", "type": "aws_security_group"}, ["ingress[1].from_port", "ingress[0].description"], []),
        )
        decision = evaluate(analysis, allow=["aws_security_group.*.ingress"], deny=[], mode="strict")
        assert decision["safe_to_refresh"] is True
        assert decision["summary"]["allowed"] == 2

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            evaluate({}, mode="bogus")
