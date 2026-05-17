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
5. Instance ``attributes`` become Ansible host variables, *minus* any path
   listed in the instance's Terraform ``sensitive_attributes`` metadata —
   sensitive values are dropped entirely (not masked) so they cannot leak
   into inventory output.  This applies even when the dropped field would
   have been used by ``hostnames``, ``compose``, ``groups``, ``keyed_groups``,
   or filters; those references will simply not resolve.  Note that this
   only protects values Terraform/its providers actually flag as sensitive —
   the ``outputs`` source is preferable when intentional inventory shape is
   the goal.

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

import copy
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
# Sensitive attribute sanitization
# ---------------------------------------------------------------------------


def _first_top_level_attribute(path: List[Any]) -> Optional[str]:
    """Return the first ``get_attr`` name in *path*, or ``None`` when missing.

    Used as the safe fallback target when a sensitive path cannot be walked
    precisely.  Terraform always begins a sensitive path with a ``get_attr``
    step naming a top-level attribute; anything else is treated as malformed.
    """
    if not path:
        return None
    first = path[0]
    if not isinstance(first, dict) or first.get("type") != "get_attr":
        return None
    value = first.get("value")
    return value if isinstance(value, str) else None


def _step_into(parent: Any, step: Any) -> Any:
    """Follow one traversal step into *parent*; return ``None`` when impossible.

    Step values must match Terraform's schema: ``get_attr`` carries a string
    attribute name, ``index`` carries an int (list) or string (map key).  Any
    other shape — including unhashable values like lists or dicts that would
    raise ``TypeError`` from a membership check — short-circuits to ``None``.
    """
    if not isinstance(step, dict):
        return None
    step_type = step.get("type")
    value = step.get("value")
    if step_type == "get_attr":
        if isinstance(value, str) and isinstance(parent, dict) and value in parent:
            return parent[value]
        return None
    if step_type == "index":
        if isinstance(parent, list) and isinstance(value, int) and 0 <= value < len(parent):
            return parent[value]
        if isinstance(parent, dict) and isinstance(value, (str, int)) and value in parent:
            return parent[value]
    return None


def _drop_sensitive_path(attributes: Dict[str, Any], path: List[Any]) -> None:
    """Remove a single sensitive path from *attributes* in-place.

    Walks *path* one step at a time.  When the leaf step targets a precise
    dict key, that element is deleted.  Any ambiguity
    (unwalkable parent, unknown step type, missing key/index) falls back to
    deleting the first top-level attribute named in the path.  Paths with no
    usable top-level reference are ignored.
    """
    top_level = _first_top_level_attribute(path)

    def _drop_top_level() -> None:
        if top_level is not None and top_level in attributes:
            del attributes[top_level]

    if len(path) == 1:
        _drop_top_level()
        return

    parent: Any = attributes
    for step in path[:-1]:
        parent = _step_into(parent, step)
        if parent is None:
            _drop_top_level()
            return

    last = path[-1]
    if not isinstance(last, dict):
        _drop_top_level()
        return

    last_type = last.get("type")
    last_value = last.get("value")

    if last_type == "get_attr" and isinstance(last_value, str) and isinstance(parent, dict) and last_value in parent:
        del parent[last_value]
        return
    if last_type == "index":
        if isinstance(parent, list) and isinstance(last_value, int) and 0 <= last_value < len(parent):
            # Deleting individual list indices can shift later Terraform
            # sensitive paths. Drop the owning top-level attribute instead so
            # multiple sensitive list entries cannot leave one another behind.
            _drop_top_level()
            return
        if isinstance(parent, dict) and isinstance(last_value, (str, int)) and last_value in parent:
            del parent[last_value]
            return

    _drop_top_level()


