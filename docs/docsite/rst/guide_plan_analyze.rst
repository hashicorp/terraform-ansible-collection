.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze:

**************************************************
Drift-safe Day 2 operations
**************************************************

This guide is a detailed reference and demo script for the collection's drift-safe Day 2
workflow: :ansplugin:`hashicorp.terraform.plan_analyze#module`,
:ansplugin:`hashicorp.terraform.plan_guard#filter`, and
:ansplugin:`hashicorp.terraform.plan_safe#test`. It complements the shorter introduction in
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs` with full option references,
the exact decision rules, and a set of realistic customer scenarios with their observed
input/output behavior — suitable for walking a product manager or customer through the feature
live.

.. contents::
   :local:
   :depth: 2

.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.concept:

The conceptual model (read this first)
=======================================

HCP Terraform and Terraform Enterprise are the source of truth for infrastructure managed by
Terraform. In Day 2 operations, infrastructure drifts from that state: someone edits a security
group, a tag, an instance type, out of band, through the AWS console or CLI. A **refresh-only
apply** updates Terraform *state* to match the real world. It does **not** change real
infrastructure.

- **"Approving drift"** = blessing the out-of-band change into Terraform state, so the next
  normal plan does not try to revert it.
- **"Remediating drift"** = a *normal* apply that reverts the real infrastructure back to what
  the configuration declares — the opposite action, and out of scope for this workflow.

``plan_guard``/``plan_safe`` answer exactly one question: *is it safe to absorb this drift into
state via a refresh-only apply?* They are **not** a replacement for HCP Terraform/Terraform
Enterprise's native Sentinel/OPA policy checks (surfaced by
:ansplugin:`hashicorp.terraform.tf_policy_checks#lookup`) — those run server-side, gate runs
inside TFE, and are authored in policy languages. This workflow is a lightweight, client-side,
attribute-path allow/deny gate evaluated in the playbook, for the narrow purpose of approving
refresh-only applies.

.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.architecture:

How the three pieces fit together
==================================

.. code-block:: text

                  +--------------------------------------------------+
     playbook --> | run (refresh_only, auto_apply:false, poll)       |  existing
                  +-------------------------+------------------------+
                                            | run_id (pending, planned)
                                            v
     +-----------------------------------------------------------------+
     | plan_analyze  (module, read-only)                               |
     |   - resolves plan JSON via run_id / plan_id / inline plan_json  |
     |   - turns it into neutral facts + a descriptive classification |
     +-------------------------+---------------------------------------+
                               | analysis dict (registered var)
                               v
     +-----------------------------------------------------------------+
     | plan_guard / plan_safe  (filter + test plugins, pure, no I/O)   |
     |   - matches allow/deny rules against a canonical target string |
     |   - returns the authoritative safe_to_refresh decision          |
     +-------------------------+---------------------------------------+
                               | when: decision.safe_to_refresh
                               v
                  +--------------------------------------------------+
                  | run: CONFIRM the SAME run (state: applied)       |  existing
                  +--------------------------------------------------+

Two design points are load-bearing and worth calling out explicitly when demoing this:

1. **Analyze and confirm the same run.** The workflow never creates a second, independent run to
   apply. If it did, the second run's plan could differ from the one that was actually analyzed
   (a time-of-check/time-of-use bug) — the gate's decision would no longer apply to what actually
   gets absorbed into state.
2. **``plan_analyze`` is descriptive; ``plan_guard``/``plan_safe`` are authoritative.** A resource
   ``plan_analyze`` classifies ``safe``/``risky`` is only a hint. Only ``plan_guard``'s
   ``safe_to_refresh`` decision is binding — except for ``blocked``, which is escalated
   unconditionally by ``plan_guard`` regardless of any ``allow`` rule (see
   :ref:`ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.scenarios.blocked`).

.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.matching_grammar:

The matching grammar (shared by all three)
============================================

Rules — ``safe_attributes``/``risky_attributes``/``blocked_attributes`` on ``plan_analyze``, and
``allow``/``deny`` on ``plan_guard``/``plan_safe`` — are ``fnmatch``-style glob patterns matched
against a canonical **target string** built from the plan JSON:

- Resource attribute target: ``<module_path>.<type>.<name>.<attribute.path>``,
  e.g. ``module.networking.aws_instance.web.tags.role``. For a root-module resource the module
  prefix is omitted: ``aws_instance.web.tags.role``.
