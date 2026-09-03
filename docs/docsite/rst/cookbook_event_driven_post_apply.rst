.. _ansible_collections.hashicorp.terraform.docsite.cookbook_event_driven_post_apply:

**********************************
Event-driven post-apply automation
**********************************

This cookbook connects HCP Terraform or Terraform Enterprise workspace notifications to
Event-Driven Ansible (EDA). A successfully applied Terraform run launches configuration against
fresh Terraform output inventory, while an errored run launches a separate failure workflow.

.. code-block:: text

   HCP Terraform/TFE run
          |
          v
   generic notification -> verified webhook ingress -> EDA rulebook
                                                  |              |
                                          applied |              | errored
                                                  v              v
                                      refresh inventory     failure workflow
                                                  |
                                                  v
                                      idempotent Ansible role

.. contents::
   :local:
   :depth: 2

Trigger and payload model
=========================

HCP Terraform/TFE does not provide a ``run:applied`` notification trigger. Subscribe to
``run:completed`` and inspect ``notifications[0].run_status`` for ``applied``. This avoids treating
a successful speculative or no-change plan as an infrastructure apply. Subscribe separately to
``run:errored`` for the failure path.

A generic run notification includes ``run_id``, ``workspace_id``, ``organization_name``, and a
``notifications`` list. HashiCorp currently sends one item in that list, but documents the list
shape so future payloads can roll up events. See the `notification configuration API reference
<https://developer.hashicorp.com/terraform/cloud-docs/api-docs/notification-configurations>`__.

Prerequisites and permissions
=============================

- Install this collection and ``pytfe>=1.4.1`` in the execution environment used by the handler
  playbooks.
- Install ``ansible-rulebook`` and an EDA decision environment containing the ``ansible.eda``
  collection, or configure the equivalent rulebook activation in Automation Decisions.
- Expose an HTTPS endpoint that HCP Terraform/TFE can reach. It must return 2xx when Terraform
  verifies the notification configuration.
- Export ``TFE_TOKEN`` to the handler execution environment. It needs read access to the notified
  run, workspace, and outputs.
- The Terraform configuration must expose a non-sensitive ``ansible_hosts`` output using the
  contract in
  :ref:`ansible_collections.hashicorp.terraform.docsite.cookbook_provision_and_configure`.
- Provide an idempotent role named ``application_baseline`` or change the handler variable.

Start the EDA activation or webhook receiver before creating or enabling the notification, because
Terraform verifies generic webhook URLs on creation and on enabled updates.

Configure the Terraform notification
====================================

Store the endpoint and HMAC secret in Vault or controller credentials. Save this playbook as
``configure-notification.yml``:

.. code-block:: yaml

   ---
   - name: Configure Terraform events for EDA
     hosts: localhost
     connection: local
     gather_facts: false
     vars:
       terraform_organization: acme
       terraform_workspace: payments-prod
       eda_webhook_url: https://eda.example.com/endpoint
       eda_webhook_hmac_token: "{{ vault_eda_webhook_hmac_token }}"
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Converge the EDA notification
         hashicorp.terraform.notification_configuration:
           organization: "{{ terraform_organization }}"
           workspace: "{{ terraform_workspace }}"
           name: ansible-post-apply
           destination_type: generic
           url: "{{ eda_webhook_url }}"
           token: "{{ eda_webhook_hmac_token }}"
           enabled: true
           triggers:
             - "run:completed"
             - "run:errored"
           state: present
         no_log: true

The token is used to sign generic notifications. The receiving ingress must verify the
``X-TFE-Notification-Signature`` header before forwarding the body to EDA.
Terraform does not return an existing token through the API, so the module cannot compare or
rotate it on an in-place update. To rotate the token, remove and recreate the notification in a
controlled change while the receiver accepts the old and new secrets during the transition.

Run the EDA rulebook
====================

Save the following as ``terraform-events.yml``. The ``ansible.eda.webhook`` source is broadly
available; newer ``ansible-rulebook`` releases may also expose it as ``eda.builtin.webhook``.

.. code-block:: yaml

   ---
   - name: Route HCP Terraform and TFE run events
     hosts: localhost
     sources:
       - ansible.eda.webhook:
           host: 0.0.0.0
           port: 5000
     rules:
       - name: Configure resources after a successful apply
         condition: >-
           event.payload.notifications is defined
           and event.payload.notifications[0] is defined
           and event.payload.notifications[0].trigger == "run:completed"
           and event.payload.notifications[0].run_status == "applied"
         action:
           run_playbook:
             name: post-apply.yml

       - name: Handle an errored Terraform run
         condition: >-
           event.payload.notifications is defined
           and event.payload.notifications[0] is defined
           and event.payload.notifications[0].trigger == "run:errored"
         action:
           run_playbook:
             name: run-errored.yml

For local testing, start it with an inventory containing ``localhost``:

.. code-block:: bash

   ansible-rulebook --rulebook terraform-events.yml --inventory inventory.yml --print-events

In Automation Decisions, replace ``run_playbook`` with ``run_job_template`` or
``run_workflow_template`` when execution should happen in Automation Controller. Matched events
are passed to the launched automation under ``ansible_eda.event``.

Complete post-apply handler
===========================

Save this as ``post-apply.yml``:

