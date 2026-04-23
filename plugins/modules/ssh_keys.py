#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: ssh_keys
version_added: "2.0.0"
short_description: Manage Terraform Cloud/Enterprise organization SSH keys (create, update, delete).
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Manages organization-scoped SSH keys on Terraform Cloud and Terraform Enterprise.
  - SSH keys are used by workspaces to clone Git-based modules and configurations from private
    repositories reachable over SSH.
  - Identify a key either directly by C(ssh_key_id), or by the combination of C(organization) and C(name).
  - The C(present) state creates the key if it does not exist, or renames it when the name drifts.
  - The C(absent) state deletes the key if it exists.
  - Note - the TFE API is write-only for the private key material; the C(value) is never returned by
    the API and therefore cannot be diffed. Re-running with the same C(name) is idempotent even when
    C(value) is supplied. To rotate key material, delete and recreate the SSH key.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  ssh_key_id:
    description:
      - The unique identifier of the SSH key (e.g. C(sshkey-...)).
      - Provide for unambiguous update or delete operations.
      - When given together with C(name), the key is looked up by ID and C(name) is treated as the desired (possibly new) name.
    type: str
  organization:
    description:
      - The name of the organization that owns the SSH key.
      - Required unless C(ssh_key_id) is provided.
    type: str
  name:
    description:
      - Human-readable name of the SSH key.
      - Required when identifying the key by (organization, name).
    type: str
  value:
    description:
      - The SSH private key material in PEM format.
      - Required when creating a new key.
      - Write-only - the API never returns this value, so drift on C(value) alone cannot be detected.
    type: str
  state:
    description:
      - Desired state of the SSH key.
      - C(present) creates or updates; C(absent) deletes.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create an SSH key
  hashicorp.terraform.ssh_keys:
    organization: "my-org"
    name: "deploy-key"
    value: "{{ lookup('file', '~/.ssh/deploy_key') }}"
    state: present

- name: Idempotent re-run with the same name
  hashicorp.terraform.ssh_keys:
    organization: "my-org"
    name: "deploy-key"
    value: "{{ lookup('file', '~/.ssh/deploy_key') }}"
    state: present
# "changed": false - the value is write-only so only name drift triggers an update

- name: Rename an existing SSH key by ID
  hashicorp.terraform.ssh_keys:
    ssh_key_id: "sshkey-abc123"
    name: "deploy-key-renamed"
    state: present

- name: Delete an SSH key by name
  hashicorp.terraform.ssh_keys:
    organization: "my-org"
    name: "deploy-key-renamed"
    state: absent

- name: Delete an SSH key by ID
  hashicorp.terraform.ssh_keys:
    ssh_key_id: "sshkey-abc123"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The SSH key identifier.
  returned: when state is present
  type: str
  sample: "sshkey-EavQ1LztoRTQHSNT"
name:
  description: The SSH key name.
  returned: when state is present
  type: str
  sample: "deploy-key"
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "SSH key sshkey-EavQ1LztoRTQHSNT has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.ssh_keys import (
    create_ssh_key,
    delete_ssh_key,
    get_ssh_key,
    get_ssh_key_by_name,
    update_ssh_key,
)


def _fetch_ssh_key(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target SSH key by ID or by (organization, name)."""
    ssh_key_id = params.get("ssh_key_id")
    if ssh_key_id:
        return get_ssh_key(adapter, ssh_key_id)
    organization = params.get("organization")
    name = params.get("name")
    if organization and name:
        return get_ssh_key_by_name(adapter, organization, name)
    return None


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update an SSH key to match the desired state."""
    current = _fetch_ssh_key(adapter, params)
    name = params.get("name")
    value = params.get("value")

    if current is None:
        if not params.get("organization"):
            raise ValueError("'organization' is required when creating a new SSH key.")
        if not name:
            raise ValueError("'name' is required when creating a new SSH key.")
        if not value:
            raise ValueError("'value' is required when creating a new SSH key.")
        if check_mode:
            return {
                "changed": True,
                "msg": f"SSH key {name} would be created. Skipped creation due to check mode.",
                "name": name,
            }
        created = create_ssh_key(adapter, params["organization"], {"name": name, "value": value})
        return {"changed": True, **created}

    # Only 'name' is mutable server-side; 'value' is write-only and cannot be diffed.
    if name and name != current.get("name"):
        if check_mode:
            return {
                "changed": True,
                "msg": f"SSH key {current.get('id')} would be renamed to {name}. Skipped update due to check mode.",
                "name": name,
            }
        updated = update_ssh_key(adapter, current["id"], {"name": name})
        return {"changed": True, **updated}

    return {"changed": False, **current}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the SSH key if present; no-op otherwise."""
    current = _fetch_ssh_key(adapter, params)
    if current is None:
        return {"changed": False, "msg": "SSH key is already absent."}

    ssh_key_id = current["id"]
    if check_mode:
        return {"changed": True, "msg": f"SSH key {ssh_key_id} would be deleted. Skipped deletion due to check mode."}

    delete_ssh_key(adapter, ssh_key_id)
    return {"changed": True, "msg": f"SSH key {ssh_key_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "ssh_key_id": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
            "value": {"type": "str", "no_log": True},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_one_of=[("ssh_key_id", "name")],
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
