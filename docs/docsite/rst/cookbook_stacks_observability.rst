.. _ansible_collections.hashicorp.terraform.docsite.cookbook_stacks_observability:

*******************************************
Onboard and observe an HCP Terraform Stack
*******************************************

This cookbook creates a VCS-backed HCP Terraform Stack, requests a speculative configuration
snapshot, observes deployment groups, and collects detailed run, step, state, and diagnostic
records during incident handling.

.. code-block:: text

   project + VCS -> Stack -> fetched speculative configuration -> deployment groups
                                              -> run/step/state/diagnostic IDs -> Ansible report

.. important::

   The current collection manages Stack metadata and configuration snapshots and reads deployment
   resources. It does not expose the complete Stack deployment initiation and operator-approval
   lifecycle. Keep this scenario scoped to onboarding and observability; use the HCP Terraform UI,
   CLI, or another supported interface for deployment actions that the collection does not expose.

.. contents::
   :local:
   :depth: 2

Prerequisites
=============

- Enable Stacks for the HCP Terraform organization and use a subscription that includes them.
- Prepare a repository containing valid component configuration and ``.tfdeploy.hcl`` deployment
  configuration.
- Configure the VCS connection and supply its OAuth token ID or GitHub App installation ID.
- Use ``source: fetch`` or ``source: reuse`` in this collection. ``source: manual`` creates a
  record that expects a separate archive upload, which this module does not perform.
- If the Stack uses agents, assign a compatible agent pool and verify agent support for Stack
  deployment runs.
- The token needs project and Stack management permission and read access to deployment data.

Example input
=============

Save this as ``vars/stack.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   stack_project_id: prj-platform123
   stack_name: payments-platform
   stack_repository: acme/terraform-stack-payments
   stack_branch: main
   stack_oauth_token_id: ot-vcs123
   deployment_names:
     - development
     - staging
     - production

Onboard and observe configuration
=================================

Save this as ``onboard-stack.yml``:

.. code-block:: yaml

   ---
   - name: Onboard and inspect an HCP Terraform Stack
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/stack.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Converge the VCS-backed Stack
         hashicorp.terraform.stack:
           organization: "{{ terraform_organization }}"
           name: "{{ stack_name }}"
           project_id: "{{ stack_project_id }}"
           description: Payments platform deployment topology
           vcs_repo:
             identifier: "{{ stack_repository }}"
             branch: "{{ stack_branch }}"
             oauth_token_id: "{{ stack_oauth_token_id }}"
           agent_pool_id: "{{ stack_agent_pool_id | default(omit, true) }}"
           state: present
         register: managed_stack

       - name: Fetch a speculative configuration snapshot from VCS
         hashicorp.terraform.stack_configuration:
           stack_id: "{{ managed_stack.id }}"
           source: fetch
           speculative_enabled: true
           selected_deployments: "{{ deployment_names }}"
           state: present
         register: stack_configuration

       - name: Read configuration status
         hashicorp.terraform.stack_configuration_info:
           stack_configuration_id: "{{ stack_configuration.id }}"
         register: configuration_status

       - name: Wait for every expected deployment group to appear
         hashicorp.terraform.stack_deployment_group_info:
           stack_configuration_id: "{{ stack_configuration.id }}"
           name: "{{ item }}"
         loop: "{{ deployment_names }}"
         loop_control:
           label: "{{ item }}"
         register: deployment_groups
         retries: 30
         delay: 10
         until: deployment_groups is succeeded

       - name: Publish Stack onboarding evidence
         ansible.builtin.debug:
           msg:
             stack_id: "{{ managed_stack.id }}"
             configuration_id: "{{ stack_configuration.id }}"
             configuration_status: "{{ configuration_status.stack_configuration.status }}"
             deployment_groups: >-
               {{ deployment_groups.results
                  | map(attribute='stack_deployment_group')
                  | list }}

``stack_configuration`` is append-only. Every invocation creates a new snapshot, so trigger it
from a source-revision event or artifact digest rather than on every generic convergence run.

Collect deployment incident evidence
====================================

Stack notifications, HCP Terraform links, or incident intake should provide the relevant IDs.
Save them in a protected incident variables file:

.. code-block:: yaml

   stack_deployment_run_id: sdr-run123
   stack_deployment_step_ids:
     - sds-plan123
     - sds-apply456
   stack_state_ids:
     - sts-state123
   stack_diagnostic_ids:
     - std-diagnostic123

Save this as ``inspect-stack-incident.yml``:

.. code-block:: yaml

   ---
   - name: Collect immutable Stack incident evidence
     hosts: localhost
     connection: local
     gather_facts: false
     tasks:
       - name: Read the deployment run
         hashicorp.terraform.stack_deployment_run_info:
           stack_deployment_run_id: "{{ stack_deployment_run_id }}"
         register: deployment_run

       - name: Read every supplied deployment step
         hashicorp.terraform.stack_deployment_step_info:
           stack_deployment_step_id: "{{ item }}"
         loop: "{{ stack_deployment_step_ids | default([]) }}"
         register: deployment_steps

       - name: Read every supplied Stack state summary
         hashicorp.terraform.stack_state_info:
           stack_state_id: "{{ item }}"
         loop: "{{ stack_state_ids | default([]) }}"
         register: stack_states

       - name: Read every supplied diagnostic
         hashicorp.terraform.stack_diagnostic_info:
           stack_diagnostic_id: "{{ item }}"
         loop: "{{ stack_diagnostic_ids | default([]) }}"
         register: stack_diagnostics

       - name: Create the local incident-artifact directory
         ansible.builtin.file:
           path: "{{ playbook_dir }}/artifacts"
           state: directory
           mode: "0700"

       - name: Build the incident report
         ansible.builtin.copy:
           dest: "{{ playbook_dir }}/artifacts/{{ stack_deployment_run_id }}.json"
           mode: "0600"
           content: >-
             {{ {
                  'run': deployment_run.stack_deployment_run,
                  'steps': deployment_steps.results
                           | map(attribute='stack_deployment_step') | list,
                  'states': stack_states.results
                            | map(attribute='stack_state') | list,
                  'diagnostics': stack_diagnostics.results
                                 | map(attribute='stack_diagnostic') | list
                } | to_nice_json }}

Operational interpretation
==========================

- A Stack is not a workspace collection. Each deployment has isolated state and identity.
- Configuration snapshots are immutable and deployment runs are ordered by HCP Terraform.
- ``stack_state_info`` returns a sanitized summary, not a raw state download.
- A failed step or diagnostic should route to the owning platform team with the Stack,
  configuration, deployment, run, and step IDs intact.
- Do not automatically retry a failed deployment without classifying whether the failure occurred
  before or after provider side effects.

The incident playbook writes a local file for illustration. In production, send the structured
report to the organization's incident or audit system and redact sensitive diagnostic detail.

.. seealso::

   - :ansplugin:`hashicorp.terraform.stack#module`
   - :ansplugin:`hashicorp.terraform.stack_configuration#module`
   - :ansplugin:`hashicorp.terraform.stack_deployment_group_info#module`
   - :ansplugin:`hashicorp.terraform.stack_diagnostic_info#module`
