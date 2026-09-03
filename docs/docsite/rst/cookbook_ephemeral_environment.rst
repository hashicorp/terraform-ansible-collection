.. _ansible_collections.hashicorp.terraform.docsite.cookbook_ephemeral_environment:

******************************
Ephemeral preview environments
******************************

This cookbook creates one HCP Terraform or Terraform Enterprise workspace per pull request or
branch, applies infrastructure, configures and tests it with Ansible, then destroys the resources
and safely deletes the workspace in an ``always`` block.

.. code-block:: text

   pull request -> temporary workspace -> Terraform apply -> Ansible configure/test
                                                               |
                                                               v
                                                   always: destroy and delete

.. contents::
   :local:
   :depth: 2

Business outcome
================

Application teams can validate infrastructure and configuration together before merging. Every
preview gets isolated Terraform state and an auditable run history, while cleanup executes after
success, task failure, or a failed smoke test.

Prerequisites and product limitations
=====================================

- Install this collection and ``pytfe>=1.4.1`` and export ``TFE_TOKEN``. Set ``TFE_ADDRESS`` for
  Terraform Enterprise.
- The token needs permission to create and delete workspaces, upload configuration versions,
  create/apply/destroy runs, and read outputs.
- Put the preview Terraform configuration under ``{{ playbook_dir }}/terraform-preview`` and
  provide its cloud credentials through workspace variables or dynamic credentials.
- Provide an idempotent role named ``preview_application`` or change ``preview_role``.
- The execution environment needs network access to the preview hosts and smoke-test URLs.
- Automatic workspace destruction based on inactivity is edition-dependent. The playbook's
  explicit destroy run is the primary cleanup; a platform TTL should be a second safety net.

An ``always`` block runs when Ansible handles task failure. It cannot protect against abrupt
termination of the execution node, revoked credentials, or an unavailable Terraform service.
Use a scheduled janitor workflow keyed by preview tags to clean up abandoned workspaces.

Terraform output contract
=========================

Expose non-sensitive host connection data and health-check URLs:

.. code-block:: hcl

   output "preview_hosts" {
     value = [
       for name, instance in aws_instance.preview : {
         name               = name
         address            = instance.public_ip
         ansible_user       = "ec2-user"
         ansible_connection = "ssh"
       }
     ]
   }

   output "smoke_urls" {
     value = [for instance in aws_instance.preview : "https://${instance.public_dns}/health"]
   }

Adapt the provider resources and connection fields for your environment. Do not expose private
keys, passwords, or application secrets as outputs.

Complete playbook
=================

Save this as ``preview-environment.yml``:

