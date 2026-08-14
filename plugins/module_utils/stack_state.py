# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound, TFEError
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class TFEError(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import (
    format_response,
)


def get_stack_state(adapter: TerraformClient, stack_state_id: str) -> Optional[Dict[str, Any]]:
    """Read a single stack state by its ID. Returns None if not found."""
    try:
        state = adapter.client.stack_states.read(stack_state_id)
        return format_response(state)
    except NotFound:
        return None


def list_stack_states(
    adapter: TerraformClient,
    stack_id: str,
) -> List[Dict[str, Any]]:
    """List all stack states for a stack. Returns an empty list if none exist or the API errors."""
    try:
        states = adapter.client.stack_states.list(stack_id)
        return [format_response(s) for s in states]
    except (NotFound, TFEError):
        return []
