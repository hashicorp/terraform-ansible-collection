# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response


def get_stack_deployment_group(adapter: TerraformClient, stack_deployment_group_id: str) -> Optional[Dict[str, Any]]:
    """Read a single deployment group by its ID. Returns None if not found."""
    try:
        group = adapter.client.stack_deployment_groups.read(stack_deployment_group_id)
        return format_response(group)
    except NotFound:
        return None


def get_stack_deployment_group_by_name(
    adapter: TerraformClient,
    stack_configuration_id: str,
    name: str,
) -> Optional[Dict[str, Any]]:
    """Read a deployment group by name within a stack configuration. Returns None if not found."""
    try:
        group = adapter.client.stack_deployment_groups.read_by_name(stack_configuration_id, name)
        return format_response(group)
    except NotFound:
        return None
