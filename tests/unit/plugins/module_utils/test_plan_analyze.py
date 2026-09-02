# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from ansible_collections.hashicorp.terraform.plugins.module_utils.plan_analyze import (
    analyze_plan,
)


def _plan(**kwargs):
    base = {"format_version": "1.2"}
    base.update(kwargs)
    return base


class TestAnalyzePlan:
    def test_unsupported_version_warns_but_does_not_raise(self):
        result = analyze_plan({"format_version": "2.0"})
        assert result["warning"] is not None
        assert result["resource_changes"] == []

    def test_supported_version_has_no_warning(self):
        result = analyze_plan(_plan())
        assert result["warning"] is None

    def test_empty_plan(self):
        result = analyze_plan(_plan())
        assert result["has_drift"] is False
        assert result["drift_count"] == 0
        assert result["has_changes"] is False
        assert result["change_count"] == 0
        assert result["resource_changes"] == []
        assert result["summary"] == {"safe": 0, "risky": 0, "blocked": 0, "unknown": 0}

    def test_skips_noop(self):
        result = analyze_plan(
            _plan(
                resource_changes=[
                    {"address": "aws_instance.web", "change": {"actions": ["no-op"]}},
                ],
            ),
        )
        assert result["change_count"] == 0
        assert result["resource_changes"] == []

    def test_resource_change_defaults_to_safe_with_no_rules(self):
        result = analyze_plan(
            _plan(
                resource_changes=[
                    {
                        "address": "aws_instance.web",
                        "type": "aws_instance",
                        "name": "web",
                        "provider_name": "registry.terraform.io/hashicorp/aws",
                        "mode": "managed",
                        "change": {
                            "actions": ["update"],
                            "before": {"instance_type": "t2.micro", "tags": {"role": "web"}},
                            "after": {"instance_type": "t3.small", "tags": {"role": "db"}},
                        },
                    },
                ],
            ),
        )
        assert result["has_changes"] is True
        assert result["change_count"] == 1
        entry = result["resource_changes"][0]
        assert entry["source"] == "resource_changes"
        assert entry["classification"] == "safe"
        assert set(entry["changed_attributes"]) == {"instance_type", "tags.role"}
        assert result["summary"]["safe"] == 1

    def test_resource_change_classified_with_type_scoped_rule(self):
        result = analyze_plan(
            _plan(
                resource_changes=[
                    {
                        "address": "aws_instance.web",
                        "type": "aws_instance",
                        "name": "web",
                        "change": {
                            "actions": ["update"],
                            "before": {"instance_type": "t2.micro"},
                            "after": {"instance_type": "t3.small"},
                        },
                    },
                ],
            ),
            risky_attributes=["aws_instance.*.instance_type"],
        )
        entry = result["resource_changes"][0]
        assert entry["classification"] == "risky"
        assert result["summary"]["risky"] == 1

    def test_drift_detected_defaults_to_safe(self):
        result = analyze_plan(
            _plan(
                resource_drift=[
                    {
                        "address": "aws_instance.web",
                        "type": "aws_instance",
                        "name": "web",
                        "change": {
                            "actions": ["update"],
                            "before": {"ami": "ami-old"},
                            "after": {"ami": "ami-new"},
                        },
                    },
                ],
            ),
        )
        assert result["has_drift"] is True
        assert result["drift_count"] == 1
        entry = result["resource_changes"][0]
        assert entry["source"] == "resource_drift"
        assert entry["classification"] == "safe"

    def test_detect_drift_disabled(self):
        result = analyze_plan(
            _plan(
                resource_drift=[
                    {"address": "aws_instance.web", "change": {"actions": ["update"], "before": {"ami": "a"}, "after": {"ami": "b"}}},
                ],
            ),
            detect_drift=False,
        )
        assert result["drift_count"] == 0

    def test_include_resource_changes_disabled(self):
        result = analyze_plan(
            _plan(
                resource_changes=[
                    {"address": "aws_instance.web", "change": {"actions": ["update"], "before": {"ami": "a"}, "after": {"ami": "b"}}},
                ],
            ),
            include_resource_changes=False,
        )
        assert result["change_count"] == 0

    def test_output_changes(self):
        result = analyze_plan(
            _plan(
                output_changes={
                    "endpoint": {"actions": ["update"], "before": "a", "after": "b"},
                    "unchanged": {"actions": ["no-op"]},
                },
            ),
        )
        names = [o["name"] for o in result["output_changes"]]
        assert names == ["endpoint"]

    def test_include_output_changes_disabled(self):
        result = analyze_plan(
            _plan(output_changes={"endpoint": {"actions": ["update"], "before": "a", "after": "b"}}),
            include_output_changes=False,
        )
        assert result["output_changes"] == []

    def test_include_values_masks_sensitive(self):
        result = analyze_plan(
            _plan(
                resource_changes=[
                    {
                        "address": "aws_db_instance.main",
                        "type": "aws_db_instance",
                        "name": "main",
                        "change": {
                            "actions": ["update"],
                            "before": {"password": "old", "instance_type": "db.t3.micro"},
                            "after": {"password": "new", "instance_type": "db.t3.small"},
                            "before_sensitive": {"password": True},
                            "after_sensitive": {"password": True},
                        },
                    },
                ],
            ),
            include_values=True,
        )
        entry = result["resource_changes"][0]
        assert entry["before"]["password"] == ""
        assert entry["after"]["password"] == ""
        assert entry["after"]["instance_type"] == "db.t3.small"

    def test_include_values_default_omits_values(self):
        result = analyze_plan(
            _plan(
                resource_changes=[
                    {"address": "aws_instance.web", "change": {"actions": ["update"], "before": {"ami": "a"}, "after": {"ami": "b"}}},
                ],
            ),
        )
        assert "before" not in result["resource_changes"][0]

    def test_custom_classification_lists(self):
        result = analyze_plan(
            _plan(
                resource_changes=[
                    {
                        "address": "test_resource.thing",
                        "type": "test_resource",
                        "name": "thing",
                        "change": {"actions": ["update"], "before": {"custom_attr": 1}, "after": {"custom_attr": 2}},
                    },
                ],
            ),
            blocked_attributes=["*.custom_attr"],
        )
        assert result["resource_changes"][0]["classification"] == "blocked"

    def test_drift_and_changes_both_counted(self):
        result = analyze_plan(
            _plan(
                resource_drift=[
                    {"address": "aws_instance.web", "change": {"actions": ["update"], "before": {"ami": "a"}, "after": {"ami": "b"}}},
                ],
                resource_changes=[
                    {"address": "aws_instance.web", "change": {"actions": ["update"], "before": {"tags": {"x": 1}}, "after": {"tags": {"x": 2}}}},
                ],
            ),
        )
        assert result["drift_count"] == 1
        assert result["change_count"] == 1
        assert len(result["resource_changes"]) == 2
        sources = {e["source"] for e in result["resource_changes"]}
        assert sources == {"resource_drift", "resource_changes"}
