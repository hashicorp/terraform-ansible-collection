#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: reserved_tag_keys
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise reserved tag keys (create, update, delete).
author: "Nimisha Shrivastava (@NimishaShrivastava-dev)"
description:
  - Manages reserved tag keys on Terraform Cloud and Terraform Enterprise.
  - Reserved tag keys prevent workspaces from overriding inherited tags with a specific key at the workspace level.
  - Identify a key either directly by C(reserved_tag_key_id), or by the combination of C(organization) and C(key).
  - The C(present) state creates the key if it does not exist, or updates its C(disable_overrides) setting when it drifts.
  - The C(absent) state deletes the key if it exists.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  reserved_tag_key_id:
    description:
      - The unique identifier of the reserved tag key (e.g. C(rtk-...)).
      - Provide for unambiguous update or delete operations.
      - When given together with C(key), the key is looked up by ID and C(key) is treated as the desired (possibly new) key.
    type: str
  organization:
    description:
      - The name of the organization that owns the reserved tag key.
      - Required unless C(reserved_tag_key_id) is provided.
    type: str
  key:
    description:
      - The key targeted by this reserved tag key.
      - Required when identifying the key by (organization, key) or when creating a new key.
    type: str
  disable_overrides:
    description:
      - If true, disables overriding inherited tags with the specified key at the workspace level.
      - Required when creating a new key.
    type: bool
  state:
    description:
      - Desired state of the reserved tag key.
      - C(present) creates or updates; C(absent) deletes.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a reserved tag key
  hashicorp.terraform.reserved_tag_keys:
    organization: "my-org"
    key: "environment"
    disable_overrides: true
    state: present

- name: Idempotent re-run with the same key
  hashicorp.terraform.reserved_tag_keys:
    organization: "my-org"
    key: "environment"
    disable_overrides: true
    state: present
# "changed": false - the key already exists with the same settings

- name: Update a reserved tag key by ID
  hashicorp.terraform.reserved_tag_keys:
    reserved_tag_key_id: "rtk-abc123"
    disable_overrides: false
    state: present

- name: Delete a reserved tag key by key name
  hashicorp.terraform.reserved_tag_keys:
    organization: "my-org"
    key: "environment"
    state: absent

- name: Delete a reserved tag key by ID
  hashicorp.terraform.reserved_tag_keys:
    reserved_tag_key_id: "rtk-abc123"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The reserved tag key identifier.
  returned: when state is present
  type: str
  sample: "rtk-EavQ1LztoRTQHSNT"
key:
  description: The reserved tag key name.
  returned: when state is present
  type: str
  sample: "environment"
disable_overrides:
  description: Whether overriding inherited tags with this key is disabled at the workspace level.
  returned: when state is present
  type: bool
  sample: true
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Reserved tag key rtk-EavQ1LztoRTQHSNT has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.reserved_tag_keys import (
    create_reserved_tag_key,
    delete_reserved_tag_key,
    get_reserved_tag_key,
    get_reserved_tag_key_by_key,
    try_delete_reserved_tag_key,
    update_reserved_tag_key,
)