- List indices are stripped from the attribute path (``ingress[0].from_port`` becomes
  ``ingress.from_port``), so rules do not need to account for how many list items changed.
- Output target: ``output.<name>``.

Two resolution rules matter in practice:

- **Prefix semantics.** A rule on a parent path also matches child paths — ``aws_instance.*.tags``
  matches both ``tags`` itself and ``tags.role``. This lets one rule cover an entire map/nested
  block without enumerating every key.
- **Type/module scoping.** Because the target includes the resource type and module path, rules
  can be as broad or as narrow as needed: ``*.tags`` (any resource, the ``tags`` attribute),
  ``aws_instance.*.instance_type`` (any ``aws_instance``, that one attribute),
  ``module.networking.*`` (anything under one module).

There are **no built-in default rules**. ``safe_attributes``, ``risky_attributes``,
``blocked_attributes``, ``allow``, and ``deny`` all default to an empty list. This is a
deliberate, provider-agnostic design choice: the collection targets HCP Terraform/TFE generically
(AWS, Azure, GCP, Kubernetes, on-prem), and baking in AWS-shaped defaults (as an early proposal
suggested) would silently misclassify everything for non-AWS users. With no rules, ``strict`` mode
reports everything as not-safe — fail-closed, the correct conservative default for a drift gate.

.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.plan_analyze:

``plan_analyze`` reference
===========================

:ansplugin:`hashicorp.terraform.plan_analyze#module` parses a Terraform plan JSON document —
fetched via ``run_id``/``plan_id``, or supplied inline via ``plan_json`` for offline analysis — and
returns machine-consumable drift and change facts. It is **read-only**: ``changed`` is always
``false``, and it supports check mode trivially.

Key options
-----------

.. list-table::
   :header-rows: 1
   :widths: 22 10 12 56

   * - Option
     - Type
     - Default
     - Notes
   * - ``run_id`` / ``plan_id`` / ``plan_json``
     - str / str / dict
     - —
     - Exactly one required. ``plan_json`` bypasses the API entirely — useful for offline
       analysis, testing, or feeding a captured :ansplugin:`hashicorp.terraform.view_plan#module`
       JSON output.
   * - ``detect_drift``
     - bool
     - ``true``
     - Walks ``resource_drift[]`` — out-of-band changes discovered by a refresh.
   * - ``include_resource_changes``
     - bool
     - ``true``
     - Walks ``resource_changes[]`` — changes the plan itself would make.
   * - ``include_output_changes``
     - bool
     - ``true``
     - Analyzes changed workspace outputs.
   * - ``include_values``
     - bool
     - ``false``
     - When true, includes masked ``before``/``after`` values per entry. Values flagged sensitive
       in the plan's own ``before_sensitive``/``after_sensitive`` markers are always masked, even
       then.
   * - ``safe_attributes`` / ``risky_attributes`` / ``blocked_attributes``
     - list[str]
     - ``[]``
     - Descriptive classification rules (see the matching grammar above). Precedence is
       ``blocked > risky > safe > unknown``. With no rules, every changed attribute is
       classified ``safe`` and every computed attribute ``unknown``.

Return shape
------------

.. code-block:: yaml

   changed: false
   has_drift: true
   drift_count: 2
   has_changes: true
   change_count: 3
   resource_changes:
     - address: "module.networking.aws_instance.web"
       type: "aws_instance"
       name: "web"
       provider_name: "registry.terraform.io/hashicorp/aws"
       module_address: "module.networking"
       mode: "managed"
       actions: ["update"]
       action_reason: "tainted"
       source: "resource_drift"          # or "resource_changes"
       changed_attributes: ["tags.role", "instance_type"]
       unknown_attributes: ["private_dns"]
       classification: "risky"           # descriptive; "unknown" if no rules supplied
       change_summary: "1 risky, 1 safe, 1 unknown"
   output_changes: []
   summary: {safe: 1, risky: 1, blocked: 0, unknown: 1}

An unrecognized ``format_version`` major version never fails the task — it emits an Ansible
warning and proceeds best-effort, since HashiCorp may extend the schema with additive fields
without breaking what this module reads.

.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.plan_guard:

``plan_guard`` (filter) reference
====================================

