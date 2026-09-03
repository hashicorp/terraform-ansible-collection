.. _ansible_collections.hashicorp.terraform.docsite.cookbook_fleet_upgrade_campaign:

*****************************************
Run a fleet Terraform upgrade campaign
*****************************************

This cookbook uses HCP Terraform Explorer to discover workspaces on older Terraform versions,
tests a target version with plan-only runs, and retains the new version only for successful
canaries.

.. code-block:: text

   Explorer inventory -> bounded canary set -> update workspace version -> speculative plan
                                                      | passed             | failed
                                                      v                    v
                                                retain version       restore old version

The same pattern can drive staged campaigns by project, tag, workspace name, or saved Explorer
view. It changes the Terraform CLI version configured on a workspace; it does not edit provider
constraints, lock files, modules, or Terraform source code.

.. contents::
   :local:
   :depth: 2

Prerequisites and permissions
=============================

- Explorer must be available and populated for the organization. Its data is eventually
  consistent, so use the workspace API as the final authority before mutation.
- The token needs broad enough read permission for Explorer, plus permission to update each
  selected workspace and queue speculative plans.
- The target Terraform version must be available on the HCP Terraform/TFE instance and compatible
  with the configuration and providers.
- Pause normal deployments for the selected workspaces during the campaign.
- Start with a small canary batch. A passing plan is evidence of compatibility, not proof that an
  apply will be harmless.

Example input
=============

Save this as ``vars/upgrade.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   target_terraform_version: "1.14.3"
   workspace_name_filter: "-dev"
   maximum_batch_size: 5
   run_poll_timeout: 1200

Complete playbook
=================

Save this as ``upgrade-fleet.yml``:

.. code-block:: yaml

   ---
   - name: Upgrade a bounded HCP Terraform workspace canary fleet
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/upgrade.yml
     vars:
       upgrade_candidates: []
       upgrade_report: []
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Query candidate workspaces through Explorer
         hashicorp.terraform.explorer_info:
           organization: "{{ terraform_organization }}"
           view_type: workspaces
           filters:
             - field: workspace_name
               operator: contains
               value: "{{ workspace_name_filter }}"
           fields: "id,workspace_name,terraform_version"
           sort: workspace_name
           page_size: 100
         register: explorer_workspaces

       - name: Select workspaces that are not already on the target version
         ansible.builtin.set_fact:
           upgrade_candidates: >-
             {{ upgrade_candidates
                + [item.attributes | combine({'workspace_id': item.id})] }}
         loop: "{{ explorer_workspaces.rows }}"
         loop_control:
           label: "{{ item.attributes.workspace_name | default(item.id) }}"
         when:
           - item.id is defined
           - item.attributes.workspace_name is defined
           - item.attributes.terraform_version is defined
           - item.attributes.terraform_version != target_terraform_version

       - name: Fail closed when discovery returns an unexpectedly large batch
         ansible.builtin.assert:
           that:
             - upgrade_candidates | length <= maximum_batch_size | int
           fail_msg: >-
             Explorer selected {{ upgrade_candidates | length }} workspaces, above the
             approved maximum of {{ maximum_batch_size }}.

       - name: Re-read every candidate from the workspace API
         hashicorp.terraform.workspace_info:
           workspace_id: "{{ item.workspace_id }}"
         loop: "{{ upgrade_candidates }}"
         loop_control:
           label: "{{ item.workspace_name }}"
         register: authoritative_workspaces

       - name: Set the target Terraform version on each canary
         hashicorp.terraform.workspace:
           workspace_id: "{{ item.workspace.id }}"
           terraform_version: "{{ target_terraform_version }}"
           state: present
         loop: "{{ authoritative_workspaces.results }}"
         loop_control:
           label: "{{ item.workspace.name }}"
         register: workspace_updates

       - name: Run a speculative compatibility plan
         hashicorp.terraform.run:
           workspace_id: "{{ item.workspace.id }}"
           run_message: >-
             Terraform {{ target_terraform_version }} upgrade compatibility test
           plan_only: true
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         loop: "{{ authoritative_workspaces.results }}"
         loop_control:
           label: "{{ item.workspace.name }}"
         register: compatibility_runs
         ignore_errors: true

       - name: Restore the previous version on failed canaries
         hashicorp.terraform.workspace:
           workspace_id: "{{ item.item.workspace.id }}"
           terraform_version: "{{ item.item.workspace.terraform_version }}"
           state: present
         loop: "{{ compatibility_runs.results }}"
         loop_control:
           label: "{{ item.item.workspace.name }}"
         when: item.failed | default(false)

       - name: Build the campaign report
         ansible.builtin.set_fact:
           upgrade_report: >-
             {{ upgrade_report + [{
                  'workspace': item.item.workspace.name,
                  'workspace_id': item.item.workspace.id,
                  'previous_version': item.item.workspace.terraform_version,
                  'target_version': target_terraform_version,
                  'run_id': item.id | default(''),
                  'passed': not (item.failed | default(false))
                }] }}
         loop: "{{ compatibility_runs.results }}"
         loop_control:
           label: "{{ item.item.workspace.name }}"

       - name: Show the auditable campaign result
         ansible.builtin.debug:
           var: upgrade_report

       - name: Fail the campaign after every failed canary has been restored
         ansible.builtin.assert:
           that:
             - upgrade_report | selectattr('passed', 'equalto', false) | list | length == 0
           fail_msg: >-
             One or more speculative plans failed. Their previous workspace versions were
             restored; inspect the run IDs and update the Terraform source before retrying.

Expected behavior
=================

Passing canaries retain ``target_terraform_version``. Failed canaries are restored to the version
reported by the authoritative workspace read, and the playbook fails after attempting all
restorations. No Terraform apply is issued.

Run separate campaigns for production and require an approval between the speculative-plan report
and updating the durable workspace baseline. Do not treat Explorer's provider or module views as
instructions to edit source automatically.

Operational extensions
======================

- Save an Explorer view for each upgrade wave with :ansplugin:`hashicorp.terraform.explorer#module`.
- Group candidates by project or tags and set a lower ``maximum_batch_size`` for production.
- Attach mandatory policies and run tasks before testing a new Terraform version.
- Archive the Explorer query, before/after workspace versions, run IDs, plan results, and rollback
  actions in the change record.
- Repeat the query after Explorer catches up to verify fleet convergence.

.. seealso::

   - :ansplugin:`hashicorp.terraform.explorer_info#module`
   - :ansplugin:`hashicorp.terraform.workspace#module`
   - :ansplugin:`hashicorp.terraform.run#module`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs`
