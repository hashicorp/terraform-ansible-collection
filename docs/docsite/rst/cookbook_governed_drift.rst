.. _ansible_collections.hashicorp.terraform.docsite.cookbook_governed_drift:

*****************************
Governed drift reconciliation
*****************************

This cookbook detects real-world infrastructure drift, classifies the changed attributes, and
requires an explicit policy and human decision before changing Terraform state.

It distinguishes two different outcomes:

- **Accept approved drift**: apply a refresh-only run so Terraform state records the current
  infrastructure. This does not change the cloud resource.
- **Remediate rejected drift**: discard the refresh-only run and, through a separate normal run,
  optionally change the cloud resource back to the Terraform configuration.

.. code-block:: text

   refresh-only plan -> plan_analyze -> plan_guard -> approval
          |                                      |
          | safe and approved                    | unsafe or rejected
          v                                      v
   apply the SAME refresh run             discard refresh run
                                                   |
                                                   v
                                      optional reviewed normal apply

.. contents::
   :local:
   :depth: 2

Prerequisites and permissions
=============================

- Install this collection and ``pytfe>=1.4.1`` and export ``TFE_TOKEN``. Set ``TFE_ADDRESS`` for
  Terraform Enterprise.
- The token needs permission to read the workspace and plan JSON, create runs, and apply or
  discard runs. Applying runs generally requires a user or team token with workspace run access.
- The workspace must use remote or agent execution and already have a current Terraform
  configuration and state.
- Define allow and deny rules for your providers and risk model. The example rules are
  illustrative and must not be adopted without review.
- Disable workspace auto-apply for this workflow. A refresh-only run must remain pending until
  the guard and approval steps complete.

``plan_guard`` is a client-side attribute gate. It complements, but does not replace, Sentinel,
OPA, tf-policy, run tasks, or the HCP Terraform/TFE permissions that govern server-side runs.

Example decision policy
=======================

Save this as ``vars/drift-policy.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   terraform_workspace: payments-prod
   run_poll_timeout: 900

   # Rules match <module_path>.<resource_type>.<name>.<attribute_path>.
   allow_rules:
     - "*.tags"
     - "*.tags.*"

   deny_rules:
     - "aws_security_group.*.ingress"
     - "aws_security_group.*.egress"
     - "aws_iam_policy.*"
     - "aws_instance.*.instance_type"

   guard_mode: strict

   # CLI runs can prompt after analysis. For Automation Controller, set this
   # false and supply trusted_approval only after a workflow approval gate.
   interactive_approval: true
   trusted_approval: false

   # True remediation is deliberately separate and disabled by default.
   remediate_unsafe_drift: false
   approve_normal_apply: false

Strict mode fails closed: unmatched attributes and computed or unknown changes are unsafe. Deny
rules and attributes classified as blocked by ``plan_analyze`` always win over allow rules.

Complete playbook
=================

Save this as ``govern-drift.yml``:

