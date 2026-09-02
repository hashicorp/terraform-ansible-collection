.. _ansible_collections.hashicorp.terraform.docsite.cookbook_governed_decommission:

***********************************
Decommission infrastructure safely
***********************************

This cookbook coordinates application shutdown with a reviewed Terraform destroy run and removes
the workspace only after Terraform confirms that managed resources were destroyed.

.. code-block:: text

   Terraform-backed inventory -> drain + backup -> destroy plan -> analyze -> approval
                                                                         -> apply same run
                                                                         -> delete workspace

Destruction is intentionally high risk. A destroy plan should not be forced through
``plan_safe`` merely to make it pass; use explicit decommission policy and human approval.

.. contents::
   :local:
   :depth: 2

Prerequisites and change controls
=================================

- Build the ``decommission_targets`` inventory group from ``tfc_inv`` or an approved Terraform
  output before deleting the workspace.
- Provide an idempotent ``application_decommission`` role that drains traffic, stops schedulers,
  deregisters service discovery, takes required backups, and records their identifiers.
- Pause deployments, run triggers, and application writes before planning destruction.
- The token needs permission to read the workspace and plan, queue and apply destroy runs, and
  delete an empty workspace.
- Set ``decommission_approved`` only through a change-management or Controller approval gate.
- Confirm retention, legal hold, DNS, certificates, backups, and dependent workspace obligations.

Example input
=============

Save this as ``vars/decommission.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   terraform_workspace: payments-legacy
   change_record: CHG-20481
   decommission_approved: false
   delete_workspace_after_destroy: true
   run_poll_timeout: 1800

Complete playbook
=================

Save this as ``decommission.yml`` and run it with the Terraform-backed inventory that defines
``decommission_targets``:

.. code-block:: yaml

   ---
   - name: Drain and preserve application data before infrastructure destruction
     hosts: decommission_targets
     gather_facts: true
     become: true
     serial: 1
     vars_files:
       - vars/decommission.yml
     tasks:
       - name: Execute the application-specific decommission contract
         ansible.builtin.include_role:
           name: application_decommission
         vars:
           decommission_change_record: "{{ change_record }}"

   - name: Destroy Terraform-managed infrastructure under approval
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/decommission.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Resolve the workspace after application drain succeeds
         hashicorp.terraform.workspace_info:
           organization: "{{ terraform_organization }}"
           workspace: "{{ terraform_workspace }}"
         register: decommission_workspace

       - name: Create a destroy plan without auto-apply
         hashicorp.terraform.run:
           workspace_id: "{{ decommission_workspace.workspace.id }}"
           run_message: "{{ change_record }} governed decommission"
           is_destroy: true
           auto_apply: false
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         register: destroy_run

       - name: Analyze the exact destroy plan
         hashicorp.terraform.plan_analyze:
           run_id: "{{ destroy_run.id }}"
           include_resource_changes: true
           detect_drift: true
         register: destroy_analysis

       - name: Find actions that are not pure deletes
         ansible.builtin.set_fact:
           unexpected_destroy_actions: >-
             {{ destroy_analysis.resource_changes
                | rejectattr('actions', 'equalto', ['delete'])
                | list }}

       - name: Validate the destroy plan shape and approval
         ansible.builtin.assert:
           that:
             - destroy_analysis.has_changes
             - unexpected_destroy_actions | length == 0
             - decommission_approved | bool
             - destroy_run.actions.is_confirmable | default(false)
           fail_msg: >-
             Destroy run {{ destroy_run.id }} is unapproved, empty, not confirmable, or contains
             an action other than delete. Leave it unapplied and inspect the plan.

       - name: Display the destructive evidence before apply
         ansible.builtin.debug:
           msg:
             change_record: "{{ change_record }}"
             workspace_id: "{{ decommission_workspace.workspace.id }}"
             run_id: "{{ destroy_run.id }}"
             resource_count: "{{ destroy_analysis.change_count }}"
             resources: >-
               {{ destroy_analysis.resource_changes | map(attribute='address') | list }}

       - name: Apply the exact approved destroy run
         hashicorp.terraform.promote_run:
           run_id: "{{ destroy_run.id }}"
           require_policy_pass: true
           allow_advisory_failures: false
           wait: true
           timeout: "{{ run_poll_timeout }}"
           comment: "{{ change_record }} approved infrastructure decommission"
         register: destroyed

       - name: Require a completed Terraform destruction
         ansible.builtin.assert:
           that:
             - destroyed.gates.applied | default(false)
             - destroyed.gates.run_status_after | default('') == 'applied'

       - name: Delete the now-empty workspace
         hashicorp.terraform.workspace:
           workspace_id: "{{ decommission_workspace.workspace.id }}"
           state: absent
         when: delete_workspace_after_destroy | bool

Failure and recovery
====================

If application drain or backup fails, no destroy run is created. If plan analysis or approval
fails, the infrastructure remains and the pending run must be discarded or reviewed manually.
If apply partially fails, retain the workspace and state, fix the provider or infrastructure
error, and create a new destroy plan. Never force-delete the workspace to hide a failed destroy.

The rollback boundary changes after destruction starts. Before apply, restore application traffic
and discard the plan. After resources are deleted, recovery is a new Terraform apply followed by
data restore; it is not a workspace undelete.

Reruns and audit evidence
=========================

The application role should report no change after a completed drain. Destroy runs are immutable
auditable events and are created only after the drain play succeeds. Once the workspace is
deleted, a full rerun is not expected to resolve it; use the retained change record to report that
the lifecycle is complete.

Store backup IDs, inventory snapshot, plan summary, destroyed resource addresses, run ID,
approver, apply result, and workspace deletion result outside the deleted workspace.

.. seealso::

   - :ansplugin:`hashicorp.terraform.run#module`
   - :ansplugin:`hashicorp.terraform.plan_analyze#module`
   - :ansplugin:`hashicorp.terraform.promote_run#module`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory`

