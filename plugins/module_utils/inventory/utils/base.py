# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, List, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient

#: Normalized host record returned by BaseInventorySource.collect_hosts.
#: Keys: output_name (str), workspace_name (str), host_vars (dict), index (int | None)
HostRecord = Dict[str, Any]


class BaseInventorySource:
    """Abstract base for all inventory data source backends.

    Subclasses must define ``NAME`` and implement ``validate_options`` (class
    method, static checks before any I/O) and ``collect_hosts`` (instance
    method, performs API/IO work and returns normalized records).
    """

    NAME: Optional[str] = None

    @classmethod
    def validate_options(cls, options: Dict[str, Any]) -> None:
        """Validate source-specific options before the API client is constructed.

        Raises ``AnsibleParserError`` with a descriptive message on failure.
        """
        raise NotImplementedError

    def __init__(self, client: TerraformClient, options: Dict[str, Any]) -> None:
        self.client = client
        self.options = options

    def collect_hosts(self) -> List[HostRecord]:
        """Fetch source data and return a list of normalized host records.

        Each record is a dict with keys:
        - ``output_name`` (str): logical name of the source output
        - ``workspace_name`` (str): used as hostname prefix
        - ``host_vars`` (dict): host variable mapping
        - ``index`` (int | None): element index for list outputs, else ``None``

        Raises ``AnsibleParserError`` on API or data errors.
        """
        raise NotImplementedError
