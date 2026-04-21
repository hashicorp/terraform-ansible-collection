# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""StatefileSource: HCP Terraform / TFE-first resource inventory via state download.

This source targets **HCP Terraform and Terraform Enterprise customers exclusively**.
It does not require the Terraform CLI, local backend access, or direct storage
access (S3, AzureRM, etc.).  Authentication is purely via the pytfe SDK wrapper.

Workflow
--------
1. Resolve the target workspace through the TFE/HCP Terraform API (by
   ``workspace_id`` or ``organization`` + ``workspace``).
2. Download the latest state version payload using
   ``client.state_versions.download_current(workspace_id)``, which follows
   HCP Terraform's signed ``hosted-state-download-url`` link.
3. Parse the Terraform state JSON (format version 4).
4. Walk ``resources[]``, filter by provider/resource-type and module scope, and
   emit one ``HostRecord`` per resource instance.
5. All instance ``attributes`` become Ansible host variables.

Key differences from ``cloud.terraform.terraform_state``
---------------------------------------------------------
- No Terraform CLI required: state is fetched directly from HCP Terraform API.
- No backend config (S3, http, azurerm, etc.): HCP Terraform is the backend.
- Hostname resolution supports ``tag:Name`` attribute lookups alongside plain
  attribute lookups; the default is ``<resource_type>_<resource_name>``.
- ``resolved_hostname`` is set on every HostRecord so the common
  ``_populate_from_host_records`` pipeline skips outputs-style resolution.

Supported resource types (extendable via ``provider_mapping``)
--------------------------------------------------------------
- AWS:    ``aws_instance``, ``aws_network_interface``
- Azure:  ``azurerm_linux_virtual_machine``, ``azurerm_windows_virtual_machine``,
           ``azurerm_virtual_machine``
- GCP:    ``google_compute_instance``
"""

import json
import re
from typing import Any, Dict, List, Optional, Union

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.base import BaseInventorySource, HostRecord
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common import resolve_workspace

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_STATE_VERSION = 4

#: Default provider → resource-type mappings for common compute resources.
#: Extend at runtime via ``provider_mapping`` inventory option.
PROVIDER_RESOURCE_TYPES: Dict[str, List[str]] = {
    "registry.terraform.io/hashicorp/aws": [
        "aws_instance",
        "aws_network_interface",
    ],
    "registry.terraform.io/hashicorp/azurerm": [
        "azurerm_linux_virtual_machine",
        "azurerm_windows_virtual_machine",
        "azurerm_virtual_machine",
    ],
    "registry.terraform.io/hashicorp/google": [
        "google_compute_instance",
    ],
}

# ---------------------------------------------------------------------------
# State file download
# ---------------------------------------------------------------------------


def _download_statefile(client: Any, workspace_id: str) -> Dict[str, Any]:
    """Download and JSON-decode the latest Terraform state for *workspace_id*.

    Uses ``client.client.state_versions.download_current`` which resolves the
    ``hosted-state-download-url`` signed link returned by HCP Terraform —
    no CLI, no direct backend access.

    Raises ``TerraformError`` when the state version is absent, the
    download fails, or the payload cannot be parsed as JSON.
    """
    try:
        raw: bytes = client.client.state_versions.download_current(workspace_id)
        return json.loads(raw)
    except NotFound:
        raise TerraformError(f"No current state version found for workspace '{workspace_id}'. " "The workspace may have no applied runs yet.")
    except (json.JSONDecodeError, ValueError) as exc:
        raise TerraformError(f"Failed to parse state file for workspace '{workspace_id}': {exc}") from exc
    except TerraformError as exc:
        raise TerraformError(f"Failed to download state file for workspace '{workspace_id}': {exc}") from exc


# ---------------------------------------------------------------------------
# Resource filtering helpers
# ---------------------------------------------------------------------------


def _parse_provider_name(provider_str: str) -> Optional[str]:
    """Extract the registry provider name from a Terraform state provider string.

    Handles both root and module formats::

        provider["registry.terraform.io/hashicorp/aws"]
        module.my_mod.provider["registry.terraform.io/hashicorp/aws"]

    Returns ``None`` when the string cannot be parsed.
    """
    m = re.search(r'provider\["([^"]+)"\]', provider_str)
    return m.group(1) if m else None


def _build_provider_configs(custom_mappings: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Return a merged provider → resource-type map (defaults + custom entries).

    Each entry in *custom_mappings* must have ``provider_name`` (str) and
    ``types`` (list[str]).  Custom types are appended without duplicates.
    """
    configs: Dict[str, List[str]] = {k: list(v) for k, v in PROVIDER_RESOURCE_TYPES.items()}
    for mapping in custom_mappings:
        provider_name = mapping.get("provider_name", "").strip()
        types: List[str] = mapping.get("types") or []
        if provider_name and types:
            existing = configs.setdefault(provider_name, [])
            for t in types:
                if t not in existing:
                    existing.append(t)
    return configs


def _should_include_resource(
    resource: Dict[str, Any],
    search_child_modules: bool,
    provider_configs: Dict[str, List[str]],
) -> bool:
    """Return True when *resource* should produce inventory hosts.

    Rules:
    - Only ``mode: managed`` resources are included (data sources are skipped).
    - Child-module resources are skipped unless ``search_child_modules=True``.
    - The resource's provider+type must appear in *provider_configs*.
    """
    if resource.get("mode") != "managed":
        return False
    if not search_child_modules and resource.get("module"):
        return False
    provider_name = _parse_provider_name(resource.get("provider", ""))
    resource_type = resource.get("type", "")
    if provider_name is None:
        return False
    allowed_types = provider_configs.get(provider_name, [])
    return resource_type in allowed_types