:ansplugin:`hashicorp.terraform.plan_guard#filter` evaluates a ``plan_safe`` result against
``allow``/``deny`` rules and returns a single, auditable decision. It performs **zero I/O** — no
network calls, no credentials — so it can be used inline (piped into ``set_fact``, or directly in
an expression) without the cost of forking a Python interpreter the way a module invocation would.

.. code-block:: yaml

   guard: "{{ drift_analysis | hashicorp.terraform.plan_guard(allow=allow_rules, deny=deny_rules, mode='strict') }}"

Inputs: ``allow`` (list[str], default ``[]``), ``deny`` (list[str], default ``[]``, always wins
over ``allow``), ``mode`` (``strict`` default-deny, or ``permissive`` default-allow).

Decision output
---------------

.. code-block:: yaml

   safe_to_refresh: false
   mode: strict
   summary: {allowed: 2, denied: 3, blocked: 0, unknown: 0}
   allowed:
     - {address: "aws_security_group.app", attribute: "ingress", rule: "aws_security_group.*.ingress"}
   denied:
     - {address: "aws_instance.web", attribute: "instance_type", rule: "aws_instance.*.instance_type"}
   blocked: []
   unknown: []
   reasons:
     - "instance_type on aws_instance.web matched deny rule 'aws_instance.*.instance_type'"

The exact truth table
----------------------

``safe_to_refresh`` is ``true`` **if and only if**:

- no attribute is classified ``blocked`` by the upstream ``plan_analyze`` result, **and**
- no attribute matches a ``deny`` rule, **and**
- in ``strict`` mode only: every changed/drifted attribute is matched by an ``allow`` rule, and
  there are no computed/unknown attributes.

In ``permissive`` mode, unmatched and unknown attributes do **not** block — but ``deny`` and
``blocked`` still do, unconditionally, in both modes. Concretely:

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   * - Attribute's situation
     - strict
     - permissive
     - Why
   * - Matches an ``allow`` rule
     - Allowed
     - Allowed
     - Explicitly trusted either way.
   * - Matches a ``deny`` rule
     - Denied
     - **Denied**
     - Deny always wins, including over a matching ``allow`` rule and regardless of mode.
   * - Classified ``blocked`` by ``plan_analyze``
     - Denied
     - **Denied**
     - Escalated unconditionally; cannot be rescued by ``allow`` — see
       :ref:`ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.scenarios.blocked`.
   * - Matches neither list (unmatched)
     - Denied (fail-closed)
     - Allowed (fail-open)
     - The one behavior that actually changes between modes.
   * - Computed/unknown (value not known until apply)
     - Denied
     - Allowed
     - Same default-disposition rule as "unmatched" — an unknown value is treated exactly like
       an unrecognized attribute.

.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.plan_safe:

``plan_safe`` (test) reference
=================================

:ansplugin:`hashicorp.terraform.plan_safe#test` is an ergonomic boolean wrapper around
``plan_guard`` for use directly in ``when:``, without an intermediate ``set_fact``. It takes the
same ``allow``/``deny``/``mode`` inputs and returns exactly the ``safe_to_refresh`` value
``plan_guard`` would for the same inputs — nothing more.

.. code-block:: yaml

   when: drift_analysis is hashicorp.terraform.plan_safe(allow=allow_rules, deny=deny_rules)

.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.end_to_end:

Full end-to-end example
==========================

.. code-block:: yaml

   - name: Create refresh-only plan (do not auto-apply)
     hashicorp.terraform.run:
       workspace_id: "{{ workspace_id }}"
       run_message: "Detect drift before Day 2 reconciliation"
       refresh_only: true
       auto_apply: false
       poll: true                 # wait until planned (terminal plan state)
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
              allow=allow_rules, deny=deny_rules, mode='strict') }}

   - name: Confirm (apply) the SAME run only when safe
     hashicorp.terraform.run:
       run_id: "{{ refresh_run.id }}"
       state: applied
       poll: true
     when: guard.safe_to_refresh

   - name: Discard the run when drift was rejected
     hashicorp.terraform.run:
       run_id: "{{ refresh_run.id }}"
       state: discarded
     when: not guard.safe_to_refresh

.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.scenarios:

Customer demo scenarios
==========================

The scenarios below were run against **real HCP Terraform + real AWS infrastructure** (an
``aws_instance`` and an ``aws_security_group``), not just synthetic test fixtures, using this
rule set:

