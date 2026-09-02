#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: explorer_info
version_added: "2.2.0"
short_description: Query the Terraform Cloud/Enterprise Explorer API (read-only).
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Read-only module for the Explorer API.
  - Provide C(view_type) to execute an ad-hoc query; provide C(view_id) to read
    a saved view definition and its result rows.
  - This module never changes state.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - The name of the organization to query. Required for all operations.
    type: str
    required: true
  view_id:
    description:
      - The unique identifier of a saved Explorer view (e.g. C(sq-...)).
      - When provided, returns the saved view definition and its result rows.
      - Mutually exclusive with C(view_type).
    type: str
  view_type:
    description:
      - The Explorer view type for an ad-hoc query.
      - Mutually exclusive with C(view_id).
    type: str
    choices:
      - workspaces
      - tf_versions
      - providers
      - modules
  filters:
    description:
      - Filter rows for an ad-hoc query. Only valid with C(view_type).
      - Each filter must contain C(field), C(operator), and C(value).
    type: list
    elements: dict
  sort:
    description:
      - Sort field for an ad-hoc query. Prefix with C(-) for descending order.
        Only valid with C(view_type).
    type: str
  fields:
    description:
      - Comma-separated column names to include in ad-hoc query result rows.
        Only valid with C(view_type).
    type: str
  page_number:
    description:
      - Page number for ad-hoc query pagination (1-based). Only valid with C(view_type).
    type: int
  page_size:
    description:
      - Page size for ad-hoc query pagination (1-100). Only valid with C(view_type).
    type: int
"""

EXAMPLES = r"""
- name: Execute an ad-hoc workspaces query
  hashicorp.terraform.explorer_info:
    organization: "my-org"
    view_type: workspaces
    filters:
      - index: 0
        field: workspace_name
        operator: contains
        value: "prod"
  register: explorer_result

- name: Read a saved view definition and its rows
  hashicorp.terraform.explorer_info:
    organization: "my-org"
    view_id: "sq-abc123"
  register: saved_view_info
"""

RETURN = r"""
rows:
  description: Explorer result rows from an ad-hoc query or saved view execution.
  returned: always
  type: list
  elements: dict
  sample:
    - id: "ws-abc123"
      type: "visibility-workspace"
      attributes:
        workspace_name: "prod-infra"
saved_view:
  description: The saved view definition, returned when C(view_id) is provided.
  returned: when O(view_id) is provided
  type: dict
  contains:
    id:
      description: The unique identifier of the saved view.
      type: str
      returned: always
      sample: "sq-abc123"
    name:
      description: The display name of the saved view.
      type: str
      returned: always
      sample: "prod-workspaces"
    query_type:
      description: The Explorer view type targeted by the saved view.
      type: str
      returned: always
      sample: "workspaces"
    query:
      description: The embedded query definition.
      type: dict
      returned: always
warnings:
  description: List of non-fatal warning messages from the module.
  returned: always
  type: list
  elements: str
  sample: []
"""

from copy import deepcopy
from typing import Any, Dict, List

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.explorer import (
    get_saved_view,
    get_saved_view_results,
    query_explorer,
)

try:
    from pytfe.models import ExplorerQueryOptions, ExplorerUrlFilter, ExplorerViewType
except ImportError:

    class ExplorerQueryOptions:  # type: ignore[no-redef]
        pass

    class ExplorerUrlFilter:  # type: ignore[no-redef]
        pass

    class ExplorerViewType:  # type: ignore[no-redef]
        pass


def _build_query_options(params: Dict[str, Any]) -> ExplorerQueryOptions:
    """Construct ExplorerQueryOptions from module params."""
    filters: List[ExplorerUrlFilter] = []
    for i, raw in enumerate(params.get("filters") or []):
        filters.append(
            ExplorerUrlFilter(
                index=raw.get("index", i),
                field=raw["field"],
                operator=raw["operator"],
                value=raw["value"],
                value_index=raw.get("value_index", 0),
            )
        )

    return ExplorerQueryOptions(
        view_type=ExplorerViewType(params["view_type"]),
        sort=params.get("sort"),
        fields=params.get("fields"),
        page_number=params.get("page_number"),
        page_size=params.get("page_size"),
        filters=filters or None,
    )


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "organization": {"type": "str", "required": True},
            "view_id": {"type": "str"},
            "view_type": {
                "type": "str",
                "choices": ["workspaces", "tf_versions", "providers", "modules"],
            },
            "filters": {"type": "list", "elements": "dict"},
            "sort": {"type": "str"},
            "fields": {"type": "str"},
            "page_number": {"type": "int"},
            "page_size": {"type": "int"},
        },
        required_one_of=[("view_id", "view_type")],
        mutually_exclusive=[("view_id", "view_type")],
        supports_check_mode=True,
    )

    warnings: List[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            organization = params["organization"]
            if params.get("view_id"):
                view = get_saved_view(adapter, organization, params["view_id"])
                if not view:
                    raise ValueError(f"Explorer saved view with ID {params['view_id']!r} not found " f"in organization {organization!r}")
                result["saved_view"] = view
                result["rows"] = get_saved_view_results(adapter, organization, params["view_id"])
            else:
                opts = _build_query_options(params)
                result["rows"] = query_explorer(adapter, organization, opts)

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
