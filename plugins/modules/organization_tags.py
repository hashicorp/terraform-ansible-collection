#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: organization_tags
version_added: "2.0.0"
short_description: Manage Terraform Cloud/Enterprise organization tags (associate workspaces, delete).
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Manages organization tags on Terraform Cloud and Terraform Enterprise.
  - Organization tags are workspace tags scoped to an organization.
  - The C(present) state associates one or more workspaces with a tag, identified by
    C(name) or C(tag_id).
  - The C(absent) state deletes one or more tags from the organization, identified by
    C(name), C(tag_id), or a list of C(ids).
  - Tags are created implicitly the first time a workspace is associated with a new tag name.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - Organization that owns the tags.
    type: str
    required: true
  name:
    description:
      - Name of the organization tag.
      - Used to identify the tag for association or deletion.
      - Mutually exclusive with C(tag_id) and C(ids).
    type: str
  tag_id:
    description:
      - The unique identifier of the organization tag (e.g. C(tag-...)).
      - Mutually exclusive with C(name) and C(ids).
    type: str
  ids:
    description:
      - List of tag identifiers to delete.
      - Only valid when C(state=absent).
      - Mutually exclusive with C(name) and C(tag_id).
    type: list
    elements: str
  workspace_ids:
    description:
      - List of workspace IDs to associate with the tag.
      - Required when C(state=present).
    type: list
    elements: str
  state:
    description:
      - Desired state of the organization tag.
      - C(present) associates the listed workspaces with the tag.
      - C(absent) deletes the tag(s) from the organization.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Associate workspaces with a tag by name
  hashicorp.terraform.organization_tags:
    organization: "my-org"
    name: "production"
    workspace_ids:
      - "ws-abc123"
      - "ws-def456"
    state: present

- name: Associate a workspace with a tag by ID
  hashicorp.terraform.organization_tags:
    organization: "my-org"
    tag_id: "tag-7tRVyqGbvrF1RmWQ"
    workspace_ids:
      - "ws-abc123"
    state: present

- name: Delete a tag by name
  hashicorp.terraform.organization_tags:
    organization: "my-org"
    name: "production"
    state: absent

- name: Delete multiple tags by ID
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
  description: Tag identifier (when the tag was resolved).
  returned: when state is present and the tag is known
  type: str
  sample: "tag-7tRVyqGbvrF1RmWQ"
name:
  description: Tag name.
  returned: when state is present and identified by name
  type: str
  sample: "production"
workspace_ids:
  description: Workspace IDs that were associated with the tag.
  returned: when state is present
  type: list
  elements: str
  sample: ["ws-abc123", "ws-def456"]
ids:
  description: Tag identifiers that were deleted.
  returned: when state is absent and tags were deleted
  type: list
  elements: str
  sample: ["tag-7tRVyqGbvrF1RmWQ"]
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Tag production has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


def _transport(adapter: TerraformClient):
    """Return the underlying HTTP transport from the pytfe client."""
    return adapter.client._transport


def list_organization_tags(adapter: TerraformClient, organization: str) -> List[Dict[str, Any]]:
    """List all tags within an organization (empty when none exist)."""
    transport = _transport(adapter)
    path = f"/api/v2/organizations/{quote(organization)}/tags"
    page = 1
    tags: List[Dict[str, Any]] = []
    while True:
        try:
            r = transport.request("GET", path, params={"page[number]": page, "page[size]": 100})
        except NotFound:
            break
        data = (r.json() or {}).get("data", [])
        for item in data:
            attrs = item.get("attributes", {})
            tag: Dict[str, Any] = {"id": item.get("id")}
            if "name" in attrs:
                tag["name"] = attrs["name"]
            if "instance-count" in attrs:
                tag["instance_count"] = attrs["instance-count"]
            tags.append(tag)
        if len(data) < 100:
            break
        page += 1
    return tags


def get_organization_tag_by_name(adapter: TerraformClient, organization: str, name: str) -> Optional[Dict[str, Any]]:
    """Look up a single organization tag by (organization, name).

    Matching is case-insensitive because Terraform Cloud/Enterprise normalizes
    tag names to lowercase on storage.
    """
    target = name.lower()
    for tag in list_organization_tags(adapter, organization):
        tag_name = tag.get("name")
        if tag_name is not None and tag_name.lower() == target:
            return tag
    return None


