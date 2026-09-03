.. _ansible_collections.hashicorp.terraform.docsite.cookbook_terraform_actions:

******************************************
Govern day-two operations with Actions
******************************************

This cookbook uses Ansible for prechecks and approval, invokes a provider-defined Terraform Action
through an HCP Terraform run, and validates the service afterward.

.. code-block:: text

   operational request -> Ansible prechecks -> plan-only action preview -> approval
                         -> action-only execution run -> Ansible health validation

Terraform Actions represent provider operations such as invoking a function or running an
operational automation. They do not create, change, or destroy Terraform-managed resources. They
are not a replacement for a normal apply when desired infrastructure must change.

.. contents::
   :local:
   :depth: 2

Prerequisites
=============

- Use Terraform 1.14 or later and an HCP Terraform plan that supports Actions.
- Declare the action in the workspace's current Terraform configuration and use a provider that
  implements the desired action.
- Use a plan-only action preview before the execution run. Direct action invocation is represented
  by a separate action-only run rather than applying the speculative preview.
- Give the HCP Terraform run identity only the provider permissions required by the action.
- Make the operation idempotent or supply an external request ID. Retrying an action can repeat its
  side effect even though Terraform-managed resources do not change.
- The token needs permission to queue and apply runs in the workspace.

Example input
=============

Save this as ``vars/action.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   terraform_workspace: payments-prod
   action_addresses:
     - action.aws_lambda_invoke.rotate_cache
   approved_action_addresses:
     - action.aws_lambda_invoke.rotate_cache
   operation_request_id: INC-48152
   operation_approved: false
   service_health_url: https://payments.example.com/health
   expected_health_status: 200
   run_poll_timeout: 900

Complete operational playbook
=============================

Save this as ``invoke-action.yml``:

.. code-block:: yaml

   ---
   - name: Execute a governed Terraform Action
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/action.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Validate the external request and action allowlist
         ansible.builtin.assert:
           that:
             - operation_request_id | length > 0
             - action_addresses | length > 0
             - >-
               action_addresses
               | difference(approved_action_addresses)
               | length == 0

       - name: Verify the service is reachable before the operation
         ansible.builtin.uri:
           url: "{{ service_health_url }}"
           method: GET
           status_code: "{{ expected_health_status }}"
           return_content: false
         register: health_before

       - name: Resolve the target workspace
         hashicorp.terraform.workspace_info:
           organization: "{{ terraform_organization }}"
           workspace: "{{ terraform_workspace }}"
         register: action_workspace

       - name: Create a plan-only preview of the action invocation
         hashicorp.terraform.run:
           workspace_id: "{{ action_workspace.workspace.id }}"
           invoke_action_addrs: "{{ action_addresses }}"
           run_message: >-
             {{ operation_request_id }} action preview
           plan_only: true
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         register: action_run

       - name: Re-read the preview before approval
         hashicorp.terraform.run_info:
           run_id: "{{ action_run.id }}"
         register: reviewed_action_run

       - name: Bind execution to the previewed configuration version
         ansible.builtin.set_fact:
           reviewed_configuration_version_id: >-
             {{ reviewed_action_run.run.configuration_version.id }}

       - name: Require explicit approval for the previewed operation
         ansible.builtin.assert:
           that:
             - operation_approved | bool
             - reviewed_action_run.run.plan_only | bool
           fail_msg: >-
             Action preview {{ action_run.id }} was not approved. Review its configuration
             version and action addresses before continuing.

       - name: Create the approved action-only execution run
         hashicorp.terraform.run:
           workspace_id: "{{ action_workspace.workspace.id }}"
           configuration_version: "{{ reviewed_configuration_version_id }}"
           invoke_action_addrs: "{{ action_addresses }}"
           run_message: >-
             {{ operation_request_id }} approved action invocation;
             preview {{ action_run.id }}
           auto_apply: true
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         register: invoked_action

       - name: Require the action run to finish successfully
         ansible.builtin.assert:
           that:
             - invoked_action.invoke_action_addrs == action_addresses
             - invoked_action.status in ['applied', 'planned_and_finished']

       - name: Wait for the service to become healthy after the action
         ansible.builtin.uri:
           url: "{{ service_health_url }}"
           method: GET
           status_code: "{{ expected_health_status }}"
           return_content: false
         register: health_after
         until: health_after.status | int == expected_health_status | int
         retries: 30
         delay: 10

Approval and retry model
========================

In Automation Controller, split the workflow after the preview is created. Publish the preview
run ID, configuration-version ID, action addresses, workspace, request ID, and precheck result as
workflow artifacts. The continuation job must re-read the preview and create the execution run
with the same configuration version and action addresses. A speculative preview itself cannot be
applied.

If the HCP Terraform run times out or the postcheck fails, inspect the action invocation history
before retrying. A transport failure does not prove the provider operation had no effect. Design
the underlying action around an idempotency key whenever possible.

Security and evidence
=====================

- Maintain an explicit action-address allowlist independent of user-supplied extra variables.
- Separate request, approval, and execution identities.
- Record the operation request, workspace, action addresses, run ID, approver, provider result,
  and before/after health checks.
- Use normal Terraform plans for resource lifecycle changes and Ansible roles for configuration
  convergence. Keep Actions focused on bounded operational commands.

.. seealso::

   - :ansplugin:`hashicorp.terraform.run#module`
   - :ansplugin:`hashicorp.terraform.run_info#module`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs`
