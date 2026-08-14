# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, List, Optional

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


def get_stack_deployment_step(
    adapter: TerraformClient,
    stack_deployment_step_id: str,
) -> Optional[Dict[str, Any]]:
    """Read a single deployment step by its ID. Returns None if not found."""
    try:
        step = adapter.client.stack_deployment_steps.read(stack_deployment_step_id)
        return format_response(step)
    except NotFound:
        return None


def list_stack_deployment_steps(
    adapter: TerraformClient,
    stack_deployment_run_id: str,
) -> List[Dict[str, Any]]:
    """List all deployment steps for a deployment run. Returns an empty list if none exist."""
    try:
        steps = adapter.client.stack_deployment_steps.list(stack_deployment_run_id)
        return [format_response(s) for s in steps]
    except NotFound:
        return []


def list_stack_diagnostics(
    adapter: TerraformClient,
    stack_deployment_step_id: str,
) -> List[Dict[str, Any]]:
    """List all diagnostics for a deployment step.

    The list_diagnostics method lives on the stack_deployment_steps pytfe resource
    (not stack_diagnostics, which only exposes read). Returns an empty list if
    the step produced no diagnostics.
    """
    try:
        diags = adapter.client.stack_deployment_steps.list_diagnostics(stack_deployment_step_id)
        return [format_response(d) for d in diags]
    except NotFound:
        return []