def delete_organization_tags(adapter: TerraformClient, organization: str, tag_ids: List[str]) -> None:
    """Delete one or more tags from an organization via DELETE /api/v2/organizations/{org}/tags (no-op if empty)."""
    if not tag_ids:
        return
    transport = _transport(adapter)
    path = f"/api/v2/organizations/{quote(organization)}/tags"
    body = {"data": [{"type": "tags", "id": tid} for tid in tag_ids]}
    transport.request("DELETE", path, json_body=body)


def _add_workspaces_to_tag_by_id(adapter: TerraformClient, tag_id: str, workspace_ids: List[str]) -> None:
    """POST /api/v2/tags/{tag_id}/relationships/workspaces — tag must already exist."""
    if not workspace_ids:
        return
    transport = _transport(adapter)
    path = f"/api/v2/tags/{quote(tag_id)}/relationships/workspaces"
    body = {"data": [{"type": "workspaces", "id": wid} for wid in workspace_ids]}
    transport.request("POST", path, json_body=body)


def _add_tag_to_workspaces_by_name(adapter: TerraformClient, tag_name: str, workspace_ids: List[str]) -> None:
    """POST /api/v2/workspaces/{ws_id}/relationships/tags — creates the tag implicitly if it doesn't exist."""
    if not workspace_ids:
        return
    transport = _transport(adapter)
    for ws_id in workspace_ids:
        path = f"/api/v2/workspaces/{quote(ws_id)}/relationships/tags"
        body = {"data": [{"type": "tags", "attributes": {"name": tag_name}}]}
        transport.request("POST", path, json_body=body)


def _resolve_tag(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve a single tag dict by tag_id or by (organization, name)."""
    tag_id = params.get("tag_id")
    organization = params["organization"]
    if tag_id:
        for tag in list_organization_tags(adapter, organization):
            if tag.get("id") == tag_id:
                return tag
        return None
    name = params.get("name")
    if name:
        return get_organization_tag_by_name(adapter, organization, name)
    return None


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Associate the listed workspaces with the tag."""
    workspace_ids = params.get("workspace_ids")
    if not workspace_ids:
        raise ValueError("'workspace_ids' is required and must be non-empty when state is present.")

    tag = _resolve_tag(adapter, params)
    tag_id = tag.get("id") if tag else params.get("tag_id")

    if not tag_id and not params.get("name"):
        raise ValueError("Either 'name' or 'tag_id' is required to identify the tag.")

    identifier = tag_id or params.get("name")

    if check_mode:
        result: Dict[str, Any] = {
            "changed": True,
            "msg": f"Workspaces {sorted(workspace_ids)} would be associated with tag {identifier}. Skipped due to check mode.",
            "workspace_ids": sorted(workspace_ids),
        }
        if tag_id:
            result["id"] = tag_id
        if params.get("name"):
            result["name"] = params["name"]
        return result

    if tag_id:
        # Tag already exists — use the tag-centric API (POST /api/v2/tags/{id}/relationships/workspaces).
        _add_workspaces_to_tag_by_id(adapter, tag_id, sorted(workspace_ids))
    else:
        # Tag doesn't exist yet — use workspace-centric API which creates the tag implicitly by name.
        _add_tag_to_workspaces_by_name(adapter, params["name"], sorted(workspace_ids))

    result = {"changed": True, "workspace_ids": sorted(workspace_ids)}
    if tag_id:
        result["id"] = tag_id
    if params.get("name"):
        result["name"] = params["name"]
    return result


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the targeted tag(s); no-op when none exist."""
    organization = params["organization"]
    explicit_ids = params.get("ids")

    if explicit_ids:
        existing = {tag["id"] for tag in list_organization_tags(adapter, organization) if tag.get("id")}
        to_delete: List[str] = [tag_id for tag_id in explicit_ids if tag_id in existing]
    else:
        tag = _resolve_tag(adapter, params)
        to_delete = [tag["id"]] if tag and tag.get("id") else []

    if not to_delete:
        return {"changed": False, "msg": "Tag is already absent."}

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
            "name": {"type": "str"},
            "tag_id": {"type": "str"},
            "ids": {"type": "list", "elements": "str"},
            "workspace_ids": {"type": "list", "elements": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        mutually_exclusive=[("name", "tag_id", "ids")],
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
