# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Shared helpers used by inventory source backends.

Pure computation helpers (hostname resolution, filtering) and lightweight API
wrappers (workspace resolution, output fetching) are kept here so every
source backend can import from a single location without circular dependencies.
"""

from typing import Any, Dict, List, Optional, Tuple

try:
    from pytfe.models.workspace import WorkspaceListOptions
except ImportError:

    class WorkspaceListOptions:  # type: ignore[no-redef]
        def __init__(self, **kwargs: Any) -> None:
            self._kwargs = kwargs


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output import get_workspace_outputs
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace, get_workspace_by_id

# workspace_filters YAML key → WorkspaceListOptions field. Keep in sync with
# DOCUMENTATION in plugins/inventory/tfc_inv.py.
_WORKSPACE_FILTER_MAP: Dict[str, str] = {
    "name_search": "search",
    "tags": "tags",
    "exclude_tags": "exclude_tags",
    "wildcard_name": "wildcard_name",
    "current_run_status": "current_run_status",
    "sort": "sort",
    "page_size": "page_size",
}

# ---------------------------------------------------------------------------
# Hostname resolution helpers
# ---------------------------------------------------------------------------


_MISSING = object()


def _lookup_path(host_vars: Dict[str, Any], path: str) -> Any:
    """Walk a dotted ``path`` through nested dicts, returning ``_MISSING`` on miss.

    A literal-key sentinel (``_MISSING``) is used so callers can distinguish
    "key absent" from "key present with value ``None``".
    """
    cur: Any = host_vars
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


def _resolve_single_preference(
    output_name: str,
    host_vars: Dict[str, Any],
    preference: str,
    index: Optional[int] = None,
) -> Optional[str]:
    """Return the resolved value for one hostname preference token.

    Handles the special token ``output_name`` and dotted-path look-ups in
    *host_vars* (e.g. ``tags.role`` walks ``host_vars["tags"]["role"]`` for
    nested user data). When the preference doesn't resolve, returns ``None``
    so the caller can try the next preference or fall back to the
    ``<workspace_name>_<output_name>[_<index>]`` default — there is *no*
    literal-string fallback (which silently collapsed multi-host inventories
    to a single literal-named host when users misspelled a field).
    """
    if preference == "output_name":
        return output_name if index is None else f"{output_name}_{index}"
    value = _lookup_path(host_vars, preference)
    if value is _MISSING:
        return None
    if value is None or not str(value).strip():
        return None
    return str(value)


def get_preferred_hostname(
    output_name: str,
    workspace_name: str,
    host_vars: Dict[str, Any],
    hostnames: Optional[List[Any]] = None,
    index: Optional[int] = None,
) -> Optional[str]:
    """Resolve the inventory hostname for one host record.

    Walks *hostnames* in order of preference and returns the first non-blank
    result, falling back to ``<workspace_name>_<output_name>[_<index>]``.

    Raises ``TerraformError`` when a dict preference entry is missing ``name``.
    """
    fallback = f"{workspace_name}_{output_name}" if index is None else f"{workspace_name}_{output_name}_{index}"

    if not hostnames:
        return fallback

    for preference in hostnames:
        hostname: Optional[str] = None

        if isinstance(preference, dict):
            if "name" not in preference:
                raise TerraformError("A 'name' key must be defined in a hostnames dictionary.")
            hostname = _resolve_single_preference(output_name, host_vars, preference["name"], index)
            if hostname and "prefix" in preference:
                prefix = _resolve_single_preference(output_name, host_vars, preference["prefix"], index)
                if prefix:
                    sep = preference.get("separator", "_")
                    hostname = f"{prefix}{sep}{hostname}"
        else:
            hostname = _resolve_single_preference(output_name, host_vars, str(preference), index)

        if hostname:
            return hostname

    return fallback


# ---------------------------------------------------------------------------
# Host filtering helpers
# ---------------------------------------------------------------------------


def _filter_dict_matches(host_vars: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
    for key, expected in filter_dict.items():
        actual = _lookup_path(host_vars, key)
        if actual is _MISSING or actual != expected:
            return False
    return True


def passes_filters(
    host_vars: Dict[str, Any],
    include_filters: Optional[List[Dict]],
    exclude_filters: Optional[List[Dict]],
) -> bool:
    """Return True when the host should appear in the inventory.

    Exclusion is checked first; a non-empty *include_filters* acts as an
    allow-list requiring at least one dict to match.
    """
    if exclude_filters:
        if any(_filter_dict_matches(host_vars, f) for f in exclude_filters):
            return False
    if include_filters:
        return any(_filter_dict_matches(host_vars, f) for f in include_filters)
    return True


# ---------------------------------------------------------------------------
# API helpers shared across source backends
# ---------------------------------------------------------------------------


def resolve_workspace(
    client: TerraformClient,
    workspace_id: Optional[str],
    organization: Optional[str],
    workspace: Optional[str],
) -> Tuple[str, str]:
    """Return ``(resolved_workspace_id, workspace_name)``.

    Raises ``TerraformError`` when the workspace cannot be found or the
    inputs are insufficient to identify one.
    """
    if workspace_id:
        ws_data = get_workspace_by_id(client, workspace_id)
        if not ws_data:
            raise TerraformError(f"Workspace with ID '{workspace_id}' was not found.")
        ws_name = ws_data.get("name") or ws_data.get("attributes", {}).get("name") or workspace_id
        return workspace_id, str(ws_name)

    if not organization or not workspace:
        raise TerraformError("Either 'workspace_id' or both 'organization' and 'workspace' must be provided.")

    ws_data = get_workspace(client, organization, workspace)
    if not ws_data:
        raise TerraformError(f"Workspace '{workspace}' was not found in organization '{organization}'.")
    resolved_id = ws_data.get("id") or ws_data.get("data", {}).get("id")
    if not resolved_id:
        raise TerraformError(f"Could not determine ID for workspace '{workspace}' in organization '{organization}'.")
    return str(resolved_id), workspace


def fetch_outputs(client: TerraformClient, workspace_id: str) -> List[Dict[str, Any]]:
    """Fetch current state version outputs for *workspace_id* via the API.

    Raises ``TerraformError`` on API and validation errors.
    """
    try:
        return get_workspace_outputs(client, workspace_id, display_sensitive=False)
    except ValueError as exc:
        raise TerraformError(str(exc)) from exc
    except TerraformError as exc:
        raise TerraformError(f"Failed to fetch workspace outputs: {exc}") from exc


def list_workspaces(
    client: TerraformClient,
    organization: str,
    filters: Dict[str, Any],
) -> List[Tuple[str, str]]:
    """Return ``[(workspace_id, workspace_name), ...]`` for *filters* via pytfe.

    *filters* is the user's ``workspace_filters`` mapping. Maps each key onto
    a ``WorkspaceListOptions`` kwarg via :data:`_WORKSPACE_FILTER_MAP`, plus the
    special-cased ``project_id`` (which is validated to start with ``prj-`` —
    project-name resolution is intentionally not supported in this version).

    Empty-string filter values are dropped (treated as unset) so an absent
    YAML entry and ``key: ""`` behave identically.

    Empty result is a valid return; callers decide whether to warn.
    """
    if not organization:
        raise TerraformError("workspace_filters requires 'organization' to be set.")

    api_kwargs: Dict[str, Any] = {}

    project_id = filters.get("project_id")
    if project_id not in (None, ""):
        if not isinstance(project_id, str) or not project_id.startswith("prj-"):
            raise TerraformError(
                "workspace_filters.project_id must be a project ID starting "
                f"with 'prj-'; got {project_id!r}. Project name resolution is "
                "not supported; use the project ID."
            )
        api_kwargs["project_id"] = project_id

    for yaml_key, pytfe_field in _WORKSPACE_FILTER_MAP.items():
        value = filters.get(yaml_key)
        if value in (None, ""):
            continue
        api_kwargs[pytfe_field] = value

    unknown = set(filters) - {"project_id"} - set(_WORKSPACE_FILTER_MAP)
    if unknown:
        raise TerraformError(
            "workspace_filters has unsupported keys: " f"{sorted(unknown)}. Supported keys: project_id, " f"{', '.join(sorted(_WORKSPACE_FILTER_MAP))}."
        )

    opts = WorkspaceListOptions(**api_kwargs)

    targets: List[Tuple[str, str]] = []
    for ws in client.client.workspaces.list(organization, opts):
        # pytfe's Workspace model exposes id / name at the top level; fall
        # back to JSON:API dict shapes for robustness against future changes.
        ws_id = getattr(ws, "id", None)
        name = getattr(ws, "name", None)
        if isinstance(ws, dict):
            ws_id = ws_id or ws.get("id")
            name = name or ws.get("name") or (ws.get("attributes") or {}).get("name")

        if ws_id and name:
            targets.append((str(ws_id), str(name)))
    return targets


def resolve_current_state_version_id(client: TerraformClient, workspace_id: str) -> Optional[str]:
    """Return the current state version ID for *workspace_id* or ``None`` on failure.

    Used by the optional cache validation mode (``cache_validate_current_state_version``)
    to confirm a cached blob still reflects the workspace's latest applied state.
    Returns ``None`` instead of raising so the caller can decide whether to
    raise (validation mode) or fall back to a non-validated cache hit.
    """
    try:
        sv = client.client.state_versions.read_current(workspace_id)
        return getattr(sv, "id", None)
    except Exception:
        return None
