.. _ansible_collections.hashicorp.terraform.docsite.cookbook_application_onboarding:

******************************
Application onboarding factory
******************************

This cookbook turns a small application definition into an idempotent HCP Terraform or Terraform
Enterprise landing zone. It creates the project, team, workspace baseline, variables, access
grant, policy-set attachment, run-task attachment, tags, and notifications needed before the
application team uploads Terraform configuration.

.. code-block:: text

   application definition
          |
          v
   Ansible factory -> project -> workspace -> variables and controls -> application team

.. contents::
   :local:
   :depth: 2

Business outcome
================

Platform teams can offer onboarding as a reviewed data change instead of a sequence of manual UI
operations. Re-running the same definition converges drift and reports ``changed: false`` once the
landing zone matches the requested state.

This cookbook creates the control-plane baseline only. Provisioning starts later, when an approved
Terraform configuration version and run are submitted to the workspace.

Prerequisites, permissions, and limitations
===========================================

- Install this collection and ``pytfe>=1.4.1`` and export ``TFE_TOKEN``. Set ``TFE_ADDRESS`` for
  Terraform Enterprise.
- The token needs permission to manage projects, workspaces, teams, variable sets, policies,
  policy sets, run-task associations, and notification configurations.
- Create the policies named by ``baseline_policy_ids`` beforehand. The factory creates an
  application-specific policy set and puts those policies in it.
- Create the organization-scoped run task named by ``run_task_name`` beforehand. This workflow
  manages its association with the new workspace, not the external run-task service.
- The notification endpoint must be reachable from HCP Terraform/TFE and return a successful
  response to the verification request sent when the notification is created.
- Policy engines, project-scoped policy sets, run tasks, and some workspace settings depend on the
  HCP Terraform edition and Terraform Enterprise version in use.
- The collection can create a team and its access grant, but team membership should normally come
  from the organization's identity provider and SSO group mapping.

The policy set and variable set in this example are deliberately application-specific. Their
membership options are authoritative lists. Reusing one shared set while passing only the new
project ID would detach projects that are not in that invocation.

Example application definition
==============================

Save this as ``vars/app-payments-dev.yml`` and replace the IDs and URLs with values from your
organization:

.. code-block:: yaml

   ---
   terraform_organization: acme

   application:
     name: payments
     environment: dev
     terraform_version: "1.9.8"
     project_description: Payments application development landing zone
     team_name: payments-developers
     team_access: write
     tags:
       application: payments
       environment: dev
       owner: payments-team

   variable_set_variables:
     - key: region
       value: us-east-1
       category: terraform
       description: Approved deployment region
     - key: TF_LOG
       value: ERROR
       category: env
       description: Terraform log level

   workspace_variables:
     - key: instance_count
       value: "2"
       category: terraform
       description: Development instance count

   baseline_policy_kind: sentinel
   baseline_policy_ids:
     - pol-replace-with-approved-policy-id

   run_task_name: security-scan
   notification:
     name: platform-events
     url: https://eda.example.com/endpoint
     triggers:
       - "run:completed"
       - "run:errored"
       - "run:needs_attention"

Complete playbook
=================

Save this as ``onboard-application.yml``:

