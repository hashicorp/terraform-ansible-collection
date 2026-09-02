#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: no_code_module
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise no-code modules.
author: "Nimisha Shrivastava (@nimisha-shrivastava)"
description:
  - Manages no-code provisioning settings on Terraform Cloud and Terraform Enterprise.
  - No-code modules enable self-service workspace creation without writing Terraform
    configuration.
  - The C(present) state creates a new no-code module when C(organization) and
    C(registry_module_id) are supplied, or updates an existing one when
    C(no_code_module_id) is supplied.
  - The C(absent) state disables no-code provisioning by deleting the no-code module
    (requires C(no_code_module_id)).
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  no_code_module_id:
    description:
      - The unique identifier of the no-code module (e.g., C(nocode-xxxxxxxx)).
      - Required when updating or deleting an existing no-code module.
      - Mutually exclusive with C(organization) and C(registry_module_id).
    type: str
  organization:
    description:
      - The name of the organization that owns the registry module.
      - Required when creating a new no-code module.
      - Mutually exclusive with C(no_code_module_id).
    type: str
  registry_module_id:
    description:
      - The ID of the registry module to enable for no-code provisioning.
      - Required when creating a new no-code module.
      - Mutually exclusive with C(no_code_module_id).
    type: str
  enabled:
    description:
      - Whether no-code provisioning is enabled.
      - When not set, the server default is used on creation.
    type: bool
  version_pin:
    description:
      - The version to pin the no-code module to (e.g., C(1.2.3)).
      - When not set, the latest version is used.
    type: str
  state:
    description:
      - Desired state of the no-code module.
      - C(present) creates or updates the no-code module.
      - C(absent) disables no-code provisioning by deleting the no-code module record.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Enable no-code provisioning for a registry module
  hashicorp.terraform.no_code_module:
    organization: "my-org"
    registry_module_id: "mod-abc123"
    enabled: true
    state: present
  register: result

- name: Pin no-code module to a specific version
  hashicorp.terraform.no_code_module:
    organization: "my-org"
    registry_module_id: "mod-abc123"
    enabled: true
    version_pin: "1.2.3"
    state: present
  register: result_pinned

- name: Update an existing no-code module
  hashicorp.terraform.no_code_module:
    no_code_module_id: "nocode-abc123"
    enabled: false
    state: present
  register: result_update

- name: Disable no-code provisioning (delete no-code module)
  hashicorp.terraform.no_code_module:
    no_code_module_id: "nocode-abc123"
    state: absent
  register: result_delete
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The unique identifier of the no-code module.
  returned: when state is present and not check mode
  type: str
  sample: "nocode-abc123"
enabled:
  description: Whether no-code provisioning is enabled.
  returned: when state is present and not check mode
  type: bool
  sample: true
version_pin:
  description: The version the no-code module is pinned to.
  returned: when state is present, not check mode, and version_pin is set on the server
  type: str
  sample: "1.2.3"
variable_options:
  description: List of allowed-values constraints configured on the no-code module.
  returned: when state is present and not check mode
  type: list
  elements: dict
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "No-code module nocode-abc123 has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.no_code_module import (
    create_no_code_module,
    delete_no_code_module,
    get_no_code_module,
    update_no_code_module,
)


def _fetch_no_code_module(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target no-code module using the direct read API."""
    no_code_module_id = params.get("no_code_module_id")
    if no_code_module_id:
        return get_no_code_module(adapter, no_code_module_id)
    return None


def _has_drift(params: Dict[str, Any], current: Dict[str, Any]) -> bool:
    """Return True if any user-specified field differs from the current no-code module."""
    for field in ("enabled", "version_pin"):
        if params.get(field) is not None and params[field] != current.get(field):
            return True
    return False


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Reconcile the desired state of a no-code module.

    If C(no_code_module_id) is provided, reads the existing record and updates
    if there is drift.  Otherwise creates a new no-code module using
    C(organization) and C(registry_module_id).

    Note: The PyTFE API provides no endpoint to look up a no-code module by
    organization or registry_module_id (no list-by-org or filter method exists).
    Create-path idempotency therefore cannot be implemented without API support.
    Callers who need idempotent re-runs on the create path should capture the
    returned C(id) and use C(no_code_module_id) on subsequent plays.
    """
    no_code_module_id = params.get("no_code_module_id")

    if no_code_module_id:
        # Update path: read current state and reconcile drift.
        current = _fetch_no_code_module(adapter, params)
        if current is None:
            raise ValueError(f"No-code module '{no_code_module_id}' was not found")

        if not _has_drift(params, current):
            return {"changed": False, **current}

        if check_mode:
            return {
                "changed": True,
                "msg": f"No-code module {no_code_module_id} would be updated. Skipped update due to check mode.",
            }

        update_data: Dict[str, Any] = {}
        if params.get("enabled") is not None:
            update_data["enabled"] = params["enabled"]
        if params.get("version_pin") is not None:
            update_data["version_pin"] = params["version_pin"]

        updated = update_no_code_module(adapter, no_code_module_id, update_data)
        return {"changed": True, **updated}

    # Create path: organization + registry_module_id required.
    if not params.get("organization"):
        raise ValueError("'organization' is required when creating a no-code module")
    if not params.get("registry_module_id"):
        raise ValueError("'registry_module_id' is required when creating a no-code module")

    if check_mode:
        return {
            "changed": True,
            "msg": "No-code module would be created. Skipped creation due to check mode.",
        }

    create_data: Dict[str, Any] = {"registry_module_id": params["registry_module_id"]}
    if params.get("enabled") is not None:
        create_data["enabled"] = params["enabled"]
    if params.get("version_pin") is not None:
        create_data["version_pin"] = params["version_pin"]

    created = create_no_code_module(adapter, params["organization"], create_data)
    return {"changed": True, **created}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Disable no-code provisioning by deleting the no-code module record."""
    no_code_module_id = params.get("no_code_module_id")
    if not no_code_module_id:
        raise ValueError("'no_code_module_id' is required when state is absent")

    current = _fetch_no_code_module(adapter, params)
    if current is None:
        return {"changed": False, "msg": "No-code module is already absent."}

    if check_mode:
        return {
            "changed": True,
            "msg": f"No-code module {no_code_module_id} would be deleted. Skipped deletion due to check mode.",
        }

    delete_no_code_module(adapter, no_code_module_id)
    return {"changed": True, "msg": f"No-code module {no_code_module_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "no_code_module_id": {"type": "str"},
            "organization": {"type": "str"},
            "registry_module_id": {"type": "str"},
            "enabled": {"type": "bool"},
            "version_pin": {"type": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        mutually_exclusive=[
            ("no_code_module_id", "organization"),
            ("no_code_module_id", "registry_module_id"),
        ],
        required_if=[("state", "absent", ["no_code_module_id"])],
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
