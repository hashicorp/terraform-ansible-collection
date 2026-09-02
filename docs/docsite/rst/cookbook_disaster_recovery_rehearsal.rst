.. _ansible_collections.hashicorp.terraform.docsite.cookbook_disaster_recovery_rehearsal:

******************************************
Rehearse disaster recovery end to end
******************************************

This cookbook creates an isolated recovery environment from a known-good Terraform configuration,
restores application data with Ansible, validates the service, records recovery evidence, and
destroys the rehearsal environment.

.. code-block:: text

   approved configuration version -> temporary DR workspace -> Terraform apply
          -> outputs become inventory -> restore + validate -> record RTO/RPO -> destroy

The collection orchestrates HCP Terraform control-plane and run operations. Application backups,
database restores, DNS isolation, and service validation remain normal Ansible responsibilities.

.. contents::
   :local:
   :depth: 2

Prerequisites and isolation
===========================

- Supply a previously approved ``configuration_version_id``. The version may originate from
  another workspace.
- Use a dedicated recovery account/subscription/project, network, DNS zone, and credential scope.
  A rehearsal must not receive production traffic or write to production data stores.
- Provide an ``ansible_hosts`` Terraform output using the contract documented in
  :ref:`ansible_collections.hashicorp.terraform.docsite.cookbook_provision_and_configure`.
- Provide an idempotent ``restore_and_validate`` role that accepts a backup identifier and records
  application-level validation results.
- The HCP Terraform token needs permission to create and delete the temporary workspace, manage
  its variables, queue and apply runs, and read outputs.
- Obtain explicit approval for both provisioning cost and final destruction.

Example input
=============

Save this as ``vars/dr-rehearsal.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   dr_workspace: payments-dr-rehearsal-20260902
   dr_project_id: prj-dr123
   dr_region: us-west-2
   approved_configuration_version_id: cv-abc123
   backup_id: payments-20260902T010000Z
   expected_recovery_point: "2026-09-02T01:00:00Z"
   run_poll_timeout: 1800
   cleanup_approved: true

Complete rehearsal
==================

Save this as ``dr-rehearsal.yml``:

