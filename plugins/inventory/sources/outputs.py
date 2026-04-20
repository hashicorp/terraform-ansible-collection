# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""OutputsSource: builds inventory by querying the HCP Terraform outputs API.

Uses the ``/state-version-outputs`` endpoint (via ``get_workspace_outputs``)
to list the current state version outputs for the target workspace.

Auto-detection mode (no ``hosts_from``)
-----------------------------------------
- ``dict`` output  → one host with the dict as host variables.
- ``list(dict)`` output → one host per element (indexed).
- All other shapes are silently skipped.

Explicit mode (``hosts_from`` configured)
------------------------------------------
All Terraform output shapes are supported via the ``hosts_from`` option:

kind × element_type  →  behaviour
------------------------------------
scalar  × *          →  single host; raw value stored as ``value``
list    × object     →  one host per element (indexed)
list    × primitive  →  one host per element; element stored as ``value``
map     × object     →  one host per key; key becomes resolved hostname
map     × primitive  →  one host per key; key becomes resolved hostname
object  × object     →  single host (dict as host variables)

For primitive element types, ``use_as`` assigns the raw element value to the
named Ansible variable directly (e.g. ``use_as: ansible_host``).
For ``map`` kinds the map key is exposed as the special variable ``key``.
"""

from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleParserError

from ansible_collections.hashicorp.terraform.plugins.inventory.utils.base import BaseInventorySource, HostRecord
from ansible_collections.hashicorp.terraform.plugins.inventory.utils.common import fetch_outputs, resolve_workspace


# ---------------------------------------------------------------------------
# hosts_from spec processor
# ---------------------------------------------------------------------------


def _collect_hosts_from_spec(
    spec: Dict[str, Any],
    outputs_map: Dict[str, Any],
    workspace_name: str,
) -> List[HostRecord]:
    """Return HostRecords for one *hosts_from* spec entry.

    *outputs_map* is ``{output_name: value}`` built from the raw outputs list.
    Returns an empty list when the named output is absent or the value type
    does not match the declared *kind*/*element_type*.
    """
    output_name: str = spec.get("output", "")
    kind: str = (spec.get("kind") or "").lower()
    element_type: str = (spec.get("element_type") or "").lower()
    use_as: Optional[str] = spec.get("use_as")

    if output_name not in outputs_map:
        return []

    value = outputs_map[output_name]
    records: List[HostRecord] = []

    if kind == "scalar":
        host_vars: Dict[str, Any] = {"value": value}
        if use_as:
            host_vars[use_as] = value
        records.append(
            {
                "output_name": output_name,
                "workspace_name": workspace_name,
                "host_vars": host_vars,
                "index": None,
            }
        )

    elif kind == "list":
        if not isinstance(value, list):
            return records
        if element_type == "object":
            # list(object) — same semantics as auto-detection, but explicit
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    records.append(
                        {
                            "output_name": output_name,
                            "workspace_name": workspace_name,
                            "host_vars": item,
                            "index": idx,
                        }
                    )
        else:
            # list(string|number|bool) — auto-named indexed hosts
            for idx, item in enumerate(value):
                host_vars = {"value": item}
                if use_as:
                    host_vars[use_as] = item
                records.append(
                    {
                        "output_name": output_name,
                        "workspace_name": workspace_name,
                        "host_vars": host_vars,
                        "index": idx,
                    }
                )

    elif kind == "map":
        if not isinstance(value, dict):
            return records
        if element_type == "object":
            # map(object) — key = hostname, dict value = host variables
            for key, obj in value.items():
                if isinstance(obj, dict):
                    host_vars = dict(obj)
                    host_vars["key"] = key
                    records.append(
                        {
                            "output_name": output_name,
                            "workspace_name": workspace_name,
                            "host_vars": host_vars,
                            "index": None,
                            "resolved_hostname": key,
                        }
                    )
        else:
            # map(string|number|bool) — key = hostname, primitive = value
            for key, item in value.items():
                host_vars = {"value": item, "key": key}
                if use_as:
                    host_vars[use_as] = item
                records.append(
                    {
                        "output_name": output_name,
                        "workspace_name": workspace_name,
                        "host_vars": host_vars,
                        "index": None,
                        "resolved_hostname": key,
                    }
                )

    elif kind == "object":
        if isinstance(value, dict):
            records.append(
                {
                    "output_name": output_name,
                    "workspace_name": workspace_name,
                    "host_vars": value,
                    "index": None,
                }
            )

    return records


# ---------------------------------------------------------------------------
# Source backend
# ---------------------------------------------------------------------------


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

        hosts_from_opt = self.options.get("hosts_from") or []
        if isinstance(hosts_from_opt, dict):
            hosts_from_opt = [hosts_from_opt]

        resolved_id, workspace_name = resolve_workspace(
            self.client, workspace_id_opt, organization, workspace
        )
        outputs = fetch_outputs(self.client, resolved_id)

        if hosts_from_opt:
            # Explicit mode: process only the declared outputs per their spec.
            outputs_map: Dict[str, Any] = {
                o.get("name", ""): o.get("value")
                for o in outputs
                if isinstance(o, dict)
            }
            records: List[HostRecord] = []
            for spec in hosts_from_opt:
                records.extend(_collect_hosts_from_spec(spec, outputs_map, workspace_name))
            return records

        # Auto-detection mode (backwards compatible).
        records = []
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
