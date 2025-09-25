# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
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

# Task output:
# ------------
# "run_result": {
#     "changed": false,
#     "failed": false,
#     "run": {
#         "attributes": {
#             "actions": {
#                 "is-cancelable": false,
#                 "is-confirmable": false,
#                 "is-discardable": false,
#                 "is-force-cancelable": false
#             },
#             "allow-config-generation": true,
#             "allow-empty-apply": false,
#             "auto-apply": false,
#             "canceled-at": null,
#             "created-at": "2025-07-30T11:35:47.183Z",
#             "has-changes": true,
#             "is-destroy": false,
#             "message": "test",
#             "permissions": {
#                 "can-apply": true,
#                 "can-cancel": true,
#                 "can-comment": true,
#                 "can-discard": true,
#                 "can-force-cancel": true,
#                 "can-force-execute": true,
#                 "can-override-policy-check": true
#             },
#             "plan-only": false,
#             "refresh": true,
#             "refresh-only": false,
#             "replace-addrs": [],
#             "save-plan": false,
#             "source": "tfe-ui",
#             "status": "discarded",
#             "status-timestamps": {
#                 "discarded-at": "2025-07-30T11:39:34+00:00",
#                 "plan-queueable-at": "2025-07-30T11:35:47+00:00",
#                 "plan-queued-at": "2025-07-30T11:35:47+00:00",
#                 "planned-at": "2025-07-30T11:36:08+00:00",
#                 "planning-at": "2025-07-30T11:35:49+00:00",
#                 "post-plan-running-at": "2025-07-30T11:36:08+00:00",
#                 "queuing-at": "2025-07-30T11:35:47+00:00"
#             },
#             "target-addrs": null,
#             "terraform-version": "1.10.5",
#             "trigger-reason": "manual",
#             "updated-at": "2025-07-30T11:39:34.091Z",
#             "variables": []
#         },
#         "id": "run-sample1234567890",
#         "links": {
#             "self": "/api/v2/runs/run-sample1234567890"
#         },
#         "relationships": {
#             "apply": {
#                 "data": {
#                     "id": "apply-XJ1s5VQrgZRNSHsn",
#                     "type": "applies"
#                 },
#                 "links": {
#                     "related": "/api/v2/runs/run-sample1234567890/apply"
#                 }
#             },
#             "comments": {
#                 "data": [],
#                 "links": {
#                     "related": "/api/v2/runs/run-sample1234567890/comments"
#                 }
#             },
#             "configuration-version": {
#                 "data": {
#                     "id": "cv-h2u3XnkPasTHbgyv",
#                     "type": "configuration-versions"
#                 },
#                 "links": {
#                     "related": "/api/v2/runs/run-sample1234567890/configuration-version"
#                 }
#             },
#             "created-by": {
#                 "data": {
#                     "id": "user-YYhuc7w4AJxv5RVp",
#                     "type": "users"
#                 },
#                 "links": {
#                     "related": "/api/v2/runs/run-sample1234567890/created-by"
#                 }
#             },
#             "plan": {
#                 "data": {
#                     "id": "plan-2hQe8iJVqBDAg9zA",
#                     "type": "plans"
#                 },
#                 "links": {
#                     "related": "/api/v2/runs/run-sample1234567890/plan"
#                 }
#             },
#             "policy-checks": {
#                 "data": [],
#                 "links": {
#                     "related": "/api/v2/runs/run-sample1234567890/policy-checks"
#                 }
#             },
#             "run-events": {
#                 "data": [
#                     {
#                         "id": "re-a6cNzRDD4THQK5xF",
#                         "type": "run-events"
#                     }
#                 ],
#                 "links": {
#                     "related": "/api/v2/runs/run-sample1234567890/run-events"
#                 }
#             },
#             "task-stages": {
#                 "data": [
#                     {
#                         "id": "ts-24rWmqCXzYtyNv6C",
#                         "type": "task-stages"
#                     }
#                 ],
#                 "links": {
#                     "related": "/api/v2/runs/run-sample1234567890/task-stages"
#                 }
#             },
#             "workspace": {
#                 "data": {
#                     "id": "ws-82Qk88p7boaHK2BT",
#                     "type": "workspaces"
#                 }
#             }
#         },
#         "type": "runs"
#     }
# }

- name: Handle case when run does not exist by ID
  hashicorp.terraform.run_info:
    run_id: "run-invalid-id"
  register: run_info
  ignore_errors: true

# Task output:
# ------------
# FAILED! => {
#     "changed": false,
#     "failed": true,
#     "msg": "The run with ID 'run-invalid-id' was not found."
# }
"""

RETURN = r"""
run:
  type: dict
  description: A dictionary containing the run information.
  returned: on success
  contains:
    id:
      type: str
      returned: always
      description: The unique identifier of the run.
      sample: "run-sample-12345"
    type:
      type: str
      returned: always
      description: The type of the resource (always "runs").
      sample: "runs"
    attributes:
      type: dict
      returned: always
      description: The attributes of the run.
    relationships:
      type: dict
      returned: always
      description: Relationships to other resources.
    links:
      type: dict
      returned: always
      description: Links related to the run.
      contains:
        self:
          type: str
          returned: always
          description: API endpoint for this run.
"""


from copy import deepcopy
from typing import TYPE_CHECKING

from ansible.module_utils._text import to_text


if TYPE_CHECKING:
    from typing import Any, Dict, List

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.run import get_run


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "run_id": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )

    warnings: List[str] = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        client = TerraformClient(**module.params)

        run_info_data = get_run(client=client, run_id=params["run_id"])
        if not run_info_data:
            raise ValueError(f"The run with ID '{params['run_id']}' was not found.")

        result["run"] = run_info_data.get("data", run_info_data)

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
