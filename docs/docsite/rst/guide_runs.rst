.. _ansible_collections.hashicorp.terraform.docsite.guide_runs:

***********************************
Runs and configuration versions
***********************************

This guide covers the run lifecycle: uploading a configuration version, queuing and applying a
run, gating an apply on policy results, inspecting and analyzing plans, managing run tasks, and
wiring runs together with triggers.

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

:ansplugin:`hashicorp.terraform.promote_run#module` evaluates the legacy Sentinel policy checks
returned by the run policy-checks API and applies only when those checks pass. This covers
Sentinel policy sets that do not use policy agents. Agent-based OPA evaluations and Terraform
policy (tf-policy) evaluations must be inspected through their dedicated modules before promotion.

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

.. _ansible_collections.hashicorp.terraform.docsite.guide_runs.plan_analyze:

Analyzing a plan for drift and changes
=======================================

:ansplugin:`hashicorp.terraform.plan_analyze#module` parses a Terraform plan JSON document and
returns machine-consumable drift and change facts. It complements
:ansplugin:`hashicorp.terraform.view_plan#module` (human-readable diff) with structured data
suitable for conditional logic. The module is **read-only** — ``changed`` is always ``false``.

Supply a ``run_id``, a ``plan_id``, or an inline ``plan_json`` dict:

.. code-block:: yaml

   - name: Analyze drift and changes for a run
     hashicorp.terraform.plan_analyze:
       run_id: "{{ run_result.id }}"
       detect_drift: true
       include_resource_changes: true
     register: analysis

   - name: Print drift and change summary
     ansible.builtin.debug:
       msg:
         - "Drift detected: {{ analysis.has_drift }} ({{ analysis.drift_count }} resource(s))"
         - "Changes: {{ analysis.has_changes }} ({{ analysis.change_count }} resource(s))"
         - "Risky: {{ analysis.summary.risky }}  Blocked: {{ analysis.summary.blocked }}"

Gate a playbook on blocked changes using custom attribute classification rules. ``safe_attributes``,
``risky_attributes``, and ``blocked_attributes`` all default to an empty list. Rules are
glob patterns matched against a canonical ``<module_path>.<type>.<name>.<attribute.path>`` target, so they
can be scoped by resource type:

.. code-block:: yaml

   # Illustrative AWS ruleset — not a default; write rules that match your own providers.
   - name: Analyze plan with attribute classification
     hashicorp.terraform.plan_analyze:
       run_id: "{{ run_result.id }}"
       blocked_attributes:
         - "aws_instance.*.ami"
         - "aws_iam_policy.*"
         - "aws_instance.*.subnet_id"
       risky_attributes:
         - "aws_instance.*.instance_type"
     register: analysis

   - name: Fail when any blocked attribute would change
     ansible.builtin.fail:
       msg: "Plan contains {{ analysis.summary.blocked }} blocked change(s) — aborting."
     when: analysis.summary.blocked > 0

Analyze a previously captured plan file without any API call:

.. code-block:: yaml

   - name: Analyze a captured plan JSON offline
     hashicorp.terraform.plan_analyze:
       plan_json: "{{ lookup('file', 'plan.json') | from_json }}"
       include_values: true
     register: offline_analysis

This module's ``classification`` field is descriptive only — see the next section for the authoritative
accept/deny decision.

.. _ansible_collections.hashicorp.terraform.docsite.guide_runs.plan_guard:

Gating a refresh-only apply with plan_guard
=============================================

A **refresh-only apply** updates Terraform *state* to match the real world — it does not change real
infrastructure. "Approving drift" means blessing an out-of-band change into state so the next normal plan
does not try to revert it. :ansplugin:`hashicorp.terraform.plan_guard#filter` and
:ansplugin:`hashicorp.terraform.plan_safe#test` answer exactly one question: *is it safe to absorb this
drift into state via a refresh-only apply?*

Both are pure, offline plugins (no API calls) so they can be used inline with ``set_fact`` or directly in
``when:``, unlike a module. They evaluate a :ansplugin:`hashicorp.terraform.plan_analyze#module` result
against ``allow``/``deny`` rules using the same matching grammar as ``plan_analyze``'s classification
rules. ``deny`` always wins over ``allow``; ``strict`` mode (the default) is fail-closed — an unmatched or
computed/unknown attribute is treated as unsafe; ``permissive`` mode default-allows unmatched attributes
but ``deny`` and any plan_analyze ``blocked`` classification still block.

