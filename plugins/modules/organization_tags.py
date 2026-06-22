#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: organization_tags
version_added: "2.1.0"
short_description: Manage Terraform Cloud/Enterprise organization tags (associate workspaces, delete).
author: "Sivaselvan I (@isivaselvan)"
description:
  - Manages organization tags on Terraform Cloud and Terraform Enterprise.
  - Organization tags are workspace tags scoped to an organization.
  - The V(present) state associates one or more workspaces with an existing tag identified by O(tag_id).
  - The V(absent) state deletes one or more tags from the organization identified by O(tag_id) or a list of O(ids).
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - Organization that owns the tags.
    type: str
    required: true
  tag_id:
    description:
      - The unique identifier of the organization tag (e.g. C(tag-...)).
      - Required when V(state=present).
      - Mutually exclusive with O(ids).
    type: str
  ids:
    description:
      - List of tag identifiers to delete.
      - Only valid when V(state=absent).
      - Mutually exclusive with O(tag_id).
    type: list
    elements: str
  workspace_ids:
    description:
      - List of workspace IDs to associate with the tag.
      - Required when V(state=present).
    type: list
    elements: str
  state:
    description:
      - Desired state of the organization tag.
      - V(present) associates the listed workspaces with the tag.
      - V(absent) deletes the tag(s) from the organization.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Associate workspaces with a tag
  hashicorp.terraform.organization_tags:
    organization: "my-org"
    tag_id: "tag-7tRVyqGbvrF1RmWQ"
    workspace_ids:
      - "ws-abc123"
      - "ws-def456"
    state: present

- name: Delete a tag
  hashicorp.terraform.organization_tags:
    organization: "my-org"
    tag_id: "tag-7tRVyqGbvrF1RmWQ"
    state: absent

- name: Delete multiple tags
  hashicorp.terraform.organization_tags:
    organization: "my-org"
    ids:
      - "tag-7tRVyqGbvrF1RmWQ"
      - "tag-8uSWzrHcwsG2SnXR"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: Tag identifier that workspaces were associated with.
  returned: when state is present
  type: str
  sample: "tag-7tRVyqGbvrF1RmWQ"
workspace_ids:
  description: Workspace IDs that were actually associated with the tag (already-associated workspaces are excluded).
  returned: when state is present
  type: list
  elements: str
  sample: ["ws-abc123", "ws-def456"]
ids:
  description: Tag identifiers that were deleted.
  returned: when state is absent and changed
  type: list
  elements: str
  sample: ["tag-7tRVyqGbvrF1RmWQ"]
msg:
  description: Informational message for no-op and check mode operations.
  returned: when relevant
  type: str
  sample: "Tags ['tag-7tRVyqGbvrF1RmWQ'] have been deleted successfully"
"""

from typing import Any, Dict

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.organization_tags import (
    add_workspaces_to_tag,
    delete_organization_tags,
    get_workspace_tag_ids,
    list_organization_tag_ids,
)


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Associate workspaces with an existing tag (idempotent: skips already-associated workspaces)."""
    workspace_ids = params.get("workspace_ids")
    if not workspace_ids:
        raise ValueError("'workspace_ids' is required and must be non-empty when state is present.")

    tag_id = params["tag_id"]
    organization = params["organization"]

    # Idempotency: only associate workspaces that don't already have the tag.
    ws_to_add = [ws_id for ws_id in sorted(workspace_ids) if tag_id not in get_workspace_tag_ids(adapter, ws_id)]

    if not ws_to_add:
        return {
            "changed": False,
            "msg": f"All workspaces are already associated with tag {tag_id}.",
            "workspace_ids": [],
            "id": tag_id,
        }

    if check_mode:
        return {
            "changed": True,
            "msg": f"Workspaces {ws_to_add} would be associated with tag {tag_id}. Skipped due to check mode.",
            "workspace_ids": ws_to_add,
            "id": tag_id,
        }

    add_workspaces_to_tag(adapter, organization, tag_id, ws_to_add)
    return {"changed": True, "workspace_ids": ws_to_add, "id": tag_id}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the targeted tag(s); idempotent — no-op for tags already absent."""
    organization = params["organization"]
    tag_id = params.get("tag_id")
    explicit_ids = params.get("ids") or []

    requested = [tag_id] if tag_id else explicit_ids

    if not requested:
        raise ValueError("Either 'tag_id' or 'ids' is required when state is absent.")

    # Idempotency: only delete tags that actually exist in the organization.
    existing_ids = list_organization_tag_ids(adapter, organization)
    to_delete = [tid for tid in requested if tid in existing_ids]

    if not to_delete:
        return {"changed": False, "msg": "Tags are already absent."}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Tags {sorted(to_delete)} would be deleted. Skipped deletion due to check mode.",
        }

    delete_organization_tags(adapter, organization, to_delete)
    return {
        "changed": True,
        "ids": sorted(to_delete),
        "msg": f"Tags {sorted(to_delete)} have been deleted successfully",
    }


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "organization": {"type": "str", "required": True},
            "tag_id": {"type": "str"},
            "ids": {"type": "list", "elements": "str"},
            "workspace_ids": {"type": "list", "elements": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        mutually_exclusive=[("tag_id", "ids")],
        required_if=[
            ("state", "present", ["tag_id", "workspace_ids"]),
        ],
        supports_check_mode=True,
    )

    try:
        with module.client() as adapter:
            if module.params["state"] == "present":
                result = state_present(adapter, module.params, module.check_mode)
            else:
                result = state_absent(adapter, module.params, module.check_mode)

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
