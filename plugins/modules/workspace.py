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
  - If a I(workspace_id) is specified, the I(state) is C(unlocked), this module will unlock the workspace,
    if it exists.
  - If a I(workspace_id) is specified, the I(state) is C(unlocked) and I(force) is set C(true), this module will force unlock the workspace,
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
  assessments_enabled:
    description:
      - When true, HCP Terraform performs health assessments for the workspace.
      - Setting this attribute to true holds relevance in HCP Terraform Plus and Premium editions only.
    type: bool
  auto_apply:
    description:
      - When true, allows changes to automatically apply when a Terraform plan is successful.
    type: bool
  auto_apply_run_trigger:
    description:
      - When true, allows changes to automatically apply when a Terraform plan is successful in runs initiated by run triggers.
    type: bool
  auto_destroy_at:
    description:
      - The timestamp when the next scheduled destroy run will occur.
      - The recommended timestamp format is UTC ISO 8601 [YYYY-MM-DDTHH:mm:ssZ].
      - Setting this attribute value holds relevance in HCP Terraform Plus and Premium editions only.
    type: str
  auto_destroy_activity_duration:
    description:
      - The value and units to automatically schedule destroy runs based on workspace activity.
      - The I(auto_destroy_activity_duration) takes precedence over I(auto_destroy_at), if both are set.
      - The valid values are greater than 0 and four digits or less.
      - The valid units are d and h.
      - Setting this attribute value holds relevance in HCP Terraform Plus and Premium editions only.
    type: str
  source_name:
    description:
      - A friendly name for the application or client creating this workspace.
      - This parameter is applicable only for creating new workspaces.
    type: str
  source_url:
    description:
      - A URL for the application or client creating this workspace.
      - This parameter is applicable only for creating new workspaces.
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
      - When the I(execution_mode) inherited from the project default mode needs to be overridden,
        then I(setting_overwrites) parameter must be provided with this.
    choices: ["remote", "local", "agent"]
    type: str
  agent_pool_id:
    description:
      - The ID of the agent pool belonging to the workspace's organization.
      - This value must not be specified if I(execution_mode) is set to `remote` or `local`.
    type: str
  tag_bindings:
    description:
      - The tags to be bound to the workspace in key and value format.
    type: dict
  setting_overwrites:
    description:
      - This parameter helps in overwriting default inherited values.
      - When the inherited I(execution-mode) needs to be overridden, this parameter needs to be specified.
    type: dict
    suboptions:
      execution_mode:
        description:
          - Defines if the project I(execution_mode) is inherited.
        type: bool
      agent_pool:
        description:
          - Defines if the project I(agent_pool) is inherited.
        type: bool
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
"""

EXAMPLES = r"""
- name: Create a new workspace with minimal data
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    state: present

# Task output:
# ------------
#  "result_create": {
#         "attributes": {
#             "actions": {
#                 "is-destroyable": true
#             },
#             "allow-destroy-plan": true,
#             "apply-duration-average": null,
#             "assessments-enabled": false,
#             "auto-apply": false,
#             "auto-apply-run-trigger": false,
#             "auto-destroy-activity-duration": null,
#             "auto-destroy-at": null,
#             "auto-destroy-status": null,
#             "created-at": "2025-09-03T04:41:20.065Z",
#             "description": null,
#             "environment": "default",
#             "execution-mode": "remote",
#             "file-triggers-enabled": true,
#             "global-remote-state": false,
#             "inherits-project-auto-destroy": true,
#             "last-assessment-result-at": null,
#             "latest-change-at": "2025-09-03T04:41:20.065Z",
#             "locked": false,
#             "locked-reason": "",
#             "name": "workspace-now",
#             "operations": true,
#             "permissions": {
#                 "can-create-state-versions": true,
#                 "can-destroy": true,
#                 "can-force-delete": false,
#                 "can-force-unlock": true,
#                 "can-lock": true,
#                 "can-manage-assessments": true,
#                 "can-manage-ephemeral-workspaces": true,
#                 "can-manage-run-tasks": true,
#                 "can-manage-tags": true,
#                 "can-queue-apply": true,
#                 "can-queue-destroy": true,
#                 "can-queue-run": true,
#                 "can-read-assessment-results": true,
#                 "can-read-change-requests": true,
#                 "can-read-run": true,
#                 "can-read-settings": true,
#                 "can-read-state-outputs": true,
#                 "can-read-state-versions": true,
#                 "can-read-variable": true,
#                 "can-unlock": true,
#                 "can-update": true,
#                 "can-update-change-requests": true,
#                 "can-update-variable": true
#             },
#             "plan-duration-average": null,
#             "policy-check-failures": null,
#             "queue-all-runs": false,
#             "resource-count": 0,
#             "run-failures": null,
#             "setting-overwrites": {
#                 "agent-pool": false,
#                 "execution-mode": false
#             },
#             "source": "tfe-api",
#             "source-name": null,
#             "source-url": null,
#             "speculative-enabled": true,
#             "structured-run-output-enabled": true,
#             "tag-names": [],
#             "terraform-version": "1.13.1",
#             "trigger-patterns": [],
#             "trigger-prefixes": [],
#             "unarchived-workspace-change-requests-count": 0,
#             "updated-at": "2025-09-03T04:41:20.065Z",
#             "vcs-repo": null,
#             "vcs-repo-identifier": null,
#             "working-directory": null,
#             "workspace-kpis-runs-count": null
#         },
#         "changed": true,
#         "failed": false,
#         "id": "ws-id",
#         "links": {
#             "self": "api-link",
#             "self-html": "api-link"
#         },
#         "relationships": {
#             "agent-pool": {
#                 "data": null
#             },
#             "current-assessment-result": {
#                 "data": null
#             },
#             "current-configuration-version": {
#                 "data": null
#             },
#             "current-run": {
#                 "data": null
#             },
#             "current-state-version": {
#                 "data": null
#             },
#             "latest-run": {
#                 "data": null
#             },
#             "organization": {
#                 "data": {
#                     "id": "Ansible-BU-TFC",
#                     "type": "organizations"
#                 }
#             },
#             "outputs": {
#                 "data": []
#             },
#             "project": {
#                 "data": {
#                     "id": "prj-id",
#                     "type": "projects"
#                 }
#             },
#             "readme": {
#                 "data": null
#             },
#             "remote-state-consumers": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "vars": {
#                 "data": []
#             }
#         },
#         "type": "workspaces"
#     }
# }

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
    auto_destroy_activity_duration: 14d
    auto_destroy_at: "2025-08-10T15:00:00Z"
    state: present

