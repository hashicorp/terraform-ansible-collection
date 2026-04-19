# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""OutputsSource: builds inventory by querying the HCP Terraform outputs API.

Uses the ``/state-version-outputs`` endpoint (via ``get_workspace_outputs``)
to list the current state version outputs for the target workspace.  This is
the lighter-weight path when only named output values are needed: it avoids
downloading the full state binary and works well when outputs are the primary
source of host data.

Dict-valued outputs produce one host each; list-of-dict outputs produce one
host per element (indexed).  All other output types are silently skipped.
"""

from typing import Any, Dict, List

from ansible.errors import AnsibleParserError

from ansible_collections.hashicorp.terraform.plugins.inventory.utils.base import BaseInventorySource, HostRecord
from ansible_collections.hashicorp.terraform.plugins.inventory.utils.common import fetch_outputs, resolve_workspace


class OutputsSource(BaseInventorySource):
    """Reads current state version outputs via the HCP Terraform outputs API."""

    NAME = "outputs"

    @classmethod
    def validate_options(cls, options: Dict[str, Any]) -> None:
        workspace_id = options.get("workspace_id")
        organization = options.get("organization")
        workspace = options.get("workspace")
        if not workspace_id and not (organization and workspace):
            raise AnsibleParserError(
                "source 'outputs' requires either 'workspace_id' or both "
                "'organization' and 'workspace'."
            )

    def collect_hosts(self) -> List[HostRecord]:
        workspace_id_opt = self.options.get("workspace_id")
        organization = self.options.get("organization")
        workspace = self.options.get("workspace")

        resolved_id, workspace_name = resolve_workspace(
            self.client, workspace_id_opt, organization, workspace
        )
        outputs = fetch_outputs(self.client, resolved_id)

        records: List[HostRecord] = []
        for output in outputs:
            output_name: str = output.get("name") or "unknown"
            value = output.get("value")

            if isinstance(value, dict):
                records.append(
                    {
                        "output_name": output_name,
                        "workspace_name": workspace_name,
                        "host_vars": value,
                        "index": None,
                    }
                )
            elif isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                for idx, item in enumerate(value):
                    records.append(
                        {
                            "output_name": output_name,
                            "workspace_name": workspace_name,
                            "host_vars": item,
                            "index": idx,
                        }
                    )

        return records
