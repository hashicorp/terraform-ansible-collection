# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Policy evaluation adapter for pytfe SDK integration."""

from __future__ import annotations

from typing import Any, Dict, List

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response


def list_policy_evaluations(adapter: TerraformClient, task_stage_id: str) -> List[Dict[str, Any]]:
    """List policy evaluations for a task stage."""
    try:
        return [format_response(pe) for pe in adapter.client.policy_evaluations.list(task_stage_id)]
    except NotFound:
        return []
