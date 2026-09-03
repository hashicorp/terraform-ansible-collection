# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: run_info
version_added: 1.1.0
short_description: Retrieve information about a run in Terraform Enterprise/Cloud.
author: "Abhishek Chaudhary (@abchaudh)"
description:
  - This module retrieves information about a given run in Terraform Enterprise/Cloud.
  - If I(run_id) is provided, the module will return information about that specific run.
  - If the run does not exist, the module will fail with an error message.
extends_documentation_fragment: hashicorp.terraform.common
options:
  run_id:
    description:
      - The unique identifier of the run to retrieve information about.
    type: str
    required: true
"""
EXAMPLES = r"""
- name: Retrieve information about a run by ID
  hashicorp.terraform.run_info:
    run_id: "run-sample-12345"
  register: run_info

# The returned run is flattened and uses snake_case keys:
# run_info.run:
#   id: run-sample-12345
#   status: applied
#   actions:
#     is_confirmable: false
#   auto_apply: false
#   is_destroy: false
#   plan_only: false
#   workspace:
#     id: ws-sample-12345

- name: Handle case when run does not exist by ID
  hashicorp.terraform.run_info:
    run_id: "run-invalid-id"
  register: run_info
  ignore_errors: true
"""

RETURN = r"""
run:
  type: dict
  description:
    - Run information flattened from the pytfe model.
    - Field names use snake_case; there is no JSON:API C(attributes) wrapper.
  returned: on success
  contains:
    id:
      type: str
      returned: always
      description: The unique identifier of the run.
      sample: "run-sample-12345"
    status:
      type: str
      returned: always
      description: The current run status.
      sample: "applied"
    actions:
      type: dict
      returned: when available
      description: Capability flags for actions available on the run.
      sample:
        is_cancelable: false
        is_confirmable: false
        is_discardable: false
        is_force_cancelable: false
    auto_apply:
      type: bool
      returned: when available
      description: Whether the run was configured to apply automatically.
      sample: false
    has_changes:
      type: bool
      returned: when available
      description: Whether the run's plan contains changes.
      sample: true
    is_destroy:
      type: bool
      returned: when available
      description: Whether this is a destroy run.
      sample: false
    message:
      type: str
      returned: when available
      description: The message associated with the run.
      sample: "Deploy production"
    plan_only:
      type: bool
      returned: when available
      description: Whether this is a speculative plan-only run.
      sample: false
    refresh_only:
      type: bool
      returned: when available
      description: Whether this is a refresh-only run.
      sample: false
    source:
      type: str
      returned: when available
      description: The source that created the run.
      sample: "tfe-api"
    status_timestamps:
      type: dict
      returned: when available
      description: Lifecycle timestamps keyed by snake_case event name.
      sample:
        planned_at: "2026-03-26T10:14:40Z"
        applied_at: "2026-03-26T10:14:55Z"
    configuration_version:
      type: dict
      returned: when available
      description: The related configuration version in flattened pytfe form.
    plan:
      type: dict
      returned: when available
      description: The related plan in flattened pytfe form.
    workspace:
      type: dict
      returned: when available
      description: The related workspace in flattened pytfe form.
    variables:
      type: list
      elements: dict
      returned: when available
      description: Variables supplied directly to the run.
"""


from copy import deepcopy
from typing import TYPE_CHECKING

from ansible.module_utils._text import to_text

if TYPE_CHECKING:
    from typing import Any, Dict, Optional

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.run import get_run


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "run_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: list[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            run_info_data: Optional[Dict[str, Any]] = None

            if params["run_id"]:
                run_info_data = get_run(adapter, params["run_id"])
                if not run_info_data:
                    raise ValueError(f"The run with ID '{params['run_id']}' was not found.")
            else:
                raise ValueError("Run ID is required.")

            result["run"] = run_info_data.get("data", run_info_data)

            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