.. code-block:: yaml

   ---
   - name: Provision an isolated disaster-recovery environment
     hosts: localhost
     connection: local
     gather_facts: true
     vars_files:
       - vars/dr-rehearsal.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Capture the rehearsal start time
         ansible.builtin.set_fact:
           rehearsal_started_at: "{{ ansible_date_time.iso8601 }}"

       - name: Bootstrap the temporary DR workspace
         hashicorp.terraform.workspace_bootstrap:
           organization: "{{ terraform_organization }}"
           workspace: "{{ dr_workspace }}"
           settings:
             project_id: "{{ dr_project_id }}"
             execution_mode: remote
             auto_apply: false
           reconcile: false
         register: dr_baseline

       - name: Set the isolated recovery region
         hashicorp.terraform.variable:
           workspace_id: "{{ dr_baseline.workspace_id }}"
           key: region
           value: "{{ dr_region }}"
           category: terraform
           description: Disaster-recovery rehearsal region
           state: present

       - name: Plan the approved configuration in the DR workspace
         hashicorp.terraform.run:
           workspace_id: "{{ dr_baseline.workspace_id }}"
           configuration_version: "{{ approved_configuration_version_id }}"
           run_message: "DR rehearsal from backup {{ backup_id }}"
           auto_apply: false
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         register: dr_plan

       - name: Apply after mandatory policy checks pass
         hashicorp.terraform.promote_run:
           run_id: "{{ dr_plan.id }}"
           require_policy_pass: true
           allow_advisory_failures: false
           wait: true
           timeout: "{{ run_poll_timeout }}"
           comment: Approved disaster-recovery rehearsal
         register: dr_apply

       - name: Require successful infrastructure recovery
         ansible.builtin.assert:
           that:
             - dr_apply.gates.applied | default(false)
             - dr_apply.gates.run_status_after | default('') == 'applied'

       - name: Read the deliberate recovery-host contract
         ansible.builtin.set_fact:
           recovered_hosts: >-
             {{ lookup('hashicorp.terraform.tf_output',
                       name='ansible_hosts',
                       workspace_id=dr_baseline.workspace_id) }}

       - name: Build isolated in-memory inventory
         ansible.builtin.add_host:
           name: "{{ item.name }}"
           ansible_host: "{{ item.address }}"
           ansible_user: "{{ item.ansible_user | default(omit) }}"
           groups:
             - dr_rehearsal_targets
         loop: "{{ recovered_hosts }}"
         loop_control:
           label: "{{ item.name }}"
         no_log: true

   - name: Restore and validate the recovered application
     hosts: dr_rehearsal_targets
     gather_facts: true
     become: true
     vars_files:
       - vars/dr-rehearsal.yml
     tasks:
       - name: Restore data and execute application checks
         ansible.builtin.include_role:
           name: restore_and_validate
         vars:
           recovery_backup_id: "{{ backup_id }}"
           recovery_point_expected: "{{ expected_recovery_point }}"

   - name: Record evidence and remove the rehearsal environment
     hosts: localhost
     connection: local
     gather_facts: true
     vars_files:
       - vars/dr-rehearsal.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Create the local evidence directory
         ansible.builtin.file:
           path: "{{ playbook_dir }}/artifacts"
           state: directory
           mode: "0700"

       - name: Record recovery rehearsal evidence
         ansible.builtin.copy:
           dest: "{{ playbook_dir }}/artifacts/{{ dr_workspace }}.json"
           mode: "0600"
           content: >-
             {{ {
                  'workspace': dr_workspace,
                  'configuration_version_id': approved_configuration_version_id,
                  'provision_run_id': dr_plan.id,
                  'backup_id': backup_id,
                  'expected_recovery_point': expected_recovery_point,
                  'started_at': rehearsal_started_at,
                  'validated_at': ansible_date_time.iso8601
                } | to_nice_json }}

       - name: Require cleanup approval
         ansible.builtin.assert:
           that:
             - cleanup_approved | bool

       - name: Create the rehearsal destroy run
         hashicorp.terraform.run:
           workspace_id: "{{ dr_baseline.workspace_id }}"
           run_message: Destroy completed DR rehearsal
           is_destroy: true
           auto_apply: false
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         register: dr_destroy

       - name: Apply the exact cleanup run
         hashicorp.terraform.promote_run:
           run_id: "{{ dr_destroy.id }}"
           require_policy_pass: true
           allow_advisory_failures: false
           wait: true
           timeout: "{{ run_poll_timeout }}"
           comment: Approved DR rehearsal cleanup
         register: dr_destroyed

       - name: Delete the empty rehearsal workspace
         hashicorp.terraform.workspace:
           workspace_id: "{{ dr_baseline.workspace_id }}"
           state: absent
         when: dr_destroyed.gates.run_status_after | default('') == 'applied'

Failure and cleanup design
==========================

Run cleanup from an Automation Controller ``always`` workflow branch so it executes even when
restore or validation fails. Preserve failed infrastructure temporarily only when incident
analysis is explicitly approved; otherwise create a reviewed destroy run.

This collection does not download, upload, or restore raw Terraform state. The backup referenced
here is application data managed by the recovery role. Terraform reconstructs infrastructure from
configuration and environment-specific inputs.

Production hardening
====================

- Use immutable backup IDs and verify checksums before restoration.
- Validate application behavior, data age, dependency reachability, monitoring, and failover DNS.
- Measure both recovery time and recovery point objectives from recorded timestamps.
- Mask host connection data and store evidence in a controlled audit system rather than a local
  artifact directory in production.
- Use cost, naming, tag, and maximum-lifetime policies for every rehearsal workspace.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.cookbook_promote_known_good_configuration`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.cookbook_ephemeral_environment`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory`