# Task output:
# ------------
# "result_create": {
#         "attributes": {
#             "actions": {
#                 "is-destroyable": true
#             },
#             "allow-destroy-plan": true,
#             "apply-duration-average": null,
#             "assessments-enabled": false,
#             "auto-apply": true,
#             "auto-apply-run-trigger": false,
#             "auto-destroy-activity-duration": "14d",
#             "auto-destroy-at": "2025-08-10T15:00:00.000Z",
#             "auto-destroy-status": null,
#             "created-at": "2025-09-03T04:45:34.533Z",
#             "description": "This is a dev workspace.",
#             "environment": "default",
#             "execution-mode": "remote",
#             "file-triggers-enabled": true,
#             "global-remote-state": false,
#             "inherits-project-auto-destroy": false,
#             "last-assessment-result-at": null,
#             "latest-change-at": "2025-09-03T04:45:34.533Z",
#             "locked": false,
#             "locked-reason": "",
#             "name": "workspace-now",
#             "operations": true,
#             "permissions": {
#                 "can-create-state-versions": true,
#                 "can-destroy": true,
#                 "can-force-delete": false,
#                 "can-force-unlock": true,
#                 "can-lock": true,
#                 "can-manage-assessments": true,
#                 "can-manage-ephemeral-workspaces": true,
#                 "can-manage-run-tasks": true,
#                 "can-manage-tags": true,
#                 "can-queue-apply": true,
#                 "can-queue-destroy": true,
#                 "can-queue-run": true,
#                 "can-read-assessment-results": true,
#                 "can-read-change-requests": true,
#                 "can-read-run": true,
#                 "can-read-settings": true,
#                 "can-read-state-outputs": true,
#                 "can-read-state-versions": true,
#                 "can-read-variable": true,
#                 "can-unlock": true,
#                 "can-update": true,
#                 "can-update-change-requests": true,
#                 "can-update-variable": true
#             },
#             "plan-duration-average": null,
#             "policy-check-failures": null,
#             "queue-all-runs": false,
#             "resource-count": 0,
#             "run-failures": null,
#             "setting-overwrites": {
#                 "agent-pool": true,
#                 "execution-mode": true
#             },
#             "source": "tfe-api",
#             "source-name": "xyz",
#             "source-url": null,
#             "speculative-enabled": true,
#             "structured-run-output-enabled": true,
#             "tag-names": [],
#             "terraform-version": "1.13.1",
#             "trigger-patterns": [],
#             "trigger-prefixes": [],
#             "unarchived-workspace-change-requests-count": 0,
#             "updated-at": "2025-09-03T04:45:34.533Z",
#             "vcs-repo": null,
#             "vcs-repo-identifier": null,
#             "working-directory": null,
#             "workspace-kpis-runs-count": null
#         },
#         "changed": true,
#         "failed": false,
#         "id": "ws-id",
#         "links": {
#             "self": "api-link",
#             "self-html": "api-link"
#         },
#         "relationships": {
#             "agent-pool": {
#                 "data": null
#             },
#             "current-assessment-result": {
#                 "data": null
#             },
#             "current-configuration-version": {
#                 "data": null
#             },
#             "current-run": {
#                 "data": null
#             },
#             "current-state-version": {
#                 "data": null
#             },
#             "effective-tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "latest-run": {
#                 "data": null
#             },
#             "organization": {
#                 "data": {
#                     "id": "Ansible-BU-TFC",
#                     "type": "organizations"
#                 }
#             },
#             "outputs": {
#                 "data": []
#             },
#             "project": {
#                 "data": {
#                     "id": "prj-id",
#                     "type": "projects"
#                 }
#             },
#             "readme": {
#                 "data": null
#             },
#             "remote-state-consumers": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "vars": {
#                 "data": []
#             }
#         },
#         "type": "workspaces"
#     }
# }

- name: Update an existing workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    description: This is an updated dev workspace.
    project_id: <your-new-project-id>
    tag_bindings:
      env: uat
      owner: abc
    execution_mode: remote
    auto_apply: true
    assessments_enabled: true
    state: present

# Task output:
# ------------
# "result_update": {
#         "attributes": {
#             "actions": {
#                 "is-destroyable": true
#             },
#             "allow-destroy-plan": true,
#             "apply-duration-average": null,
#             "assessments-enabled": true,
#             "auto-apply": true,
#             "auto-apply-run-trigger": false,
#             "auto-destroy-activity-duration": "14d",
#             "auto-destroy-at": null,
#             "auto-destroy-status": null,
#             "created-at": "2025-09-03T04:45:34.533Z",
#             "description": "This is an updated dev workspace.",
#             "environment": "default",
#             "execution-mode": "remote",
#             "file-triggers-enabled": true,
#             "global-remote-state": false,
#             "inherits-project-auto-destroy": false,
#             "last-assessment-result-at": null,
#             "latest-change-at": "2025-09-03T04:45:34.533Z",
#             "locked": false,
#             "locked-reason": "",
#             "name": "workspace-now",
#             "operations": true,
#             "permissions": {
#                 "can-create-state-versions": true,
#                 "can-destroy": true,
#                 "can-force-delete": false,
#                 "can-force-unlock": true,
#                 "can-lock": true,
#                 "can-manage-assessments": true,
#                 "can-manage-ephemeral-workspaces": true,
#                 "can-manage-run-tasks": true,
#                 "can-manage-tags": true,
#                 "can-queue-apply": true,
#                 "can-queue-destroy": true,
#                 "can-queue-run": true,
#                 "can-read-assessment-results": true,
#                 "can-read-change-requests": true,
#                 "can-read-run": true,
#                 "can-read-settings": true,
#                 "can-read-state-outputs": true,
#                 "can-read-state-versions": true,
#                 "can-read-variable": true,
#                 "can-unlock": true,
#                 "can-update": true,
#                 "can-update-change-requests": true,
#                 "can-update-variable": true
#             },
#             "plan-duration-average": null,
#             "policy-check-failures": null,
#             "queue-all-runs": false,
#             "resource-count": 0,
#             "run-failures": null,
#             "setting-overwrites": {
#                 "agent-pool": true,
#                 "execution-mode": true
#             },
#             "source": "tfe-api",
#             "source-name": "xyz",
#             "source-url": null,
#             "speculative-enabled": true,
#             "structured-run-output-enabled": true,
#             "tag-names": [],
#             "terraform-version": "1.13.1",
#             "trigger-patterns": [],
#             "trigger-prefixes": [],
#             "unarchived-workspace-change-requests-count": 0,
#             "updated-at": "2025-09-03T04:50:09.208Z",
#             "vcs-repo": null,
#             "vcs-repo-identifier": null,
#             "working-directory": null,
#             "workspace-kpis-runs-count": null
#         },
#         "changed": true,
#         "failed": false,
#         "id": "ws-id",
#         "links": {
#             "self": "api-link",
#             "self-html": "api-link"
#         },
#         "relationships": {
#             "agent-pool": {
#                 "data": null
#             },
#             "current-assessment-result": {
#                 "data": null
#             },
#             "current-configuration-version": {
#                 "data": null
#             },
#             "current-run": {
#                 "data": null
#             },
#             "current-state-version": {
#                 "data": null
#             },
#             "effective-tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "latest-run": {
#                 "data": null
#             },
#             "organization": {
#                 "data": {
#                     "id": "Ansible-BU-TFC",
#                     "type": "organizations"
#                 }
#             },
#             "outputs": {
#                 "data": []
#             },
#             "project": {
#                 "data": {
#                     "id": "prj-id",
#                     "type": "projects"
#                 }
#             },
#             "readme": {
#                 "data": null
#             },
#             "remote-state-consumers": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "vars": {
#                 "data": []
#             }
#         },
#         "type": "workspaces"
#     }
# }

