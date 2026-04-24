#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: notification_configuration
version_added: "2.0.0"
short_description: Manage Terraform Cloud/Enterprise workspace notification configurations (create, update, delete).
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Manages workspace-scoped notification configurations on Terraform Cloud and Terraform Enterprise.
  - Supports the C(generic), C(slack), C(microsoft-teams), and C(email) destination types.
  - A notification may be identified either directly by C(notification_configuration_id),
    or by the combination of its workspace (C(workspace_id) or C(workspace)+C(organization)) and its C(name).
  - The C(present) state creates the notification if missing, or updates it in place on drift.
  - The C(absent) state deletes the notification if it exists.
  - B(Webhook verification) - For C(generic), C(slack), and C(microsoft-teams) destinations,
    Terraform Cloud verifies the C(url) on create by POSTing a small payload; the URL must return 2xx.
extends_documentation_fragment: hashicorp.terraform.common
options:
  notification_configuration_id:
    description:
      - The unique identifier of the notification configuration (e.g. C(nc-...)).
      - Provide for unambiguous update or delete operations.
      - Mutually exclusive with C(name).
    type: str
  workspace_id:
    description:
      - The workspace that owns the notification configuration.
      - One of C(workspace_id) or (C(workspace) and C(organization)) is required unless
        C(notification_configuration_id) is provided.
    type: str
  workspace:
    description:
      - The workspace name, used together with C(organization) to locate the workspace.
    type: str
  organization:
    description:
      - The name of the organization that owns the workspace.
    type: str
  name:
    description:
      - Human-readable name used to identify the notification configuration within the workspace.
      - Required when creating, or when identifying by (workspace, name) for update/delete.
      - Mutually exclusive with C(notification_configuration_id).
    type: str
  destination_type:
    description:
      - Where to deliver the notification.
      - Required when creating. Cannot be changed after creation.
    type: str
    choices: ["generic", "slack", "microsoft-teams", "email"]
  url:
    description:
      - Webhook URL. Required for C(generic), C(slack), and C(microsoft-teams) destinations.
      - Ignored for C(email).
    type: str
  token:
    description:
      - Optional HMAC signing secret forwarded to C(generic) webhooks as the C(X-TFE-Notification-Signature) header.
    type: str
    no_log: true
  enabled:
    description:
      - Whether the notification is active. Disabled notifications are retained but not delivered.
    type: bool
    default: true
  triggers:
    description:
      - List of run/assessment/workspace events that cause a notification to fire.
      - See the HCP Terraform notification trigger reference for the full list of accepted values
        (for example C(run:needs_attention), C(run:errored), C(run:completed), C(assessment:drifted)).
    type: list
    elements: str
  email_addresses:
    description:
      - Email recipients for C(destination_type=email). Ignored for webhook destinations.
    type: list
    elements: str
  state:
    description:
      - Desired state of the notification configuration.
      - C(present) creates or updates; C(absent) deletes.
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a generic webhook notification
  hashicorp.terraform.notification_configuration:
    organization: "my-org"
    workspace: "app"
    name: "ops-webhook"
    destination_type: "generic"
    url: "https://hooks.example.com/tfc/ops"
    enabled: true
    triggers:
      - "run:needs_attention"
      - "run:errored"
    state: present

- name: Idempotent re-run with identical input
  hashicorp.terraform.notification_configuration:
    organization: "my-org"
    workspace: "app"
    name: "ops-webhook"
    destination_type: "generic"
    url: "https://hooks.example.com/tfc/ops"
    enabled: true
    triggers:
      - "run:needs_attention"
      - "run:errored"
    state: present
# "changed": false

- name: Disable an existing notification (drift fixes on re-run)
  hashicorp.terraform.notification_configuration:
    organization: "my-org"
    workspace: "app"
    name: "ops-webhook"
    destination_type: "generic"
    url: "https://hooks.example.com/tfc/ops"
    enabled: false
    triggers:
      - "run:needs_attention"
      - "run:errored"
    state: present

- name: Create an email notification
  hashicorp.terraform.notification_configuration:
    workspace_id: "ws-abc123"
    name: "release-watch"
    destination_type: "email"
    email_addresses:
      - "releases@example.com"
    triggers:
      - "run:completed"
    state: present

- name: Delete a notification by ID
  hashicorp.terraform.notification_configuration:
    notification_configuration_id: "nc-xyz789"
    state: absent

- name: Delete a notification by (workspace, name)
  hashicorp.terraform.notification_configuration:
    organization: "my-org"
    workspace: "app"
    name: "ops-webhook"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The notification configuration identifier.
  returned: when state is present
  type: str
  sample: "nc-xyz789"
name:
  description: Notification configuration name.
  returned: when state is present
  type: str
  sample: "ops-webhook"
destination_type:
  description: Delivery channel (C(generic), C(slack), C(microsoft-teams), C(email)).
  returned: when state is present
  type: str
  sample: "generic"
enabled:
  description: Whether the notification is active.
  returned: when state is present
  type: bool
  sample: true
url:
  description: Webhook URL (null for email destinations).
  returned: when state is present
  type: str
  sample: "https://hooks.example.com/tfc/ops"