.. code-block:: yaml

   ---
   - name: Converge an application landing zone
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/app-payments-dev.yml
     vars:
       project_name: "{{ application.name }}-{{ application.environment }}"
       workspace_name: "{{ application.name }}-{{ application.environment }}"
       variable_set_name: "{{ project_name }}-variables"
       policy_set_name: "{{ project_name }}-baseline"
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Validate the onboarding request
         ansible.builtin.assert:
           that:
             - application.name | length > 0
             - application.environment | length > 0
             - baseline_policy_ids | length > 0
             - notification.url | length > 0
           fail_msg: The application definition is incomplete.

       - name: Converge the application project
         hashicorp.terraform.project:
           organization: "{{ terraform_organization }}"
           project: "{{ project_name }}"
           description: "{{ application.project_description }}"
           default_execution_mode: remote
           tag_bindings: >-
             {{ application.tags
                | dict2items(key_name='key', value_name='value') }}
           state: present
         register: app_project

       - name: Converge the application team
         hashicorp.terraform.team:
           organization: "{{ terraform_organization }}"
           name: "{{ application.team_name }}"
           visibility: organization
           allow_member_token_management: false
           state: present
         register: app_team

       - name: Converge the application workspace
         hashicorp.terraform.workspace:
           organization: "{{ terraform_organization }}"
           workspace: "{{ workspace_name }}"
           project_id: "{{ app_project.id }}"
           description: "{{ application.name }} {{ application.environment }} workspace"
           terraform_version: "{{ application.terraform_version }}"
           execution_mode: remote
           auto_apply: false
           tag_bindings: "{{ application.tags }}"
           state: present
         register: app_workspace

       - name: Converge the application variable set and project attachment
         hashicorp.terraform.variable_sets:
           organization: "{{ terraform_organization }}"
           name: "{{ variable_set_name }}"
           description: "Shared inputs for {{ project_name }}"
           global: false
           priority: false
           project_ids:
             - "{{ app_project.id }}"
           state: present
         register: app_variable_set

       - name: Converge variables in the application variable set
         hashicorp.terraform.variable:
           variable_set_id: "{{ app_variable_set.id }}"
           key: "{{ item.key }}"
           value: "{{ item.value }}"
           category: "{{ item.category }}"
           description: "{{ item.description | default(omit) }}"
           hcl: "{{ item.hcl | default(false) }}"
           sensitive: "{{ item.sensitive | default(false) }}"
           state: present
         loop: "{{ variable_set_variables }}"
         loop_control:
           label: "{{ item.key }}"
         register: app_variable_set_values
         no_log: true

       - name: Converge workspace-specific variables
         hashicorp.terraform.variable:
           workspace_id: "{{ app_workspace.id }}"
           key: "{{ item.key }}"
           value: "{{ item.value }}"
           category: "{{ item.category }}"
           description: "{{ item.description | default(omit) }}"
           hcl: "{{ item.hcl | default(false) }}"
           sensitive: "{{ item.sensitive | default(false) }}"
           state: present
         loop: "{{ workspace_variables }}"
         loop_control:
           label: "{{ item.key }}"
         register: app_workspace_values
         no_log: true

       - name: Converge team access to the project
         hashicorp.terraform.team_project_access:
           team_id: "{{ app_team.id }}"
           project_id: "{{ app_project.id }}"
           access: "{{ application.team_access }}"
           state: present
         register: app_team_access

       - name: Converge the application policy set
         hashicorp.terraform.policy_set:
           organization: "{{ terraform_organization }}"
           name: "{{ policy_set_name }}"
           description: "Approved baseline controls for {{ project_name }}"
           kind: "{{ baseline_policy_kind }}"
           global: false
           overridable: false
           policy_ids: "{{ baseline_policy_ids }}"
           project_ids:
             - "{{ app_project.id }}"
           state: present
         register: app_policy_set

       - name: Attach the approved run task to the workspace
         hashicorp.terraform.workspace_run_task:
           organization: "{{ terraform_organization }}"
           workspace: "{{ workspace_name }}"
           run_task_name: "{{ run_task_name }}"
           enforcement_level: mandatory
           stages:
             - post_plan
           state: present
         register: app_run_task
         when: run_task_name | default('') | length > 0

       - name: Converge workspace notifications
         hashicorp.terraform.notification_configuration:
           workspace_id: "{{ app_workspace.id }}"
           name: "{{ notification.name }}"
           destination_type: generic
           url: "{{ notification.url }}"
           enabled: true
           triggers: "{{ notification.triggers }}"
           state: present
         register: app_notification

       - name: Report whether any landing-zone component changed
         ansible.builtin.set_fact:
           onboarding_changed: >-
             {{ app_project.changed
                or app_team.changed
                or app_workspace.changed
                or app_variable_set.changed
                or app_variable_set_values.changed
                or app_workspace_values.changed
                or app_team_access.changed
                or app_policy_set.changed
                or (app_run_task.changed | default(false))
                or app_notification.changed }}

       - name: Show the onboarding result
         ansible.builtin.debug:
           msg:
             application: "{{ application.name }}"
             environment: "{{ application.environment }}"
             project_id: "{{ app_project.id }}"
             workspace_id: "{{ app_workspace.id }}"
             changed: "{{ onboarding_changed }}"

Run the same request twice to demonstrate convergence:

.. code-block:: bash

   export TFE_TOKEN="<token>"
   ansible-playbook onboard-application.yml
   ansible-playbook onboard-application.yml

Expected result and idempotent rerun
====================================

The first run reports each created component and prints ``changed: true`` in the final summary.
With the same input, the second run prints the same stable IDs and ``changed: false``. Changing a
tag, access level, variable, policy membership, run-task stage, or notification trigger converges
only that component.

Sensitive variable values are write-only in the Terraform API. The collection intentionally
treats an otherwise identical sensitive variable as unchanged because it cannot compare the
stored value. Rotate one by also changing its description or by deleting and recreating it. See
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_variables.sensitive`.

Approval, failure, and rollback
===============================

Treat the input file as the approval object: validate it in source control, require review from
the platform owner and application owner, and let automation apply only merged definitions.

If the play fails partway through, rerun the same definition. Every completed module is
idempotent, so the factory resumes at the missing or drifted component. Do not delete the whole
landing zone just because a later notification or run-task attachment failed.

Rollback is another reviewed definition. For example, reduce a team's access or remove a policy
from this application-specific set and rerun. Deleting a durable application is a separate,
explicit workflow because it can affect infrastructure and access records.

Cleanup
=======

For approved decommissioning, remove resources in dependency order:

#. Destroy managed infrastructure with a reviewed Terraform destroy run.
#. Remove the workspace run-task association and notification configuration.
#. Delete the empty workspace without ``force``.
#. Remove the team-project access grant.
#. Delete the application-specific policy set and variable set.
#. Delete the project after it contains no workspaces.
#. Delete the team only if it is application-specific and no longer used elsewhere.

Keep the team, policy objects, and organization-scoped run task when they are shared platform
resources. Use ``state: absent`` on the same modules and identify resources by their IDs wherever
possible.

Production hardening
====================

- Validate the application definition against a schema before running the playbook.
- Split platform-owned values and application-owned values into separately reviewed files.
- Source sensitive variables from Vault or a secret manager and keep ``no_log: true``.
- Add an HMAC token to generic notifications and validate the signature at the ingress. See
  :ref:`ansible_collections.hashicorp.terraform.docsite.cookbook_event_driven_post_apply`.
- Pin policy IDs, run-task names, Terraform versions, and collection versions.
- Run one onboarding job per application/environment key to prevent concurrent reconciliation.
- Export component IDs to a service catalog or CMDB so later workflows do not rely only on names.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_variables`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_teams_and_access`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_workspace_bootstrap`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs`