The critical detail is that the drift is **analyzed and confirmed on the same run** — never a second,
independent run — so the decision always applies to exactly what gets applied:

.. code-block:: yaml

   - name: Create refresh-only plan (do not auto-apply)
     hashicorp.terraform.run:
       workspace_id: "{{ workspace_id }}"
       run_message: "Detect drift before Day 2 reconciliation"
       refresh_only: true
       auto_apply: false
       poll: true
       state: present
     register: refresh_run

   - name: Analyze the plan for THIS run
     hashicorp.terraform.plan_analyze:
       run_id: "{{ refresh_run.id }}"
       detect_drift: true
     register: drift_analysis

   - name: Gate the decision
     ansible.builtin.set_fact:
       guard: >-
         {{ drift_analysis | hashicorp.terraform.plan_guard(
              allow=['*.tags', 'aws_security_group.*.ingress'],
              deny=['aws_instance.*.instance_type', 'aws_iam_policy.*'],
              mode='strict') }}

   - name: Confirm (apply) the SAME run only when safe
     hashicorp.terraform.promote_run:
       run_id: "{{ refresh_run.id }}"
       wait: true
       comment: "Accept approved drift into Terraform state"
     when: guard.safe_to_refresh

Use the ``plan_safe`` test plugin for a more ergonomic ``when:`` when you don't need the full decision
breakdown:

.. code-block:: yaml

   - name: Confirm the run only when the drift is safe to accept
     hashicorp.terraform.promote_run:
       run_id: "{{ refresh_run.id }}"
       wait: true
     when: drift_analysis is hashicorp.terraform.plan_safe(allow=allow_rules, deny=deny_rules)

Compose ``fail_on_denied``-style hard failure with the built-in ``assert``, keeping failure semantics
idiomatic to Ansible instead of a module option:

.. code-block:: yaml

   - name: Fail loudly on any denied drift
     ansible.builtin.assert:
       that: "guard.safe_to_refresh"
       fail_msg: "Denied drift: {{ guard.denied }}"

``plan_guard`` is **not** a replacement for HCP Terraform/TFE-native Sentinel or OPA policy
evaluation. Use :ansplugin:`hashicorp.terraform.tf_policy_checks#lookup` for legacy Sentinel
checks and :ansplugin:`hashicorp.terraform.policy_evaluation_info#module` for agent-based OPA
evaluations. Those policies run server-side and gate runs inside TFE; ``plan_guard`` is a
lightweight, client-side, attribute-path gate evaluated in the playbook for the narrow purpose of
approving refresh-only applies.

Checking tf-policy posture
=============================

**Terraform policy (tf-policy)** is a separate, HCP-Terraform-only policy engine from
Sentinel/OPA, evaluated during a run's Init, Plan, and Apply stages. See
:ref:`guide_tf_policy <ansible_collections.hashicorp.terraform.docsite.guide_tf_policy>` for the
full pre-flight compliance gate and override pattern using
:ansplugin:`hashicorp.terraform.tf_policy_evaluation_info#module` and
:ansplugin:`hashicorp.terraform.tf_policy_evaluation#module`.

.. _ansible_collections.hashicorp.terraform.docsite.guide_runs.run_tasks:

Managing run tasks
==================

A *run task* is an external HTTPS endpoint that Terraform Cloud calls at designated stages of a
run (``pre_plan``, ``post_plan``, ``pre_apply``, ``post_apply``). Run tasks let you integrate
security scanners, cost estimators, or any webhook-based tooling directly into the Terraform run
lifecycle.

:ansplugin:`hashicorp.terraform.run_task#module` creates, updates, or deletes an
organization-scoped run task. Use :ansplugin:`hashicorp.terraform.run_task_info#module` to
inspect existing tasks:

.. code-block:: yaml

   - name: Register a security-scan run task
     hashicorp.terraform.run_task:
       organization: my-org
       name: security-scan
       url: https://scanner.example.com/hook
       description: "External SAST scan"
       enabled: true
       state: present
     register: task

   - name: Look up a run task by name
     hashicorp.terraform.run_task_info:
       organization: my-org
       name: security-scan
     register: task_info

   - name: List all run tasks in an organization
     hashicorp.terraform.run_task_info:
       organization: my-org
     register: all_tasks