.. code-block:: yaml

   ---
   - name: Detect and govern Terraform drift
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/drift-policy.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Resolve the workspace
         hashicorp.terraform.workspace_info:
           organization: "{{ terraform_organization }}"
           workspace: "{{ terraform_workspace }}"
         register: workspace_info

       - name: Create a refresh-only plan without auto-apply
         hashicorp.terraform.run:
           workspace_id: "{{ workspace_info.workspace.id }}"
           run_message: Detect drift for governed reconciliation
           refresh_only: true
           auto_apply: false
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         register: refresh_run

       - name: Analyze the plan from this exact refresh-only run
         hashicorp.terraform.plan_analyze:
           run_id: "{{ refresh_run.id }}"
           detect_drift: true
           include_resource_changes: true
           blocked_attributes: "{{ deny_rules }}"
         register: drift_analysis

       - name: Evaluate the authoritative drift decision
         ansible.builtin.set_fact:
           drift_guard: >-
             {{ drift_analysis
                | hashicorp.terraform.plan_guard(
                    allow=allow_rules,
                    deny=deny_rules,
                    mode=guard_mode) }}

       - name: Show the auditable decision
         ansible.builtin.debug:
           msg:
             run_id: "{{ refresh_run.id }}"
             has_drift: "{{ drift_analysis.has_drift }}"
             safe_to_refresh: "{{ drift_guard.safe_to_refresh }}"
             summary: "{{ drift_guard.summary }}"
             reasons: "{{ drift_guard.reasons }}"
             denied: "{{ drift_guard.denied }}"
             blocked: "{{ drift_guard.blocked }}"
             unknown: "{{ drift_guard.unknown }}"

       - name: Ask a CLI operator to approve safe drift
         ansible.builtin.pause:
           prompt: >-
             Run {{ refresh_run.id }} is allowed by policy. Type yes to accept
             this drift into Terraform state; any other response discards it
         register: approval_prompt
         when:
           - interactive_approval | bool
           - drift_guard.safe_to_refresh
           - refresh_run.actions.is_confirmable | default(false)

       - name: Calculate the final approval decision
         ansible.builtin.set_fact:
           drift_approved: >-
             {{ drift_guard.safe_to_refresh
                and (
                  (interactive_approval | bool
                   and (approval_prompt.user_input | default('no') | lower) == 'yes')
                  or
                  (not interactive_approval | bool and trusted_approval | bool)
                ) }}

       - name: Apply the same refresh-only run when safe and approved
         hashicorp.terraform.run:
           run_id: "{{ refresh_run.id }}"
           run_message: Accept approved drift into Terraform state
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: applied
         register: accepted_refresh
         when:
           - drift_approved
           - refresh_run.actions.is_confirmable | default(false)

       - name: Discard a rejected or unsafe refresh-only run
         hashicorp.terraform.run:
           run_id: "{{ refresh_run.id }}"
           run_message: Drift was unsafe or not approved
           poll: true
           state: discarded
         register: discarded_refresh
         when:
           - not drift_approved
           - refresh_run.actions.is_discardable | default(false)

       - name: Report a no-drift terminal run
         ansible.builtin.debug:
           msg: "Run {{ refresh_run.id }} found no actionable drift; no state update was required."
         when:
           - not (refresh_run.actions.is_confirmable | default(false))
           - not (refresh_run.actions.is_discardable | default(false))

       - name: Create a separate normal plan to remediate unsafe drift
         hashicorp.terraform.run:
           workspace_id: "{{ workspace_info.workspace.id }}"
           run_message: Remediate rejected drift back to Terraform configuration
           auto_apply: false
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         register: remediation_run
         when:
           - not drift_guard.safe_to_refresh
           - remediate_unsafe_drift | bool

       - name: Analyze the separate remediation plan
         hashicorp.terraform.plan_analyze:
           run_id: "{{ remediation_run.id }}"
           detect_drift: true
           include_resource_changes: true
         register: remediation_analysis
         when:
           - remediation_run is not skipped
           - remediation_run.id is defined

       - name: Show the normal plan before infrastructure remediation
         ansible.builtin.debug:
           msg:
             run_id: "{{ remediation_run.id }}"
             summary: "{{ remediation_analysis.summary }}"
             changes: "{{ remediation_analysis.resource_changes }}"
         when:
           - remediation_analysis is not skipped
           - remediation_analysis.summary is defined

       - name: Apply the normal run only after separate approval and policy checks
         hashicorp.terraform.promote_run:
           run_id: "{{ remediation_run.id }}"
           require_policy_pass: true
           allow_advisory_failures: false
           wait: true
           timeout: "{{ run_poll_timeout }}"
           comment: Approved remediation of rejected drift
         register: remediation_result
         when:
           - remediation_run is not skipped
           - remediation_run.id is defined
           - approve_normal_apply | bool

       - name: Discard an unapproved normal remediation plan
         hashicorp.terraform.run:
           run_id: "{{ remediation_run.id }}"
           run_message: Normal remediation was not approved
           state: discarded
         when:
           - remediation_run is not skipped
           - remediation_run.id is defined
           - not approve_normal_apply | bool
           - remediation_run.actions.is_discardable | default(false)

Expected decisions
==================

- **No drift**: the refresh run finishes without an apply or discard action.
- **Only allowed drift, approved**: the same refresh-only run is applied and Terraform state is
  updated to match reality. Infrastructure is unchanged.
- **Allowed drift, not approved**: the pending refresh run is discarded and state is unchanged.
- **Denied, blocked, unknown, or unmatched drift**: strict mode rejects the refresh; the run is
  discarded. No infrastructure remediation occurs unless both remediation variables explicitly
  authorize a separate normal run and apply.

Every invocation creates a new refresh-only run, which is an auditable observation at that point
in time. The decision is not reusable for a later run because infrastructure may have changed
between plans.

Automation Controller approval pattern
======================================

``ansible.builtin.pause`` is suitable for an interactive CLI demonstration. In Automation
Controller, split the workflow into two job templates around a workflow approval node:

#. The analysis job creates the refresh run, records ``run_id`` and the guard result as workflow
   artifacts, and ends without applying it.
#. The approval node exposes the decision and run URL to the approver.
#. The promotion job re-reads that same ``run_id``, verifies that it is still confirmable, and
   applies or discards it. Set ``interactive_approval: false`` and inject
   ``trusted_approval: true`` only on the approved branch.

Do not create a second refresh-only run after approval. Approval must remain bound to the exact
plan that was analyzed.

Failure and rollback
====================

If analysis fails, leave the run unapplied and investigate. A timeout, unreadable plan, missing
rule, or unknown value must never be converted into approval.

Accepting drift updates Terraform state. There is no automatic rollback because the previous
state may no longer describe reality. To reverse that decision, first decide whether configuration
or infrastructure is authoritative, then use a reviewed normal Terraform workflow. This
collection intentionally does not expose raw state download/upload operations.

Cleanup and operational hygiene
===============================

The playbook creates no temporary infrastructure. Its cleanup responsibility is to leave no
reviewable run hanging: rejected runs are discarded, while no-change runs are already terminal.
Periodically inspect workspaces for old confirmable runs and resolve them under the same approval
policy.

Persist the run ID, rule version, guard mode, decision summary, approver, and job ID in an audit
system. Redact plan values when they may contain sensitive data.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs.plan_guard`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_tf_policy`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_authentication`