.. code-block:: yaml

   ---
   - name: Verify the event and refresh Terraform-backed inventory
     hosts: localhost
     connection: local
     gather_facts: false
     vars:
       allowed_terraform_organization: acme
       configuration_role: application_baseline
       event_payload: "{{ ansible_eda.event.payload }}"
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Validate the event scope
         ansible.builtin.assert:
           that:
             - event_payload.payload_version | int == 1
             - event_payload.organization_name == allowed_terraform_organization
             - event_payload.run_id is match('^run-')
             - event_payload.workspace_id is match('^ws-')
           fail_msg: The Terraform event is outside the approved scope.

       - name: Re-read the run from Terraform
         hashicorp.terraform.run_info:
           run_id: "{{ event_payload.run_id }}"
         register: verified_run

       - name: Verify the authoritative run state
         ansible.builtin.assert:
           that:
             - verified_run.run.id == event_payload.run_id
             - verified_run.run.status == 'applied'
           fail_msg: The event does not correspond to an applied Terraform run.

       - name: Stop post-apply configuration for a destroy run
         ansible.builtin.meta: end_play
         when: verified_run.run.is_destroy | default(false)

       - name: Read the current non-sensitive inventory output
         ansible.builtin.set_fact:
           terraform_hosts: >-
             {{ lookup('hashicorp.terraform.tf_output',
                       name='ansible_hosts',
                       workspace_id=event_payload.workspace_id) }}

       - name: Validate the inventory contract
         ansible.builtin.assert:
           that:
             - terraform_hosts is sequence
             - terraform_hosts is not string
             - terraform_hosts | selectattr('name', 'defined') | list | length == terraform_hosts | length
             - terraform_hosts | selectattr('address', 'defined') | list | length == terraform_hosts | length

       - name: Add the applied resources to in-memory inventory
         ansible.builtin.add_host:
           name: "{{ item.name }}"
           ansible_host: "{{ item.address }}"
           ansible_user: "{{ item.ansible_user | default(omit) }}"
           groups: >-
             {{ (item.inventory_groups | default([])) + ['terraform_applied'] }}
         loop: "{{ terraform_hosts }}"
         loop_control:
           label: "{{ item.name }}"
         no_log: true

   - name: Apply post-provision configuration
     hosts: terraform_applied
     gather_facts: true
     become: true
     vars:
       configuration_role: application_baseline
     tasks:
       - name: Converge the application baseline
         ansible.builtin.include_role:
           name: "{{ configuration_role }}"

Complete failure handler
========================

Save this as ``run-errored.yml``. Replace the final failure with your incident-management or
notification role when integrating with an operational system:

.. code-block:: yaml

   ---
   - name: Record an errored Terraform run
     hosts: localhost
     connection: local
     gather_facts: false
     vars:
       event_payload: "{{ ansible_eda.event.payload }}"
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Re-read the errored run
         hashicorp.terraform.run_info:
           run_id: "{{ event_payload.run_id }}"
         register: errored_run

       - name: Show the failure context
         ansible.builtin.debug:
           msg:
             run_id: "{{ event_payload.run_id }}"
             workspace: "{{ event_payload.workspace_name }}"
             organization: "{{ event_payload.organization_name }}"
             status: "{{ errored_run.run.status }}"
             run_url: "{{ event_payload.run_url }}"

       - name: Mark the failure workflow unsuccessful
         ansible.builtin.fail:
           msg: >-
             Terraform run {{ event_payload.run_id }} failed in
             {{ event_payload.workspace_name }}. Review {{ event_payload.run_url }}.

Expected behavior and idempotency
=================================

- A ``run:completed`` event with ``run_status: applied`` re-verifies the run, reloads current
  outputs, and applies the role.
- Completed plans with another status do not match the post-apply rule.
- Applied destroy runs are verified but skip configuration.
- A ``run:errored`` event launches only the failure handler.
- Duplicate or deliberately replayed webhook events may run the handler more than once. The role
  must be idempotent, so replay converges to the same state rather than repeating an unsafe action.

Failure, replay, and rollback
=============================

Do not rely on Terraform to redeliver a failed notification. Monitor the rulebook activation and
configure durable buffering plus a dead-letter or incident path at the ingress so a prolonged EDA
outage is visible and captured events can be replayed deliberately.

If Terraform applied successfully but host configuration failed, rerun ``post-apply.yml`` with a
captured, validated event or run the same configuration role against ``tfc_inv`` inventory. Do not
rerun Terraform merely to retrigger Ansible.

Rollback is domain-specific: revert infrastructure through a new Terraform run and revert
application configuration through an idempotent Ansible role. A webhook notification is an event,
not a distributed transaction across both systems.

Cleanup
=======

Disable or remove the notification when retiring the integration:

.. code-block:: yaml

   - name: Remove the EDA notification
     hashicorp.terraform.notification_configuration:
       organization: acme
       workspace: payments-prod
       name: ansible-post-apply
       state: absent

Then stop the rulebook activation only after all workspaces have been detached or redirected.

Production hardening
====================

- Do not expose the raw demonstration webhook directly to the internet. Put an API gateway,
  reverse proxy, or supported event-stream ingress in front of EDA and validate the HMAC signature.
- Re-read the run from HCP Terraform/TFE, as the example does, and allowlist organizations and
  workspaces before launching automation.
- Use HTTPS, short-lived credentials, network allowlists, request-size limits, and rate limits.
- Deduplicate on ``notification_configuration_id``, ``run_id``, trigger, and run update time when
  the downstream action is not naturally idempotent.
- Keep the decision environment and execution environment versioned together. They need different
  dependencies: the former receives and evaluates events; the latter runs this collection and
  ``pytfe``.
- Never print full event headers, signatures, sensitive outputs, or connection credentials.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_lookups.tf_output`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_execution_environments`
   - `Ansible Rulebook webhook example <https://ansible.readthedocs.io/projects/rulebook/en/stable/getting_started.html>`__
