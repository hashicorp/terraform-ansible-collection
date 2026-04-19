# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Shared helpers used by inventory source backends.

Pure computation helpers (hostname resolution, filtering) and lightweight API
wrappers (workspace resolution, output fetching) are kept here so every
source backend can import from a single location without circular dependencies.
"""

from typing import Any, Dict, List, Optional, Tuple

from ansible.errors import AnsibleError, AnsibleParserError

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output import get_workspace_outputs
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace, get_workspace_by_id


# ---------------------------------------------------------------------------
# Hostname resolution helpers
# ---------------------------------------------------------------------------


def _resolve_single_preference(
    output_name: str,
    host_vars: Dict[str, Any],
    preference: str,
    index: Optional[int] = None,
) -> Optional[str]:
    """Return the resolved value for one hostname preference token.

    Handles the special token ``output_name``, field look-ups in *host_vars*,
    and falls back to treating *preference* as a literal string.
    Returns ``None`` when the resolved string would be blank.
    """
    if preference == "output_name":
        return output_name if index is None else f"{output_name}_{index}"
    if preference in host_vars:
        value = host_vars[preference]
        if value is not None and str(value).strip():
            return str(value)
        return None
    return preference if preference.strip() else None


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

    Raises ``AnsibleError`` when a dict preference entry is missing ``name``.
    """
    fallback = (
        f"{workspace_name}_{output_name}"
        if index is None
        else f"{workspace_name}_{output_name}_{index}"
    )

    if not hostnames:
        return fallback

    for preference in hostnames:
        hostname: Optional[str] = None

        if isinstance(preference, dict):
            if "name" not in preference:
                raise AnsibleError("A 'name' key must be defined in a hostnames dictionary.")
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
    return all(host_vars.get(k) == v for k, v in filter_dict.items())


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

    Raises ``AnsibleParserError`` when the workspace cannot be found or the
    inputs are insufficient to identify one.
    """
    if workspace_id:
        ws_data = get_workspace_by_id(client, workspace_id)
        if not ws_data:
            raise AnsibleParserError(f"Workspace with ID '{workspace_id}' was not found.")
        ws_name = (
            ws_data.get("name")
            or ws_data.get("attributes", {}).get("name")
            or workspace_id
        )
        return workspace_id, str(ws_name)

    if not organization or not workspace:
        raise AnsibleParserError(
            "Either 'workspace_id' or both 'organization' and 'workspace' must be provided."
        )

    ws_data = get_workspace(client, organization, workspace)
    if not ws_data:
        raise AnsibleParserError(
            f"Workspace '{workspace}' was not found in organization '{organization}'."
        )
    resolved_id = ws_data.get("id") or ws_data.get("data", {}).get("id")
    if not resolved_id:
        raise AnsibleParserError(
            f"Could not determine ID for workspace '{workspace}' in organization '{organization}'."
        )
    return str(resolved_id), workspace


def fetch_outputs(client: TerraformClient, workspace_id: str) -> List[Dict[str, Any]]:
    """Fetch current state version outputs for *workspace_id* via the API.

    Raises ``AnsibleParserError`` on API and validation errors.
    """
    try:
        return get_workspace_outputs(client, workspace_id, display_sensitive=False)
    except ValueError as exc:
        raise AnsibleParserError(str(exc)) from exc
    except TerraformError as exc:
        raise AnsibleParserError(f"Failed to fetch workspace outputs: {exc}") from exc