- name: Update workspace execution mode to 'agent' by overwriting inherited execution mode from project
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    execution_mode: agent
    agent_pool_id: <your-agent-pool-id>
    setting_overwrites:
      execution_mode: true
      agent_pool: true
    state: present

# Task output:
# ------------
# "result_update": {
#         "attributes": {
#             "actions": {
#                 "is-destroyable": true
#             },
#             "allow-destroy-plan": true,
#             "apply-duration-average": null,
#             "assessments-enabled": true,
#             "auto-apply": true,
#             "auto-apply-run-trigger": false,
#             "auto-destroy-activity-duration": "14d",
#             "auto-destroy-at": null,
#             "auto-destroy-status": null,
#             "created-at": "2025-09-03T04:45:34.533Z",
#             "description": "This is an updated dev workspace.",
#             "environment": "default",
#             "execution-mode": "agent",
#             "file-triggers-enabled": true,
#             "global-remote-state": false,
#             "inherits-project-auto-destroy": false,
#             "last-assessment-result-at": null,
#             "latest-change-at": "2025-09-03T04:45:34.533Z",
#             "locked": false,
#             "locked-reason": "",
#             "name": "workspace-now",
#             "operations": true,
#             "permissions": {
#                 "can-create-state-versions": true,
#                 "can-destroy": true,
#                 "can-force-delete": false,
#                 "can-force-unlock": true,
#                 "can-lock": true,
#                 "can-manage-assessments": true,
#                 "can-manage-ephemeral-workspaces": true,
#                 "can-manage-run-tasks": true,
#                 "can-manage-tags": true,
#                 "can-queue-apply": true,
#                 "can-queue-destroy": true,
#                 "can-queue-run": true,
#                 "can-read-assessment-results": true,
#                 "can-read-change-requests": true,
#                 "can-read-run": true,
#                 "can-read-settings": true,
#                 "can-read-state-outputs": true,
#                 "can-read-state-versions": true,
#                 "can-read-variable": true,
#                 "can-unlock": true,
#                 "can-update": true,
#                 "can-update-change-requests": true,
#                 "can-update-variable": true
#             },
#             "plan-duration-average": null,
#             "policy-check-failures": null,
#             "queue-all-runs": false,
#             "resource-count": 0,
#             "run-failures": null,
#             "setting-overwrites": {
#                 "agent-pool": true,
#                 "execution-mode": true
#             },
#             "source": "tfe-api",
#             "source-name": "xyz",
#             "source-url": null,
#             "speculative-enabled": true,
#             "structured-run-output-enabled": true,
#             "tag-names": [],
#             "terraform-version": "1.13.1",
#             "trigger-patterns": [],
#             "trigger-prefixes": [],
#             "unarchived-workspace-change-requests-count": 0,
#             "updated-at": "2025-09-03T04:53:12.902Z",
#             "vcs-repo": null,
#             "vcs-repo-identifier": null,
#             "working-directory": null,
#             "workspace-kpis-runs-count": null
#         },
#         "changed": true,
#         "failed": false,
#         "id": "ws-id",
#         "links": {
#             "self": "api-link",
#             "self-html": "api-link"
#         },
#         "relationships": {
#             "agent-pool": {
#                 "data": {
#                     "id": "apool-id",
#                     "type": "agent-pools"
#                 }
#             },
#             "current-assessment-result": {
#                 "data": null
#             },
#             "current-configuration-version": {
#                 "data": null
#             },
#             "current-run": {
#                 "data": null
#             },
#             "current-state-version": {
#                 "data": null
#             },
#             "effective-tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "latest-run": {
#                 "data": null
#             },
#             "organization": {
#                 "data": {
#                     "id": "Ansible-BU-TFC",
#                     "type": "organizations"
#                 }
#             },
#             "outputs": {
#                 "data": []
#             },
#             "project": {
#                 "data": {
#                     "id": "prj-id",
#                     "type": "projects"
#                 }
#             },
#             "readme": {
#                 "data": null
#             },
#             "remote-state-consumers": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "vars": {
#                 "data": []
#             }
#         },
#         "type": "workspaces"
#     }
# }

# If the workspace is updated with the same data again the results would look like:
# "result_update": {
#         "changed": false,
#         "failed": false,
#     }

- name: Safe delete a workspace
  hashicorp.terraform.workspace:
    workspace: <your-workspace-name>
    organization: <your-organization>
    state: absent

# Task output:
# ------------
# "result_delete": {
#         "changed": true,
#         "failed": false,
#         "msg": "The workspace ws-id was safe-deleted successfully."
#     }

- name: Force delete a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    force: true
    state: absent

# Task output:
# ------------
# "result_delete": {
#         "changed": true,
#         "failed": false,
#         "msg": "The workspace ws-id was force-deleted successfully."
#     }

