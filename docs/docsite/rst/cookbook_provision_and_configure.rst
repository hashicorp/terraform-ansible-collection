.. _ansible_collections.hashicorp.terraform.docsite.cookbook_provision_and_configure:

**************************************************
Provision with Terraform, configure with Ansible
**************************************************

This cookbook implements the core integration story for the collection:

.. code-block:: text

   Ansible -> HCP Terraform/TFE workspace -> configuration version -> plan/apply
           -> Terraform outputs -> in-memory Ansible inventory -> configuration role

Terraform remains responsible for provisioning infrastructure. Ansible orchestrates the run,
turns its outputs into inventory, and configures the resources that Terraform created.

.. contents::
   :local:
   :depth: 2

Business outcome
================

One playbook can take an approved Terraform configuration from source to a configured service:

#. Converge the workspace baseline.
#. Upload the Terraform configuration without automatically queuing a run.
#. Plan and explicitly apply that exact configuration version.
#. Read a deliberately shaped, non-sensitive Terraform output.
#. Add the returned hosts to an in-memory inventory group.
#. Apply an idempotent Ansible role to those hosts.

This separates ownership cleanly. Terraform owns infrastructure lifecycle and state; Ansible owns
workflow orchestration and operating-system or application configuration.

Prerequisites and permissions
=============================

- Install this collection and ``pytfe>=1.4.1`` in the environment that runs the playbook.
- Export ``TFE_TOKEN``. For Terraform Enterprise, also export ``TFE_ADDRESS``. The token needs
  permission to manage the target workspace, upload configuration versions, create and apply
  runs, and read state outputs.
- Place a valid Terraform configuration under ``{{ playbook_dir }}/terraform``. Its provider
  credentials should be supplied through HCP Terraform/TFE workspace variables or dynamic
  provider credentials, not committed to the configuration directory.
- Make the provisioned hosts reachable from the Ansible execution environment over SSH or
  WinRM. The example below assumes Linux hosts reachable over SSH.
- Provide an idempotent Ansible role named ``application_baseline``, or change
  ``configuration_role`` to a role available in your project.

The workflow uses remote or agent execution. It does not require the Terraform CLI on the
Ansible controller and does not access a state backend directly.

Define the Terraform-to-Ansible contract
=========================================

Expose only the connection data Ansible needs. The following AWS-shaped example produces a list
of host dictionaries; use equivalent attributes for Azure, Google Cloud, or another provider:

.. code-block:: hcl

   output "ansible_hosts" {
     description = "Non-sensitive connection data consumed by Ansible"
     value = [
       for name, instance in aws_instance.web : {
         name         = name
         address      = instance.public_ip
         ansible_user = "ec2-user"
         inventory_groups = ["terraform_provisioned", "web"]
       }
     ]
   }

Do not put private keys, passwords, bootstrap tokens, or other secrets in this output. Supply
connection secrets to Ansible through Vault, an external secret manager, or controller
credentials.

Example input
=============

Save the environment-specific values as ``vars/provision.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   terraform_workspace: payments-dev
   terraform_version: "1.9.8"
   terraform_configuration: "{{ playbook_dir }}/terraform"
   configuration_role: application_baseline
   configure_become: true
   run_poll_timeout: 900

Complete playbook
=================

Save this as ``provision-and-configure.yml``:

.. code-block:: yaml

   ---
   - name: Provision infrastructure and build in-memory inventory
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/provision.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Converge the workspace baseline
         hashicorp.terraform.workspace_bootstrap:
           organization: "{{ terraform_organization }}"
           workspace: "{{ terraform_workspace }}"
           settings:
             execution_mode: remote
             terraform_version: "{{ terraform_version }}"
             auto_apply: false
           reconcile: false
         register: workspace_baseline

       - name: Upload the Terraform configuration
         hashicorp.terraform.configuration_version:
           workspace_id: "{{ workspace_baseline.workspace_id }}"
           configuration_files_path: "{{ terraform_configuration }}"
           auto_queue_runs: false
           poll_interval: 5
           poll_timeout: 300
           state: present
         register: configuration_version

       - name: Plan the uploaded configuration
         hashicorp.terraform.run:
           workspace_id: "{{ workspace_baseline.workspace_id }}"
           configuration_version: "{{ configuration_version.id }}"
           run_message: Provisioned through Ansible
           auto_apply: false
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         register: terraform_run

       - name: Wait for the plan to become confirmable or finish with no changes
         hashicorp.terraform.run_info:
           run_id: "{{ terraform_run.id }}"
         register: terraform_run_ready
         retries: "{{ (run_poll_timeout | int + 9) // 10 }}"
         delay: 10
         until: >-
           terraform_run_ready.run.actions.is_confirmable | default(false)
           or terraform_run_ready.run.status == 'planned_and_finished'

       - name: Apply the exact run when it has changes
         hashicorp.terraform.run:
           run_id: "{{ terraform_run.id }}"
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: applied
         register: applied_run
         when: terraform_run_ready.run.actions.is_confirmable | default(false)

       - name: Verify that the run reached an acceptable state
         ansible.builtin.assert:
           that:
             - >-
               (applied_run.status | default('')) == 'applied'
               or terraform_run_ready.run.status == 'planned_and_finished'
           fail_msg: "Terraform run {{ terraform_run.id }} was not applied successfully."

       - name: Read the non-sensitive host contract from Terraform
         ansible.builtin.set_fact:
           provisioned_hosts: >-
             {{ lookup('hashicorp.terraform.tf_output',
                       name='ansible_hosts',
                       workspace_id=workspace_baseline.workspace_id) }}

       - name: Validate the host contract
         ansible.builtin.assert:
           that:
             - provisioned_hosts is sequence
             - provisioned_hosts is not string
             - provisioned_hosts | length > 0
             - provisioned_hosts | selectattr('name', 'defined') | list | length == provisioned_hosts | length
             - provisioned_hosts | selectattr('address', 'defined') | list | length == provisioned_hosts | length
           fail_msg: "The ansible_hosts output does not match the documented contract."

       - name: Add Terraform-provisioned hosts to in-memory inventory
         ansible.builtin.add_host:
           name: "{{ item.name }}"
           ansible_host: "{{ item.address }}"
           ansible_user: "{{ item.ansible_user | default(omit) }}"
           groups: "{{ item.inventory_groups | default(['terraform_provisioned']) }}"
         loop: "{{ provisioned_hosts }}"
         loop_control:
           label: "{{ item.name }}"
         no_log: true

   - name: Configure the infrastructure provisioned by Terraform
     hosts: terraform_provisioned
     gather_facts: true
     become: "{{ configure_become }}"
     vars_files:
       - vars/provision.yml
     tasks:
       - name: Apply the application baseline
         ansible.builtin.include_role:
           name: "{{ configuration_role }}"