triggers:
  description: List of events that cause the notification to fire.
  returned: when state is present
  type: list
  elements: str
  sample: ["run:needs_attention", "run:errored"]
email_addresses:
  description: Email recipients (only populated for email destinations).
  returned: when state is present
  type: list
  elements: str
  sample: []
created_at:
  description: Timestamp when the notification configuration was created.
  returned: when state is present
  type: str
  sample: "2025-07-03T08:10:20.479Z"
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Notification configuration nc-xyz789 has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.notification_configuration import (
    create_notification_configuration,
    delete_notification_configuration,
    get_notification_configuration,
    get_notification_configuration_by_name,
    update_notification_configuration,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import get_workspace

# Keys that participate in drift detection / payload construction.
_SDK_KEYS = {"name", "destination_type", "url", "token", "enabled", "triggers", "email_addresses"}


def _resolve_workspace_id(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[str]:
    """Return the workspace_id, resolving by name+organization when necessary."""
    if params.get("workspace_id"):
        return params["workspace_id"]
    workspace_name = params.get("workspace")
    organization = params.get("organization")
    if workspace_name and organization:
        workspace = get_workspace(adapter, organization, workspace_name)
        if workspace:
            return workspace.get("id")
    return None


def _fetch_notification(
    adapter: TerraformClient,
    workspace_id: Optional[str],
    params: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Resolve the target notification by ID or by (workspace_id, name)."""
    notification_id = params.get("notification_configuration_id")
    if notification_id:
        return get_notification_configuration(adapter, notification_id)
    name = params.get("name")
    if workspace_id and name:
        return get_notification_configuration_by_name(adapter, workspace_id, name)
    return None


def _build_desired_state(params: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only SDK-relevant, user-specified fields for drift/create payloads."""
    return {k: v for k, v in params.items() if k in _SDK_KEYS and v is not None}


def _filter_current_state(have: Dict[str, Any], want: Dict[str, Any]) -> Dict[str, Any]:
    """Project the server view down to keys the user explicitly managed."""
    return {k: have.get(k) for k in want.keys() if k in have}


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update a notification configuration to match the desired state."""
    workspace_id = _resolve_workspace_id(adapter, params)
    current = _fetch_notification(adapter, workspace_id, params)
    want = _build_desired_state(params)

    if current is None:
        if not workspace_id:
            raise ValueError("Unable to resolve workspace: provide 'workspace_id' or both 'workspace' and 'organization'.")
        if not params.get("name"):
            raise ValueError("'name' is required when creating a new notification configuration.")
        if not params.get("destination_type"):
            raise ValueError("'destination_type' is required when creating a new notification configuration.")
        if check_mode:
            return {
                "changed": True,
                "msg": f"Notification {params['name']!r} would be created. Skipped creation due to check mode.",
                **want,
            }
        created = create_notification_configuration(adapter, workspace_id, want)
        return {"changed": True, **created}

    # destination_type cannot be mutated in place; flag it rather than silently drifting.
    if want.get("destination_type") and current.get("destination_type") and want["destination_type"] != current["destination_type"]:
        raise ValueError(
            f"Cannot change destination_type from {current['destination_type']!r} to {want['destination_type']!r}; "
            "delete and recreate the notification configuration instead."
        )

    have = _filter_current_state(current, want)
    # destination_type is immutable and always matches here; exclude from the diff payload.
    have.pop("destination_type", None)
    want_for_diff = {k: v for k, v in want.items() if k != "destination_type"}
    diff = dict_diff(have, want_for_diff)
    if not diff:
        return {"changed": False, **current}

    if check_mode:
        return {
            "changed": True,
            "msg": f"Notification {current.get('id')} would be updated with the given options. Skipped update due to check mode.",
            **want,
        }
    updated = update_notification_configuration(adapter, current["id"], diff)
    return {"changed": True, **updated}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the notification configuration if present; no-op otherwise."""
    workspace_id = _resolve_workspace_id(adapter, params)
    current = _fetch_notification(adapter, workspace_id, params)
    if current is None:
        return {"changed": False, "msg": "Notification configuration is already absent."}

    notification_id = current["id"]
    if check_mode:
        return {
            "changed": True,
            "msg": f"Notification configuration {notification_id} would be deleted. Skipped deletion due to check mode.",
        }

    delete_notification_configuration(adapter, notification_id)
    return {"changed": True, "msg": f"Notification configuration {notification_id} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "notification_configuration_id": {"type": "str"},
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
            "name": {"type": "str"},
            "destination_type": {"type": "str", "choices": ["generic", "slack", "microsoft-teams", "email"]},
            "url": {"type": "str"},
            "token": {"type": "str", "no_log": True},
            "enabled": {"type": "bool", "default": True},
            "triggers": {"type": "list", "elements": "str"},
            "email_addresses": {"type": "list", "elements": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_together=[["workspace", "organization"]],
        mutually_exclusive=[
            ("notification_configuration_id", "name"),
            ("workspace_id", "workspace"),
        ],
        required_one_of=[("notification_configuration_id", "name")],
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
