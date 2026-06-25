.. _ansible_collections.hashicorp.terraform.docsite.guide_runs:

***********************************
Runs and configuration versions
***********************************

This guide covers the run lifecycle: uploading a configuration version, queuing and applying a
run, gating an apply on policy results, inspecting plans, and wiring runs together with triggers.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_runs.config_version:

Uploading a configuration version
=================================

:ansplugin:`hashicorp.terraform.configuration_version#module` packages a local Terraform
configuration directory and uploads it to a workspace. It can optionally wait for the upload to
finish processing:

.. code-block:: yaml

   - name: Upload a configuration version
     hashicorp.terraform.configuration_version:
       workspace_id: "{{ workspace_id }}"
       configuration_files_path: "{{ playbook_dir }}/terraform"
       auto_queue_runs: false
       poll_interval: 5
       poll_timeout: 60
       state: present
     register: config_version

Use :ansplugin:`hashicorp.terraform.configuration_version_info#module` to look up an existing
configuration version.

.. _ansible_collections.hashicorp.terraform.docsite.guide_runs.run:

Queuing and applying a run
==========================

:ansplugin:`hashicorp.terraform.run#module` creates a run (plan) and, separately, applies it. Set
``poll: true`` to wait for the run to reach a terminal state:

.. code-block:: yaml

   - name: Create and plan a run
     hashicorp.terraform.run:
       workspace_id: "{{ workspace_id }}"
       configuration_version: "{{ config_version.id }}"
       run_message: Deployed by Ansible
       poll: true
       poll_interval: 10
       poll_timeout: 300
       state: present
     register: run_result

   - name: Apply the run
     hashicorp.terraform.run:
       run_id: "{{ run_result.id }}"
       poll: true
       poll_interval: 10
       poll_timeout: 300
       state: applied

Check on a run later with :ansplugin:`hashicorp.terraform.run_info#module` (useful when you set
``poll: false`` to avoid blocking).

.. _ansible_collections.hashicorp.terraform.docsite.guide_runs.promote:

Gating an apply on policy results
=================================

:ansplugin:`hashicorp.terraform.promote_run#module` evaluates a run's Sentinel/OPA policy checks
and applies only when the policies pass — a safer apply step for governed workspaces:

.. code-block:: yaml

   - name: Apply only if mandatory policies pass
     hashicorp.terraform.promote_run:
       run_id: "{{ run_result.id }}"
       require_policy_pass: true
       allow_advisory_failures: true
       wait: true
       timeout: 900
     register: promote

   - name: Evaluate policies without applying
     hashicorp.terraform.promote_run:
       run_id: "{{ run_result.id }}"
       auto_apply_when_eligible: false
     register: evaluation

For ad-hoc policy inspection in conditionals, the
:ansplugin:`hashicorp.terraform.tf_policy_checks#lookup` lookup returns policy-check results
directly. See :ref:`ansible_collections.hashicorp.terraform.docsite.guide_lookups`.

.. _ansible_collections.hashicorp.terraform.docsite.guide_runs.view_plan:

Inspecting a plan
=================

:ansplugin:`hashicorp.terraform.view_plan#module` renders a run's plan as a human-readable diff or
as structured JSON:

.. code-block:: yaml

   - name: View plan diff for a run
     hashicorp.terraform.view_plan:
       run_id: "{{ run_result.id }}"
       output_format: diff

   - name: Retrieve plan as structured JSON
     hashicorp.terraform.view_plan:
       run_id: "{{ run_result.id }}"
       output_format: json
     register: plan_json

.. _ansible_collections.hashicorp.terraform.docsite.guide_runs.triggers:

Connecting workspaces with run triggers
=======================================

:ansplugin:`hashicorp.terraform.run_trigger#module` creates a run trigger so that an apply in a
source workspace queues a run in a target workspace — for example, a networking workspace that
feeds an application workspace:

.. code-block:: yaml

   - name: Trigger 'app' runs from 'networking'
     hashicorp.terraform.run_trigger:
       organization: my-org
       workspace: app                 # target
       sourceable_workspace: networking  # source
       state: present

   # or by IDs
   - hashicorp.terraform.run_trigger:
       workspace_id: ws-app123
       sourceable_id: ws-net456
       state: present

.. _ansible_collections.hashicorp.terraform.docsite.guide_runs.events:

Auditing run events
====================

The :ansplugin:`hashicorp.terraform.tf_run_events#lookup` lookup retrieves the timeline of events
for a run (queued, planned, applied, …), optionally filtered by action or time window. See
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_lookups`.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_variables` — set the variables a
     run uses.
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_lookups` — read outputs, policy
     checks, and run events.