.. code-block:: yaml

   allow_rules:
     - "aws_instance.*.tags"
     - "aws_instance.*.tags_all"
     - "aws_security_group.*.tags"
     - "aws_security_group.*.tags_all"
   deny_rules:
     - "aws_instance.*.instance_type"
     - "aws_instance.*.ami"
     - "aws_security_group.*.ingress"

Scenario 1 — governance tag added out-of-band
-----------------------------------------------

**Story**: a FinOps team enforces a tagging mandate directly in the AWS console — a
``CostCenter`` tag — faster than the platform team can add it to the Terraform configuration.

**Change**: ``aws_instance.demo_web`` gains ``tags.CostCenter`` (and the provider-computed
``tags_all.CostCenter``).

**Result**: ``safe_to_refresh: true``. Both attributes matched ``aws_instance.*.tags`` /
``aws_instance.*.tags_all``.

**Takeaway**: purely additive, cosmetic metadata is exactly the kind of drift teams want absorbed
automatically, without a human in the loop for every tag.

Scenario 2 — emergency access opened for an incident
-------------------------------------------------------

**Story**: an on-call engineer opens port 8080 directly on the security group during an incident,
intending to formalize it in Terraform later (a very common real-world drift source).

**Change**: a new ``aws_security_group.demo`` ingress rule appears, producing **six** changed
sub-attributes (``ingress[1].cidr_blocks[0]``, ``.description``, ``.from_port``, ``.protocol``,
``.self``, ``.to_port``).

**Result**: ``safe_to_refresh: false``. All six sub-attributes matched the single
``aws_security_group.*.ingress`` deny rule, via prefix semantics — one rule, not six.

**Takeaway**: security-relevant network changes are never silently absorbed, no matter how many
underlying fields Terraform reports them as.

Scenario 3 — an existing rule is edited, not replaced
---------------------------------------------------------

**Story**: instead of adding a new rule, a "security remediation" narrows the existing SSH rule's
CIDR from ``0.0.0.0/0`` to a specific address and updates its description — same ports, different
scope.

**Change**: ``ingress[0].cidr_blocks[0]`` and ``ingress[0].description`` change; ports are
untouched and so do not appear in ``changed_attributes`` at all.

**Result**: ``safe_to_refresh: false`` — still matched by ``aws_security_group.*.ingress`` even
though it is a narrowing (arguably an improvement), not a new rule.

**Takeaway**: ``plan_guard`` does not get to judge *intent* — a security-tightening change is
denied by the same rule as a security-loosening one. Good automated intent still needs human
review before being absorbed; this is deliberate, not a limitation.

Scenario 4 — a change nobody wrote a rule for
--------------------------------------------------

**Story**: someone enables detailed CloudWatch monitoring on the instance — unrelated to tags,
unrelated to networking, and not anticipated by either the ``allow`` or ``deny`` list.

**Change**: ``aws_instance.demo_web`` attribute ``monitoring`` changes.

**Result** (same analysis, evaluated both ways):

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Mode
     - ``safe_to_refresh``
     - Why
   * - ``strict``
     - false
     - Unmatched attribute; strict mode's fail-closed default treats anything not explicitly
       allowed as unsafe.
   * - ``permissive``
     - would be allowed *for this attribute*
     - Unmatched attributes default-allow in permissive mode — but see Scenario 5, where a
       ``deny`` match elsewhere in the same run still keeps the overall run unsafe.

**Takeaway**: this is the cleanest way to demo the strict/permissive knob — the identical drift,
evaluated twice against the identical analysis (no second Terraform run needed), flips outcome.

.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.scenarios.mixed:

Scenario 5 — a realistic mixed maintenance window
------------------------------------------------------

**Story**: in practice, changes rarely arrive one at a time. A maintenance window touches several
things at once: the tag from Scenario 1, the CIDR narrowing from Scenario 3, and the monitoring
toggle from Scenario 4, all landing in the **same** refresh-only run.

**Result**:

.. code-block:: text

   STRICT:     safe_to_refresh=False   allowed=2  denied=3
   PERMISSIVE: safe_to_refresh=False   allowed=3  denied=2

The tag attributes are allowed in both modes. The ``monitoring`` attribute flips from denied to
allowed between modes, exactly as Scenario 4 predicted. The ingress attributes stay denied in
**both** modes — because ``deny`` is unconditional — which is why the overall verdict is unsafe
either way, even though the *allowed* count went up.

