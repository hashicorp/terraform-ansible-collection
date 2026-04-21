# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""SearchSource: placeholder reserved for future cross-workspace search."""

from typing import Any, Dict, List

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.base import BaseInventorySource, HostRecord

_NOT_IMPLEMENTED = "source 'search' is not yet implemented. Use source 'statefile' or 'outputs' for the current release."


class SearchSource(BaseInventorySource):
    """Placeholder reserved for a future cross-workspace / cross-org search source."""

    NAME = "search"

    @classmethod
    def validate_options(cls, options: Dict[str, Any]) -> None:
        raise TerraformError(_NOT_IMPLEMENTED)

    def collect_hosts(self) -> List[HostRecord]:
        raise TerraformError(_NOT_IMPLEMENTED)
