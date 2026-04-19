# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""StatefileSource: builds inventory by downloading the raw Terraform state file.

The HCP Terraform API exposes a signed download URL for the current state
version of each workspace.  This source fetches that binary blob, decodes it
as JSON (Terraform state format v4), and extracts the top-level ``outputs``
section to produce host records — one host per dict-valued output, one host
per element of a list-of-dicts output.

This approach works even when the outputs API endpoint is unavailable or when
you need raw access to the full state structure.
"""

import json
from typing import Any, Dict, List

from ansible.errors import AnsibleParserError
from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.inventory.utils.base import BaseInventorySource, HostRecord
from ansible_collections.hashicorp.terraform.plugins.inventory.utils.common import resolve_workspace
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError


def _download_statefile(client: Any, workspace_id: str) -> Dict[str, Any]:
    """Download and JSON-decode the current Terraform state file for *workspace_id*.

    Uses ``client.client.state_versions.download_current`` which follows the
    ``hosted-state-download-url`` signed link returned by HCP Terraform.

    Raises ``AnsibleParserError`` when the state version is missing, the
    download fails, or the content cannot be parsed as JSON.
    """
    try:
        raw: bytes = client.client.state_versions.download_current(workspace_id)
        return json.loads(raw)
    except NotFound:
        raise AnsibleParserError(
            f"No current state version found for workspace '{workspace_id}'. "
            "The workspace may have no applied runs yet."
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise AnsibleParserError(
            f"Failed to parse state file for workspace '{workspace_id}': {exc}"
        ) from exc
    except TerraformError as exc:
        raise AnsibleParserError(
            f"Failed to download state file for workspace '{workspace_id}': {exc}"
        ) from exc


class StatefileSource(BaseInventorySource):
    """Downloads the raw ``.tfstate`` JSON and reads its ``outputs`` section.

    Supports dict-valued outputs (one host each) and list-of-dict outputs
    (one host per element, indexed).  All other output types are silently
    skipped.
    """

    NAME = "statefile"

    @classmethod
    def validate_options(cls, options: Dict[str, Any]) -> None:
        workspace_id = options.get("workspace_id")
        organization = options.get("organization")
        workspace = options.get("workspace")
        if not workspace_id and not (organization and workspace):
            raise AnsibleParserError(
                "source 'statefile' requires either 'workspace_id' or both "
                "'organization' and 'workspace'."
            )

    def collect_hosts(self) -> List[HostRecord]:
        workspace_id_opt = self.options.get("workspace_id")
        organization = self.options.get("organization")
        workspace = self.options.get("workspace")

        resolved_id, workspace_name = resolve_workspace(
            self.client, workspace_id_opt, organization, workspace
        )

        state_data = _download_statefile(self.client, resolved_id)

        records: List[HostRecord] = []
        for output_name, output_obj in state_data.get("outputs", {}).items():
            value = output_obj.get("value")

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
