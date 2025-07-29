#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
module: plan_info
version_added: "1.0.0"
short_description: Retrieve information about Terraform Cloud/Enterprise plans
description:
  - Retrieve information about a Terraform execution plan from HashiCorp Terraform Cloud or Terraform Enterprise.
  - Can check plan status, resource changes, and execution details.
  - Supports both Terraform Cloud and Terraform Enterprise deployments.
  - Plan information can be retrieved using either a plan ID or a run ID.
  - Always returns both metadata and JSON output for comprehensive plan analysis.
  - Can use the task `ansible.utils.fact_diff` to analyze drift in resources based on the plan changes.
options:
  plan_id:
    description:
      - The ID of the plan to retrieve information for.
      - Plan IDs can be found in the relationships.plan property of a run object.
      - When provided, the module will use the /plans/:id endpoint.
      - Mutually exclusive with run_id.
    type: str
    aliases: ['id']
  run_id:
    description:
      - The ID of the run whose plan information should be retrieved.
      - When provided, the module will use the /runs/:id/plan endpoint.
      - Mutually exclusive with plan_id.
    type: str
extends_documentation_fragment:
  - hashicorp.terraform.auth
"""

EXAMPLES = r"""
# Get plan information
- name: Get plan information by plan ID
  hashicorp.terraform.plan_info:
    plan_id: <your-plan-id>
    token: "{{ tf_token }}"
    hostname: "{{ tf_hostname }}"
  register: plan_result
# Task output:
# ------------
# "changed": false,
# "metadata": {
#     "data": {
#         "attributes": {
#             "has_changes": true,
#             "resource_additions": 1,
#             "resource_changes": 0,
#             "resource_destructions": 0,
#             "status": "finished"
#         },
#         "id": "plan-8F5JFydVYAmRZLLC",
#         "type": "plans"
#     }
# },
# "json_output": {
#     "applyable": true,
#     "complete": true,
#     "configuration": {
#         "provider_config": {
#             "aws": {
#                 "name": "aws",
#                 "full_name": "registry.terraform.io/hashicorp/aws"
#             }
#         },
#         "root_module": {
#             "resources": [
#                 {
#                     "address": "aws_instance.example",
#                     "mode": "managed",
#                     "name": "example",
#                     "provider_config_key": "aws",
#                     "schema_version": 1,
#                     "type": "aws_instance"
#                 }
#             ]
#         }
#     },
#     "errored": false,
#     "format_version": "1.2",
#     "planned_values": {
#         "root_module": {
#             "resources": [
#                 {
#                     "address": "aws_instance.example",
#                     "mode": "managed",
#                     "name": "example",
#                     "provider_name": "registry.terraform.io/hashicorp/aws",
#                     "schema_version": 1,
#                     "type": "aws_instance",
#                     "values": {
#                         "ami": "ami-0c02fb55956c7d316",
#                         "instance_type": "t2.micro"
#                     }
#                 }
#             ]
#         }
#     },
#     "resource_changes": [
#         {
#             "address": "aws_instance.example",
#             "change": {
#                 "actions": ["create"],
#                 "before": null,
#                 "after": {
#                     "ami": "ami-0c02fb55956c7d316",
#                     "instance_type": "t2.micro",
#                     "tags": null
#                 },
#                 "after_unknown": {
#                     "arn": true,
#                     "id": true,
#                     "public_ip": true
#                 },
#             },
#             "mode": "managed",
#             "name": "example",
#             "provider_name": "registry.terraform.io/hashicorp/aws",
#             "type": "aws_instance"
#         }
#     ],
#     "terraform_version": "1.5.0",
#     "timestamp": "2025-07-25T10:15:30Z"
# },
# "plan_status": "finished"

- name: Get plan information by run ID
  hashicorp.terraform.plan_info:
    run_id: <your-run-id>
    token: "{{ tf_token }}"
    hostname: "{{ tf_hostname }}"
  register: plan_result
