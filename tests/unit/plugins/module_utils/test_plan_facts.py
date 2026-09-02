# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from ansible_collections.hashicorp.terraform.plugins.module_utils.plan_facts import (
    check_format_version,
    diff_attributes,
    iter_output_changes,
    iter_resource_changes,
    iter_resource_drift,
    mask_sensitive,
)


class TestCheckFormatVersion:
    def test_accepts_1_x(self):
        assert check_format_version({"format_version": "1.2"}) is None

    def test_missing_version_warns(self):
        warning = check_format_version({})
        assert warning is not None
        assert "missing 'format_version'" in warning

    def test_2_x_warns_but_does_not_raise(self):
        warning = check_format_version({"format_version": "2.0"})
        assert warning is not None
        assert "2.0" in warning

    def test_non_numeric_warns(self):
        warning = check_format_version({"format_version": "beta"})
        assert warning is not None
        assert "Unrecognized" in warning


class TestDiffAttributes:
    def test_scalar_change(self):
        change = {"before": {"instance_type": "t2.micro"}, "after": {"instance_type": "t3.small"}}
        changed, unknown = diff_attributes(change)
        assert changed == ["instance_type"]
        assert unknown == []

    def test_nested_change(self):
        change = {
            "before": {"tags": {"role": "web"}},
            "after": {"tags": {"role": "db"}},
        }
        changed, unknown = diff_attributes(change)
        assert changed == ["tags.role"]

    def test_create_marks_all_after_keys(self):
        change = {"before": None, "after": {"ami": "ami-123", "instance_type": "t2.micro"}}
        changed, _unknown = diff_attributes(change)
        assert set(changed) == {"ami", "instance_type"}

    def test_list_element_change(self):
        change = {
            "before": {"ingress": [{"port": 80}]},
            "after": {"ingress": [{"port": 443}]},
        }
        changed, _unknown = diff_attributes(change)
        assert changed == ["ingress[0].port"]

    def test_list_length_change(self):
        change = {"before": {"ingress": [1]}, "after": {"ingress": [1, 2]}}
        changed, _unknown = diff_attributes(change)
        assert "ingress[1]" in changed

    def test_unknown_tracked_separately(self):
        change = {
            "before": {"private_dns": "old"},
            "after": {"private_dns": None},
            "after_unknown": {"private_dns": True},
        }
        changed, unknown = diff_attributes(change)
        assert unknown == ["private_dns"]
        assert "private_dns" not in changed

    def test_no_change(self):
        change = {"before": {"a": 1}, "after": {"a": 1}}
        changed, unknown = diff_attributes(change)
        assert changed == []
        assert unknown == []


class TestMaskSensitive:
    def test_masks_flagged_scalar(self):
        assert mask_sensitive("secret", True) == ""

    def test_leaves_unflagged_scalar(self):
        assert mask_sensitive("visible", False) == "visible"

    def test_masks_nested_dict_leaf(self):
        value = {"password": "hunter2", "user": "admin"}
        sensitive = {"password": True, "user": False}
        assert mask_sensitive(value, sensitive) == {"password": "", "user": "admin"}

    def test_masks_list_items(self):
        value = ["a", "b"]
        sensitive = [False, True]
        assert mask_sensitive(value, sensitive) == ["a", ""]


class TestIterators:
    def test_iter_resource_drift_skips_noop(self):
        plan = {"resource_drift": [{"address": "a", "change": {"actions": ["no-op"]}}, {"address": "b", "change": {"actions": ["update"]}}]}
        assert [r["address"] for r in iter_resource_drift(plan)] == ["b"]

    def test_iter_resource_changes_skips_noop(self):
        plan = {"resource_changes": [{"address": "a", "change": {"actions": ["no-op"]}}, {"address": "b", "change": {"actions": ["create"]}}]}
        assert [r["address"] for r in iter_resource_changes(plan)] == ["b"]

    def test_iter_output_changes_skips_noop(self):
        plan = {"output_changes": {"a": {"actions": ["no-op"]}, "b": {"actions": ["update"]}}}
        assert [name for name, _change in iter_output_changes(plan)] == ["b"]
