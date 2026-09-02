# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import (
    format_response,
)


def get_stack_diagnostic(adapter: TerraformClient, stack_diagnostic_id: str) -> Optional[Dict[str, Any]]:
    """Read a single stack diagnostic by its ID. Returns None if not found."""
    try:
        diagnostic = adapter.client.stack_diagnostics.read(stack_diagnostic_id)
        return format_response(diagnostic)
    except NotFound:
        return None
