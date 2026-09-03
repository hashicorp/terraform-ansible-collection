.. _ansible_collections.hashicorp.terraform.docsite.cookbook_event_driven_drift_response:

******************************************
Respond to drift through an EDA workflow
******************************************

This cookbook connects HCP Terraform health-assessment notifications to an Event-Driven Ansible
workflow that analyzes an actionable refresh-only run and waits for an explicit decision.

.. code-block:: text

   assessment:drifted -> verified webhook -> EDA -> analysis job -> approval
                                                          | approve safe drift
                                                          v
                                                apply SAME refresh-only run
                                                          |
                                                   reject or unsafe
                                                          v
                                                     discard run

The health assessment is the signal, not the plan that is applied. The analysis job creates a
normal refresh-only run because health assessments are non-actionable observations.

.. contents::
   :local:
   :depth: 2

Prerequisites and boundaries
============================

- Enable health assessments on eligible remote- or agent-execution workspaces.
- Install an EDA decision environment containing ``ansible.eda`` and this collection.
- Expose an HTTPS ingress that validates the Terraform notification HMAC signature before
  forwarding accepted payloads to the rulebook source.
- Disable auto-apply on governed workspaces.
- Define provider-specific allow and deny rules. The example rules are illustrative.
- Use an Automation Controller workflow approval node. An EDA event must never be treated as
  approval to change state or infrastructure.

Applying the approved refresh-only run updates Terraform state to match real infrastructure. It
does not revert the cloud object. True remediation requires a separate normal Terraform plan and
apply, as described in
:ref:`ansible_collections.hashicorp.terraform.docsite.cookbook_governed_drift`.

Configure the drift notification
================================

Save this as ``configure-drift-events.yml``:

.. code-block:: yaml

   ---
   - name: Send drift signals to the verified EDA ingress
     hosts: localhost
     connection: local
     gather_facts: false
     tasks:
       - name: Enable workspace health assessments
         hashicorp.terraform.workspace:
           workspace_id: "{{ terraform_workspace_id }}"
           assessments_enabled: true
           state: present

       - name: Configure the signed drift webhook
         hashicorp.terraform.notification_configuration:
           workspace_id: "{{ terraform_workspace_id }}"
           name: ansible-drift-response
           destination_type: generic
           url: "{{ verified_eda_webhook_url }}"
           token: "{{ terraform_webhook_hmac_secret }}"
           enabled: true
           triggers:
             - "assessment:drifted"
             - "assessment:failed"
           state: present
         no_log: true

The notification endpoint is verified during creation and enabled updates and must return a
successful response. Terraform does not return an existing HMAC token through the API; rotate it
by deleting and recreating the notification in a controlled change.

Route drift events
==================

Save this as ``drift-events.yml``:

.. code-block:: yaml

   ---
   - name: Route verified HCP Terraform drift notifications
     hosts: localhost
     sources:
       - ansible.eda.webhook:
           host: 0.0.0.0
           port: 5000
     rules:
       - name: Launch governed drift analysis
         condition: >-
           event.payload.notifications is defined
           and event.payload.notifications[0] is defined
           and event.payload.notifications[0].trigger == "assessment:drifted"
         action:
           run_workflow_template:
             name: Governed Terraform drift
             organization: Default
             job_args:
               extra_vars:
                 workflow_phase: analyze
                 event_payload: "{{ event.payload }}"

The controller workflow should contain an analysis job, an approval node, and a decision job.
Pass the analysis job's ``reviewed_run_id`` artifact to the decision job. On the approved path set
``approval_decision: approve``; on rejection set ``approval_decision: reject``.

Complete two-phase handler
==========================

Save this as ``govern-drift-event.yml``. The same playbook runs in both workflow phases:

