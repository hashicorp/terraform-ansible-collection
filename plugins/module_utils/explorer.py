# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        ExplorerQueryOptions,
        ExplorerSavedViewCreateOptions,
        ExplorerSavedViewUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class ExplorerQueryOptions:  # type: ignore[no-redef]
        pass

    class ExplorerSavedViewCreateOptions:  # type: ignore[no-redef]
        pass

    class ExplorerSavedViewUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def query_explorer(adapter: TerraformClient, organization: str, options: ExplorerQueryOptions) -> List[Dict[str, Any]]:
    """Execute an ad-hoc Explorer query. Returns an empty list when the organization is not found."""
    try:
        return [format_response(row) for row in adapter.client.explorer.query(organization, options)]
    except NotFound:
        return []


def list_saved_views(adapter: TerraformClient, organization: str) -> List[Dict[str, Any]]:
    """List all saved Explorer views in an organization. Returns an empty list when the organization is not found."""
    try:
        return [format_response(view) for view in adapter.client.explorer.list_saved_views(organization)]
    except NotFound:
        return []


def get_saved_view(adapter: TerraformClient, organization: str, view_id: str) -> Optional[Dict[str, Any]]:
    """Read a single saved view by ID. Returns None if not found."""
    try:
        return format_response(adapter.client.explorer.read_saved_view(organization, view_id))
    except NotFound:
        return None


def get_saved_view_by_name(adapter: TerraformClient, organization: str, name: str) -> Optional[Dict[str, Any]]:
    """Locate a saved view by name within an organization. Returns None if no match is found."""
    for view in list_saved_views(adapter, organization):
        if view.get("name") == name:
            return view
    return None


def get_saved_view_results(adapter: TerraformClient, organization: str, view_id: str) -> List[Dict[str, Any]]:
    """Execute a saved view and return the result rows.

    NotFound is intentionally not caught: this is only called after the view is
    confirmed to exist, so an error here indicates a real API failure, not absence.
    """
    return [format_response(row) for row in adapter.client.explorer.saved_view_results(organization, view_id)]


def create_saved_view(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a saved Explorer view under the given organization."""
    options = ExplorerSavedViewCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.explorer.create_saved_view,
        organization,
        options,
        error_context=f"Failed to create Explorer saved view {data.get('name')!r} in organization {organization}",
    )
    return format_response(response)


def update_saved_view(adapter: TerraformClient, organization: str, view_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing saved Explorer view."""
    options = ExplorerSavedViewUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.explorer.update_saved_view,
        organization,
        view_id,
        options,
        error_context=f"Failed to update Explorer saved view {view_id}",
    )
    return format_response(response)


def delete_saved_view(adapter: TerraformClient, organization: str, view_id: str) -> None:
    """Delete a saved Explorer view by ID."""
    safe_api_call(
        adapter.client.explorer.delete_saved_view,
        organization,
        view_id,
        error_context=f"Failed to delete Explorer saved view {view_id}",
    )
