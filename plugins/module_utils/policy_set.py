# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Policy set adapter for pytfe SDK integration.

Wraps ``client.policy_sets`` (``/api/v2/organizations/{org}/policy-sets``,
``/api/v2/policy-sets/{id}``). Unlike most resources in this collection, the
5 relationship types (policies, workspaces, workspace_exclusions, projects,
project_exclusions) are **not** settable via a plain PATCH on an existing
policy set - only ``policies``/``workspaces``/``workspace_exclusions``/
``projects`` can be seeded at create time, and every relationship (including
those four, post-creation) requires dedicated add/remove endpoints. The
module layer (``plugins/modules/policy_set.py``) is responsible for diffing
desired relationship ID lists against current state and calling the add/remove
helpers below for the deltas - this adapter only wraps the raw SDK calls.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pytfe.errors import NotFound
    from pytfe.models import (
        PolicySetAddPoliciesOptions,
        PolicySetAddProjectExclusionsOptions,
        PolicySetAddProjectsOptions,
        PolicySetAddWorkspaceExclusionsOptions,
        PolicySetAddWorkspacesOptions,
        PolicySetCreateOptions,
        PolicySetRemovePoliciesOptions,
        PolicySetRemoveProjectExclusionsOptions,
        PolicySetRemoveProjectsOptions,
        PolicySetRemoveWorkspaceExclusionsOptions,
        PolicySetRemoveWorkspacesOptions,
        PolicySetUpdateOptions,
    )
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    PolicySetAddPoliciesOptions = None  # type: ignore[assignment]
    PolicySetAddProjectExclusionsOptions = None  # type: ignore[assignment]
    PolicySetAddProjectsOptions = None  # type: ignore[assignment]
    PolicySetAddWorkspaceExclusionsOptions = None  # type: ignore[assignment]
    PolicySetAddWorkspacesOptions = None  # type: ignore[assignment]
    PolicySetCreateOptions = None  # type: ignore[assignment]
    PolicySetRemovePoliciesOptions = None  # type: ignore[assignment]
    PolicySetRemoveProjectExclusionsOptions = None  # type: ignore[assignment]
    PolicySetRemoveProjectsOptions = None  # type: ignore[assignment]
    PolicySetRemoveWorkspaceExclusionsOptions = None  # type: ignore[assignment]
    PolicySetRemoveWorkspacesOptions = None  # type: ignore[assignment]
    PolicySetUpdateOptions = None  # type: ignore[assignment]


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call

# Relationship kind -> (add options class, remove options class, options field name).
_RELATIONSHIP_SPECS = {
    "policies": (PolicySetAddPoliciesOptions, PolicySetRemovePoliciesOptions, "policies"),
    "workspaces": (PolicySetAddWorkspacesOptions, PolicySetRemoveWorkspacesOptions, "workspaces"),
    "workspace_exclusions": (PolicySetAddWorkspaceExclusionsOptions, PolicySetRemoveWorkspaceExclusionsOptions, "workspace_exclusions"),
    "projects": (PolicySetAddProjectsOptions, PolicySetRemoveProjectsOptions, "projects"),
    "project_exclusions": (PolicySetAddProjectExclusionsOptions, PolicySetRemoveProjectExclusionsOptions, "project_exclusions"),
}
_RELATIONSHIP_METHOD_NAMES = {
    "policies": ("add_policies", "remove_policies"),
    "workspaces": ("add_workspaces", "remove_workspaces"),
    "workspace_exclusions": ("add_workspace_exclusions", "remove_workspace_exclusions"),
    "projects": ("add_projects", "remove_projects"),
    "project_exclusions": ("add_project_exclusions", "remove_project_exclusions"),
}


def list_policy_sets(adapter: TerraformClient, organization: str) -> List[Dict[str, Any]]:
    """List policy sets in an organization."""
    try:
        return [format_response(ps) for ps in adapter.client.policy_sets.list(organization)]
    except NotFound:
        return []


def get_policy_set(adapter: TerraformClient, policy_set_id: str) -> Optional[Dict[str, Any]]:
    """Read a single policy set by its ID. Returns None if not found."""
    try:
        return format_response(adapter.client.policy_sets.read(policy_set_id))
    except NotFound:
        return None


def get_policy_set_by_name(adapter: TerraformClient, organization: str, name: str) -> Optional[Dict[str, Any]]:
    """Locate a policy set by name within an organization."""
    for policy_set in list_policy_sets(adapter, organization):
        if policy_set.get("name") == name:
            return policy_set
    return None


def create_policy_set(adapter: TerraformClient, organization: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a policy set with attributes only."""
    options = PolicySetCreateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.policy_sets.create,
        organization,
        options,
        error_context=f"Failed to create policy set {data.get('name')!r} in organization {organization}",
    )
    return format_response(response)


def update_policy_set(adapter: TerraformClient, policy_set_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a policy set's attributes (not relationships) by its ID."""
    options = PolicySetUpdateOptions.model_validate(data)
    response = safe_api_call(
        adapter.client.policy_sets.update,
        policy_set_id,
        options,
        error_context=f"Failed to update policy set {policy_set_id}",
    )
    return format_response(response)


def delete_policy_set(adapter: TerraformClient, policy_set_id: str) -> None:
    """Delete a policy set by its ID."""
    safe_api_call(
        adapter.client.policy_sets.delete,
        policy_set_id,
        error_context=f"Failed to delete policy set {policy_set_id}",
    )


def sync_relationship(adapter: TerraformClient, policy_set_id: str, relationship: str, add_ids: List[str], remove_ids: List[str]) -> None:
    """Add and/or remove members of one relationship type on a policy set.

    ``relationship`` must be one of the keys in ``_RELATIONSHIP_SPECS``
    ("policies", "workspaces", "workspace_exclusions", "projects",
    "project_exclusions").
    """
    add_cls, remove_cls, field = _RELATIONSHIP_SPECS[relationship]
    add_method_name, remove_method_name = _RELATIONSHIP_METHOD_NAMES[relationship]

    if add_ids:
        options = add_cls.model_validate({field: [{"id": item_id} for item_id in add_ids]})
        safe_api_call(
            getattr(adapter.client.policy_sets, add_method_name),
            policy_set_id,
            options,
            error_context=f"Failed to add {relationship} to policy set {policy_set_id}",
        )
    if remove_ids:
        options = remove_cls.model_validate({field: [{"id": item_id} for item_id in remove_ids]})
        safe_api_call(
            getattr(adapter.client.policy_sets, remove_method_name),
            policy_set_id,
            options,
            error_context=f"Failed to remove {relationship} from policy set {policy_set_id}",
        )
