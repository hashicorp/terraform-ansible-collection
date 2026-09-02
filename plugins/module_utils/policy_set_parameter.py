# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Policy set parameter adapter for pytfe SDK integration.

Wraps ``client.policy_set_parameters``, scoped under a ``policy_set_id``. Same
shape as workspace/variable-set variables: full CRUD, ``category`` is always
``policy-set`` (fixed server-side), and ``sensitive=true`` values are
write-only - the API never returns them, so drift on ``value`` alone can't be
detected once a parameter is sensitive (see ``variable.py``'s
``_strip_unverifiable_sensitive_value`` for the same handling at the module
layer).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import PolicySetParameterCreateOptions, PolicySetParameterUpdateOptions
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class PolicySetParameterCreateOptions:  # type: ignore[no-redef]
        pass

    class PolicySetParameterUpdateOptions:  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def list_policy_set_parameters(adapter: TerraformClient, policy_set_id: str) -> List[Dict[str, Any]]:
    """List parameters for a policy set."""
    try:
        return [format_response(p) for p in adapter.client.policy_set_parameters.list(policy_set_id)]
    except NotFound:
        return []


def get_policy_set_parameter(adapter: TerraformClient, policy_set_id: str, parameter_id: str) -> Optional[Dict[str, Any]]:
    """Read a single policy set parameter by its ID. Returns None if not found."""
    try:
        return format_response(adapter.client.policy_set_parameters.read(policy_set_id, parameter_id))
    except NotFound:
        return None


def get_policy_set_parameter_by_key(adapter: TerraformClient, policy_set_id: str, key: str) -> Optional[Dict[str, Any]]:
    """Locate a policy set parameter by key within a policy set."""
    for parameter in list_policy_set_parameters(adapter, policy_set_id):
        if parameter.get("key") == key:
            return parameter
    return None


def create_policy_set_parameter(adapter: TerraformClient, policy_set_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a parameter on a policy set."""
    options = PolicySetParameterCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.policy_set_parameters.create,
        policy_set_id,
        options,
        error_context=f"Failed to create parameter {data.get('key')!r} on policy set {policy_set_id}",
    )
    return format_response(response)


def update_policy_set_parameter(adapter: TerraformClient, policy_set_id: str, parameter_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a policy set parameter by its ID."""
    options = PolicySetParameterUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.policy_set_parameters.update,
        policy_set_id,
        parameter_id,
        options,
        error_context=f"Failed to update parameter {parameter_id} on policy set {policy_set_id}",
    )
    return format_response(response)


def delete_policy_set_parameter(adapter: TerraformClient, policy_set_id: str, parameter_id: str) -> None:
    """Delete a policy set parameter by its ID."""
    safe_api_call(
        adapter.client.policy_set_parameters.delete,
        policy_set_id,
        parameter_id,
        error_context=f"Failed to delete parameter {parameter_id} on policy set {policy_set_id}",
    )