.. code-block:: yaml

   ---
   - name: Analyze or decide an event-driven drift run
     hosts: localhost
     connection: local
     gather_facts: false
     vars:
       workflow_phase: analyze
       approval_decision: pending
       reviewed_run_id: ""
       allowed_organization: acme
       run_poll_timeout: 900
       allow_rules:
         - "*.tags"
         - "*.tags.*"
       deny_rules:
         - "aws_security_group.*.ingress"
         - "aws_security_group.*.egress"
         - "aws_iam_policy.*"
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Validate workflow inputs
         ansible.builtin.assert:
           that:
             - workflow_phase in ['analyze', 'decide']
             - approval_decision in ['pending', 'approve', 'reject']
             - >-
               workflow_phase != 'analyze'
               or event_payload.organization_name == allowed_organization
             - >-
               workflow_phase != 'analyze'
               or event_payload.workspace_id is match('^ws-')
             - >-
               workflow_phase != 'decide'
               or reviewed_run_id is match('^run-')

       - name: Create the actionable refresh-only run
         hashicorp.terraform.run:
           workspace_id: "{{ event_payload.workspace_id }}"
           run_message: >-
             Investigate drift reported by a health assessment
           refresh_only: true
           auto_apply: false
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         register: event_refresh_run
         when: workflow_phase == 'analyze'

       - name: Bind all later work to one run ID
         ansible.builtin.set_fact:
           governed_run_id: >-
             {{ event_refresh_run.id
                if workflow_phase == 'analyze'
                else reviewed_run_id }}

       - name: Re-read the exact run before analysis or decision
         hashicorp.terraform.run_info:
           run_id: "{{ governed_run_id }}"
         register: governed_run

       - name: Analyze the exact refresh-only plan
         hashicorp.terraform.plan_analyze:
           run_id: "{{ governed_run_id }}"
           detect_drift: true
           include_resource_changes: true
           blocked_attributes: "{{ deny_rules }}"
         register: drift_analysis

       - name: Evaluate the drift guard again from the plan
         ansible.builtin.set_fact:
           drift_guard: >-
             {{ drift_analysis
                | hashicorp.terraform.plan_guard(
                    allow=allow_rules,
                    deny=deny_rules,
                    mode='strict') }}

       - name: Publish review artifacts from the analysis phase
         ansible.builtin.set_stats:
           data:
             reviewed_run_id: "{{ governed_run_id }}"
             reviewed_safe_to_refresh: "{{ drift_guard.safe_to_refresh }}"
             reviewed_summary: "{{ drift_guard.summary }}"
             reviewed_reasons: "{{ drift_guard.reasons }}"
           per_host: false
         when: workflow_phase == 'analyze'

       - name: Require an explicit decision in the continuation phase
         ansible.builtin.assert:
           that:
             - approval_decision in ['approve', 'reject']
           fail_msg: "The decision phase requires approve or reject."
         when: workflow_phase == 'decide'

       - name: Apply the same refresh-only run when safe and approved
         hashicorp.terraform.promote_run:
           run_id: "{{ governed_run_id }}"
           require_policy_pass: true
           allow_advisory_failures: false
           wait: true
           timeout: "{{ run_poll_timeout }}"
         register: governed_refresh_apply
         when:
           - workflow_phase == 'decide'
           - approval_decision == 'approve'
           - drift_guard.safe_to_refresh

       - name: Require the approved refresh to complete
         ansible.builtin.assert:
           that:
             - >-
               governed_refresh_apply.gates.run_status_after | default('') == 'applied'
               or governed_refresh_apply.run.status | default('')
                  in ['applied', 'planned_and_finished']
         when:
           - workflow_phase == 'decide'
           - approval_decision == 'approve'
           - drift_guard.safe_to_refresh

       - name: Discard rejected or unsafe drift
         hashicorp.terraform.run:
           run_id: "{{ governed_run_id }}"
           state: discarded
         when:
           - workflow_phase == 'decide'
           - >-
             approval_decision == 'reject'
             or not drift_guard.safe_to_refresh
           - governed_run.run.status != 'planned_and_finished'

       - name: Refuse an approval that conflicts with the guard
         ansible.builtin.assert:
           that:
             - approval_decision != 'approve' or drift_guard.safe_to_refresh
           fail_msg: >-
             Run {{ governed_run_id }} was approved by a person but rejected by the
             strict drift guard. It was not applied.
         when: workflow_phase == 'decide'

Local validation
================

Run the analysis phase with a captured, verified payload, record the returned run ID, and then run
the decision phase:

.. code-block:: bash

   ansible-playbook govern-drift-event.yml \
     -e @captured-event.json -e workflow_phase=analyze

   ansible-playbook govern-drift-event.yml \
     -e workflow_phase=decide \
     -e reviewed_run_id=run-abc123 \
     -e approval_decision=reject

Replay protection and operations
================================

Deduplicate assessment events at the verified ingress using a stable event identifier and short
retention window. Do not rely on Terraform to redeliver failures; buffer accepted events durably
and replay them through the ingress when necessary. Also prevent concurrent drift workflows for
one workspace; otherwise multiple confirmable refresh runs can present conflicting decisions.

Persist the assessment event, run ID, policy version, guard output, approval identity, and final
run status. Expire or discard runs that remain pending beyond the organization's approval SLA.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.cookbook_governed_drift`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.cookbook_event_driven_post_apply`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze`
