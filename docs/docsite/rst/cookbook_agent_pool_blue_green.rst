.. _ansible_collections.hashicorp.terraform.docsite.cookbook_agent_pool_blue_green:

*********************************
Replace an agent pool blue-green
*********************************

This cookbook replaces a private HCP Terraform or Terraform Enterprise execution plane without
moving workspaces back to remote execution.

.. code-block:: text

   create green pool + token -> install agents -> verify capacity
             -> move project/workspaces -> drain blue agents -> revoke and delete blue pool

The collection manages the pool, token, project/workspace assignment, and status checks. Normal
Ansible modules install and supervise the agent process on infrastructure you control.

.. contents::
   :local:
   :depth: 2

Use cases
=========

- Rotate a write-once agent token with overlapping capacity.
- Upgrade the agent image without interrupting queued Terraform runs.
- Move from x86_64 to ARM64 by creating a new pool. A pool cannot mix architectures.
- Replace hosts, networks, or operating systems behind a stable project boundary.

Prerequisites and safety controls
=================================

- Install ``community.docker`` in the execution environment, or replace the container task with
  your systemd/Kubernetes implementation.
- Put the replacement hosts in the Ansible inventory group ``terraform_agent_nodes``.
- The HCP Terraform token needs permission to manage agent pools and tokens and to update the
  target project or workspaces.
- Pin an agent image version. Do not use ``latest`` in production.
- Wait for in-progress runs to finish before changing execution mode. A plan and apply can use
  different agents, so do not remove the old capacity early.
- Store the token value immediately. HCP Terraform returns it only when the token is created.

Example input
=============

Save this as ``vars/agent-migration.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   target_project_id: prj-abc123

   replacement_pool_name: private-runners-green
   replacement_agent_image: hashicorp/tfc-agent:1.25.2
   replacement_container_name: tfc-agent-green

   # Persist these two values in controller credentials after the first run.
   replacement_agent_token_id: ""
   replacement_agent_token_value: ""

   old_agent_token_id: at-old123
   old_agent_pool_id: apool-old123
   old_container_name: tfc-agent-blue

   expected_agent_count: 2
   retire_old_pool: false

Complete playbook
=================

Save this as ``replace-agent-pool.yml``:

.. code-block:: yaml

   ---
   - name: Create the replacement HCP Terraform execution plane
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/agent-migration.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Create a project-scoped replacement pool
         hashicorp.terraform.agent_pool:
           organization: "{{ terraform_organization }}"
           name: "{{ replacement_pool_name }}"
           organization_scoped: false
           allowed_project_ids:
             - "{{ target_project_id }}"
           state: present
         register: replacement_pool

       - name: Create or verify the replacement token
         hashicorp.terraform.agent_token:
           agent_token_id: >-
             {{ replacement_agent_token_id | default(omit, true) }}
           agent_pool_id: "{{ replacement_pool.id }}"
           description: "{{ replacement_pool_name }} rollout"
           state: present
         register: replacement_token
         no_log: true

       - name: Select the newly returned or securely persisted token value
         ansible.builtin.set_fact:
           effective_agent_token: >-
             {{ replacement_token.token
                | default(replacement_agent_token_value, true) }}
         no_log: true

       - name: Require a usable token value before touching agent hosts
         ansible.builtin.assert:
           that:
             - effective_agent_token | length > 0
           fail_msg: >-
             The token secret is available only on creation. Supply
             replacement_agent_token_value from a protected controller credential.
         no_log: true

       - name: Expose non-secret pool identity to later plays
         ansible.builtin.set_fact:
           green_pool_id: "{{ replacement_pool.id }}"
           green_token_id: "{{ replacement_token.id }}"

   - name: Install and register replacement agents
     hosts: terraform_agent_nodes
     become: true
     gather_facts: true
     serial: 1
     vars_files:
       - vars/agent-migration.yml
     tasks:
       - name: Run the pinned HCP Terraform agent container
         community.docker.docker_container:
           name: "{{ replacement_container_name }}"
           image: "{{ replacement_agent_image }}"
           pull: true
           restart_policy: unless-stopped
           state: started
           env:
             TFC_AGENT_TOKEN: "{{ hostvars['localhost'].effective_agent_token }}"
             TFC_AGENT_NAME: "{{ inventory_hostname }}-green"
         no_log: true

   - name: Verify capacity and cut the project over
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/agent-migration.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Wait for the expected number of agents to register
         hashicorp.terraform.agent_pool_info:
           agent_pool_id: "{{ green_pool_id }}"
         register: pool_health
         until: >-
           pool_health.agent_pool.agent_count | int >= expected_agent_count | int
         retries: 30
         delay: 10

       - name: Move the project default execution mode to the green pool
         hashicorp.terraform.project:
           project_id: "{{ target_project_id }}"
           default_execution_mode: agent
           default_agent_pool_id: "{{ green_pool_id }}"
           state: present

       - name: Report identifiers that must be persisted securely
         ansible.builtin.debug:
           msg:
             replacement_agent_pool_id: "{{ green_pool_id }}"
             replacement_agent_token_id: "{{ green_token_id }}"

   - name: Drain old agent processes after Terraform runs finish
     hosts: terraform_agent_nodes
     become: true
     gather_facts: false
     vars_files:
       - vars/agent-migration.yml
     tasks:
       - name: Stop the old agent container
         community.docker.docker_container:
           name: "{{ old_container_name }}"
           state: absent
         when: retire_old_pool | bool

   - name: Revoke old credentials and remove the unused pool
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/agent-migration.yml
     tasks:
       - name: Delete the old agent token
         hashicorp.terraform.agent_token:
           agent_token_id: "{{ old_agent_token_id }}"
           state: absent
         when: retire_old_pool | bool

       - name: Delete the old agent pool
         hashicorp.terraform.agent_pool:
           agent_pool_id: "{{ old_agent_pool_id }}"
           state: absent
         when: retire_old_pool | bool

Set ``retire_old_pool: true`` only after checking that no workspace or Stack still selects the old
pool and no run is pending, planning, or applying.

Idempotency and rollback
========================

Pool and project convergence are idempotent. Token creation is intentionally different: without
``replacement_agent_token_id`` every run creates a new token, and an existing token cannot reveal
its secret. Persist the token ID and secret in a protected credential system before rerunning.

Before retiring the old pool, rollback is simply assigning the project back to
``old_agent_pool_id``. After revocation, rollback requires a new token and running old or new
agents with that token.

Production hardening
====================

- Use at least two agents per critical pool and monitor status, version, and last ping.
- Verify image signatures and checksums and scan custom agent images.
- Use a process supervisor and persistent telemetry; do not rely only on container restart policy.
- Limit pool scope to explicit projects or workspaces and reconcile the complete allowlist.
- Keep token values out of job output, facts cache, and workflow artifacts.
- Test outbound access to HCP Terraform/TFE, provider registries, VCS, and private APIs before
  cutover.

.. seealso::

   - :ansplugin:`hashicorp.terraform.agent_pool#module`
   - :ansplugin:`hashicorp.terraform.agent_token#module`
   - :ansplugin:`hashicorp.terraform.agent_pool_info#module`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_execution_environments`

