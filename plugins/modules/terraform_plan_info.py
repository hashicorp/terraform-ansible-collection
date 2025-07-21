#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = """
module: terraform_plan_info
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

EXAMPLES = """
# Get plan information using plan ID
- name: Get plan info
  hashicorp.terraform.terraform_plan_info:
    plan_id: <your-plan_id>
    token: "{{ tf_token }}"
    hostname: "{{ tf_hostname }}"
  register: plan_result

# Get plan information using run ID
- name: Get plan info using run ID
  hashicorp.terraform.terraform_plan_info:
    run_id: <your-run_id>
    token: "{{ tf_token }}"
    hostname: "{{ tf_hostname }}"
  register: plan_result

# For drift analysis, use this task in the playbook:
- name: Test fact_diff with resource change
  ansible.utils.fact_diff:
    before: "{{ plan_result.json_output.resource_changes[0].change.before | default({}) | ansible.utils.to_paths }}"
    after: "{{ plan_result.json_output.resource_changes[0].change.after | default({}) | ansible.utils.to_paths }}"
  when: plan_result.json_output.resource_changes | length > 0

- name: Display what we got from the module
  ansible.builtin.debug:
    msg: |
      Plan Status: {{ plan_result.metadata.data.attributes.status }}
      Resource Changes Count: {{ plan_result.json_output.resource_changes | length }}

- name: Show resource changes summary
  ansible.builtin.debug:
    msg: |
      Changes:
        Additions: {{ plan_result.metadata.data.attributes.resource_additions | default(0) }}
        Changes: {{ plan_result.metadata.data.attributes.resource_changes | default(0) }}
        Deletions: {{ plan_result.metadata.data.attributes.resource_destructions | default(0) }}
"""

RETURN = """
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
fact_diff_result:
  description: Drift analysis of the plan changes
  returned: when the playbook with fact_diff task is used
  type: dict
  contains:
    summary:
      description: Summary of changes
      type: str
    plan_status:
      description: The status of the plan
      type: str
"""

from typing import Any, Dict

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    TerraformClient,
    TerraformModule,
)


def get_plan_metadata(
    client: TerraformClient,
    identifier: str,
    use_plan_id: bool,
) -> Dict[str, Any]:
    """
    Retrieve plan metadata from Terraform API.

    Args:
        client: Authenticated Terraform API client
        identifier: Either plan_id or run_id
        use_plan_id: True if identifier is plan_id, False if it's run_id

    Returns:
        Dict containing plan metadata response

    Raises:
        Exception: If API request fails
    """
    if use_plan_id:
        path = f"/plans/{identifier}"
    else:
        path = f"/runs/{identifier}/plan"

    response = client.get(path)
    return response


def get_plan_json_output(
    client: TerraformClient,
    identifier: str,
    use_plan_id: bool,
) -> Dict[str, Any]:
    """
    Retrieve plan JSON output from Terraform API.

    Args:
        client: Authenticated Terraform API client
        identifier: Either plan_id or run_id
        use_plan_id: True if identifier is plan_id, False if it's run_id

    Returns:
        Dict containing plan JSON output response

    Raises:
        Exception: If API request fails
    """
    if use_plan_id:
        path = f"/plans/{identifier}/json-output"
    else:
        path = f"/runs/{identifier}/plan/json-output"

    response = client.get(path)
    return response


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

    result = {}

    try:
        client = TerraformClient(**params)

        # Determine which ID is provided and get the data
        if plan_id:
            identifier = plan_id
            use_plan_id = True
        else:  # run_id is provided
            identifier = run_id
            use_plan_id = False

        metadata_response = get_plan_metadata(client, identifier, use_plan_id)
        json_output_response = get_plan_json_output(client, identifier, use_plan_id)

        plan_status = (
            metadata_response.get("data", {})
            .get("data", {})
            .get("attributes", {})
            .get("status", "unknown")
        )

        result.update(
            {
                "metadata": metadata_response.get("data", {}),
                "json_output": json_output_response.get("data", {}),
                "plan_status": plan_status,
            },
        )

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=f"Failed to retrieve plan information: {str(e)}")


if __name__ == "__main__":
    main()