def _fetch_reserved_tag_key(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target reserved tag key by ID or by (organization, key)."""
    reserved_tag_key_id = params.get("reserved_tag_key_id")
    if reserved_tag_key_id:
        return get_reserved_tag_key(adapter, reserved_tag_key_id)
    organization = params.get("organization")
    key = params.get("key")
    if organization and key:
        return get_reserved_tag_key_by_key(adapter, organization, key)
    return None


def _has_drift(params: Dict[str, Any], current: Dict[str, Any]) -> bool:
    """Check if there is drift between desired and current state.

    Only check fields the user explicitly supplied (non-None).
    """
    disable_overrides = params.get("disable_overrides")
    if disable_overrides is not None and disable_overrides != current.get("disable_overrides"):
        return True
    key = params.get("key")
    if key is not None and key != current.get("key"):
        return True
    return False


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update a reserved tag key to match the desired state."""
    reserved_tag_key_id = params.get("reserved_tag_key_id")
    key = params.get("key")
    disable_overrides = params.get("disable_overrides")
    organization = params.get("organization")

    # Try to fetch current state if we have enough info
    current = None
    if organization and key:
        current = get_reserved_tag_key_by_key(adapter, organization, key)
    # Note: We can't fetch by ID alone since pytfe doesn't have read() for reserved_tag_keys
    # So if only ID is provided, we must proceed with update without checking current state

    # Determine if we're in create or update mode
    is_create = current is None and not reserved_tag_key_id

    if is_create:
        # Create new reserved tag key
        if not organization:
            raise ValueError("'organization' is required when creating a new reserved tag key.")
        if not key:
            raise ValueError("'key' is required when creating a new reserved tag key.")
        if disable_overrides is None:
            raise ValueError("'disable_overrides' is required when creating a new reserved tag key.")
        if check_mode:
            return {
                "changed": True,
                "msg": f"Reserved tag key {key} would be created. Skipped creation due to check mode.",
                "key": key,
                "disable_overrides": disable_overrides,
            }
        created = create_reserved_tag_key(adapter, organization, {"key": key, "disable_overrides": disable_overrides})
        return {"changed": True, **created}

    # Update mode (either have current from lookup, or have reserved_tag_key_id)
    if current:
        # Check for drift
        if _has_drift(params, current):
            if check_mode:
                return {
                    "changed": True,
                    "msg": f"Reserved tag key {current.get('id')} would be updated. Skipped update due to check mode.",
                    "id": current.get("id"),
                    "key": current.get("key"),
                    "disable_overrides": current.get("disable_overrides"),
                }
            # Build update payload with only supplied fields
            update_data = {}
            if key is not None:
                update_data["key"] = key
            if disable_overrides is not None:
                update_data["disable_overrides"] = disable_overrides
            updated = update_reserved_tag_key(adapter, current["id"], update_data)
            return {"changed": True, **updated}
        return {"changed": False, **current}

    elif reserved_tag_key_id:
        # Update by ID without pre-checking current state (since read() not available)
        # Build update payload with only supplied fields
        update_data = {}
        if key is not None:
            update_data["key"] = key
        if disable_overrides is not None:
            update_data["disable_overrides"] = disable_overrides

        if not update_data:
            # No fields to update, so this is a no-op
            return {
                "changed": False,
                "msg": f"No changes specified for reserved tag key {reserved_tag_key_id}",
                "id": reserved_tag_key_id,
            }

        if check_mode:
            return {
                "changed": True,
                "msg": f"Reserved tag key {reserved_tag_key_id} would be updated. Skipped update due to check mode.",
                "id": reserved_tag_key_id,
            }
        updated = update_reserved_tag_key(adapter, reserved_tag_key_id, update_data)
        return {"changed": True, **updated}

    else:
        raise ValueError("'organization' and 'key' OR 'reserved_tag_key_id' is required")


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the reserved tag key if present; no-op otherwise.

    When C(reserved_tag_key_id) is supplied without C(organization)/C(key),
    the pytfe service offers no read-by-ID method, so the module attempts the
    delete directly and treats a NotFound response as "already absent".
    When the key is identified by C(organization) + C(key), the current state is
    fetched first so the module can give an accurate idempotent result.
    """
    reserved_tag_key_id = params.get("reserved_tag_key_id")
    organization = params.get("organization")
    key = params.get("key")

    # --- ID-only path: attempt the delete directly ---
    if reserved_tag_key_id and not (organization and key):
        if check_mode:
            # We have no way to verify existence; optimistically report changed.
            return {
                "changed": True,
                "msg": f"Reserved tag key {reserved_tag_key_id} would be deleted. Skipped deletion due to check mode.",
            }
        deleted = try_delete_reserved_tag_key(adapter, reserved_tag_key_id)
        if deleted:
            return {"changed": True, "msg": f"Reserved tag key {reserved_tag_key_id} has been deleted successfully"}
        return {"changed": False, "msg": "Reserved tag key is already absent."}

    # --- org+key path: fetch first for accurate idempotency ---
    current = _fetch_reserved_tag_key(adapter, params)
    if current is None:
        return {"changed": False, "msg": "Reserved tag key is already absent."}

    rtk_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"Reserved tag key {rtk_id} would be deleted. Skipped deletion due to check mode."}

    delete_reserved_tag_key(adapter, rtk_id)
    return {"changed": True, "msg": f"Reserved tag key {rtk_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "reserved_tag_key_id": {"type": "str"},
            "organization": {"type": "str"},
            "key": {"type": "str", "no_log": False},
            "disable_overrides": {"type": "bool"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_one_of=[("reserved_tag_key_id", "key")],
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
