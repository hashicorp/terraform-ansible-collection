# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: workspace
version_added: 1.0.0
short_description: Manage workspaces in Terraform Enterprise/Cloud.
author: "Kaushiki Singh (@kausingh)"
description:
  - Create, Update, Lock, Unlock or Delete workspaces in Terraform Enterprise/Cloud.
  - If I(workspace) and I(organization) is specified for a non-existent workspace and the I(state) is C(present),
    this module will create a new workspace.
  - If either I(workspace) (and I(organization)) or I(workspace_id) is specified for an existing workspace and the I(state) is C(present),
    this module will update the existing workspace.
  - If a I(workspace_id) is specified, the I(state) is C(absent) and the I(force) is set C(true),
    this module will force delete the workspace, if it exists, without checking whether it is managing resources.
  - If a I(workspace_id) is specified, the I(state) is C(absent), this module will safe delete the
    workspace, if it exists. This would only delete the workspace if it is not managing any resources.
  - If a I(workspace_id) is specified, the I(state) is C(locked) and I(lock_reason) is set, this module will lock the workspace, if it exists.
  - If a I(workspace_id) is specified, the I(state) is C(unlocked) and I(force) is set C(true), this module will unlock the workspace,
    if it exists.
  - If a I(workspace_id) is specified, the I(state) is C(unlock) and I(force) is set C(true), this module will force unlock the workspace,
    if it exists.
extends_documentation_fragment: hashicorp.terraform.common
options:
  state:
    description:
      - The state the workspace should be in.
      - Setting `state=present` create a workspace if it does not exist, and updates the workspace, if it exists.
      - Setting `state=absent` deletes an existing workspace, if it exists.
      - Setting `state=locked` locks an existing workspace, if it exists.
      - Setting `state=unlocked` unlocks an existing workspace, if it exists.
    type: str
    choices: ["present", "absent", "locked", "unlocked"]
    default: present
  organization:
    description:
      - Name of the organization that the workspace belongs to.
      - This is required when I(workspace) key is set.
    type: str
  workspace:
    description:
      - Name of the workspace.
      - When this key is set, I(organization) must be specified so that the ID of the workspace can be retrieved.
      - Workspace names can only include letters, numbers, -, and _.
    type: str
  new_workspace_name:
    description:
      - This is the new name of the workspace.
      - It is tied to updating workspaces only and applicable to existing workspaces.
    type: str
  workspace_id:
    description:
      - ID of the workspace.
      - Either I(workspace) (and I(organization)) or I(workspace_id) must be specified when updating a `workspace`.
    type: str
  project_id:
    description:
      - ID of the project that the workspace will belong to.
      - If no I(project_id) is provided, the workspace is created in the organization's default project.
    type: str
  allow_destroy_plan:
    description:
      - When true, allows destroy plans to be queued on the workspace.
    type: bool
    default: true
  assessments_enabled:
    description:
      - When true, HCP Terraform performs health assessments for the workspace.
    type: bool
    default: false
  auto_apply:
    description:
      - When true, allows changes to automatically apply when a Terraform plan is successful.
    type: bool
    default: false
  auto_apply_run_trigger:
    description:
      - When true, allows changes to automatically apply when a Terraform plan is successful in runs initiated by run triggers.
    type: bool
    default: false
  auto_destroy_at:
    description:
      - The timestamp when the next scheduled destroy run will occur.
      - The recommended timestamp format is the ISO format for UTC time [YYYY-MM-DDTHH:mm:ssZ].
    type: str
  auto_destroy_activity_duration:
    description:
      - The value and units to automatically schedule destroy runs based on workspace activity.
      - The I(auto_destroy_activity_duration) takes precedence over I(auto_destroy_at), if both are set.
      - The valid values are greater than 0 and four digits or less.
      - The valid units are d and h.
    type: str
  source_name:
    description:
      - A friendly name for the application or client creating this workspace.
    type: str
  source_url:
    description:
      - A URL for the application or client creating this workspace.
    type: str
  description:
    description:
      - A description for the workspace.
    type: str
  terraform_version:
    description:
      - This specifies the version of Terraform to use for this workspace.
      - If a constraint is specified, the workspace always uses the newest release that meets that constraint.
      - If omitted when creating a new I(workspace), this defaults to the latest released version.
    type: str
  execution_mode:
    description:
      - This specifies the execution mode for the workspace.
      - This inherits the default project mode by default.
      - The I(agent_pool_id) must be provided when the I(execution_mode) is `agent`
    choices: ["remote", "local", "agent"]
    type: str
  agent_pool_id:
    description:
      - The ID of the agent pool belonging to the workspace's organization.
      - This value must not be specified if I(execution_mode) is set to `remote` or `local`.
    type: str
  tag_bindings:
    description:
      - The tags to attach to the workspace.
    type: dict
  setting_overwrites:
    description:
      - This paramter helps in overwriting default inherited values.
    type: dict
    suboptions:
      execution_mode:
        description:
          - Defines if the project I(execution_mode) is inherited.
        type: bool
        default: false
      agent_pool:
        description:
          - Defines if the project I(agent_pool) is inherited.
        type: bool
        default: false
  lock_reason:
    description:
      - The reason for locking the workspace.
      - This is only applicable with I(state) is C(locked).
    type: str
  force:
    description:
      - Determines if the specified operation should be forced.
      - This parameter is applicable only with states C(unlocked) and C(absent).
      - When set to C(True) with state C(absent), the module will attempt a force delete operation.
      - When set to C(True) with state C(unlocked), the module will attempt a force unlock.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Create a new workspace
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    description: This is a dev workspace.
    project_id: <your-project-id>
    tag_bindings:
      env: dev
      owner: abc
    execution_mode: remote
    source_name: xyz
    auto_apply: true
    state: present

- name: Create a new workspace
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    execution_mode: agent
    agent_pool_id: <your-agent-pool-id>
    setting_overwrites:
      execution_mode: true
      agent_pool: true
    auto_destroy_activity_duration: 14d
    auto_destroy_at: 2025-08-10T15:00:00Z
    state: present

- name: Update an existing workspace
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    new_workspace_name: <new-name-for-the-workspace>
    description: This is an updated dev workspace.
    project_id: <your-new-project-id>
    tag_bindings:
      env: uat
      owner: abc
    execution_mode: remote
    source_name: xyz
    auto_apply: true
    assessments_enabled: true
    state: present

- name: Safe delete a workspace
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    state: absent

- name: Force delete a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    force: true
    state: absent
  
- name: Lock a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    lock_reason: "your specific reason"
    state: locked

- name: Unlock a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    state: unlocked

- name: Force unlock a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    force: true
    state: unlocked
"""

RETURN = r"""
outputs:
  type: dict
  description: A dictionary of the workspace details.
  returned: on success
  contains:
    attributes:
        type: dict
        returned: always
        description: The attributes of the workspace created.
    workspace_id:
      type: str
      returned: always
      description: ID of the workspace created/updated/deleted.
    msg:
      type: str
      returned: when state is 'absent'
      description: The successfull completion of delete.
"""
