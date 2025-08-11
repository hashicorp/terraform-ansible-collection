# 273 lines wala
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
module: view_plan
version_added: "1.0.0"
short_description: View Terraform Cloud/Enterprise plan information in different formats
author: "Tanwi Geetika (@tgeetika)"
description:
  - View information about a Terraform execution plan from HashiCorp Terraform Cloud or Terraform Enterprise.
  - Can return plan information in raw format or as a diff-formatted output (default).
  - Supports both Terraform Cloud and Terraform Enterprise deployments.
  - Plan information can be retrieved using either a plan ID or a run ID.
  - By default, returns diff-formatted output similar to 'terraform plan' CLI command.
  - Can optionally return raw plan information including metadata and JSON output.
  - Automatically masks sensitive values in diff output with descriptive messages.
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
  output_format:
    description:
      - Format for the module output.
      - 'diff' (default) returns a diff-formatted output similar to terraform plan CLI.
      - 'raw' returns the raw plan information including metadata and JSON output.
    type: str
    choices: ['diff', 'raw']
    default: 'diff'
extends_documentation_fragment:
  - hashicorp.terraform.common
"""

EXAMPLES = r"""
# Get plan information in diff format (default)
- name: View plan diff by plan ID
  hashicorp.terraform.view_plan:
    plan_id: <your-plan-id>
    token: "{{ tf_token }}"
    hostname: "{{ tf_hostname }}"
  register: plan_result

- name: View plan diff by run ID
  hashicorp.terraform.view_plan:
    run_id: <your-run-id>
    token: "{{ tf_token }}"
    hostname: "{{ tf_hostname }}"
    output_format: diff
  register: plan_result

# Get raw plan information
- name: Get raw plan information by plan ID
  hashicorp.terraform.view_plan:
    plan_id: <your-plan-id>
    token: "{{ tf_token }}"
    hostname: "{{ tf_hostname }}"
    output_format: raw
  register: plan_result

# Display diff results
- name: Display plan changes summary
  ansible.builtin.debug:
    msg: |
      Plan has changes: {{ plan_result.changed }}
      Resource changes: {{ plan_result.diff | length }}
  when: plan_result.output_format == 'diff'
"""

RETURN = r"""
output_format:
  description: The format used for the output
  returned: always
  type: str
changed:
  description: Indicates if the plan has any changes (only meaningful in diff format)
  returned: always
  type: bool
diff:
  description: Diff-formatted changes (when output_format is 'diff')
  returned: when output_format is 'diff'
  type: list
  elements: dict
  contains:
    before:
      description: Resource state before changes
      type: dict
    after:
      description: Resource state after changes
      type: dict
metadata:
  description: The metadata about the Terraform plan (when output_format is 'raw')
  returned: when output_format is 'raw'
  type: dict
json_output:
  description: The JSON output of the Terraform plan (when output_format is 'raw')
  returned: when output_format is 'raw'
  type: dict
"""

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.plan import (
    get_plan_json_output,
    get_plan_metadata,
)


def _mask_sensitive_value(value, is_sensitive, is_before=True):
    """Apply descriptive sensitivity masking."""
    if is_sensitive:
        return "<sensitive> changed from" if is_before else "<sensitive> changed to"
    return value


def _mask_object_values(obj, sensitive_flags, is_before=True):
    """
    Recursively applies sensitivity masking to an object.
    Supports nested dictionaries and lists of dictionaries.
    """
    if isinstance(obj, dict) and isinstance(sensitive_flags, dict):
        masked_obj = {}
        for key, value in obj.items():
            sensitive_flag = sensitive_flags.get(key, False)

            if isinstance(value, dict) and isinstance(sensitive_flag, dict):
                masked_obj[key] = _mask_object_values(value, sensitive_flag, is_before)
            elif isinstance(value, list):
                masked_obj[key] = [_mask_object_values(v, sensitive_flag if isinstance(sensitive_flag, dict) else {}, is_before) for v in value]
            else:
                is_sensitive = sensitive_flag is True
                masked_obj[key] = _mask_sensitive_value(value, is_sensitive, is_before)
        return masked_obj

    elif isinstance(obj, list):
        return [_mask_object_values(item, {}, is_before) for item in obj]

    else:
        return obj


def _get_diff_sequences(json_output_data):
    """Extract diff sequences from plan data - simplified approach."""
    diffs = []

    # Process resource changes and resource drift
    for change_type in ["resource_changes", "resource_drift"]:
        for item in json_output_data.get(change_type, []):
            # Skip no-op actions - no changes to show
            if "no-op" in item.get("actions", []):
                continue

            change = item.get("change", {})
            before = change.get("before", {})
            after = change.get("after", {})
            before_sensitive = change.get("before_sensitive", {})
            after_sensitive = change.get("after_sensitive", {})

            # Apply sensitivity masking
            masked_before = _mask_object_values(before, before_sensitive, is_before=True)
            masked_after = _mask_object_values(after, after_sensitive, is_before=False)

            # Only add if there are actual differences
            if masked_before != masked_after:
                diffs.append({"before": masked_before, "after": masked_after})

    # Process output changes
    for output_name, change in json_output_data.get("output_changes", {}).items():
        # Skip no-op actions
        if "no-op" in change.get("actions", []):
            continue

        before = change.get("before")
        after = change.get("after")
        before_sensitive = change.get("before_sensitive", False)
        after_sensitive = change.get("after_sensitive", False)

        # Only show outputs that actually changed
        if before != after:
            # Apply descriptive masking to output values
            before_val = _mask_sensitive_value(before, before_sensitive, is_before=True)
            after_val = _mask_sensitive_value(after, after_sensitive, is_before=False)

            diff_entry = {"before": {}, "after": {output_name: after_val}}
            if before is not None:
                diff_entry["before"][output_name] = before_val

            diffs.append(diff_entry)

    return diffs


def main():
    module = AnsibleTerraformModule(
        argument_spec=dict(
            plan_id=dict(type="str", aliases=["id"]),
            run_id=dict(type="str"),
            output_format=dict(type="str", choices=["diff", "raw"], default="diff"),
        ),
        mutually_exclusive=[["plan_id", "run_id"]],
        required_one_of=[["plan_id", "run_id"]],
        supports_check_mode=True,
    )

    params = module.params
    plan_id = params.get("plan_id")
    run_id = params.get("run_id")
    output_format = params.get("output_format")

    result = {"changed": False, "output_format": output_format}

    try:
        client = TerraformClient(**params)

        # Determine which ID is provided
        if plan_id:
            identifier = plan_id
            use_plan_id = True
        else:  # run_id is provided
            identifier = run_id
            use_plan_id = False

        # Get plan information
        metadata_response = get_plan_metadata(client, identifier, use_plan_id)
        json_output_response = get_plan_json_output(client, identifier, use_plan_id)

        # Check if plan was found
        if not metadata_response:
            if use_plan_id:
                raise ValueError(f"Plan with ID '{identifier}' was not found.")
            else:
                raise ValueError(f"Plan for run with ID '{identifier}' was not found.")

        if output_format == "raw":
            # Return raw format - metadata and json_output as-is
            result.update(
                {
                    "metadata": metadata_response.get("data", {}),
                    "json_output": json_output_response.get("data", {}),
                },
            )
        else:  # output_format == "diff" (default)
            # Return diff format
            json_output_data = json_output_response.get("data", {})
            diff_sequences = _get_diff_sequences(json_output_data)

            result["diff"] = diff_sequences

            # Set changed=True if there are any changes in the diff
            if diff_sequences:
                result["changed"] = True

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