**Takeaway**: this is the scenario to use if a customer asks "what happens when several things
change at once?" — the allow/deny/unknown buckets stay cleanly separated per attribute, and the
overall verdict is exactly as conservative as the worst single attribute in the run.

.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.scenarios.blocked:

Scenario 6 — a rule that cannot be talked out of it
---------------------------------------------------------

**Story**: a platform team wants certain changes to be non-negotiable — not just "denied by
default," but denied even if someone (accidentally or otherwise) adds a broad ``allow`` rule
later.

**Setup**: run ``plan_analyze`` with ``blocked_attributes: ["aws_security_group.*.ingress"]``, so
those attributes carry ``classification: blocked`` in the analysis. Then evaluate ``plan_guard``
with a deliberately permissive ``allow: ["*"]``.

**Result**: ``safe_to_refresh: false``, with the ingress attributes reported in the ``blocked``
bucket, not ``allowed`` — the wildcard ``allow`` rule has no effect on them.

**Takeaway**: ``blocked_attributes`` in ``plan_analyze`` is how a platform team encodes rules that
individual playbook authors cannot override with a looser ``allow`` list — a guardrail on the
guardrail.

Scenario 7 — one intentional change, several unintentional ones
----------------------------------------------------------------------

**Story**: an operator changes ``instance_type`` to right-size an instance. AWS requires a
stop/start cycle to apply that change to a running instance.

**Change**: as expected, ``instance_type`` changes (denied — explicit deny match). But the plan
also reports:

- ``public_ip`` and ``public_dns`` changed — an instance without an Elastic IP gets a **new**
  public address on every restart, an incidental side effect of the stop/start, not something the
  operator asked for.
- ``cpu_options[*].threads_per_core`` / ``cpu_threads_per_core`` changed — different instance
  families have different default CPU topologies.

**Result**: ``safe_to_refresh: false`` — every one of those attributes is unmatched by any rule,
so strict mode denies the whole run.

**Takeaway**: this is arguably the most important scenario to show a customer. A naive
"remediate drift automatically" tool might only look at the attribute someone intentionally
changed and miss that the *side effects* of that change are also drift. Fail-closed, attribute-
level analysis catches all of it — including a new public IP that could silently break anything
hardcoded to the old one.

.. _ansible_collections.hashicorp.terraform.docsite.guide_plan_analyze.faq:

Frequently asked questions
=============================

**Why does nothing get applied by default?**
   Because ``safe_attributes``/``risky_attributes``/``blocked_attributes``/``allow``/``deny`` all
   default to an empty list, and ``strict`` mode is fail-closed. This is intentional: a
   drift-acceptance gate that guesses "probably fine" by default is not a gate. Rules must be
   supplied deliberately, and are provider/attribute-shape specific by design (see the matching
   grammar section above) — there is no universal "safe" tag name or instance attribute across
   AWS, Azure, GCP, and Kubernetes.

**Can I try this without a real cloud account?**
   Yes — ``plan_analyze`` accepts inline ``plan_json``, so you can feed it a previously captured
   :ansplugin:`hashicorp.terraform.view_plan#module` JSON output, or a hand-built fixture, entirely
   offline:

   .. code-block:: yaml

      - name: Analyze a captured plan JSON offline
        hashicorp.terraform.plan_analyze:
          plan_json: "{{ lookup('file', 'plan.json') | from_json }}"
        register: analysis

      - name: Gate it the same way, no network calls at all
        ansible.builtin.set_fact:
          guard: "{{ analysis | hashicorp.terraform.plan_guard(allow=allow_rules, deny=deny_rules) }}"

**Does this replace Sentinel/OPA policy checks?**
   No. Sentinel/OPA (see :ansplugin:`hashicorp.terraform.tf_policy_checks#lookup` and
   :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs`) run server-side inside TFE
   and are authored in a policy language; they gate *any* run. ``plan_guard``/``plan_safe`` are a
   lightweight, client-side, attribute-path allow/deny check evaluated in the playbook, scoped
   specifically to deciding whether a refresh-only apply is safe to confirm.

**What does it cost to evaluate a decision?**
   Nothing, computationally. ``plan_guard`` and ``plan_safe`` are filter/test plugins: pure
   functions with no I/O and no external process fork, unlike a module invocation. Re-evaluating
   the same analysis under a different ``mode`` or rule set (as in Scenario 4/5 above) is free —
   no new Terraform run is required.