Apply a run task globally to all workspaces in the organization:

.. code-block:: yaml

   - name: Apply security-scan globally at pre_plan (mandatory)
     hashicorp.terraform.run_task:
       organization: my-org
       name: security-scan
       url: https://scanner.example.com/hook
       global_configuration:
         enabled: true
         stages:
           - pre_plan
         enforcement_level: mandatory
       state: present

Delete a run task by name or by its ID:

.. code-block:: yaml

   - name: Delete run task by name
     hashicorp.terraform.run_task:
       organization: my-org
       name: security-scan
       state: absent

   - name: Delete run task by ID
     hashicorp.terraform.run_task:
       run_task_id: "{{ task.id }}"
       state: absent

.. _ansible_collections.hashicorp.terraform.docsite.guide_runs.workspace_run_tasks:

Attaching run tasks to a workspace
-----------------------------------

:ansplugin:`hashicorp.terraform.workspace_run_task#module` associates an existing run task with a
specific workspace, controlling the enforcement level and stages that apply to that workspace.
Use :ansplugin:`hashicorp.terraform.workspace_run_task_info#module` to inspect the associations:

.. code-block:: yaml

   - name: Attach security-scan to a workspace (advisory, post_plan)
     hashicorp.terraform.workspace_run_task:
       organization: my-org
       workspace: app-prod
       run_task_name: security-scan
       enforcement_level: advisory
       stages:
         - post_plan
       state: present
     register: association

   - name: Idempotent re-run — reports changed=false when already present
     hashicorp.terraform.workspace_run_task:
       organization: my-org
       workspace: app-prod
       run_task_name: security-scan
       enforcement_level: advisory
       stages:
         - post_plan
       state: present

   - name: Escalate to mandatory enforcement using IDs
     hashicorp.terraform.workspace_run_task:
       workspace_id: "{{ workspace_id }}"
       run_task_id: "{{ task.id }}"
       enforcement_level: mandatory
       state: present

Inspect existing associations on a workspace:

.. code-block:: yaml

   - name: List all run tasks on a workspace
     hashicorp.terraform.workspace_run_task_info:
       organization: my-org
       workspace: app-prod
     register: associations

   - name: Look up a specific association by run task name
     hashicorp.terraform.workspace_run_task_info:
       organization: my-org
       workspace: app-prod
       run_task_name: security-scan
     register: association

Remove an association by name or by its direct ID:

.. code-block:: yaml

   - name: Remove run task from workspace by name
     hashicorp.terraform.workspace_run_task:
       organization: my-org
       workspace: app-prod
       run_task_name: security-scan
       state: absent

   - name: Remove run task from workspace by association ID
     hashicorp.terraform.workspace_run_task:
       workspace_id: "{{ workspace_id }}"
       workspace_run_task_id: "{{ association.workspace_run_task.id }}"
       state: absent

.. _ansible_collections.hashicorp.terraform.docsite.guide_runs.task_stages:

Inspecting task stages and results
------------------------------------

After a run completes, :ansplugin:`hashicorp.terraform.task_stage_info#module` returns the task
stages for the run and :ansplugin:`hashicorp.terraform.task_result_info#module` reads the outcome
for a specific task within a stage. Together they let you audit post-run task results without
leaving Ansible:

.. code-block:: yaml

   - name: List all task stages for a run
     hashicorp.terraform.task_stage_info:
       run_id: "{{ run_result.id }}"
     register: stages

   - name: Get the first task stage with its task results sideloaded
     hashicorp.terraform.task_stage_info:
       task_stage_id: "{{ stages.task_stages[0].id }}"
       include:
         - task_results
     register: stage_detail

   - name: Read the first individual task result
     hashicorp.terraform.task_result_info:
       task_result_id: "{{ stage_detail.task_stage.task_results[0].id }}"
     register: result

   - name: Show task outcome
     ansible.builtin.debug:
       msg: >-
         {{ result.task_result.task_name }}: {{ result.task_result.status }}
         — {{ result.task_result.message }}

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
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_registry_modules` — manage the
     private registry modules that runs consume.
