#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: gcp_oidc_configuration
version_added: "2.2.0"
short_description: Manage HCP Terraform GCP OIDC configurations for HYOK.
author: "Sivaselvan I (@isivaselvan)"
description:
  - Manages the HCP Terraform-side record of a GCP OIDC configuration - the service account
    email and Workload Identity Federation provider HCP Terraform impersonates, most commonly
    as the C(oidc_configuration_id) dependency of a M(hashicorp.terraform.hyok_configuration).
  - Does B(not) create or manage the GCP-side workload identity pool, provider, or
    service-account IAM bindings - only the HCP Terraform-side configuration record. Provision
    the GCP side with your usual GCP tooling first.
  - The API has no C(list) endpoint and the configuration record has no C(name) field, so
    there is no way to search for an existing configuration by any user-supplied key.
    C(state=present) is only idempotent when C(oidc_configuration_id) is supplied (it then
    reads, diffs, and updates that specific record); without it, every run creates a B(new)
    configuration. Save the returned C(id) (for example via C(register:)) and pass it back in
    on subsequent runs to update in place instead of duplicating.
  - C(state=absent) requires C(oidc_configuration_id) - there is no other way to identify the
    record to delete.
extends_documentation_fragment: hashicorp.terraform.common
options:
  oidc_configuration_id:
    description:
      - The unique identifier of the OIDC configuration (e.g. C(oidc-...)).
      - Required for C(state=absent), and for an idempotent C(state=present) update.
      - Omit on C(state=present) to create a new configuration.
    type: str
  organization:
    description:
      - The name of the organization to create the configuration in.
      - Required when creating (C(oidc_configuration_id) not supplied).
    type: str
  service_account_email:
    description:
      - Email of the GCP service account HCP Terraform impersonates.
      - Required when creating a new configuration.
    type: str
  project_number:
    description:
      - The GCP project number the workload identity pool belongs to.
      - Required when creating a new configuration.
    type: str
  workload_provider_name:
    description:
      - Full resource name of the Workload Identity Federation provider
        (e.g. C(projects/123/locations/global/workloadIdentityPools/pool/providers/provider)).
      - Required when creating a new configuration.
    type: str
  state:
    description:
      - Desired state of the OIDC configuration.
      - C(present) creates a new configuration, or updates an existing one identified by
        C(oidc_configuration_id).
      - C(absent) deletes the configuration identified by C(oidc_configuration_id).
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a GCP OIDC configuration
  hashicorp.terraform.gcp_oidc_configuration:
    organization: "my-org"
    service_account_email: "tfc@project.iam.gserviceaccount.com"
    project_number: "123456789012"
    workload_provider_name: "projects/123456789012/locations/global/workloadIdentityPools/tfc-pool/providers/tfc-provider"
    state: present
  register: result

- name: Update the service account on an existing configuration (idempotent)
  hashicorp.terraform.gcp_oidc_configuration:
    oidc_configuration_id: "{{ result.id }}"
    service_account_email: "new@project.iam.gserviceaccount.com"
    state: present

- name: Delete a GCP OIDC configuration
  hashicorp.terraform.gcp_oidc_configuration:
    oidc_configuration_id: "{{ result.id }}"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The OIDC configuration identifier.
  returned: when state is present
  type: str
  sample: "oidc-gcp-1"
service_account_email:
  description: Email of the GCP service account HCP Terraform impersonates.
  returned: when state is present
  type: str
project_number:
  description: The GCP project number the workload identity pool belongs to.
  returned: when state is present
  type: str
workload_provider_name:
  description: Full resource name of the Workload Identity Federation provider.
  returned: when state is present
  type: str
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "gcp OIDC configuration oidc-gcp-1 has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.oidc_configuration import state_absent, state_present

_PROVIDER = "gcp"
_REQUIRED_FIELDS = ("service_account_email", "project_number", "workload_provider_name")


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "oidc_configuration_id": {"type": "str"},
            "organization": {"type": "str"},
            "service_account_email": {"type": "str"},
            "project_number": {"type": "str"},
            "workload_provider_name": {"type": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
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
                    action_result = state_present(adapter, _PROVIDER, _REQUIRED_FIELDS, params, params["check_mode"])
                case "absent":
                    action_result = state_absent(adapter, _PROVIDER, params, params["check_mode"])

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
