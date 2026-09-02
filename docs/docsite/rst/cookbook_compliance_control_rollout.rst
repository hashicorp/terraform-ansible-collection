.. _ansible_collections.hashicorp.terraform.docsite.cookbook_compliance_control_rollout:

****************************************
Roll out compliance controls safely
****************************************

This cookbook introduces a policy and an external run task to a canary workspace in advisory
mode, captures evidence from a speculative run, and promotes both controls to mandatory
enforcement only after review.

.. code-block:: text

   policy source + run-task service -> advisory canary -> plan-only run -> outcomes
                                                                    -> approval
                                                                    -> mandatory rollout

Policy and run tasks serve different purposes. Policy evaluates Terraform data inside HCP
Terraform/TFE. A run task sends run context to an external service and waits for its callback.

.. contents::
   :local:
   :depth: 2

Prerequisites
=============

- Store reviewed Sentinel, OPA, or tf-policy source in version control. The example uses a
  standalone Sentinel policy loaded from a file.
- Operate a run-task service that verifies HMAC signatures, returns promptly, posts progress, and
  completes its callback within the platform timeout.
- Use a canary configuration that exercises the resources and attributes the controls evaluate.
- The token needs permission to manage policies, policy sets, run tasks, workspace associations,
  and speculative runs.
- Supply ``promote_controls: true`` only after reviewing all policy and task outcomes.

Example input
=============

Save this as ``vars/controls.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   canary_workspace_id: ws-canary123
   rollout_workspace_ids:
     - ws-canary123
     - ws-staging456
     - ws-production789

   policy_name: require-standard-tags
   policy_file: "{{ playbook_dir }}/policies/require-standard-tags.sentinel"
   run_task_name: security-plan-review
   run_task_url: https://security.example.com/tfc/run-task
   run_task_hmac_key: "{{ vault_run_task_hmac_key }}"
   promote_controls: false
   reviewed_canary_run_id: ""
   run_poll_timeout: 900

Complete rollout playbook
=========================

Save this as ``rollout-controls.yml``:

.. code-block:: yaml

   ---
   - name: Canary and promote Terraform compliance controls
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/controls.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Converge the policy in advisory mode
         hashicorp.terraform.policy:
           organization: "{{ terraform_organization }}"
           name: "{{ policy_name }}"
           kind: sentinel
           description: Standard tagging control under staged rollout
           enforcement_level: advisory
           policy_content: "{{ lookup('ansible.builtin.file', policy_file) }}"
           state: present
         register: canary_policy

       - name: Attach the advisory policy only to the canary
         hashicorp.terraform.policy_set:
           organization: "{{ terraform_organization }}"
           name: staged-platform-controls
           description: Controls promoted through an advisory canary
           kind: sentinel
           global: false
           overridable: false
           policy_ids:
             - "{{ canary_policy.id }}"
           workspace_ids:
             - "{{ canary_workspace_id }}"
           state: present
         register: control_set

       - name: Converge the external run task
         hashicorp.terraform.run_task:
           organization: "{{ terraform_organization }}"
           name: "{{ run_task_name }}"
           url: "{{ run_task_url }}"
           description: External security analysis under staged rollout
           enabled: true
           hmac_key: "{{ run_task_hmac_key }}"
           state: present
         register: security_task
         no_log: true

       - name: Attach the run task to the canary in advisory mode
         hashicorp.terraform.workspace_run_task:
           workspace_id: "{{ canary_workspace_id }}"
           run_task_id: "{{ security_task.id }}"
           enforcement_level: advisory
           stages:
             - post_plan
           state: present
         register: canary_task_association

       - name: Queue a canary speculative run
         hashicorp.terraform.run:
           workspace_id: "{{ canary_workspace_id }}"
           run_message: Advisory compliance-control canary
           plan_only: true
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         register: canary_run
         when: reviewed_canary_run_id | length == 0

       - name: Bind review and promotion to one canary run
         ansible.builtin.set_fact:
           effective_canary_run_id: >-
             {{ reviewed_canary_run_id
                if reviewed_canary_run_id | length > 0
                else canary_run.id }}

       - name: Read Sentinel policy-check evidence
         hashicorp.terraform.policy_check_info:
           run_id: "{{ effective_canary_run_id }}"
         register: canary_policy_checks

       - name: Read task stages and external-task evidence
         hashicorp.terraform.task_stage_info:
           run_id: "{{ effective_canary_run_id }}"
         register: canary_task_stages

       - name: Display the evidence that must be reviewed
         ansible.builtin.debug:
           msg:
             run_id: "{{ effective_canary_run_id }}"
             policy_checks: "{{ canary_policy_checks.policy_checks }}"
             task_stages: "{{ canary_task_stages.task_stages }}"

       - name: Publish the canary evidence for workflow approval
         ansible.builtin.set_stats:
           data:
             reviewed_canary_run_id: "{{ effective_canary_run_id }}"
             reviewed_policy_id: "{{ canary_policy.id }}"
             reviewed_policy_set_id: "{{ control_set.id }}"
             reviewed_run_task_id: "{{ security_task.id }}"
             reviewed_workspace_run_task_id: "{{ canary_task_association.id }}"
             reviewed_policy_checks: "{{ canary_policy_checks.policy_checks }}"
             reviewed_task_stages: "{{ canary_task_stages.task_stages }}"
           per_host: false

       - name: Report that controls remain advisory pending approval
         ansible.builtin.debug:
           msg: >-
             Advisory controls remain attached only to the canary. Review run
             {{ effective_canary_run_id }} and rerun through an approved continuation job.
         when: not promote_controls | bool

       - name: End successfully before mandatory rollout when not approved
         ansible.builtin.meta: end_play
         when: not promote_controls | bool

       - name: Promote the policy enforcement level
         hashicorp.terraform.policy:
           policy_id: "{{ canary_policy.id }}"
           enforcement_level: hard-mandatory
           policy_content: "{{ lookup('ansible.builtin.file', policy_file) }}"
           state: present

       - name: Expand the policy set to the approved fleet
         hashicorp.terraform.policy_set:
           policy_set_id: "{{ control_set.id }}"
           policy_ids:
             - "{{ canary_policy.id }}"
           workspace_ids: "{{ rollout_workspace_ids }}"
           state: present

       - name: Enforce the run task on the approved fleet
         hashicorp.terraform.workspace_run_task:
           workspace_id: "{{ item }}"
           run_task_id: "{{ security_task.id }}"
           enforcement_level: mandatory
           stages:
             - post_plan
           state: present
         loop: "{{ rollout_workspace_ids }}"
         loop_control:
           label: "{{ item }}"

Controller workflow pattern
===========================

In production, split the example at the ``promote_controls`` assertion:

#. The canary job publishes the run ID, policy IDs, policy-set ID, run-task ID, association ID,
   checks, and task stages as workflow artifacts.
#. An approval node links to the HCP Terraform run and external scanner evidence.
#. The continuation job re-reads the same run before changing enforcement and receives the exact
   approved workspace-ID list from change control.

Do not make an organization-global run task mandatory as the first rollout step. A timeout or
service outage can block every Terraform run in scope.

Rollback and idempotency
========================

Return the policy to ``advisory`` and workspace run-task associations to ``advisory`` before
debugging a control outage. Removing an association does not delete the organization-scoped run
task. Keep the task disabled rather than deleting it when evidence must be preserved.

Policy content, metadata, memberships, and workspace associations are diffed on rerun. The run
task HMAC key is write-only and cannot participate in drift detection; rotate it through a
versioned secret procedure and coordinated service update.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_tf_policy`
   - :ansplugin:`hashicorp.terraform.policy#module`
   - :ansplugin:`hashicorp.terraform.policy_set#module`
   - :ansplugin:`hashicorp.terraform.run_task#module`
   - :ansplugin:`hashicorp.terraform.workspace_run_task#module`
