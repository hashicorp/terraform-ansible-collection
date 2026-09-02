.. _ansible_collections.hashicorp.terraform.docsite.cookbook_promote_known_good_configuration:

****************************************
Promote one known-good configuration
****************************************

This cookbook uploads Terraform configuration once and promotes that exact immutable
configuration version through development, staging, and production workspaces.

.. code-block:: text

   source archive -> one configuration version -> dev run -> staging run -> production run
                                                  |            |               |
                                             policy gate   policy gate     policy + approval

HCP Terraform and Terraform Enterprise support creating a run with a configuration version from
another workspace. That makes the configuration-version ID an infrastructure artifact: every
environment runs the same files while retaining its own variables, state, credentials, policies,
and approvals.

.. contents::
   :local:
   :depth: 2

Business outcome
================

The workflow provides evidence that production used the artifact already tested in lower
environments. It avoids rebuilding or repackaging Terraform configuration between stages and
keeps each approval attached to the exact run that was reviewed.

This is configuration promotion, not state promotion. Never copy state between the workspaces.

Prerequisites and permissions
=============================

- Install this collection and ``pytfe>=1.4.1`` and export ``TFE_TOKEN``. Set ``TFE_ADDRESS`` for
  Terraform Enterprise.
- Create the target workspaces before promotion. Their Terraform version and working directory
  must be compatible with the uploaded configuration.
- Configure environment-specific inputs through workspace variables or variable sets. Do not
  place production credentials or values in the promoted archive.
- The token needs permission to upload a configuration version to the artifact workspace, queue
  plans in every target workspace, read policy results, and apply eligible runs.
- Disable workspace auto-apply. The playbook uses ``promote_run`` after policy and human gates.

Example input
=============

Save the following as ``vars/promotion.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   artifact_workspace: payments-artifacts
   terraform_configuration: "{{ playbook_dir }}/terraform"
   run_poll_timeout: 1200

   promotion_targets:
     - name: payments-dev
       approval_prompt: false
     - name: payments-staging
       approval_prompt: false
     - name: payments-prod
       approval_prompt: true

For Automation Controller, replace the CLI prompt with a workflow approval node. Pass
``promotion_approved: true`` only to the continuation job on the approved path.

Complete promotion workflow
===========================

Save this as ``promote.yml``:

.. code-block:: yaml

   ---
   - name: Build and promote one Terraform configuration artifact
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/promotion.yml
     vars:
       promotion_approved: false
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Resolve the artifact workspace
         hashicorp.terraform.workspace_info:
           organization: "{{ terraform_organization }}"
           workspace: "{{ artifact_workspace }}"
         register: artifact_workspace_info

       - name: Upload the immutable configuration artifact
         hashicorp.terraform.configuration_version:
           workspace_id: "{{ artifact_workspace_info.workspace.id }}"
           configuration_files_path: "{{ terraform_configuration }}"
           auto_queue_runs: false
           poll_interval: 5
           poll_timeout: 300
           state: present
         register: promoted_configuration

       - name: Record the artifact identity before starting promotion
         ansible.builtin.debug:
           msg:
             configuration_version_id: "{{ promoted_configuration.id }}"
             source_workspace_id: "{{ artifact_workspace_info.workspace.id }}"

       - name: Promote the same artifact through each environment
         ansible.builtin.include_tasks: promote-environment.yml
         loop: "{{ promotion_targets }}"
         loop_control:
           loop_var: promotion_target
           label: "{{ promotion_target.name }}"

Save the sequential stage implementation as ``promote-environment.yml`` beside the playbook:

.. code-block:: yaml

   ---
   - name: Resolve target workspace - {{ promotion_target.name }}
     hashicorp.terraform.workspace_info:
       organization: "{{ terraform_organization }}"
       workspace: "{{ promotion_target.name }}"
     register: target_workspace

   - name: Plan the promoted artifact - {{ promotion_target.name }}
     hashicorp.terraform.run:
       workspace_id: "{{ target_workspace.workspace.id }}"
       configuration_version: "{{ promoted_configuration.id }}"
       run_message: >-
         Promote {{ promoted_configuration.id }} to {{ promotion_target.name }}
       auto_apply: false
       poll: true
       poll_interval: 10
       poll_timeout: "{{ run_poll_timeout }}"
       state: present
     register: target_run

   - name: Analyze the exact target plan - {{ promotion_target.name }}
     hashicorp.terraform.plan_analyze:
       run_id: "{{ target_run.id }}"
       include_resource_changes: true
       detect_drift: true
     register: target_plan

   - name: Display the promotion evidence - {{ promotion_target.name }}
     ansible.builtin.debug:
       msg:
         environment: "{{ promotion_target.name }}"
         configuration_version_id: "{{ promoted_configuration.id }}"
         run_id: "{{ target_run.id }}"
         summary: "{{ target_plan.summary }}"

   - name: Request production approval for this exact run
     ansible.builtin.pause:
       prompt: >-
         Approve run {{ target_run.id }} using configuration
         {{ promoted_configuration.id }} in {{ promotion_target.name }}? Type yes
     register: promotion_prompt
     when:
       - promotion_target.approval_prompt | bool
       - target_run.actions.is_confirmable | default(false)

   - name: Calculate approval for this stage
     ansible.builtin.set_fact:
       stage_approved: >-
         {{ (not (target_run.actions.is_confirmable | default(false)))
            or (not promotion_target.approval_prompt | bool)
            or ((promotion_prompt.user_input | default('no') | lower) == 'yes')
            or (promotion_approved | bool) }}

   - name: Apply after policy and approval gates - {{ promotion_target.name }}
     hashicorp.terraform.promote_run:
       run_id: "{{ target_run.id }}"
       require_policy_pass: true
       allow_advisory_failures: false
       wait: true
       timeout: "{{ run_poll_timeout }}"
       auto_apply_when_eligible: true
       comment: >-
         Promoted configuration {{ promoted_configuration.id }}
     register: promotion_result
     when:
       - stage_approved
       - target_run.actions.is_confirmable | default(false)

   - name: Discard a rejected target run
     hashicorp.terraform.run:
       run_id: "{{ target_run.id }}"
       state: discarded
     when:
       - not stage_approved
       - target_run.actions.is_discardable | default(false)

   - name: Stop promotion after a rejection or failed gate
     ansible.builtin.assert:
       that:
         - stage_approved
         - >-
           (not (target_run.actions.is_confirmable | default(false)))
           or (promotion_result.gates.applied | default(false))
       fail_msg: >-
         Promotion stopped at {{ promotion_target.name }} for run {{ target_run.id }}.

Because ``include_tasks`` loops sequentially, a rejected or failed lower environment prevents the
next environment from starting.

Reruns, rollback, and evidence
==============================

Uploading creates a new immutable configuration version, so a complete rerun intentionally
creates a new artifact ID. Use a source commit or archive digest in the surrounding CI/CD system
to avoid rebuilding a revision that has already been promoted.

Record the source revision, archive digest, configuration-version ID, target run IDs, policy
outcomes, approvers, and final statuses. A rollback is another reviewed configuration version;
do not reuse an old plan after workspace variables or infrastructure have changed.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_tf_policy`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.cookbook_provision_and_configure`
