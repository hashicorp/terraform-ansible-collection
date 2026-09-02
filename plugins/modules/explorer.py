#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: explorer
short_description: Manage Terraform Cloud/Enterprise Explorer saved views.
version_added: "2.2.0"
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Creates, updates, or deletes an Explorer saved view in an organization.
  - Identify a saved view by C(view_id), or by the combination of C(organization)
    and C(name).
  - C(present) creates the view if absent, or updates it when configuration drifts.
  - C(absent) deletes the view if present.
  - C(organization) is always required because Explorer operations are
    organization-scoped.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - The name of the organization that owns the saved view.
      - Required for all operations.
    type: str
    required: true
  view_id:
    description:
      - The unique identifier of the saved view (e.g. C(sq-...)).
      - When provided, the view is looked up by ID.
      - When not provided, C(name) is used for lookup.
      - When provided together with C(name), C(view_id) identifies the resource
        and C(name) represents the desired (possibly new) display name.
    type: str
  name:
    description:
      - Human-readable display name of the saved view.
      - Required when creating a new view or when identifying a view by name.
    type: str
  query_type:
    description:
      - The Explorer view type this saved query targets.
      - Required when creating a new saved view.
    type: str
    choices:
      - workspaces
      - tf_versions
      - providers
      - modules
  query:
    description:
      - The query definition embedded in the saved view.
      - Required when creating a new saved view.
      - Contains C(query_type) and optionally C(filter), C(fields), and C(sort).
    type: dict
    suboptions:
      query_type:
        description:
          - The Explorer view type for this query.
        type: str
        required: true
        choices:
          - workspaces
          - tf_versions
          - providers
          - modules
      filter:
        description:
          - List of filter rows. Each must contain C(field), C(operator),
            and C(value) (a list of strings).
        type: list
        elements: dict
      fields:
        description:
          - List of column names (snake_case) to include in result rows.
        type: list
        elements: str
      sort:
        description:
          - List of sort fields. Prefix with C(-) for descending order.
        type: list
        elements: str
  state:
    description:
      - C(present) creates or updates; C(absent) deletes.
    type: str
    choices:
      - present
      - absent
    default: present
"""

EXAMPLES = r"""
- name: Create a workspaces saved view
  hashicorp.terraform.explorer:
    organization: "my-org"
    name: "prod-workspaces"
    query_type: workspaces
    query:
      query_type: workspaces
      filter:
        - field: workspace_name
          operator: contains
          value:
            - prod
    state: present
  register: view

- name: Idempotent re-run (no change expected)
  hashicorp.terraform.explorer:
    organization: "my-org"
    name: "prod-workspaces"
    query_type: workspaces
    query:
      query_type: workspaces
      filter:
        - field: workspace_name
          operator: contains
          value:
            - prod
    state: present

- name: Rename a saved view by ID
  hashicorp.terraform.explorer:
    organization: "my-org"
    view_id: "sq-abc123"
    name: "prod-workspaces-renamed"
    query:
      query_type: workspaces
    state: present

- name: Delete a saved view by name
  hashicorp.terraform.explorer:
    organization: "my-org"
    name: "prod-workspaces"
    state: absent

- name: Delete a saved view by ID
  hashicorp.terraform.explorer:
    organization: "my-org"
    view_id: "sq-abc123"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The unique identifier of the saved view.
  returned: when state is present and not check mode
  type: str
  sample: "sq-abc123"
name:
  description: The display name of the saved view.
  returned: when state is present
  type: str
  sample: "prod-workspaces"
query_type:
  description: The Explorer view type targeted by the saved view.
  returned: when state is present and not check mode
  type: str
  sample: "workspaces"
query:
  description: The embedded query definition.
  returned: when state is present and not check mode
  type: dict
created_at:
  description: ISO 8601 timestamp when the saved view was created.
  returned: when state is present and not check mode
  type: str
  sample: "2024-10-11T16:18:51.442Z"
msg:
  description: Informational message for delete, no-op, and check mode outcomes.
  returned: when relevant
  type: str
  sample: "Explorer saved view sq-abc123 has been deleted successfully"
warnings:
  description: List of non-fatal warning messages from the module.
  returned: always
  type: list
  elements: str
  sample: []
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.explorer import (
    create_saved_view,
    delete_saved_view,
    get_saved_view,
    get_saved_view_by_name,
    update_saved_view,
)


