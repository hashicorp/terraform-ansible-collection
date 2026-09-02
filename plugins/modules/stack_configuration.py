#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: stack_configuration
version_added: "2.2.0"
short_description: Create a Terraform stack configuration snapshot.
author: "Tanya Singh (@TanyaSingh369-svg)"
description:
  - Creates a new stack configuration snapshot for a Terraform stack on HCP Terraform or Terraform Enterprise.
  - Stack configurations are immutable, append-only records. Every invocation with C(state=present)
    creates a new snapshot. There is no update or delete in the API.
  - The C(source) option controls how the configuration content is sourced.
    Use C(manual) for archive uploads, C(fetch) to pull from VCS, or C(reuse) to reuse the previous configuration.
  - Use M(hashicorp.terraform.stack_configuration_info) to read an existing configuration by ID.
  - Compatible with both HCP Terraform and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  stack_id:
    description:
      - The unique identifier of the parent stack (e.g. C(st-xyz789)).
      - Required when C(state=present).
    type: str
  source:
    description:
      - How to source the configuration content.
      - C(manual) expects you to upload a configuration archive separately.
      - C(fetch) triggers a pull from the linked VCS repository.
      - C(reuse) reuses the configuration from the previous stack configuration.
    type: str
    choices: ["manual", "fetch", "reuse"]
    default: "manual"
  speculative_enabled:
    description:
      - When C(true), the resulting plans are speculative (plan-only, no apply).
    type: bool
    default: false
  destroy_all:
    description:
      - When C(true), the configuration targets destruction of all deployments.
    type: bool
    default: false
  selected_deployments:
    description:
      - An explicit list of deployment names to target.
      - When omitted all deployments are included.
    type: list
    elements: str
  state:
    description:
      - C(present) creates a new stack configuration snapshot.
      - C(absent) is not supported; stack configurations are immutable, append-only records.
    type: str
    choices: ["present"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a stack configuration (manual upload)
  hashicorp.terraform.stack_configuration:
    stack_id: "st-xyz789"
    speculative_enabled: false
    state: present
  register: stack_configuration

- name: Trigger a VCS fetch
  hashicorp.terraform.stack_configuration:
    stack_id: "st-xyz789"
    source: fetch
    state: present
  register: stack_configuration_vcs

- name: Create a speculative stack configuration
  hashicorp.terraform.stack_configuration:
    stack_id: "st-xyz789"
    speculative_enabled: true
    state: present
  register: stack_configuration_speculative
"""

RETURN = r"""
changed:
  description: Whether a stack configuration was created.
  returned: always
  type: bool
  sample: true
id:
  description: The stack configuration identifier assigned by HCP Terraform.
  returned: when state is present
  type: str
  sample: "stc-abc123"
status:
  description: The initial status of the created stack configuration.
  returned: when state is present
  type: str
  sample: "pending"
sequence_number:
  description: The sequential number of this configuration for the stack.
  returned: when state is present
  type: int
  sample: 3
speculative:
  description: Whether this is a speculative (plan-only) configuration.
  returned: when state is present
  type: bool
  sample: false
created_at:
  description: ISO-8601 timestamp when the configuration was created.
  returned: when state is present
  type: str
  sample: "2025-01-01T00:00:00+00:00"
updated_at:
  description: ISO-8601 timestamp when the configuration was last updated.
  returned: when state is present
  type: str
  sample: "2025-01-01T00:00:01+00:00"
msg:
  description: Informational message, primarily for no-op and check mode operations.
  returned: when relevant
  type: str
  sample: "Stack configuration for st-xyz789 would be created. Skipped due to check mode."
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_configuration import (
    create_stack_configuration,
)

# Fields that are passed to StackConfigurationCreateOptions (excluding 'source' which is a
# top-level pytfe parameter handled separately by the adapter).
_CREATE_OPTION_KEYS = ("speculative_enabled", "destroy_all", "selected_deployments")


def _desired_payload(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build the create payload from the user-supplied (non-None) params."""
    data: Dict[str, Any] = {}
    for key in _CREATE_OPTION_KEYS:
        if params.get(key) is not None:
            data[key] = params[key]
    # Include source so the adapter can resolve the StackConfigurationSource enum
    source = params.get("source")
    if source is not None:
        data["source"] = source
    return data


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create a new stack configuration."""
    stack_id = params.get("stack_id")
    if not stack_id:
        raise ValueError("'stack_id' is required when creating a stack configuration.")

    if check_mode:
        return {
            "changed": True,
            "msg": f"Stack configuration for {stack_id} would be created. Skipped due to check mode.",
        }

    created = create_stack_configuration(adapter, stack_id, _desired_payload(params))
    return {"changed": True, **created}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "stack_id": {"type": "str"},
            "source": {
                "type": "str",
                "default": "manual",
                "choices": ["manual", "fetch", "reuse"],
            },
            "speculative_enabled": {"type": "bool", "default": False},
            "destroy_all": {"type": "bool", "default": False},
            "selected_deployments": {"type": "list", "elements": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present"]},
        },
        required_if=[("state", "present", ("stack_id",))],
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    action_result: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = deepcopy(module.params)

    try:
        with module.client() as adapter:
            match params["state"]:
                case "present":
                    action_result = state_present(adapter, params, module.check_mode)

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