- name: Lock a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    lock_reason: "your specific reason"
    state: locked

# Task output:
# ------------
# "result_lock": {
#         "attributes": {
#             "actions": {
#                 "is-destroyable": true
#             },
#             "allow-destroy-plan": true,
#             "apply-duration-average": null,
#             "assessments-enabled": true,
#             "auto-apply": true,
#             "auto-apply-run-trigger": false,
#             "auto-destroy-activity-duration": "14d",
#             "auto-destroy-at": null,
#             "auto-destroy-status": null,
#             "created-at": "2025-09-03T04:45:34.533Z",
#             "description": "This is an updated dev workspace.",
#             "environment": "default",
#             "execution-mode": "agent",
#             "file-triggers-enabled": true,
#             "global-remote-state": false,
#             "inherits-project-auto-destroy": false,
#             "last-assessment-result-at": null,
#             "latest-change-at": "2025-09-03T04:45:34.533Z",
#             "locked": true,
#             "locked-reason": "this is my reason",
#             "name": "workspace-now",
#             "operations": true,
#             "permissions": {
#                 "can-create-state-versions": true,
#                 "can-destroy": true,
#                 "can-force-delete": false,
#                 "can-force-unlock": true,
#                 "can-lock": true,
#                 "can-manage-assessments": true,
#                 "can-manage-ephemeral-workspaces": true,
#                 "can-manage-run-tasks": true,
#                 "can-manage-tags": true,
#                 "can-queue-apply": true,
#                 "can-queue-destroy": true,
#                 "can-queue-run": true,
#                 "can-read-assessment-results": true,
#                 "can-read-change-requests": true,
#                 "can-read-run": true,
#                 "can-read-settings": true,
#                 "can-read-state-outputs": true,
#                 "can-read-state-versions": true,
#                 "can-read-variable": true,
#                 "can-unlock": true,
#                 "can-update": true,
#                 "can-update-change-requests": true,
#                 "can-update-variable": true
#             },
#             "plan-duration-average": null,
#             "policy-check-failures": null,
#             "queue-all-runs": false,
#             "resource-count": 0,
#             "run-failures": null,
#             "setting-overwrites": {
#                 "agent-pool": true,
#                 "execution-mode": true
#             },
#             "source": "tfe-api",
#             "source-name": "xyz",
#             "source-url": null,
#             "speculative-enabled": true,
#             "structured-run-output-enabled": true,
#             "tag-names": [],
#             "terraform-version": "1.13.1",
#             "trigger-patterns": [],
#             "trigger-prefixes": [],
#             "unarchived-workspace-change-requests-count": 0,
#             "updated-at": "2025-09-03T04:59:39.739Z",
#             "vcs-repo": null,
#             "vcs-repo-identifier": null,
#             "working-directory": null,
#             "workspace-kpis-runs-count": null
#         },
#         "changed": true,
#         "failed": false,
#         "id": "ws-id",
#         "links": {
#             "self": "api-link",
#             "self-html": "api-link"
#         },
#         "relationships": {
#             "agent-pool": {
#                 "data": {
#                     "id": "apool-id",
#                     "type": "agent-pools"
#                 }
#             },
#             "current-assessment-result": {
#                 "data": null
#             },
#             "current-configuration-version": {
#                 "data": null
#             },
#             "current-run": {
#                 "data": null
#             },
#             "current-state-version": {
#                 "data": null
#             },
#             "effective-tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "latest-run": {
#                 "data": null
#             },
#             "locked-by": {
#                 "data": {
#                     "id": "user-id",
#                     "type": "users"
#                 },
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "organization": {
#                 "data": {
#                     "id": "Ansible-BU-TFC",
#                     "type": "organizations"
#                 }
#             },
#             "outputs": {
#                 "data": []
#             },
#             "project": {
#                 "data": {
#                     "id": "prj-id",
#                     "type": "projects"
#                 }
#             },
#             "readme": {
#                 "data": null
#             },
#             "remote-state-consumers": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "vars": {
#                 "data": []
#             }
#         },
#         "type": "workspaces"
#     }

- name: Unlock a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    state: unlocked

# Task output:
# ------------
# "result_unlock": {
#         "attributes": {
#             "actions": {
#                 "is-destroyable": true
#             },
#             "allow-destroy-plan": true,
#             "apply-duration-average": null,
#             "assessments-enabled": true,
#             "auto-apply": true,
#             "auto-apply-run-trigger": false,
#             "auto-destroy-activity-duration": "14d",
#             "auto-destroy-at": null,
#             "auto-destroy-status": null,
#             "created-at": "2025-09-03T04:45:34.533Z",
#             "description": "This is an updated dev workspace.",
#             "environment": "default",
#             "execution-mode": "agent",
#             "file-triggers-enabled": true,
#             "global-remote-state": false,
#             "inherits-project-auto-destroy": false,
#             "last-assessment-result-at": null,
#             "latest-change-at": "2025-09-03T04:45:34.533Z",
#             "locked": false,
#             "locked-reason": "",
#             "name": "workspace-now",
#             "operations": true,
#             "permissions": {
#                 "can-create-state-versions": true,
#                 "can-destroy": true,
#                 "can-force-delete": false,
#                 "can-force-unlock": true,
#                 "can-lock": true,
#                 "can-manage-assessments": true,
#                 "can-manage-ephemeral-workspaces": true,
#                 "can-manage-run-tasks": true,
#                 "can-manage-tags": true,
#                 "can-queue-apply": true,
#                 "can-queue-destroy": true,
#                 "can-queue-run": true,
#                 "can-read-assessment-results": true,
#                 "can-read-change-requests": true,
#                 "can-read-run": true,
#                 "can-read-settings": true,
#                 "can-read-state-outputs": true,
#                 "can-read-state-versions": true,
#                 "can-read-variable": true,
#                 "can-unlock": true,
#                 "can-update": true,
#                 "can-update-change-requests": true,
#                 "can-update-variable": true
#             },
#             "plan-duration-average": null,
#             "policy-check-failures": null,
#             "queue-all-runs": false,
#             "resource-count": 0,
#             "run-failures": null,
#             "setting-overwrites": {
#                 "agent-pool": true,
#                 "execution-mode": true
#             },
#             "source": "tfe-api",
#             "source-name": "xyz",
#             "source-url": null,
#             "speculative-enabled": true,
#             "structured-run-output-enabled": true,
#             "tag-names": [],
#             "terraform-version": "1.13.1",
#             "trigger-patterns": [],
#             "trigger-prefixes": [],
#             "unarchived-workspace-change-requests-count": 0,
#             "updated-at": "2025-09-03T05:01:35.165Z",
#             "vcs-repo": null,
#             "vcs-repo-identifier": null,
#             "working-directory": null,
#             "workspace-kpis-runs-count": null
#         },
#         "changed": true,
#         "failed": false,
#         "id": "ws-id",
#         "links": {
#             "self": "api-link",
#             "self-html": "api-link"
#         },
#         "relationships": {
#             "agent-pool": {
#                 "data": {
#                     "id": "apool-id",
#                     "type": "agent-pools"
#                 }
#             },
#             "current-assessment-result": {
#                 "data": null
#             },
#             "current-configuration-version": {
#                 "data": null
#             },
#             "current-run": {
#                 "data": null
#             },
#             "current-state-version": {
#                 "data": null
#             },
#             "effective-tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "latest-run": {
#                 "data": null
#             },
#             "organization": {
#                 "data": {
#                     "id": "Ansible-BU-TFC",
#                     "type": "organizations"
#                 }
#             },
#             "outputs": {
#                 "data": []
#             },
#             "project": {
#                 "data": {
#                     "id": "prj-id",
#                     "type": "projects"
#                 }
#             },
#             "readme": {
#                 "data": null
#             },
#             "remote-state-consumers": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "vars": {
#                 "data": []
#             }
#         },
#         "type": "workspaces"
#     }
# }

- name: Force unlock a workspace
  hashicorp.terraform.workspace:
    workspace_id: <your-workspace-id>
    force: true
    state: unlocked

# Task output:
# ------------
# "result_unlock": {
#         "attributes": {
#             "actions": {
#                 "is-destroyable": true
#             },
#             "allow-destroy-plan": true,
#             "apply-duration-average": null,
#             "assessments-enabled": true,
#             "auto-apply": true,
#             "auto-apply-run-trigger": false,
#             "auto-destroy-activity-duration": "14d",
#             "auto-destroy-at": null,
#             "auto-destroy-status": null,
#             "created-at": "2025-09-03T04:45:34.533Z",
#             "description": "This is an updated dev workspace.",
#             "environment": "default",
#             "execution-mode": "agent",
#             "file-triggers-enabled": true,
#             "global-remote-state": false,
#             "inherits-project-auto-destroy": false,
#             "last-assessment-result-at": null,
#             "latest-change-at": "2025-09-03T04:45:34.533Z",
#             "locked": false,
#             "locked-reason": "",
#             "name": "workspace-now",
#             "operations": true,
#             "permissions": {
#                 "can-create-state-versions": true,
#                 "can-destroy": true,
#                 "can-force-delete": false,
#                 "can-force-unlock": true,
#                 "can-lock": true,
#                 "can-manage-assessments": true,
#                 "can-manage-ephemeral-workspaces": true,
#                 "can-manage-run-tasks": true,
#                 "can-manage-tags": true,
#                 "can-queue-apply": true,
#                 "can-queue-destroy": true,
#                 "can-queue-run": true,
#                 "can-read-assessment-results": true,
#                 "can-read-change-requests": true,
#                 "can-read-run": true,
#                 "can-read-settings": true,
#                 "can-read-state-outputs": true,
#                 "can-read-state-versions": true,
#                 "can-read-variable": true,
#                 "can-unlock": true,
#                 "can-update": true,
#                 "can-update-change-requests": true,
#                 "can-update-variable": true
#             },
#             "plan-duration-average": null,
#             "policy-check-failures": null,
#             "queue-all-runs": false,
#             "resource-count": 0,
#             "run-failures": null,
#             "setting-overwrites": {
#                 "agent-pool": true,
#                 "execution-mode": true
#             },
#             "source": "tfe-api",
#             "source-name": "xyz",
#             "source-url": null,
#             "speculative-enabled": true,
#             "structured-run-output-enabled": true,
#             "tag-names": [],
#             "terraform-version": "1.13.1",
#             "trigger-patterns": [],
#             "trigger-prefixes": [],
#             "unarchived-workspace-change-requests-count": 0,
#             "updated-at": "2025-09-03T05:03:39.704Z",
#             "vcs-repo": null,
#             "vcs-repo-identifier": null,
#             "working-directory": null,
#             "workspace-kpis-runs-count": null
#         },
#         "changed": true,
#         "failed": false,
#         "id": "ws-id",
#         "links": {
#             "self": "api-link",
#             "self-html": "api-link"
#         },
#         "relationships": {
#             "agent-pool": {
#                 "data": {
#                     "id": "apool-id",
#                     "type": "agent-pools"
#                 }
#             },
#             "current-assessment-result": {
#                 "data": null
#             },
#             "current-configuration-version": {
#                 "data": null
#             },
#             "current-run": {
#                 "data": null
#             },
#             "current-state-version": {
#                 "data": null
#             },
#             "effective-tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "latest-run": {
#                 "data": null
#             },
#             "organization": {
#                 "data": {
#                     "id": "Ansible-BU-TFC",
#                     "type": "organizations"
#                 }
#             },
#             "outputs": {
#                 "data": []
#             },
#             "project": {
#                 "data": {
#                     "id": "prj-id",
#                     "type": "projects"
#                 }
#             },
#             "readme": {
#                 "data": null
#             },
#             "remote-state-consumers": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "tag-bindings": {
#                 "links": {
#                     "related": "api-link"
#                 }
#             },
#             "vars": {
#                 "data": []
#             }
#         },
#         "type": "workspaces"
#     }
"""

RETURN = r"""
id:
  description: The unique identifier of the workspace.
  returned: when state is 'present'/'locked'/'unlocked'
  type: str
  sample: "ws-ybMGvqhs6MWLa5S2"
type:
    description: The resource type, always 'workspaces'.
    returned: when state is 'present'/'locked'/'unlocked'
    type: str
    sample: "workspaces"
attributes:
  type: dict
  returned: when state is 'present'/'locked'/'unlocked'
  description: The attributes of the workspace created/updated/locked/unlocked.
relationships:
  description: Related resources linked to the run.
  returned: when state is 'present'/'locked'/'unlocked'
  type: dict
  sample: {
        "agent-pool": {
            "data": {
                "id": "apool-id",
                "type": "agent-pools"
            }
        },
        "current-assessment-result": {
            "data": null
        },
        "current-configuration-version": {
            "data": null
        },
        "current-run": {
            "data": null
        },
        "current-state-version": {
            "data": null
        },
        "effective-tag-bindings": {
            "links": {
                "related": "/api/v2/workspaces/ws-id/effective-tag-bindings"
            }
        },
        "latest-run": {
            "data": null
        },
        "organization": {
            "data": {
                "id": "org",
                "type": "organizations"
            }
        },
        "outputs": {
            "data": []
        },
        "project": {
            "data": {
                "id": "prj-id",
                "type": "projects"
            }
        },
        "readme": {
            "data": null
        },
        "remote-state-consumers": {
            "links": {
                "related": "/api/v2/workspaces/ws-id/relationships/remote-state-consumers"
            }
        },
        "tag-bindings": {
            "links": {
                "related": "/api/v2/workspaces/ws-id/tag-bindings"
            }
        },
        "vars": {
            "data": []
        }
    }
links:
  description: API links for the run.
  returned: when state is 'present'/'locked'/'unlocked'
  type: dict
  sample: {
        "self": "/api/v2/organizations/org/workspaces/workspace",
        "self-html": "/app/org/workspaces/workspace"
    }
msg:
  type: str
  returned: when state is 'absent'.
  description: The status of the operation.
"""


from datetime import datetime
from typing import TYPE_CHECKING

from ansible.module_utils._text import to_text


if TYPE_CHECKING:
    from typing import Any, Dict

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.workspace import WorkspaceRequest
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import (
    create_workspace,
    force_delete_workspace,
    force_unlock_workspace,
    get_tag_bindings,
    get_workspace,
    get_workspace_by_id,
    lock_workspace,
    safe_delete_workspace,
    unlock_workspace,
    update_workspace,
)


IGNORE_LIST = ["tf_hostname", "tf_token", "tf_timeout", "tf_max_retries", "tf_validate_certs", "check_mode", "state"]


def fetch_workspace_tag_bindings(client_terraform, workspace_id: str) -> dict:
    """
    Fetch actual tag key-value pairs for a workspace's tag bindings.

    Args:
        client_terraform: An instance of TerraformClient.
        workspace_id (str): The workspace ID.

    Returns:
        Dict[str, str]: A mapping of tag keys to values.
    """
    response = get_tag_bindings(client_terraform, workspace_id)

    if not response or "data" not in response:
        return {}

    tag_values = {}
    for item in response["data"]:
        if item.get("type") == "tag-bindings":
            attributes = item.get("attributes", {})
            key = attributes.get("key")
            value = attributes.get("value")
            if key is not None:
                tag_values[key] = value

    return tag_values


def normalize_workspace_response(response_data: dict, client_terraform: Any, workspace_id: str) -> dict:
    """
    Normalizes the raw workspace API response into a simplified, structured dictionary
    representing the current state of a workspace.

    This function extracts key attributes and relationships from the Terraform workspace
    API response and formats certain fields for consistency (e.g., converting the
    `auto-destroy-at` timestamp to a standard format). It also includes related data such
    as tag bindings and conditionally includes the agent pool ID if the execution mode is 'agent'.

    Args:
        response_data (dict): The raw JSON response from the workspace API.
        client_terraform (Any): A client instance used to fetch additional workspace data
        workspace_id (str): The ID of the workspace whose data is being normalized.

    Returns:
        dict: A dictionary representing the normalized state of the workspace, excluding
              any fields that are `None`.
    """

    auto_destroy_at = response_data.get("attributes", {}).get("auto-destroy-at")
    if auto_destroy_at:
        try:
            dt = datetime.strptime(auto_destroy_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            auto_destroy_at = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            # if parsing fails, keep the original value
            pass
    execution_mode = response_data.get("attributes", {}).get("execution-mode")
    agent_pool_id = None
    if execution_mode == "agent":
        agent_pool_id = response_data.get("relationships", {}).get("agent-pool", {}).get("data", {}).get("id", None)
    normalized = {
        "name": response_data.get("attributes", {}).get("name"),
        "description": response_data.get("attributes", {}).get("description"),
        "allow_destroy_plan": response_data.get("attributes", {}).get("allow-destroy-plan"),
        "assessments_enabled": response_data.get("attributes", {}).get("assessments-enabled"),
        "auto_apply": response_data.get("attributes", {}).get("auto-apply"),
        "auto_apply_run_trigger": response_data.get("attributes", {}).get("auto-apply-run-trigger"),
        "auto_destroy_at": auto_destroy_at,
        "auto_destroy_activity_duration": response_data.get("attributes", {}).get("auto-destroy-activity-duration"),
        "terraform_version": response_data.get("attributes", {}).get("terraform-version"),
        "execution_mode": execution_mode,
        "agent_pool_id": agent_pool_id,
        "setting_overwrites": {k.replace("-", "_"): v for k, v in response_data.get("attributes", {}).get("setting-overwrites", {}).items()},
        "project_id": response_data.get("relationships", {}).get("project", {}).get("data", {}).get("id", None),
    }
    # Include tag bindings
    tag_bindings = fetch_workspace_tag_bindings(client_terraform, workspace_id)
    normalized["tag_bindings"] = tag_bindings
    return {k: v for k, v in normalized.items() if v is not None}


def state_create(client_terraform: Any, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Creates a new Terraform workspace using the provided client and parameters.

    This function filters out irrelevant parameters, formats the workspace data,
    and sends a request to create the workspace under the specified organization.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary of parameters including workspace details.
        check_mode (bool): A check mode parameter.

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): Always True, indicating that a workspace was created.
            - "msg" (str): Success message.
            - Additional data returned from the workspace creation API.

    Raises:
        Any exceptions raised by the underlying Terraform client or request methods
        will propagate up to the caller.
    """

    action_result = {}
    ignore_list = ["force"]
    ignore_list.extend(IGNORE_LIST)
    workspace_params = params.copy()
    # pop unwanted values
    for value in ignore_list:
        workspace_params.pop(value, None)
    # store required values for the api endpoint and relationships
    workspace_params["name"] = workspace_params.pop("workspace")
    organization = workspace_params.pop("organization")
    project_id = workspace_params.pop("project_id", None)
    tag_bindings = workspace_params.pop("tag_bindings", None)
    # create the model and use the payload for the creation request of workspace
    workspace_request = WorkspaceRequest.create(project_id=project_id, tag_bindings=tag_bindings, **workspace_params)
    workspace_payload = workspace_request.model_dump(by_alias=True, exclude_unset=False, exclude_none=True)
    if not check_mode:
        response = create_workspace(client_terraform, organization, workspace_payload)
        params["workspace_id"] = response.get("data").get("id")
        action_result.update(
            {"changed": True, **response["data"]},
        )
    else:
        action_result.update(
            {
                "changed": True,
                "msg": f"The workspace {params['workspace']} would be created with the given options. Skipped creation due to check mode.",
                **workspace_payload["data"],
            },
        )
    return action_result


def state_update(client_terraform: Any, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Updates an existing Terraform workspace using the provided client and parameters.

    This function filters out irrelevant parameters, prepares the updated workspace data,
    and sends a request to update the workspace with the specified ID.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary of parameters including updated workspace details.
        check_mode (bool): A check mode parameter.

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): Always True, indicating that the workspace was updated.
            - "msg" (str): Success message.
            - Additional data returned from the workspace update API.

    Raises:
        Any exceptions raised by the underlying Terraform client or request methods
        will propagate up to the caller.
    """

    action_result = {}
    # pop unwanted values and also remove source_name and source_url if present as they are not applicable for update operations
    ignore_list = [
        "lock_reason",
        "force",
        "organization",
        "source_name",
        "source_url",
    ]
    ignore_list.extend(IGNORE_LIST)
    workspace_params = params.copy()
    for value in ignore_list:
        workspace_params.pop(value, None)
    workspace_params["name"] = workspace_params.pop("workspace")
    workspace_id = workspace_params.pop("workspace_id")
    workspace_response = get_workspace_by_id(client_terraform, workspace_id)
    if not workspace_response:
        raise ValueError(f"The workspace {workspace_id} was not found.")
    # the keys and their corresponding values the workspace already has
    have = normalize_workspace_response(workspace_response.get("data"), client_terraform, workspace_id)
    # the keys input by the user
    want = workspace_params.copy()
    want = {k: v for k, v in want.items() if v is not None}
    # removing excessive keys from have to match it to want
    have = {k: v for k, v in have.items() if k in want}
    # comparing the two dictionaries
    updates_response = dict_diff(have, want)

    if not updates_response:
        action_result.update(
            {
                "changed": False,
            },
        )
        return action_result

    project_id = workspace_params.pop("project_id", None)
    tag_bindings = workspace_params.pop("tag_bindings", None)
    # Since these keys are coupled, they need to be preserved to avoid running into scenarios where absence/removal (during diff)
    # of either of the attributes causes a mismatch
    preserve_keys = {"setting_overwrites", "execution_mode", "agent_pool_id"}
    # If there are differences to be updated
    for key in list(workspace_params.keys()):
        if key not in updates_response and key not in preserve_keys:
            workspace_params.pop(key)

    # create the model and use the payload for the update request of workspace
    workspace_request = WorkspaceRequest.create(project_id=project_id, tag_bindings=tag_bindings, **workspace_params)
    workspace_payload = workspace_request.model_dump(by_alias=True, exclude_unset=False, exclude_none=True)

    if not check_mode:
        response = update_workspace(client_terraform, workspace_id, workspace_payload)
        action_result.update(
            {"changed": True, **response["data"]},
        )
    else:
        action_result.update(
            {
                "changed": True,
                "msg": f"The workspace {params['workspace_id']} would be updated with the given options. Skipped update due to check mode.",
                **workspace_payload["data"],
            },
        )
    return action_result


def get_workspace_id(client_terraform: Any, params: Dict[str, Any]) -> str:
    """
    Retrieves the ID of a Terraform workspace based on its name and organization.

    This function queries the Terraform API to fetch workspace details and returns
    the corresponding workspace ID. If the workspace is not found, it raises a ValueError.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary containing:
            - "organization" (str): The name of the organization that owns the workspace.
            - "workspace" (str): The name of the workspace to retrieve.

    Returns:
        str: The ID of the workspace.

    Raises:
        ValueError: If the specified workspace does not exist in the given organization.
    """
    # get the workspace_id from the provided workspace name
    workspace_response = get_workspace(client_terraform, params["organization"], params["workspace"])
    if not workspace_response:
        raise ValueError(f"The workspace {params['workspace']} in {params['organization']} organization was not found.")
    # retrieve the workspace ID
    workspace_id = workspace_response.get("data")["id"]
    # update module params to have a workspace ID
    return workspace_id


def state_absent(client_terraform: Any, params: Dict[str, Any], workspace_response: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Deletes a Terraform workspace using either a safe or force delete method.

    If a workspace ID is not provided in the parameters, the function attempts to retrieve it
    using the organization and workspace name. Based on the `force_delete` flag, it will perform
    either a forceful or safe deletion.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary of module parameters.
        workspace_response (Dict[str, Any]): A dictionary of workspace response parameters.
        check_mode (bool): A check mode parameter.

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): True if the workspace was deleted.
            - "msg" (str): A message describing the result of the deletion.

    Raises:
        ValueError: If the workspace cannot be found when attempting to resolve the ID.
        Any exceptions from the delete functions will propagate up to the caller.
    """
    action_result = {
        "changed": False,
    }
    if not workspace_response:
        action_result["msg"] = f"The workspace {params['workspace_id']} was not found."
        action_result["changed"] = False
        return action_result
    if not check_mode:
        if params["force"]:
            force_delete_workspace(client_terraform, params["workspace_id"])
            msg = f"The workspace {params['workspace_id']} was force-deleted successfully."
            action_result["changed"] = True
        else:
            safe_delete_workspace(client_terraform, params["workspace_id"])
            msg = f"The workspace {params['workspace_id']} was safe-deleted successfully."
            action_result["changed"] = True
    else:
        msg = f"The workspace {params['workspace_id']} was found. Skipped delete due to check mode."
        action_result["changed"] = True
    action_result["msg"] = msg
    return action_result


def state_unlocked(client_terraform: Any, params: Dict[str, Any], workspace_response: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Unlocks a Terraform workspace, either forcefully or gracefully depending on the provided parameters.

    If the workspace ID is not provided, it attempts to retrieve it using the organization and workspace name.
    Unlocking is then performed based on the value of the `force` flag.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary of module parameters.
        workspace_response (Dict[str, Any]): A dictionary of workspace response parameters.
        check_mode (bool): A check mode parameter.

    Returns:
        Dict[str, Any]: A dictionary with the result of the unlock operation, including:
            - "changed" (bool): Always True, indicating the workspace was unlocked.
            - "msg" (str): A success message.
            - Additional data returned from the unlock operation.

    Raises:
        ValueError: If the workspace ID could not be resolved.
        Any exceptions raised by the underlying unlock functions will propagate up to the caller.
    """
    action_result = {}
    if not workspace_response:
        raise ValueError(f"The workspace {params['workspace_id']} was not found, hence cannot proceed with unlocking.")
    locked_status = workspace_response.get("data").get("attributes", {}).get("locked")
    if not locked_status:
        action_result.update(
            {"changed": False, "msg": f"The workspace {params['workspace_id']} is already unlocked."},
        )
        return action_result
    if not check_mode:
        if params["force"]:
            response = force_unlock_workspace(client_terraform, params["workspace_id"])
        else:
            response = unlock_workspace(client_terraform, params["workspace_id"])
        action_result.update(
            {"changed": True, **response["data"]},
        )
    else:
        action_result.update(
            {"changed": True, "msg": f"The workspace {params['workspace_id']} was found. Skipped unlocking due to check mode."},
        )
    return action_result


def state_locked(client_terraform: Any, params: Dict[str, Any], workspace_response: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """
    Locks a Terraform workspace.

    If the workspace ID is not provided, the function retrieves it using the organization
    and workspace name. It then locks the workspace with the given reason.

    Args:
        client_terraform (TerraformClient): An instance of the Terraform client used to communicate with the API.
        params (Dict[str, Any]): A dictionary of module parameters.
        workspace_response (Dict[str, Any]): A dictionary of workspace response parameters.
        check_mode (bool): A check mode parameter.

    Returns:
        Dict[str, Any]: A dictionary indicating the result of the operation, including:
            - "changed" (bool): True if the workspace was successfully locked.
            - "msg" (str): A message indicating success.
            - Additional data returned from the lock operation.

    Raises:
        ValueError: If the workspace cannot be found or resolved.
        Any exceptions from the lock operation will propagate to the caller.
    """
    action_result = {
        "changed": False,
    }
    if not workspace_response:
        raise ValueError(f"The workspace {params['workspace_id']} was not found, hence cannot proceed with locking.")
    locked_status = workspace_response.get("data").get("attributes", {}).get("locked")
    if locked_status:
        action_result.update(
            {"changed": False, "msg": f"The workspace {params['workspace_id']} is already locked."},
        )
        return action_result
    if not check_mode:
        response = lock_workspace(client_terraform, params["workspace_id"], params["lock_reason"])
        action_result.update(
            {"changed": True, **response["data"]},
        )
    else:
        action_result.update(
            {"changed": True, "msg": f"The workspace {params['workspace_id']} was found. Skipped locking due to check mode."},
        )

    return action_result


def main():
    module = AnsibleTerraformModule(
        argument_spec={
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent", "unlocked", "locked"]},
            "project_id": {"type": "str"},
            "allow_destroy_plan": {"type": "bool"},
            "assessments_enabled": {"type": "bool"},
            "auto_apply": {"type": "bool"},
            "auto_apply_run_trigger": {"type": "bool"},
            "auto_destroy_at": {"type": "str"},
            "auto_destroy_activity_duration": {"type": "str"},
            "source_name": {"type": "str"},
            "source_url": {"type": "str"},
            "description": {"type": "str"},
            "terraform_version": {"type": "str"},
            "execution_mode": {"type": "str", "choices": ["remote", "local", "agent"]},
            "agent_pool_id": {"type": "str"},
            "tag_bindings": {"type": "dict"},
            "setting_overwrites": {"type": "dict"},
            "force": {"type": "bool"},
            "lock_reason": {"type": "str"},
        },
        supports_check_mode=True,
        required_together=[["workspace", "organization"]],
        required_if=[
            ("state", "absent", ("workspace_id", "workspace"), True),
            ("state", "present", ("workspace_id", "workspace"), True),
        ],
        mutually_exclusive=[
            ("workspace", "workspace_id"),
        ],
    )
    warnings = []
    result = {"changed": False, "warnings": warnings}
    action_result = {}
    params = module.params
    params["check_mode"] = module.check_mode

    try:
        client_terraform = TerraformClient(**module.params)

        if params["state"] == "present":
            # validate the format of the timestamp
            if params.get("auto_destroy_at"):
                datetime.strptime(params["auto_destroy_at"], "%Y-%m-%dT%H:%M:%SZ")
            # either workspace_id or workspace MUST be provided when state is present
            # when a workspace is provided, organization must be given
            if not params.get("workspace_id"):
                # get the workspace_id from the provided workspace name
                workspace_response = get_workspace(client_terraform, params["organization"], params["workspace"])
                if not workspace_response:
                    action_result = state_create(client_terraform, params, params["check_mode"])
                else:
                    # retrieve the workspace ID
                    workspace_id = workspace_response.get("data")["id"]
                    # update module params to have a workspace ID
                    params["workspace_id"] = workspace_id
                    action_result = state_update(client_terraform, params, params["check_mode"])
            else:
                # if workspace_id is provided then update is triggered
                action_result = state_update(client_terraform, params, params["check_mode"])
        elif params["state"] in ("absent", "locked", "unlocked"):
            # get the workspace response
            if not params.get("workspace_id"):
                workspace_response = get_workspace(client_terraform, params["organization"], params["workspace"])
                if not workspace_response:
                    raise ValueError(f"The workspace {params['workspace']} in {params['organization']} organization was not found.")
                params["workspace_id"] = workspace_response.get("data")["id"]
            else:
                workspace_response = get_workspace_by_id(client_terraform, params["workspace_id"])

            if params["state"] == "absent":
                action_result = state_absent(client_terraform, params, workspace_response, params["check_mode"])

            elif params["state"] == "locked":
                action_result = state_locked(client_terraform, params, workspace_response, params["check_mode"])

            elif params["state"] == "unlocked":
                action_result = state_unlocked(client_terraform, params, workspace_response, params["check_mode"])

        result.update(action_result)
        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()