Run it with:

.. code-block:: bash

   export TFE_TOKEN="<token>"
   # export TFE_ADDRESS="https://terraform.example.com"  # Terraform Enterprise only
   ansible-playbook provision-and-configure.yml

Expected result and reruns
==========================

On the first run, the workspace baseline is created or updated, Terraform provisions the
resources, and the Ansible role configures every host in ``terraform_provisioned``.

On a rerun with unchanged inputs:

- ``workspace_bootstrap`` and the configuration role should report no infrastructure or
  configuration drift.
- ``configuration_version`` uploads a new immutable configuration version and ``run`` creates a
  new auditable run, so those tasks correctly report ``changed`` even when Terraform ultimately
  reports no resource changes.
- A no-change Terraform run reaches ``planned_and_finished`` and is not sent to the apply action.

For a workflow that should only create runs when source content changes, put a source revision or
artifact digest in the surrounding CI/CD system and skip this playbook when that digest was
already promoted.

Approval, failure, and rollback
===============================

The example disables auto-apply and applies only the run that Ansible just planned. In a governed
environment, replace the apply task with :ansplugin:`hashicorp.terraform.promote_run#module` or
place an Automation Controller workflow approval between planning and promotion.

If planning or policy checks fail, the module fails before inventory is created and no host
configuration runs. Preserve ``terraform_run.id`` in job output so an operator can inspect the
same run in HCP Terraform/TFE.

Infrastructure rollback is another Terraform configuration version and normal run. Application
rollback belongs in the Ansible role or deployment workflow. Do not attempt to repair Terraform
state from Ansible: this collection does not expose state download or upload operations.

Cleanup
=======

This cookbook creates durable infrastructure and intentionally does not destroy it at the end.
For a controlled teardown, queue a run with ``is_destroy: true``, review and apply that exact run,
then delete the empty workspace with :ansplugin:`hashicorp.terraform.workspace#module`. Never
force-delete a workspace that still manages resources unless abandoning those resources is an
explicitly approved decision.

Using ``tfc_inv`` instead of ``add_host``
=========================================

For repeated operations, write a ``tfc_inv.yml`` inventory configuration that consumes the same
output and run Ansible against it independently:

.. code-block:: yaml

   plugin: hashicorp.terraform.tfc_inv
   source: outputs
   organization: acme
   workspace: payments-dev
   hosts_from:
     output: ansible_hosts
     type: list(object)
   hostnames:
     - name
   compose:
     ansible_host: address
   groups:
     terraform_provisioned: "true"
     web: "'web' in inventory_groups"

The dynamic inventory path is better when provisioning and configuration run as separate jobs,
or when operators need to rediscover the current fleet later. See
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory` for supported
output shapes and grouping options.

Production hardening
====================

- Pin the collection, ``pytfe``, Terraform, provider, and Ansible role versions.
- Use dynamic cloud credentials and short-lived HCP Terraform/TFE tokens where possible.
- Keep host-key checking enabled and pre-populate trusted SSH host keys or certificates.
- Treat outputs as an API contract. Validate their type and avoid sensitive outputs.
- Use policy sets and mandatory run tasks before apply for security and cost controls.
- Set realistic polling timeouts and prevent concurrent jobs from applying to the same workspace.
- Run the playbook from an execution environment containing this collection, ``pytfe``, the
  required cloud collections, and the configuration role.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_workspace_bootstrap`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_authentication`
