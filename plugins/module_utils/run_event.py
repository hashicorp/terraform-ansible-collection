# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Helpers for run event timelines."""

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response


def list_run_events(adapter: TerraformClient, run_id: str) -> List[Dict[str, Any]]:
    """List run events for the given run. Empty list on not-found."""
    try:
        return [format_response(e) for e in adapter.client.run_events.list(run_id)]
    except NotFound:
        return []


def filter_events(
    events: List[Dict[str, Any]],
    action: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Apply optional filters over an event list.

    ``since``/``until`` compare lexicographically on the ISO-8601 ``created_at``
    field — sufficient for the UTC timestamps TFE returns.
    """
    result = events
    if action:
        result = [e for e in result if e.get("action") == action]
    if since:
        result = [e for e in result if (e.get("created_at") or "") >= since]
    if until:
        result = [e for e in result if (e.get("created_at") or "") <= until]
    return result
