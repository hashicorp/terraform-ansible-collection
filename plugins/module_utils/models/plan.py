#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Data models for Terraform plan operations."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SensitiveValueData:
    """Data structure for handling sensitive value processing."""

    before_item: Any
    after_item: Any
    is_before_sensitive: bool
    is_after_sensitive: bool
    before_raw_item: Any
    after_raw_item: Any


@dataclass
class ViewPlanResourceData:
    """Unified resource data structure."""

    address: str
    resource_changes: Optional[Dict]
    resource_drift: Optional[Dict]
    has_drift: bool