# Task output:
# ------------
# "changed": false,
# "metadata": {
#     "data": {
#         "attributes": {
#             "has_changes": true,
#             "resource_additions": 0,
#             "resource_changes": 1,
#             "resource_destructions": 0,
#             "status": "finished"
#         },
#         "id": "plan-9G6KGzfWZBnSaMLD",
#         "type": "plans"
#     }
# },
# "json_output": {
#     "applyable": true,
#     "complete": true,
#     "errored": false,
#     "format_version": "1.2",
#     "resource_changes": [
#         {
#             "address": "aws_s3_bucket.example",
#             "change": {
#                 "actions": ["update"],
#                 "before": {
#                     "bucket": "my-terraform-bucket",
#                     "versioning": {
#                         "enabled": false
#                     }
#                 },
#                 "after": {
#                     "bucket": "my-terraform-bucket",
#                     "versioning": {
#                         "enabled": true
#                     }
#                 },
#                 "after_unknown": {
#                     "id": true
#                 },
#             },
#             "mode": "managed",
#             "name": "example",
#             "provider_name": "registry.terraform.io/hashicorp/aws",
#             "type": "aws_s3_bucket"
#         }
#     ],
#     "terraform_version": "1.5.0",
#     "timestamp": "2025-07-25T10:20:45Z"
# },
# "plan_status": "finished"

- name: Get plan information for a plan with no changes
  hashicorp.terraform.plan_info:
    plan_id: <your-plan-id>
    token: "{{ tf_token }}"
    hostname: "{{ tf_hostname }}"
  register: plan_result
# Task output:
# ------------
# "changed": false,
# "metadata": {
#     "data": {
#         "attributes": {
#             "has_changes": false,
#             "resource_additions": 0,
#             "resource_changes": 0,
#             "resource_destructions": 0,
#             "status": "finished"
#         },
#         "id": "plan-NoChangesExample",
#         "type": "plans"
#     }
# },
# "json_output": {
#     "applyable": false,
#     "complete": true,
#     "errored": false,
#     "format_version": "1.2",
#     "resource_changes": [],
#     "terraform_version": "1.5.0",
#     "timestamp": "2025-07-25T10:25:12Z"
# },
# "plan_status": "finished"

- name: Get plan information with error status (plan failed)
  hashicorp.terraform.plan_info:
    run_id: <your-run-id>
    token: "{{ tf_token }}"
    hostname: "{{ tf_hostname }}"
  register: plan_result
# Task output:
# ------------
# "changed": false,
# "metadata": {
#     "data": {
#         "attributes": {
#             "has_changes": false,
#             "resource_additions": 0,
#             "resource_changes": 0,
#             "resource_destructions": 0,
#             "status": "errored"
#         },
#         "id": "plan-ErrorExample123",
#         "type": "plans"
#     }
# },
# "json_output": {
#     "applyable": false,
#     "complete": false,
#     "errored": true,
#     "format_version": "1.2",
#     "resource_changes": [],
#     "terraform_version": "1.5.0",
#     "timestamp": "2025-07-25T10:30:22Z"
# },
# "plan_status": "errored"

# For drift analysis, use these tasks in the playbook
# To see diff output, run the playbook with --diff flag:
# $ ansible-playbook playbooks/test_plan_info.yml --diff

- name: Analyze each resource changes for drift detection
  ansible.utils.fact_diff:
    before: "{{ item.change.before | default({}) | ansible.utils.to_paths }}"
    after: "{{ item.change.after | default({}) | ansible.utils.to_paths }}"
  loop: "{{ plan_result.json_output.resource_changes }}"
  loop_control:
    label: "diff"
  when: plan_result.json_output.resource_changes is defined
# Task output:
# ------------
# --- before
# +++ after
# @@ -25,7 +25,7 @@
#     "id": "i-0417e9e07585b0962",
#     "instance_initiated_shutdown_behavior": "stop",
#     "instance_state": "running",
# -    "instance_type": "t3.large",
# +    "instance_type": "t3.micro",
#     "ipv6_address_count": 0,
#     "ipv6_addresses": [],
#     "key_name": "",
# @@ -64,10 +64,8 @@
#     "source_dest_check": true,
#     "subnet_id": "subnet-071443af7288cb251",
#     "tags.Name": "instance-check_2",
# -    "tags.architecture": "x86_64",
#     "tags.owner": "geet_2",
#     "tags_all.Name": "instance-check_2",
# -    "tags_all.architecture": "x86_64",
#     "tags_all.owner": "geet_2",
#     "tenancy": "default",
#     "timeouts": null,

- name: Display plan status and resource change count
  ansible.builtin.debug:
    msg: |
      Plan Status: {{ plan_result.metadata.data.attributes.status }}
      Resource Changes Count: {{ plan_result.json_output.resource_changes | length }}
# Task output:
# ------------
# "msg": "Plan Status: planned\nResource Changes Count: 2"

- name: Show resource changes summary
  ansible.builtin.debug:
    msg: |
      Changes:
        Additions: {{ plan_result.metadata.data.attributes.resource_additions | default(0) }}
        Changes: {{ plan_result.metadata.data.attributes.resource_changes | default(0) }}
        Deletions: {{ plan_result.metadata.data.attributes.resource_destructions | default(0) }}