# ---------------------------------------------------------------------------
# Hostname resolution helpers
# ---------------------------------------------------------------------------


def _get_tag_value(attributes: Dict[str, Any], tag_spec: str) -> Optional[str]:
    """Extract a tag value from resource *attributes* using a tag spec string.

    Two forms are supported:

    ``Name``
        Returns the value of ``tags["Name"]`` when present.

    ``Name=MyServer``
        Returns ``"Name_MyServer"`` only when ``tags["Name"] == "MyServer"``.
        Useful for unambiguous tag-based group membership checks.
    """
    tags = attributes.get("tags") or {}
    if not isinstance(tags, dict):
        return None

    parts = tag_spec.split("=", 1)
    if len(parts) == 2:
        key, expected_value = parts
        actual = str(tags.get(key, ""))
        return f"{key}_{expected_value}" if actual == expected_value else None

    value = tags.get(tag_spec)
    return str(value) if value else None


def _resolve_resource_preference(
    attributes: Dict[str, Any],
    preference: str,
) -> Optional[str]:
    """Resolve one hostname preference token against resource *attributes*.

    Handles:

    - ``tag:<spec>``  → tag-based lookup via ``_get_tag_value``
    - ``<attr_name>`` → direct attribute lookup
    - literal strings (not in attributes) → returned as-is

    Returns ``None`` when the resolved value would be empty.
    """
    if preference.startswith("tag:"):
        return _get_tag_value(attributes, preference[4:])

    if preference in attributes:
        value = attributes[preference]
        if value is not None and str(value).strip():
            return str(value)
        return None

    return preference.strip() or None


def get_resource_hostname(
    resource_type: str,
    resource_name: str,
    attributes: Dict[str, Any],
    hostnames: Optional[List[Any]] = None,
    index_key: Optional[Union[int, str]] = None,
) -> str:
    """Resolve the inventory hostname for one resource instance.

    Walks *hostnames* in order of preference, returning the first non-empty
    result.  Falls back to ``<resource_type>_<resource_name>[_<index_key>]``.

    Each *hostnames* entry can be:

    - A plain string: attribute name, ``tag:<spec>``, or literal.
    - A dict with ``name`` (required), ``prefix`` (optional), and
      ``separator`` (default ``_``).

    Raises ``TerraformError`` when a dict entry is missing ``name``.
    """
    if index_key is not None:
        fallback = f"{resource_type}_{resource_name}_{index_key}"
    else:
        fallback = f"{resource_type}_{resource_name}"

    if not hostnames:
        return fallback

    for preference in hostnames:
        hostname: Optional[str] = None

        if isinstance(preference, dict):
            if "name" not in preference:
                raise TerraformError("A 'name' key must be defined in a hostnames dictionary.")
            hostname = _resolve_resource_preference(attributes, preference["name"])
            if hostname and "prefix" in preference:
                prefix = _resolve_resource_preference(attributes, preference["prefix"])
                if prefix:
                    sep = preference.get("separator", "_")
                    hostname = f"{prefix}{sep}{hostname}"
        else:
            hostname = _resolve_resource_preference(attributes, str(preference))

        if hostname:
            return hostname

    return fallback


# ---------------------------------------------------------------------------
# Source backend
# ---------------------------------------------------------------------------


class StatefileSource(BaseInventorySource):
    """Downloads the latest ``.tfstate`` from HCP Terraform and builds inventory from resources.

    Uses ``pytfe`` SDK's ``state_versions.download_current()`` — no Terraform
    CLI, no direct backend access.  Resources are filtered by provider/type
    (see ``PROVIDER_RESOURCE_TYPES`` and ``provider_mapping`` option).
    """

    NAME = "statefile"

    @classmethod
    def validate_options(cls, options: Dict[str, Any]) -> None:
        workspace_id = options.get("workspace_id")
        organization = options.get("organization")
        workspace = options.get("workspace")
        if not workspace_id and not (organization and workspace):
            raise TerraformError("source 'statefile' requires either 'workspace_id' or both 'organization' and 'workspace'.")

    def collect_hosts(self) -> List[HostRecord]:
        workspace_id_opt = self.options.get("workspace_id")
        organization = self.options.get("organization")
        workspace = self.options.get("workspace")
        search_child_modules: bool = bool(self.options.get("search_child_modules", False))
        provider_mapping: List[Dict[str, Any]] = self.options.get("provider_mapping") or []
        hostnames: List[Any] = self.options.get("hostnames") or []

        resolved_id, workspace_name = resolve_workspace(self.client, workspace_id_opt, organization, workspace)

        state_data = _download_statefile(self.client, resolved_id)
        provider_configs = _build_provider_configs(provider_mapping)

        records: List[HostRecord] = []
        for resource in state_data.get("resources", []):
            if not _should_include_resource(resource, search_child_modules, provider_configs):
                continue

            resource_type: str = resource.get("type", "")
            resource_name: str = resource.get("name", "")
            instances: List[Dict[str, Any]] = resource.get("instances") or []

            # When any instance carries an index_key (count / for_each),
            # include the key in the fallback hostname to avoid collisions.
            multi_instance = len(instances) > 1 or any("index_key" in inst for inst in instances)

            for instance in instances:
                attributes: Dict[str, Any] = instance.get("attributes") or {}
                index_key: Optional[Union[int, str]] = instance.get("index_key")

                effective_index = index_key if multi_instance else None

                resolved_hostname = get_resource_hostname(
                    resource_type,
                    resource_name,
                    attributes,
                    hostnames,
                    effective_index,
                )

                records.append(
                    {
                        "output_name": f"{resource_type}_{resource_name}",
                        "workspace_name": workspace_name,
                        "host_vars": attributes,
                        "index": effective_index,
                        "resolved_hostname": resolved_hostname,
                    }
                )

        return records