def _sanitize_sensitive_attributes(
    attributes: Dict[str, Any],
    sensitive_paths: List[Any],
) -> Dict[str, Any]:
    """Return a copy of *attributes* with Terraform-flagged sensitive paths removed.

    *sensitive_paths* matches Terraform raw-state ``sensitive_attributes``: a
    list of paths where each path is a list of traversal steps shaped like
    ``{"type": "get_attr", "value": "<name>"}`` or
    ``{"type": "index", "value": <int|str>}``.

    Sensitive values are dropped entirely (not masked) so they cannot leak
    into Ansible inventory output.  When precise traversal is not possible,
    the first top-level attribute referenced by the path is removed as the
    safe fallback.
    """
    if not isinstance(attributes, dict) or not sensitive_paths:
        return attributes

    sanitized = copy.deepcopy(attributes)
    for path in sensitive_paths:
        if not isinstance(path, list) or not path:
            continue
        _drop_sensitive_path(sanitized, path)
    return sanitized


def _sanitize_state_for_cache(state_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep-copy of *state_data* with all sensitive attributes stripped.

    Walks every resource instance, applies :func:`_sanitize_sensitive_attributes`
    using the instance's ``sensitive_attributes`` marker, and removes the
    marker afterwards (its values are gone, so the second-pass sanitization
    inside :meth:`StatefileSource.collect_hosts` is a no-op on the cleaned
    blob).

    The result is what gets persisted via Ansible's cache plugins. Values
    Terraform flagged as sensitive must not be written to disk under
    ``~/.ansible/cache/`` or any other backend, so this scrubbing happens
    *before* the blob enters the cache.
    """
    cleaned = copy.deepcopy(state_data) if state_data is not None else {}
    for resource in cleaned.get("resources") or []:
        for instance in resource.get("instances") or []:
            attrs = instance.get("attributes") or {}
            sensitive_paths = instance.get("sensitive_attributes") or []
            instance["attributes"] = _sanitize_sensitive_attributes(attrs, sensitive_paths)
            instance.pop("sensitive_attributes", None)
    return cleaned


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

    Returns ``None`` when the preference does not resolve to a non-blank
    value.  Plain strings are *not* treated as literal hostnames — an
    unresolved preference falls through to the next preference (and
    ultimately to the ``<resource_type>_<resource_name>`` default), instead
    of silently collapsing multi-host inventories to a single literal-named
    host when an attribute is missing or has been stripped as sensitive.
    Mirrors the outputs source's ``_resolve_single_preference``.
    """
    if preference.startswith("tag:"):
        return _get_tag_value(attributes, preference[4:])

    if preference in attributes:
        value = attributes[preference]
        if value is not None and str(value).strip():
            return str(value)
    return None


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

        # Cache-aware fetch.
        # ``_cached_blob`` (if set by the plugin) is a v1 blob whose ``data`` is
        # an already-sanitized state body — cache hits never touch the network.
        # ``_validation_ctx`` (if set) carries a pre-resolved workspace and the
        # current state version ID, so on a validation-mode cache miss the
        # source skips its own ``resolve_workspace`` call and writes a blob
        # tagged with the state version that produced it.
        cached_blob = getattr(self, "_cached_blob", None)
        if cached_blob is not None:
            workspace_name = cached_blob["workspace_name"]
            resolved_id = cached_blob.get("workspace_id")
            state_data = cached_blob["data"]
        else:
            ctx = getattr(self, "_validation_ctx", None)
            if ctx is not None:
                resolved_id = ctx["workspace_id"]
                workspace_name = ctx["workspace_name"]
                pre_sv_id: Optional[str] = ctx.get("state_version_id")
            else:
                resolved_id, workspace_name = resolve_workspace(self.client, workspace_id_opt, organization, workspace)
                pre_sv_id = None
            raw_state = _download_statefile(self.client, resolved_id)
            # Strip Terraform-flagged sensitive attributes BEFORE the blob is
            # ever handed to the cache plugin: persisted cache files must not
            # contain values Terraform marked sensitive.
            state_data = _sanitize_state_for_cache(raw_state)
            self._fetched_blob = {
                "schema": "tfc_inv_cache_v1",
                "source": "statefile",
                "workspace_name": workspace_name,
                "workspace_id": resolved_id,
                "state_version_id": pre_sv_id,
                "data": state_data,
            }
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
                sensitive_paths: List[Any] = instance.get("sensitive_attributes") or []
                attributes = _sanitize_sensitive_attributes(attributes, sensitive_paths)
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
                        "workspace_id": resolved_id,
                    }
                )

        return records
