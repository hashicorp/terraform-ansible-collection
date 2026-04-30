# -*- coding: utf-8 -*-
# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plan models."""

from dataclasses import asdict

from ansible_collections.hashicorp.terraform.plugins.module_utils.models.plan import (
    SensitiveValueData,
    ViewPlanResourceData,
)


class TestSensitiveValueData:
    """Tests for SensitiveValueData dataclass."""

    def test_creation_and_attributes(self):
        """Test creating SensitiveValueData and accessing attributes."""
        data = SensitiveValueData(
            before_item=123,
            after_item=456,
            is_before_sensitive=True,
            is_after_sensitive=False,
            before_raw_item="***",
            after_raw_item="456",
        )

        assert data.before_item == 123
        assert data.after_item == 456
        assert data.is_before_sensitive is True
        assert data.is_after_sensitive is False
        assert data.before_raw_item == "***"
        assert data.after_raw_item == "456"

    def test_asdict_conversion(self):
        """Test converting SensitiveValueData to dict with asdict()."""
        data = SensitiveValueData(
            before_item="old",
            after_item="new",
            is_before_sensitive=False,
            is_after_sensitive=True,
            before_raw_item="plain",
            after_raw_item="***",
        )

        result = asdict(data)

        assert result == {
            "before_item": "old",
            "after_item": "new",
            "is_before_sensitive": False,
            "is_after_sensitive": True,
            "before_raw_item": "plain",
            "after_raw_item": "***",
        }


class TestViewPlanResourceData:
    """Tests for ViewPlanResourceData dataclass."""

    def test_creation_and_attributes(self):
        """Test creating ViewPlanResourceData and accessing attributes."""
        resource = ViewPlanResourceData(
            address="aws_instance.example",
            resource_changes={"actions": ["create"]},
            resource_drift=None,
            has_drift=False,
        )

        assert resource.address == "aws_instance.example"
        assert resource.resource_changes == {"actions": ["create"]}
        assert resource.resource_drift is None
        assert resource.has_drift is False

    def test_asdict_conversion(self):
        """Test converting ViewPlanResourceData to dict with asdict()."""
        resource = ViewPlanResourceData(
            address="aws_s3_bucket.mybucket",
            resource_changes=None,
            resource_drift={"id": "bucket-123"},
            has_drift=True,
        )

        result = asdict(resource)

        assert result == {
            "address": "aws_s3_bucket.mybucket",
            "resource_changes": None,
            "resource_drift": {"id": "bucket-123"},
            "has_drift": True,
        }