def _fetch_saved_view(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target saved view by view_id or by (organization, name)."""
    organization = params["organization"]
    view_id = params.get("view_id")
    if view_id:
        return get_saved_view(adapter, organization, view_id)
    name = params.get("name")
    if name:
        return get_saved_view_by_name(adapter, organization, name)
    return None


def _desired_payload(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build the create/update payload from user-supplied (non-None) params."""
    data: Dict[str, Any] = {}
    if params.get("name") is not None:
        data["name"] = params["name"]
    if params.get("query_type") is not None:
        data["query_type"] = params["query_type"]
    if params.get("query") is not None:
        data["query"] = deepcopy(params["query"])
    return data


def _normalise_list(val: Optional[List[str]]) -> List[str]:
    """Return a sorted list for stable comparison; treat None as empty."""
    return sorted(val) if val else []


def _normalise_filters(filters: Optional[List[Dict[str, Any]]]) -> List[tuple]:
    """Return a sorted sequence of (field, operator, values) tuples.

    Row order is insignificant; value order within a row is preserved.
    """
    if not filters:
        return []
    return sorted((f.get("field", ""), f.get("operator", ""), tuple(f.get("value") or [])) for f in filters)


def _has_drift(params: Dict[str, Any], current: Dict[str, Any]) -> bool:
    """Return True if any user-specified field differs from the current saved view.

    Only fields explicitly supplied by the user (non-None) are compared.
    """
    if params.get("name") is not None and params["name"] != current.get("name"):
        return True
    if params.get("query_type") is not None and params["query_type"] != current.get("query_type"):
        return True
    if params.get("query") is not None:
        desired_q = params["query"]
        current_q = current.get("query") or {}

        # Server responses may use either "query_type" or "type"; accept both on the current side.
        desired_inner_type = desired_q.get("query_type")
        current_inner_type = current_q.get("query_type") or current_q.get("type")
        if desired_inner_type is not None and desired_inner_type != current_inner_type:
            return True

        if desired_q.get("filter") is not None:
            if _normalise_filters(desired_q["filter"]) != _normalise_filters(current_q.get("filter")):
                return True

        if desired_q.get("fields") is not None:
            # fields has no ordering guarantee on reads; compare sorted.
            if _normalise_list(desired_q["fields"]) != _normalise_list(current_q.get("fields")):
                return True

        if desired_q.get("sort") is not None:
            desired_sort = desired_q["sort"] or []
            current_sort = current_q.get("sort") or []
            if desired_sort != current_sort:
                return True

    return False


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update a saved Explorer view to match the desired state."""
    current = _fetch_saved_view(adapter, params)
    name = params.get("name")

    if current is None:
        if not name:
            raise ValueError("'name' is required when creating a new Explorer saved view.")
        if not params.get("query_type"):
            raise ValueError("'query_type' is required when creating a new Explorer saved view.")
        if not params.get("query"):
            raise ValueError("'query' is required when creating a new Explorer saved view.")
        if check_mode:
            return {
                "changed": True,
                "msg": f"Explorer saved view {name!r} would be created. Skipped creation due to check mode.",
                "name": name,
            }
        created = create_saved_view(adapter, params["organization"], _desired_payload(params))
        return {"changed": True, **created}

    if _has_drift(params, current):
        if check_mode:
            return {
                "changed": True,
                "msg": f"Explorer saved view {current.get('id')} would be updated. Skipped update due to check mode.",
                "name": name or current.get("name"),
            }
        updated = update_saved_view(adapter, params["organization"], current["id"], _desired_payload(params))
        return {"changed": True, **updated}

    return {"changed": False, **current}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the saved view if present; no-op otherwise."""
    current = _fetch_saved_view(adapter, params)
    if current is None:
        return {"changed": False, "msg": "Explorer saved view is already absent."}

    view_id = current["id"]
    if check_mode:
        return {
            "changed": True,
            "msg": f"Explorer saved view {view_id} would be deleted. Skipped deletion due to check mode.",
        }

    delete_saved_view(adapter, params["organization"], view_id)
    return {"changed": True, "msg": f"Explorer saved view {view_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "organization": {"type": "str", "required": True},
            "view_id": {"type": "str"},
            "name": {"type": "str"},
            "query_type": {
                "type": "str",
                "choices": ["workspaces", "tf_versions", "providers", "modules"],
            },
            "query": {"type": "dict"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_one_of=[("view_id", "name")],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    action_result: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            match params["state"]:
                case "present":
                    action_result = state_present(adapter, params, params["check_mode"])
                case "absent":
                    action_result = state_absent(adapter, params, params["check_mode"])

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
