#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: workspace_bootstrap
version_added: "2.0.0"
short_description: Converge a Terraform Cloud/Enterprise workspace baseline in a single task.
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Orchestrates the day-0 setup of a Terraform Cloud/Enterprise workspace. It creates or updates
    the workspace itself and reconciles its variables, variable-set attachments, run triggers,
    and notification configurations against a declarative desired state.
  - Implemented as an action plugin that wraps the collection's pytfe-backed helpers; it does
    not issue its own HTTP calls.
  - Re-running with the same inputs is a no-op (idempotent).
  - Returns per-component change summaries so callers can report exactly what was changed.
extends_documentation_fragment: hashicorp.terraform.common
options:
  workspace_id:
    description:
      - ID of an existing workspace to bootstrap.
      - Mutually exclusive with C(workspace).
    type: str
  workspace:
    description:
      - Name of the workspace to create or bootstrap.
      - Required together with C(organization) when C(workspace_id) is not provided.
    type: str
  organization:
    description:
      - Organization that owns the workspace.
      - Required when C(workspace_id) is not provided, or when creating a new workspace.
    type: str
  settings:
    description:
      - Workspace-level settings applied on create and reconciled on drift.
    type: dict
  variables:
    description:
      - Desired list of workspace-scoped variables.
      - Each entry must include C(key) and typically C(value); C(category) defaults to C(terraform).
    type: list
    elements: dict
  variable_sets:
    description:
      - Variable sets to attach to the workspace.
      - Each entry is either an ID string or a dict with C(id) or C(name).
    type: list
    elements: raw
  run_triggers:
    description:
      - Inbound run triggers to reconcile on the workspace.
      - Each entry is either a sourceable workspace ID string or a dict with C(sourceable_id).
    type: list
    elements: raw
  notifications:
    description:
      - Notification configurations to reconcile on the workspace, keyed by C(name).
    type: list
    elements: dict
  reconcile:
    description:
      - When true, remove variables, run triggers, and notifications that exist on the
        workspace but are not present in the desired state.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Bootstrap a workspace with variables, triggers, and notifications
  hashicorp.terraform.workspace_bootstrap:
    organization: my-org
    workspace: app-prod
    settings:
      execution_mode: remote
      terraform_version: "1.9.5"
      auto_apply: false
    variables:
      - key: APP_REGION
        value: us-east-1
        category: env
      - key: replicas
        value: "3"
        category: terraform
    variable_sets:
      - name: shared-platform-defaults
    run_triggers:
      - ws-upstream-dep
    notifications:
      - name: ops-webhook
        destination_type: generic
        url: https://hooks.example.com/tfc
        triggers:
          - "run:errored"
          - "run:needs_attention"
  register: bootstrap
"""

RETURN = r"""
changed:
  description: True if any component was created, updated, or deleted.
  type: bool
  returned: always
workspace_id:
  description: ID of the bootstrapped workspace.
  type: str
  returned: always
components:
  description: Per-component change summaries.
  type: dict
  returned: always
  contains:
    workspace:
      description: Create/update summary for the workspace itself.
      type: dict
    variables:
      description: Variables that were created, updated, or deleted.
      type: dict
    variable_sets:
      description: Variable set attachments that changed.
      type: dict
    run_triggers:
      description: Run triggers that were created or deleted.
      type: dict
    notifications:
      description: Notification configurations that were created, updated, or deleted.
      type: dict
"""
