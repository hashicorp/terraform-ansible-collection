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


def get_stack_deployment_run(
    adapter: TerraformClient,
    stack_deployment_run_id: str,
) -> Optional[Dict[str, Any]]:
    """Read a single deployment run by its ID. Returns None if not found."""
    try:
        run = adapter.client.stack_deployment_runs.read(stack_deployment_run_id)
        return format_response(run)
    except NotFound:
        return None