.. code-block:: yaml

   ---
   - name: Create, test, and remove a preview environment
     hosts: localhost
     connection: local
     gather_facts: false
     vars:
       terraform_organization: acme
       preview_id: pr-184
       preview_workspace: "preview-{{ preview_id }}"
       terraform_version: "1.9.8"
       terraform_configuration: "{{ playbook_dir }}/terraform-preview"
       preview_role: preview_application
       preview_apply_approved: true
       run_poll_timeout: 900
       force_workspace_delete: false
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Initialize cleanup facts
         ansible.builtin.set_fact:
           preview_workspace_id: ""
           preview_destroy_succeeded: false

       - name: Run the preview lifecycle
         block:
           - name: Validate the preview identifier
             ansible.builtin.assert:
               that:
                 - preview_id is match('^[A-Za-z0-9_-]+$')
                 - preview_workspace | length <= 90
                 - preview_apply_approved | bool
               fail_msg: Preview input is invalid or its apply was not approved.

           - name: Converge the isolated preview workspace
             hashicorp.terraform.workspace:
               organization: "{{ terraform_organization }}"
               workspace: "{{ preview_workspace }}"
               description: "Temporary environment for {{ preview_id }}"
               execution_mode: remote
               terraform_version: "{{ terraform_version }}"
               auto_apply: false
               allow_destroy_plan: true
               tag_bindings:
                 lifecycle: ephemeral
                 preview_id: "{{ preview_id }}"
                 managed_by: ansible
               state: present
             register: preview_workspace_result

           - name: Save the workspace ID for unconditional cleanup
             ansible.builtin.set_fact:
               preview_workspace_id: "{{ preview_workspace_result.id }}"

           - name: Upload the preview Terraform configuration
             hashicorp.terraform.configuration_version:
               workspace_id: "{{ preview_workspace_id }}"
               configuration_files_path: "{{ terraform_configuration }}"
               auto_queue_runs: false
               poll_interval: 5
               poll_timeout: 300
               state: present
             register: preview_configuration

           - name: Plan the preview infrastructure
             hashicorp.terraform.run:
               workspace_id: "{{ preview_workspace_id }}"
               configuration_version: "{{ preview_configuration.id }}"
               run_message: "Create preview {{ preview_id }}"
               auto_apply: false
               poll: true
               poll_interval: 10
               poll_timeout: "{{ run_poll_timeout }}"
               state: present
             register: preview_plan

           - name: Wait for the plan to become confirmable or finish with no changes
             hashicorp.terraform.run_info:
               run_id: "{{ preview_plan.id }}"
             register: preview_plan_ready
             retries: "{{ (run_poll_timeout | int + 9) // 10 }}"
             delay: 10
             until: >-
               preview_plan_ready.run.actions.is_confirmable | default(false)
               or preview_plan_ready.run.status == 'planned_and_finished'

           - name: Apply the exact preview run
             hashicorp.terraform.run:
               run_id: "{{ preview_plan.id }}"
               run_message: "Approved preview for {{ preview_id }}"
               poll: true
               poll_interval: 10
               poll_timeout: "{{ run_poll_timeout }}"
               state: applied
             register: preview_apply
             when: preview_plan_ready.run.actions.is_confirmable | default(false)

           - name: Verify preview provisioning
             ansible.builtin.assert:
               that:
                 - >-
                   (preview_apply.status | default('')) == 'applied'
                   or preview_plan_ready.run.status == 'planned_and_finished'
               fail_msg: "Preview Terraform run {{ preview_plan.id }} did not complete."

           - name: Read preview hosts from Terraform outputs
             ansible.builtin.set_fact:
               preview_hosts: >-
                 {{ lookup('hashicorp.terraform.tf_output',
                           name='preview_hosts',
                           workspace_id=preview_workspace_id) }}
               preview_smoke_urls: >-
                 {{ lookup('hashicorp.terraform.tf_output',
                           name='smoke_urls',
                           workspace_id=preview_workspace_id) }}

           - name: Validate preview output contracts
             ansible.builtin.assert:
               that:
                 - preview_hosts is sequence
                 - preview_hosts is not string
                 - preview_hosts | length > 0
                 - preview_smoke_urls is sequence
                 - preview_smoke_urls is not string

           - name: Add preview hosts to in-memory inventory
             ansible.builtin.add_host:
               name: "{{ item.name }}"
               ansible_host: "{{ item.address }}"
               ansible_user: "{{ item.ansible_user | default(omit) }}"
               ansible_connection: "{{ item.ansible_connection | default('ssh') }}"
               groups:
                 - preview
             loop: "{{ preview_hosts }}"
             loop_control:
               label: "{{ item.name }}"
             no_log: true

           - name: Wait for SSH on every preview host
             ansible.builtin.wait_for:
               host: "{{ item.address }}"
               port: 22
               timeout: 300
             loop: "{{ preview_hosts }}"
             loop_control:
               label: "{{ item.name }}"

           - name: Gather facts from each preview host
             ansible.builtin.setup:
             delegate_to: "{{ item.name }}"
             delegate_facts: true
             loop: "{{ preview_hosts }}"
             loop_control:
               label: "{{ item.name }}"

           - name: Configure each preview host
             ansible.builtin.include_role:
               name: "{{ preview_role }}"
               apply:
                 delegate_to: "{{ preview_host.name }}"
                 become: true
             loop: "{{ preview_hosts }}"
             loop_control:
               loop_var: preview_host
               label: "{{ preview_host.name }}"

           - name: Run HTTP smoke tests
             ansible.builtin.uri:
               url: "{{ item }}"
               method: GET
               status_code: 200
               return_content: false
               validate_certs: true
             register: preview_smoke_results
             retries: 12
             delay: 10
             until: preview_smoke_results.status == 200
             loop: "{{ preview_smoke_urls }}"
             loop_control:
               label: "{{ item }}"

         always:
           - name: Queue and auto-apply the preview destroy run
             hashicorp.terraform.run:
               workspace_id: "{{ preview_workspace_id }}"
               run_message: "Destroy preview {{ preview_id }}"
               is_destroy: true
               auto_apply: true
               poll: true
               poll_interval: 10
               poll_timeout: "{{ run_poll_timeout }}"
               state: present
             register: preview_destroy
             ignore_errors: true
             when: preview_workspace_id | length > 0

           - name: Record whether Terraform completed the destroy
             ansible.builtin.set_fact:
               preview_destroy_succeeded: >-
                 {{ not (preview_destroy.failed | default(true))
                    and (preview_destroy.status | default(''))
                        in ['applied', 'planned_and_finished'] }}
             when: preview_workspace_id | length > 0

           - name: Safely delete the empty preview workspace
             hashicorp.terraform.workspace:
               workspace_id: "{{ preview_workspace_id }}"
               force: false
               state: absent
             register: preview_workspace_delete
             ignore_errors: true
             when:
               - preview_workspace_id | length > 0
               - preview_destroy_succeeded | bool

           - name: Force-delete only when explicitly authorized
             hashicorp.terraform.workspace:
               workspace_id: "{{ preview_workspace_id }}"
               force: true
               state: absent
             register: preview_workspace_force_delete
             ignore_errors: true
             when:
               - preview_workspace_id | length > 0
               - force_workspace_delete | bool
               - >-
                 not preview_destroy_succeeded
                 or preview_workspace_delete.failed | default(true)

           - name: Report incomplete cleanup
             ansible.builtin.fail:
               msg: >-
                 Cleanup did not safely delete {{ preview_workspace }}. Preserve
                 workspace ID {{ preview_workspace_id }} for the janitor workflow.
             when:
               - preview_workspace_id | length > 0
               - >-
                 not preview_destroy_succeeded
                 or preview_workspace_delete.failed | default(true)
               - >-
                 not (force_workspace_delete | bool)
                 or preview_workspace_force_delete.failed | default(true)