# Task output:
# ------------
# "msg": "Changes:\n  Additions: 2\n  Changes: 1\n  Deletions: 0"
"""

RETURN = r"""
metadata:
  description: The metadata about the Terraform plan.
  returned: always
  type: dict
  contains:
    data:
      type: dict
      description: Plan metadata
      contains:
        id:
          type: str
          description: The plan ID
        type:
          type: str
          description: Resource type (always "plans")
        attributes:
          type: dict
          description: Plan attributes
          contains:
            status:
              type: str
              description: Current status of the plan
            has_changes:
              type: bool
              description: Whether the plan contains changes
            resource_additions:
              type: int
              description: Number of resources to be added
            resource_changes:
              type: int
              description: Number of resources to be changed
            resource_destructions:
              type: int
              description: Number of resources to be destroyed
json_output:
  description: The JSON output of the Terraform plan.
  returned: always
  type: dict
  contains:
    format_version:
      type: str
      description: Version of the plan output format.
    terraform_version:
      type: str
      description: Version of Terraform used to generate this plan.
    variables:
      type: dict
      description: Variables used in the plan.
    planned_values:
      type: dict
      description: Values that Terraform plans to apply.
    resource_drift:
      type: list
      description: List of detected drift in existing resources.
    resource_changes:
      type: list
      description: List of resource changes in the plan.
      elements: dict
      contains:
        address:
          type: str
          description: The resource address (e.g. `aws_instance.my_server`).
        mode:
          type: str
          description: The resource mode (e.g. managed).
        type:
          type: str
          description: The resource type (e.g. `aws_instance`).
        name:
          type: str
          description: The resource name.
        provider_name:
          type: str
          description: The name of the provider.
        change:
          type: dict
          description: Details of the change to this resource.
          contains:
            actions:
              type: list
              description: List of actions (e.g. `["create"]`, `["update"]`, `["delete"]`).
            before:
              type: dict
              description: The state of the resource before the change.
            after:
              type: dict
              description: The state of the resource after the change.
            after_unknown:
              type: dict
              description: Any attributes whose values are unknown until apply.
    output_changes:
      type: dict
      description: Any changes to output values.
    prior_state:
      type: dict
      description: The prior state before the plan.
    configuration:
      type: dict
      description: The configuration used for the plan.
    relevant_attributes:
      type: list
      description: Attributes relevant to the plan result.
    timestamp:
      type: str
      description: The timestamp when the plan was generated.
    applyable:
      type: bool
      description: Whether the plan is applyable.
    complete:
      type: bool
      description: Whether the plan is complete.
    errored:
      type: bool
      description: Whether the plan errored out.
plan_status:
  description: The current status of the plan
  returned: always
  type: str
changed:
  description: Indicates if the module execution resulted in any changes
  returned: always
  type: bool
"""

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    TerraformClient,
    TerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.plan_info import (
    get_plan_json_output,
    get_plan_metadata,
)


def main():
    module = TerraformModule(
        argument_spec=dict(
            plan_id=dict(type="str", aliases=["id"]),
            run_id=dict(type="str"),
        ),
        mutually_exclusive=[["plan_id", "run_id"]],
        supports_check_mode=True,
    )

    params = module.params
    plan_id = params.get("plan_id")
    run_id = params.get("run_id")

    # Validate that at least one identifier is provided
    if not plan_id and not run_id:
        module.fail_json(msg="Either plan_id or run_id must be provided.")

    result = {"changed": False}

    try:
        client = TerraformClient(**params)

        # Determine which ID is provided and get the data
        if plan_id:
            identifier = plan_id
            use_plan_id = True
        else:  # run_id is provided
            identifier = run_id
            use_plan_id = False

        # Use the module_utils functions to get plan information
        metadata_response = get_plan_metadata(client, identifier, use_plan_id)
        json_output_response = get_plan_json_output(client, identifier, use_plan_id)

        # Check if plan was found
        if not metadata_response:
            if use_plan_id:
                module.fail_json(msg=f"Plan with ID '{identifier}' was not found.")
            else:
                module.fail_json(msg=f"Plan for run with ID '{identifier}' was not found.")

        # Extract plan status from metadata
        plan_status = metadata_response.get("data", {}).get("attributes", {}).get("status", "unknown")

        result.update(
            {
                "metadata": metadata_response.get("data", {}),
                "json_output": json_output_response.get("data", {}),
                "plan_status": plan_status,
            },
        )

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
