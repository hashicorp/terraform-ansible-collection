# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from ansible_collections.hashicorp.terraform.plugins.filter.plan_guard import (
    FilterModule,
    plan_guard,
)


def _analysis(address, changed_attributes, type_="aws_instance"):
    return {
        "resource_changes": [
            {
                "address": address,
                "type": type_,
                "name": address.split(".")[-1],
                "module_address": None,
                "classification": None,
                "changed_attributes": changed_attributes,
                "unknown_attributes": [],
            },
        ],
    }


class TestFilterModule:
    def test_filters_registers_plan_guard(self):
        assert FilterModule().filters() == {"plan_guard": plan_guard}


class TestPlanGuardFilter:
    def test_defaults_to_strict_fail_closed(self):
        decision = plan_guard(_analysis("aws_instance.web", ["ami"]))
        assert decision["safe_to_refresh"] is False
        assert decision["mode"] == "strict"

    def test_allow_rule_makes_safe(self):
        decision = plan_guard(_analysis("aws_instance.web", ["tags.role"]), allow=["*.tags"])
        assert decision["safe_to_refresh"] is True

    def test_deny_rule_blocks(self):
        decision = plan_guard(
            _analysis("aws_instance.web", ["instance_type"]),
            allow=["aws_instance.*.instance_type"],
            deny=["aws_instance.*.instance_type"],
        )
        assert decision["safe_to_refresh"] is False

    def test_permissive_mode(self):
        decision = plan_guard(_analysis("aws_instance.web", ["ami"]), mode="permissive")
        assert decision["safe_to_refresh"] is True

    def test_none_analysis_is_safe(self):
        decision = plan_guard(None)
        assert decision["safe_to_refresh"] is True
