# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: view_plan
version_added: "1.1.0"
short_description: View Terraform Cloud/Enterprise plan information
author: "Tanwi Geetika (@tgeetika)"
description:
  - View information about a Terraform execution plan from HashiCorp Terraform Cloud or Terraform Enterprise.
  - Can return plan information in JSON format or as a diff-formatted output (default).
  - Supports both Terraform Cloud and Terraform Enterprise deployments.
  - Plan information can be retrieved using either a plan ID or a run ID.
  - By default, returns diff-formatted output similar to the C(terraform plan) CLI command.
  - Optionally return JSON plan information including metadata and JSON output.
  - Automatically masks sensitive values in diff output with descriptive messages.
  - Provides resource context at before_header and after_header in the output for better understanding of changes.
options:
  plan_id:
    description:
      - The ID of the plan to retrieve information for.
      - Plan IDs can be found in the C(relationships.plan) property of a run object.
      - When provided, the module will use the C(/plans/:id) endpoint.
      - Mutually exclusive with run_id.
    type: str
    aliases: ['id']
  run_id:
    description:
      - The ID of the run whose plan information should be retrieved.
      - When provided, the module will use the C(/runs/:id/plan) endpoint.
      - Mutually exclusive with plan_id.
    type: str
  output_format:
    description:
      - Format for the module output.
      - C(diff) (default) returns a diff-formatted output similar to C(terraform plan).
      - C(json) returns the JSON plan information including metadata and JSON output.
    type: str
    choices: ['diff', 'json']
    default: diff
extends_documentation_fragment:
  - hashicorp.terraform.common
"""

EXAMPLES = r"""
# Get plan information in diff format (default)
- name: View plan diff by plan ID
  hashicorp.terraform.view_plan:
    plan_id: plan-ZRJZNANFgoYhx3Ch
  register: plan_result

- name: View plan diff by run ID
  hashicorp.terraform.view_plan:
    run_id: run-FDuANSTFnnDowa3C
    output_format: diff
  register: plan_result

# Task output:
# ------------
# --- before
# +++ after: aws_instance.new_server will be created
#  Changes to apply.
# @@ -0,0 +1,14 @@
# +{
# +    "ami": "ami-07b0c09aab6e66ee9",
# +    "credit_specification": [],
# +    "get_password_data": false,
# +    "hibernation": null,
# +    "instance_type": "t2.micro",
# +    "launch_template": [],
# +    "source_dest_check": true,
# +    "tags": null,
# +    "timeouts": null,
# +    "user_data": "<sensitive>",
# +    "user_data_replace_on_change": false,
# +    "volume_tags": null
# +}

# Get json plan information
- name: Get json plan information by plan ID
  hashicorp.terraform.view_plan:
    plan_id: plan-ZYSSTANWIoYhx3Ch
    output_format: json
  register: plan_result

# Task output:
# ------------
# {
#     "changed": false,
#     "failed": false,
#     "json_output": {
#         "format_version": "1.1",
#         "terraform_version": "1.5.0",
#         "resource_changes": [
#             {
#                 "address": "aws_instance.example",
#                 "mode": "managed",
#                 "type": "aws_instance",
#                 "name": "example",
#                 "change": {
#                     "actions": ["create"],
#                     "before": null,
#                     "after": {
#                         "ami": "ami-0c02fb55956c7d316",
#                         "instance_type": "t2.micro"
#                     }
#                 }
#             }
#         ]
#     },
#     "metadata": {
#         "id": "plan-ZYSSTANWIoYhx3Ch",
#         "type": "plans",
#         "attributes": {
#             "has-changes": true,
#             "status": "finished",
#             "log-read-url": "https://app.terraform.io/api/v2/plans/.../logs"
#         }
#     },
# }

# Display diff results
- name: Display plan changes summary
  ansible.builtin.debug:
    msg: |
      Plan has changes: {{ plan_diff_result.changed }}
  when: plan_diff_result is defined

# Task output:
# ------------
# {
#     "msg": "Plan has changes"
# }

# Handle case where plan doesn't exist
- name: Try to view non-existent plan
  hashicorp.terraform.view_plan:
    plan_id: plan-NonExistentPlan123
  register: plan_result
  failed_when: false

# Task output:
# ------------
# {
#     "changed": false,
#     "msg": "Plan with ID 'plan-NonExistentPlan123' was not found.",
# }
"""

RETURN = r"""
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
  description: The metadata about the Terraform plan (when output_format is 'json')
  returned: when output_format is 'json'
  type: dict
json_output:
  description: The JSON output of the Terraform plan (when output_format is 'json')
  returned: when output_format is 'json'
  type: dict
msg:
  description: Informational message when no changes are detected
  returned: when no changes are found in diff format
  type: str
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Dict, List, Optional, Tuple, Union

