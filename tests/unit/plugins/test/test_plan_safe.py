# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from ansible_collections.hashicorp.terraform.plugins.test.plan_safe import TestModule as PlanSafeTestModule
from ansible_collections.hashicorp.terraform.plugins.test.plan_safe import plan_safe


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


class TestTestModule:
    def test_tests_registers_plan_safe(self):
        assert PlanSafeTestModule().tests() == {"plan_safe": plan_safe}


class TestPlanSafeTest:
    def test_returns_bool(self):
        assert plan_safe(_analysis("aws_instance.web", ["tags.role"]), allow=["*.tags"]) is True

    def test_matches_filter_verdict_for_same_inputs(self):
        from ansible_collections.hashicorp.terraform.plugins.filter.plan_guard import (
            plan_guard,
        )

        analysis = _analysis("aws_instance.web", ["ami"])
        assert plan_safe(analysis) == plan_guard(analysis)["safe_to_refresh"]

    def test_empty_analysis_is_safe(self):
        assert plan_safe({}) is True