Expected behavior and reruns
============================

The preview workspace exists only while the play runs. A successful execution provisions,
configures, tests, destroys, and deletes it. A task failure enters ``always`` before Ansible
returns the original failure.

Because successful cleanup removes the workspace, another run with the same ``preview_id`` starts
a fresh lifecycle and correctly reports changes. If a previous job stopped before cleanup, the
workspace task converges the existing workspace and the final cleanup reuses its stable ID.
Configuration versions and runs are immutable audit objects, so each retry creates new ones.

Approval, failure, and rollback
===============================

Set ``preview_apply_approved`` only after the pull request, Terraform source revision, and
environment scope have passed review. For protected previews, place an Automation Controller
approval node before this playbook or split plan and apply into separate jobs while preserving the
exact run ID.

If configuration or smoke testing fails, cleanup still attempts a destroy. A failed destroy does
not automatically force-delete the workspace; the cleanup task fails and leaves its state and
resources visible for investigation and for the janitor workflow. Set
``force_workspace_delete: true`` only when orphaning remaining resources is understood and
explicitly accepted.

Rollback is normally unnecessary because the environment is destroyed. When a failed preview must
be retained for debugging, temporarily disable cleanup through a separately reviewed diagnostic
variant rather than changing the safe defaults of the shared workflow.

Production hardening
====================

- Derive ``preview_id`` from a trusted CI value and validate it before using it as a workspace
  name or tag.
- Limit previews to a dedicated project, cloud account/subscription, network, and credential set.
- Enforce cost, resource-type, region, and TTL policy before apply.
- Run a scheduled janitor that finds ``lifecycle=ephemeral`` workspaces older than the allowed TTL,
  destroys them, and reports any failed cleanup.
- Prevent two jobs with the same preview ID from running concurrently.
- Keep smoke tests retry-safe and configuration roles idempotent.
- Preserve Terraform run URLs and cleanup results as CI artifacts.
- Avoid ``force: true`` in unattended cleanup unless orphaned infrastructure is separately tracked.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.cookbook_provision_and_configure`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory`