from copy import deepcopy

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.plan import (
    SensitiveValueData,
    ViewPlanResourceData,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.plan import (
    get_plan_data,
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
    data: Union[Dict[str, Any], List[Any]],
    sensitive_flags: Union[Dict[str, Any], bool],
    replacement_text: str = SENSITIVE_MASK,
) -> Union[Dict[str, Any], List[Any]]:
    """Apply masking to sensitive values in an object based on sensitivity flags.

    Args:
        data: The object (dict/list) to mask sensitive values in
        sensitive_flags: Dictionary/structure indicating which values are sensitive
        replacement_text: Text to replace sensitive values with

    Returns:
        Object with sensitive values replaced by replacement_text
    """
    if isinstance(data, dict) and isinstance(sensitive_flags, dict):
        return {
            key: (
                _mask_sensitive_object(value, sensitive_flags.get(key, {}), replacement_text)
                if isinstance(value, (dict, list)) and isinstance(sensitive_flags.get(key, None), dict)
                else replacement_text if sensitive_flags.get(key, None) is True else value
            )
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [_mask_sensitive_object(item, {}, replacement_text) for item in data]
    return data


def _get_change_indicator_text(
    before_raw_item: Any,
    after_raw_item: Any,
    is_sensitive_before: bool,
    is_sensitive_after: bool,
) -> Tuple[Optional[str], Optional[str]]:
    """Get appropriate text for sensitive value changes."""
    if not (is_sensitive_before or is_sensitive_after):
        return None, None

    if before_raw_item != after_raw_item:
        return "<sensitive> changed from", "<sensitive> changed to"

    return SENSITIVE_MASK, SENSITIVE_MASK


def _assign_value_if_key_exists(source_dict: Dict, target_dict: Dict, key: str, value: Any) -> None:
    """Assign value to target dict if key exists in source dict."""
    if key in source_dict:
        target_dict[key] = value


def _extract_sensitive_value_data(
    key: str,
    before_obj: Dict,
    after_obj: Dict,
    before_sensitive: Union[Dict, bool],
    after_sensitive: Union[Dict, bool],
    before_raw: Dict,
    after_raw: Dict,
) -> SensitiveValueData:
    """Extract all necessary data for processing a sensitive value."""
    before_item = before_obj.get(key, None)
    after_item = after_obj.get(key, None)
    is_before_sensitive = before_sensitive.get(key, False) if isinstance(before_sensitive, dict) else False
    is_after_sensitive = after_sensitive.get(key, False) if isinstance(after_sensitive, dict) else False
    before_raw_item = before_raw.get(key, None) if isinstance(before_raw, dict) else None
    after_raw_item = after_raw.get(key, None) if isinstance(after_raw, dict) else None

    return SensitiveValueData(
        before_item=before_item,
        after_item=after_item,
        is_before_sensitive=is_before_sensitive,
        is_after_sensitive=is_after_sensitive,
        before_raw_item=before_raw_item,
        after_raw_item=after_raw_item,
    )


def _process_dict_sensitive_values(
    key: str,
    sensitive_data: SensitiveValueData,
    result_before: Dict,
    result_after: Dict,
    before_obj: Dict,
    after_obj: Dict,
) -> None:
    """Process dictionary-type sensitive values."""
    updated_before, updated_after = _update_changed_sensitive_values(
        sensitive_data.before_item or {},
        sensitive_data.after_item or {},
        sensitive_data.is_before_sensitive,
        sensitive_data.is_after_sensitive,
        sensitive_data.before_raw_item or {},
        sensitive_data.after_raw_item or {},
    )

    _assign_value_if_key_exists(before_obj, result_before, key, updated_before)
    _assign_value_if_key_exists(after_obj, result_after, key, updated_after)


def _process_scalar_sensitive_values(
    key: str,
    sensitive_data: SensitiveValueData,
    result_before: Dict,
    result_after: Dict,
    before_obj: Dict,
    after_obj: Dict,
) -> None:
    """Process scalar-type sensitive values."""
    before_text, after_text = _get_change_indicator_text(
        sensitive_data.before_raw_item,
        sensitive_data.after_raw_item,
        sensitive_data.is_before_sensitive,
        sensitive_data.is_after_sensitive,
    )

    if before_text is not None:
        _assign_value_if_key_exists(before_obj, result_before, key, before_text)
        _assign_value_if_key_exists(after_obj, result_after, key, after_text)
    else:
        _assign_value_if_key_exists(before_obj, result_before, key, sensitive_data.before_item)
        _assign_value_if_key_exists(after_obj, result_after, key, sensitive_data.after_item)


def _process_sensitive_value_update(
    key: str,
    before_obj: Dict,
    after_obj: Dict,
    before_sensitive: Union[Dict, bool],
    after_sensitive: Union[Dict, bool],
    before_raw: Dict,
    after_raw: Dict,
    result_before: Dict,
    result_after: Dict,
) -> None:
    """Process a single key for sensitive value updates."""
    sensitive_data = _extract_sensitive_value_data(
        key,
        before_obj,
        after_obj,
        before_sensitive,
        after_sensitive,
        before_raw,
        after_raw,
    )

    # Check if we're dealing with dictionary values
    if isinstance(sensitive_data.before_item, dict) or isinstance(sensitive_data.after_item, dict):
        _process_dict_sensitive_values(key, sensitive_data, result_before, result_after, before_obj, after_obj)
    else:
        _process_scalar_sensitive_values(key, sensitive_data, result_before, result_after, before_obj, after_obj)


def _update_changed_sensitive_values(
    before_obj: Dict,
    after_obj: Dict,
    before_sensitive: Union[Dict, bool],
    after_sensitive: Union[Dict, bool],
    before_raw: Dict,
    after_raw: Dict,
) -> Tuple[Dict, Dict]:
    """Update masked values to show change indicators for sensitive values that actually changed.

    Args:
        before_obj: Masked before object
        after_obj: Masked after object
        before_sensitive: Sensitivity flags for before object
        after_sensitive: Sensitivity flags for after object
        before_raw: Original unmasked before object
        after_raw: Original unmasked after object

    Returns:
        Tuple: (updated_before_obj, updated_after_obj) with change indicators
    """
    if not isinstance(before_obj, dict) or not isinstance(after_obj, dict):
        return before_obj, after_obj

    result_before, result_after = {}, {}
    all_keys = set(before_obj.keys()) | set(after_obj.keys())

    for key in all_keys:
        _process_sensitive_value_update(
            key,
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
    before_sensitive: Union[Dict, bool],
    after_sensitive: Union[Dict, bool],
) -> Tuple[Dict, Dict]:
    """Apply sensitivity masking to both before and after objects, preserving unchanged sensitive values.

    Args:
        before_obj: Object representing state before changes
        after_obj: Object representing state after changes
        before_sensitive: Sensitivity flags for before object
        after_sensitive: Sensitivity flags for after object

    Returns:
        Tuple: (masked_before, masked_after) with sensitive values appropriately masked
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


def _convert_actions_to_readable_string(actions: List[str]) -> str:
    """Convert action list to a human-readable string.

    Args:
        actions: List of Terraform actions (e.g., ['create'], ['delete', 'create'])

    Returns:
        str: Human-readable action description (e.g., 'created', 'replaced', 'updated')
    """
    if not actions:
        return "no-op"

    if len(actions) == 1:
        return ACTION_MAPPING.get(actions[0], actions[0])

    actions_set = set(actions)

    if actions in REPLACEMENT_ACTIONS or actions_set == {"delete", "create"}:
        return "replaced"

    if "update" in actions_set:
        if len(actions_set) == 1:
            return "updated"
        return f"updated ({', '.join(sorted(actions_set))})"

    mapped_actions = [ACTION_MAPPING.get(action, action) for action in actions]
    return " + ".join(mapped_actions)


def _create_unified_resources(
    resource_changes: List[Dict],
    resource_drift: List[Dict],
) -> List[ViewPlanResourceData]:
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

    for address in set(changes_by_address) | set(drift_by_address):
        unified_resources.append(
            ViewPlanResourceData(
                address=address,
                resource_changes=changes_by_address.get(address),
                resource_drift=drift_by_address.get(address),
                has_drift=address in drift_by_address,
            ),
        )

    return unified_resources


def _determine_primary_item_and_scenario(resource_data: ViewPlanResourceData) -> Tuple[Optional[Dict], Optional[str]]:
    """Determine the primary item and scenario type for diff processing."""
    changes_item = resource_data.resource_changes
    drift_item = resource_data.resource_drift

    if changes_item:
        changes_actions = changes_item.get("change", {}).get("actions", [])
        if changes_actions and "no-op" not in changes_actions:
            return changes_item, "changes_with_actions"

    if resource_data.has_drift and drift_item:
        drift_actions = drift_item.get("change", {}).get("actions", [])
        if drift_actions and "no-op" not in drift_actions:
            return drift_item, "drift_only"

    return None, None


def _create_diff_headers(
    scenario_type: str,
    address: str,
    resource_id: str,
    action_type: str,
    has_drift: bool,
    drift_item: Optional[Dict],
) -> Dict[str, str]:
    """Create appropriate headers for diff entry based on scenario."""
    id_part = f" (ID={resource_id})" if resource_id else ""
    headers = {}

    if scenario_type == "drift_only":
        headers["before_header"] = f"Resource changed outside Terraform ({action_type})."
        headers["after_header"] = f"{address}{id_part}: Drift detected\n No Planned changes to apply for this resource."
    elif has_drift and drift_item:
        drift_actions = drift_item.get("change", {}).get("actions", [])
        drift_action_type = _convert_actions_to_readable_string(drift_actions)
        headers["before_header"] = f"Resource changed outside Terraform ({drift_action_type})."
        headers["after_header"] = f"{address}{id_part} will be {action_type}\n Changes to apply."
    else:
        headers["after_header"] = f"{address}{id_part} will be {action_type}\n Changes to apply."

    return headers


def _has_meaningful_changes(masked_before: Dict, masked_after: Dict) -> bool:
    """Check if there are meaningful changes between before and after states."""
    return masked_before != masked_after


def _create_diff_entry(resource_data: ViewPlanResourceData) -> Optional[Dict]:
    """Create a diff entry for a resource.

    Args:
        resource_data: ViewPlanResourceData object containing unified resource change and drift information

    Returns:
        dict or None: Diff entry with before/after states and headers, or None if no changes
    """
    # Determine primary item and scenario
    primary_item, scenario_type = _determine_primary_item_and_scenario(resource_data)

    if not primary_item or not scenario_type:
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

    if not _has_meaningful_changes(masked_before, masked_after):
        return None

    # Prepare diff entry
    actions_list = change.get("actions", [])
    action_type = _convert_actions_to_readable_string(actions_list)
    resource_id = str((before or after or {}).get("id", ""))

    diff_entry = {
        "before": masked_before,
        "after": masked_after,
    }

    # Add headers
    headers = _create_diff_headers(
        scenario_type,
        resource_data.address,
        resource_id,
        action_type,
        resource_data.has_drift,
        resource_data.resource_drift,
    )
    diff_entry.update(headers)

    return diff_entry


def _has_output_changes(change: Dict) -> bool:
    """Check if an output has meaningful changes."""
    if "no-op" in change.get("actions", []):
        return False

    before = change.get("before", None)
    after = change.get("after", None)

    return before != after


def _create_sensitive_output_values(change: Dict) -> Tuple[Any, Any]:
    """Create appropriate values for sensitive outputs."""
    before = change.get("before", None)
    after = change.get("after", None)
    before_sensitive = change.get("before_sensitive", False)
    after_sensitive = change.get("after_sensitive", False)

    if before_sensitive or after_sensitive:
        before_val = "<sensitive> changed from" if before_sensitive else before
        after_val = "<sensitive> changed to" if after_sensitive else after
    else:
        before_val = before
        after_val = after

    return before_val, after_val


def _process_single_output_change(output_name: str, change: Dict) -> Optional[Dict]:
    """Process a single output change and return diff entry if changed."""
    if not _has_output_changes(change):
        return None

    before_val, after_val = _create_sensitive_output_values(change)

    diff_entry = {"before": {}, "after": {output_name: after_val}}

    if change.get("before", None) is not None:
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
    unified_resources = _create_unified_resources(resource_changes, resource_drift)

    for resource_data in unified_resources:
        diff_entry = _create_diff_entry(resource_data)
        if diff_entry:
            diffs.append(diff_entry)

    # Process output changes
    output_diffs = _process_output_changes(output_changes)
    diffs.extend(output_diffs)

    return diffs


def main() -> None:
    """Main module execution function."""
    module = AnsibleTerraformModule(
        argument_spec={
            "plan_id": {"type": "str", "aliases": ["id"]},
            "run_id": {"type": "str"},
            "output_format": {"type": "str", "choices": ["diff", "json"], "default": "diff"},
        },
        mutually_exclusive=[["plan_id", "run_id"]],
        required_one_of=[["plan_id", "run_id"]],
    )

    params = deepcopy(module.params)
    plan_id = params.get("plan_id")
    run_id = params.get("run_id")
    output_format = params.get("output_format")

    result = {}

    try:
        with module.client() as adapter:
            # Determine which ID is provided
            identifier = plan_id if plan_id else run_id
            use_plan_id = plan_id is not None

            # Get plan information
            metadata_response = get_plan_data(adapter, identifier, use_plan_id, include_json_output=False)
            json_output_response = get_plan_data(adapter, identifier, use_plan_id, include_json_output=True)

            # Check if plan was found
            if not metadata_response:
                id_type = "Plan" if use_plan_id else "Plan for run"
                raise ValueError(f"{id_type} with ID '{identifier}' was not found.")

            if output_format == "json":
                # Return json format
                result.update(
                    {
                        "metadata": metadata_response,
                        "json_output": json_output_response,
                    },
                )
            else:
                # Return diff format
                json_output_data = json_output_response
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
