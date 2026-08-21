.. _ansible_collections.hashicorp.terraform.docsite.guide_tf_policy:

***********************************
Enforcing tf-policy compliance
***********************************

This guide covers Terraform policy (tf-policy) — HCP Terraform's native policy-as-code engine,
distinct from the Sentinel/OPA policy-check flow covered in :ref:`guide_runs
<ansible_collections.hashicorp.terraform.docsite.guide_runs.plan_guard>`. tf-policy evaluates
policies during a run's Init, Plan, and Apply stages and is HCP Terraform only — it has no
Terraform Enterprise (self-hosted) equivalent.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_tf_policy.gate:

Gating a workflow on tf-policy compliance
==========================================

:ansplugin:`hashicorp.terraform.tf_policy_evaluation_info#module` is a read-only pre-flight
compliance gate. Point it at a run and it returns one evaluation per applicable stage:

.. code-block:: yaml

   - name: Read tf-policy posture for the run
     hashicorp.terraform.tf_policy_evaluation_info:
       run_id: "{{ tfc_run_id }}"
       include_outcomes: true
     register: posture

   - name: Fail the play if the run is non-compliant
     ansible.builtin.assert:
       that:
         - posture.evaluations
           | selectattr('status', 'in', ['failed', 'errored'])
           | list | length == 0
       fail_msg: "Run {{ tfc_run_id }} has failed tf-policy evaluation(s)."

Set ``include_outcomes: true`` to attach each evaluation's policy-set outcomes (as
``set_outcomes``) in the same task — useful for surfacing *why* a run failed, not just that it
did. Narrow those outcomes with ``filter``:

.. code-block:: yaml

   - name: Only fetch mandatory_overridable failures
     hashicorp.terraform.tf_policy_evaluation_info:
       run_id: "{{ tfc_run_id }}"
       include_outcomes: true
       filter:
         status: failed
         enforcement_level: mandatory_overridable
     register: posture

Read a single evaluation directly with ``evaluation_id`` instead of ``run_id`` — the two are
mutually exclusive:

.. code-block:: yaml

   - name: Read one evaluation by ID
     hashicorp.terraform.tf_policy_evaluation_info:
       evaluation_id: "tfpeval-EavQ1LztoRTQHSNT"
     register: evaluation

.. _ansible_collections.hashicorp.terraform.docsite.guide_tf_policy.override:

Overriding a mandatory_overridable failure
============================================

:ansplugin:`hashicorp.terraform.tf_policy_evaluation#module` overrides an evaluation that is
``awaiting_override``. Override only succeeds for Plan-stage evaluations with at least one
``mandatory_overridable`` failure and no non-overridable ``mandatory`` failures — check
``actions.is_overridable`` before attempting one:

.. code-block:: yaml

   - name: Override every overridable awaiting_override evaluation from the run
     hashicorp.terraform.tf_policy_evaluation:
       evaluation_id: "{{ item.id }}"
       comment: "Ops approved - ticket OPS-123"
     loop: >-
       {{ posture.evaluations
          | selectattr('status', 'eq', 'awaiting_override')
          | selectattr('actions.is_overridable', 'eq', true)
          | list }}

Evaluations are produced by Terraform runs and are never created, updated, or deleted by this
module — ``state: overridden`` (the default and only supported value) is the single transition it
performs. Re-running it against an already-overridden evaluation is a no-op (``changed: false``).

.. _ansible_collections.hashicorp.terraform.docsite.guide_tf_policy.policy_set:

Managing tf-policy policy sets
================================

tf-policy policy sets are ordinary :ansplugin:`hashicorp.terraform.policy_set#module` resources
with ``kind: tfpolicy`` — no separate module is needed. VCS-connected policy sets are the
primarily supported path:

.. code-block:: yaml

   - name: Create a VCS-connected tf-policy policy set
     hashicorp.terraform.policy_set:
       organization: "my-org"
       name: "tfpolicy-guardrails"
       kind: tfpolicy
       policy_tool_version: "0.1.0"
       overridable: true
       vcs_repo:
         identifier: "my-org/policy-repo"
         branch: "main"
         oauth_token_id: "ot-abc123"
       state: present
     register: policy_set

For local iteration without a VCS connection,
:ansplugin:`hashicorp.terraform.policy_set_version#module` uploads a local directory directly:

.. code-block:: yaml

   - name: Create a non-VCS tf-policy policy set
     hashicorp.terraform.policy_set:
       organization: "my-org"
       name: "tfpolicy-guardrails"
       kind: tfpolicy
       policy_tool_version: "0.1.0"
       overridable: true
       state: present
     register: policy_set

   - name: Upload local policy files
     hashicorp.terraform.policy_set_version:
       policy_set_id: "{{ policy_set.id }}"
       policy_files_path: "{{ playbook_dir }}/policies"
     register: policy_version

If your ``.policy.hcl`` files live in a subdirectory rather than at the root of
``policy_files_path``, set ``policies_path`` on the policy set to point at it:

.. code-block:: yaml

   - name: Create a non-VCS tf-policy policy set with policies in a subdirectory
     hashicorp.terraform.policy_set:
       organization: "my-org"
       name: "tfpolicy-guardrails"
       kind: tfpolicy
       policy_tool_version: "0.1.0"
       overridable: true
       policies_path: "policies"
       state: present
     register: policy_set

Without ``policies_path`` set, the engine looks for policy files at the archive root. A nested
layout with ``policies_path`` left unset is accepted without error and silently evaluates zero
policies — every evaluation "passes" with an empty result count, indistinguishable from a
genuinely compliant run until you notice nothing was actually checked.

Attach the policy set to a workspace the same way as any other policy set:

.. code-block:: yaml

   - name: Attach the policy set to a workspace
     hashicorp.terraform.policy_set:
       policy_set_id: "{{ policy_set.id }}"
       workspace_ids:
         - "{{ workspace_id }}"
       state: present

.. _ansible_collections.hashicorp.terraform.docsite.guide_tf_policy.terraform_version:

Terraform version requirement
===============================

tf-policy requires the workspace's Terraform CLI version to meet a minimum the org must have
enabled — evaluations on an incompatible version come back ``errored`` rather than being
silently skipped. Set it explicitly on the workspace rather than relying on ``latest``, which
resolves to the newest *stable* release, not a tf-policy-compatible build:

.. code-block:: yaml

   - name: Create a workspace on a tf-policy-compatible Terraform version
     hashicorp.terraform.workspace:
       workspace: "my-workspace"
       organization: "my-org"
       terraform_version: "1.16.0-alpha20260626"
       state: present

Check with your organization admin for the minimum version currently required — this is a
fast-moving target on a beta feature.
