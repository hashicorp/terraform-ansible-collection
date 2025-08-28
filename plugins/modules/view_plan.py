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
  - Provides resource context at before_header and after_header in the output for better understanding of changes.
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
msg:
  description: Informational message when no changes are detected
  returned: when no changes are found in diff format
  type: str
"""

from typing import Any, Dict, List, Optional, Union

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    TerraformClient,
    TerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.plan import (
    get_plan_json_output,
    get_plan_metadata,
)


# Action mapping constants
ACTION_MAPPING = {
    "create": "created",
    "update": "updated",
    "delete": "destroyed",
    "read": "read",
}

REPLACEMENT_ACTIONS = [["delete", "create"], ["create", "delete"]]
SENSITIVE_MASK = "<sensitive>"


def _mask_sensitive_object(
    obj: Union[Dict, List, Any],
    sensitive_flags: Union[Dict, bool],
    replacement_text: str = SENSITIVE_MASK,
) -> Union[Dict, List, str]:
    """Apply masking to sensitive values in an object based on sensitivity flags.

    Args:
        obj: The object (dict/list) to mask sensitive values in
        sensitive_flags: Dictionary/structure indicating which values are sensitive
        replacement_text: Text to replace sensitive values with

    Returns:
        Object with sensitive values replaced by replacement_text
    """
    if isinstance(obj, dict) and isinstance(sensitive_flags, dict):
        return {
            key: (
                _mask_sensitive_object(value, sensitive_flags.get(key, {}), replacement_text)
                if isinstance(value, (dict, list)) and isinstance(sensitive_flags.get(key), dict)
                else replacement_text if sensitive_flags.get(key) is True else value
            )
            for key, value in obj.items()
        }
    elif isinstance(obj, list):
        return [_mask_sensitive_object(item, {}, replacement_text) for item in obj]
    return obj


def _get_change_indicator_text(before_raw_item, after_raw_item, is_sensitive_before, is_sensitive_after):
    """Get appropriate text for sensitive value changes."""
    if not (is_sensitive_before or is_sensitive_after):
        return None, None

    if before_raw_item != after_raw_item:
        return "<sensitive> changed from", "<sensitive> changed to"
    return SENSITIVE_MASK, SENSITIVE_MASK


def _process_sensitive_value_update(
    key,
    all_keys,
    before_obj,
    after_obj,
    before_sensitive,
    after_sensitive,
    before_raw,
    after_raw,
    result_before,
    result_after,
):
    """Process a single key for sensitive value updates."""
    before_item = before_obj.get(key)
    after_item = after_obj.get(key)
    before_sens = before_sensitive.get(key, False) if isinstance(before_sensitive, dict) else False
    after_sens = after_sensitive.get(key, False) if isinstance(after_sensitive, dict) else False
    before_raw_item = before_raw.get(key) if isinstance(before_raw, dict) else None
    after_raw_item = after_raw.get(key) if isinstance(after_raw, dict) else None

    if isinstance(before_item, dict) or isinstance(after_item, dict):
        updated_before, updated_after = _update_changed_sensitive_values(
            before_item or {},
            after_item or {},
            before_sens,
            after_sens,
            before_raw_item or {},
            after_raw_item or {},
        )
        if key in before_obj:
            result_before[key] = updated_before
        if key in after_obj:
            result_after[key] = updated_after
    else:
        before_text, after_text = _get_change_indicator_text(
            before_raw_item,
            after_raw_item,
            before_sens is True,
            after_sens is True,
        )

        if before_text is not None:
            if key in before_obj:
                result_before[key] = before_text
            if key in after_obj:
                result_after[key] = after_text
        else:
            if key in before_obj:
                result_before[key] = before_item
            if key in after_obj:
                result_after[key] = after_item


def _update_changed_sensitive_values(
    before_obj: Dict,
    after_obj: Dict,
    before_sensitive,
    after_sensitive,
    before_raw: Dict,
    after_raw: Dict,
) -> tuple:
    """Update masked values to show change indicators for sensitive values that actually changed.

    Args:
        before_obj: Masked before object
        after_obj: Masked after object
        before_sensitive: Sensitivity flags for before object
        after_sensitive: Sensitivity flags for after object
        before_raw: Original unmasked before object
        after_raw: Original unmasked after object

    Returns:
        tuple: (updated_before_obj, updated_after_obj) with change indicators
    """
    if not isinstance(before_obj, dict) or not isinstance(after_obj, dict):
        return before_obj, after_obj

    result_before, result_after = {}, {}
    all_keys = set(before_obj.keys()) | set(after_obj.keys())

    for key in all_keys:
        _process_sensitive_value_update(
            key,
            all_keys,
            before_obj,
            after_obj,
            before_sensitive,
            after_sensitive,
            before_raw,
            after_raw,
            result_before,
            result_after,
        )

    return result_before, result_after


def _mask_sensitive_values_in_objects(
    before_obj: Dict,
    after_obj: Dict,
    before_sensitive,
    after_sensitive,
):
    """Apply sensitivity masking to both before and after objects, preserving unchanged sensitive values.

    Args:
        before_obj: Object representing state before changes
        after_obj: Object representing state after changes
        before_sensitive: Sensitivity flags for before object
        after_sensitive: Sensitivity flags for after object

    Returns:
        tuple: (masked_before, masked_after) with sensitive values appropriately masked
    """
    masked_before = _mask_sensitive_object(before_obj, before_sensitive)
    masked_after = _mask_sensitive_object(after_obj, after_sensitive)

    return _update_changed_sensitive_values(
        masked_before,
        masked_after,
        before_sensitive,
        after_sensitive,
        before_obj,
        after_obj,
    )


def _action_to_str(actions: List[str]) -> str:
    """Convert action list to a better-readable string.

    Args:
        actions: List of Terraform actions (e.g., ['create'], ['delete', 'create'])

    Returns:
        str: Better-readable action description (e.g., 'created', 'replaced', 'updated')
    """
    if not actions:
        return "no-op"

    if len(actions) == 1:
        return ACTION_MAPPING.get(actions[0], actions[0])

    if actions in REPLACEMENT_ACTIONS or set(actions) == {"delete", "create"}:
        return "replaced"

    actions_set = set(actions)
    if "update" in actions_set:
        return "updated" if len(actions_set) == 1 else f"updated ({', '.join(sorted(actions_set))})"

    mapped_actions = [ACTION_MAPPING.get(action, action) for action in actions]
    return " + ".join(mapped_actions)


def _process_resource_changes(
    resource_changes: List[Dict],
    resource_drift: List[Dict],
) -> List[Dict]:
    """Process and unify resource changes with drift data.

    Args:
        resource_changes: List of resource changes from Terraform plan
        resource_drift: List of resource drift data from Terraform plan

    Returns:
        list: Unified resource data with both changes and drift information
    """
    changes_by_address = {item.get("address", ""): item for item in resource_changes}
    drift_by_address = {item.get("address", ""): item for item in resource_drift}

    unified_resources = []

    # Process resources with changes
    for address, changes_item in changes_by_address.items():
        drift_item = drift_by_address.pop(address, None)
        unified_resources.append(
            {
                "address": address,
                "resource_changes": changes_item,
                "resource_drift": drift_item,
                "has_drift": drift_item is not None,
            },
        )

    # Process remaining drift-only resources
    for address, drift_item in drift_by_address.items():
        unified_resources.append(
            {
                "address": address,
                "resource_changes": None,
                "resource_drift": drift_item,
                "has_drift": True,
            },
        )

    return unified_resources


def _determine_primary_item_and_scenario(resource_data: Dict):
    """Determine the primary item and scenario type for diff processing."""
    changes_item = resource_data["resource_changes"]
    drift_item = resource_data["resource_drift"]
    has_drift = resource_data["has_drift"]

    if changes_item:
        changes_actions = changes_item.get("change", {}).get("actions", [])
        if changes_actions and "no-op" not in changes_actions:
            return changes_item, "changes_with_actions"
        elif has_drift and drift_item:
            drift_actions = drift_item.get("change", {}).get("actions", [])
            if drift_actions and "no-op" not in drift_actions:
                return drift_item, "drift_only"
    elif drift_item:
        drift_actions = drift_item.get("change", {}).get("actions", [])
        if drift_actions and "no-op" not in drift_actions:
            return drift_item, "drift_only"

    return None, None


def _create_diff_headers(scenario_type, address, resource_id, action_type, has_drift, drift_item):
    """Create appropriate headers for diff entry based on scenario."""
    id_part = f" (ID={resource_id})" if resource_id else ""
    diff_entry = {}

    if scenario_type == "drift_only":
        diff_entry["before_header"] = f"Resource changed outside Terraform ({action_type})."
        diff_entry["after_header"] = f"{address}{id_part}: Drift detected\n No Planned changes to apply for this resource."
    elif has_drift and drift_item:
        drift_actions = drift_item.get("change", {}).get("actions", [])
        drift_action_type = _action_to_str(drift_actions)
        diff_entry["before_header"] = f"Resource changed outside Terraform ({drift_action_type})."
        diff_entry["after_header"] = f"{address}{id_part} will be {action_type}\n Changes to apply."
    else:
        diff_entry["after_header"] = f"{address}{id_part} will be {action_type}\n Changes to apply."

    return diff_entry


def _create_diff_entry(resource_data: Dict) -> Optional[Dict]:
    """Create a diff entry for a resource.

    Args:
        resource_data: Dictionary containing unified resource change and drift information

    Returns:
        dict or None: Diff entry with before/after states and headers, or None if no changes
    """
    address = resource_data["address"]
    has_drift = resource_data["has_drift"]
    drift_item = resource_data["resource_drift"]

    # Determine primary item and scenario
    primary_item, scenario_type = _determine_primary_item_and_scenario(resource_data)

    if not primary_item:
        return None

    # Extract change information
    change = primary_item.get("change", {})
    before = change.get("before", {})
    after = change.get("after", {})
    before_sensitive = change.get("before_sensitive", {})
    after_sensitive = change.get("after_sensitive", {})

    # Apply sensitivity masking
    masked_before, masked_after = _mask_sensitive_values_in_objects(
        before,
        after,
        before_sensitive,
        after_sensitive,
    )

    if masked_before == masked_after:
        return None

    actions_list = change.get("actions", [])
    action_type = _action_to_str(actions_list)
    resource_id = str((before or after or {}).get("id", ""))

    diff_entry = {
        "before": masked_before,
        "after": masked_after,
    }

    # Create headers
    headers = _create_diff_headers(scenario_type, address, resource_id, action_type, has_drift, drift_item)
    diff_entry.update(headers)

    return diff_entry


def _process_single_output_change(output_name, change):
    """Process a single output change and return diff entry if changed."""
    if "no-op" in change.get("actions", []):
        return None

    before = change.get("before")
    after = change.get("after")

    if before == after:
        return None

    before_sensitive = change.get("before_sensitive", False)
    after_sensitive = change.get("after_sensitive", False)

    # Handle sensitive outputs
    if before_sensitive or after_sensitive:
        before_val = "<sensitive> changed from" if before_sensitive else before
        after_val = "<sensitive> changed to" if after_sensitive else after
    else:
        before_val = before
        after_val = after

    diff_entry = {"before": {}, "after": {output_name: after_val}}
    if before is not None:
        diff_entry["before"][output_name] = before_val

    return diff_entry


def _process_output_changes(output_changes: Dict) -> List[Dict]:
    """Process output changes and return diff entries.

    Args:
        output_changes: Dictionary of Terraform output changes

    Returns:
        list: List of diff entries for changed outputs
    """
    diffs = []

    for output_name, change in output_changes.items():
        diff_entry = _process_single_output_change(output_name, change)
        if diff_entry:
            diffs.append(diff_entry)

    return diffs


def _get_diff_sequences(json_output_data: Dict) -> List[Dict]:
    """Extract diff sequences from plan data using unified resource processing.

    Args:
        json_output_data: The JSON output data from Terraform plan

    Returns:
        list: List of diff entries showing all changes in the plan
    """
    resource_changes = json_output_data.get("resource_changes", [])
    resource_drift = json_output_data.get("resource_drift", [])
    output_changes = json_output_data.get("output_changes", {})

    diffs = []

    # Process resource changes
    unified_resources = _process_resource_changes(resource_changes, resource_drift)

    for resource_data in unified_resources:
        diff_entry = _create_diff_entry(resource_data)
        if diff_entry:
            diffs.append(diff_entry)

    # Process output changes
    output_diffs = _process_output_changes(output_changes)
    diffs.extend(output_diffs)

    return diffs


def main() -> None:
    module = TerraformModule(
        argument_spec={
            "plan_id": {"type": "str", "aliases": ["id"]},
            "run_id": {"type": "str"},
            "output_format": {"type": "str", "choices": ["diff", "raw"], "default": "diff"},
        },
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
        identifier = plan_id if plan_id else run_id
        use_plan_id = plan_id is not None

        # Get plan information
        metadata_response = get_plan_metadata(client, identifier, use_plan_id)
        json_output_response = get_plan_json_output(client, identifier, use_plan_id)

        # Check if plan was found
        if not metadata_response:
            id_type = "Plan" if use_plan_id else "Plan for run"
            module.fail_json(msg=f"{id_type} with ID '{identifier}' was not found.")

        if output_format == "raw":
            # Return raw format
            result.update(
                {
                    "metadata": metadata_response.get("data", {}),
                    "json_output": json_output_response.get("data", {}),
                },
            )
        else:
            # Return diff format
            json_output_data = json_output_response.get("data", {})
            diff_sequences = _get_diff_sequences(json_output_data)
            result["diff"] = diff_sequences

            if diff_sequences:
                result["changed"] = True
            else:
                result["msg"] = "No changes. Your infrastructure matches the configuration."

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
