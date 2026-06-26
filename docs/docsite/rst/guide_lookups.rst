.. _ansible_collections.hashicorp.terraform.docsite.guide_lookups:

**************
Lookup plugins
**************

The collection ships four lookup plugins for reading data from HCP Terraform / Terraform Enterprise
inline in your playbooks and templates. Like the modules, they authenticate with ``tfe_token`` /
``TFE_TOKEN`` and honor ``tfe_address`` / ``TFE_ADDRESS``. Lookup arguments are passed as keyword
arguments (not positional terms).

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_lookups.tf_output:

``tf_output`` — read state outputs
==================================

:ansplugin:`hashicorp.terraform.tf_output#lookup` returns the value of a workspace output (or all
outputs). Identify the workspace by ID or by organization plus name, and the output by ``name``.
Use ``display_sensitive=true`` to retrieve a sensitive value.

.. code-block:: yaml

   - name: Read one output by name
     ansible.builtin.set_fact:
       vpc_id: "{{ lookup('hashicorp.terraform.tf_output',
                          name='vpc_id', organization='my-org', workspace='my-workspace') }}"

   - name: Read a sensitive output
     ansible.builtin.set_fact:
       api_token: "{{ lookup('hashicorp.terraform.tf_output',
                            name='api_token', workspace_id='ws-123', display_sensitive=true) }}"

Omit ``name`` to return all outputs as a structure.

.. _ansible_collections.hashicorp.terraform.docsite.guide_lookups.tf_variable_set_vars:

``tf_variable_set_vars`` — read variable-set values
===================================================

:ansplugin:`hashicorp.terraform.tf_variable_set_vars#lookup` returns the variables in a variable
set, identified by ``variable_set_id`` or by ``name`` plus ``organization``:

.. code-block:: yaml

   - name: Fetch platform defaults by variable-set ID
     ansible.builtin.set_fact:
       platform_vars: "{{ lookup('hashicorp.terraform.tf_variable_set_vars',
                                 variable_set_id='varset-abc123') }}"

   - name: Fetch by variable-set name
     ansible.builtin.set_fact:
       platform_vars: "{{ lookup('hashicorp.terraform.tf_variable_set_vars',
                                 name='platform-defaults', organization='my-org',
                                 display_sensitive=false) }}"

.. _ansible_collections.hashicorp.terraform.docsite.guide_lookups.tf_policy_checks:

``tf_policy_checks`` — read policy results
==========================================

:ansplugin:`hashicorp.terraform.tf_policy_checks#lookup` returns the policy checks for a run. Use
``only_failures=true`` to narrow the result, for example to gate an apply in a conditional:

.. code-block:: yaml

   - name: Fail if any hard-mandatory policy failed
     ansible.builtin.fail:
       msg: "Mandatory policy checks failed on run {{ run_id }}"
     when: >-
       lookup('hashicorp.terraform.tf_policy_checks', run_id=run_id, only_failures=true)
       | selectattr('status', 'equalto', 'hard_failed') | list | length > 0

For an apply that is gated on policy automatically, prefer
:ansplugin:`hashicorp.terraform.promote_run#module` — see
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs`.

.. _ansible_collections.hashicorp.terraform.docsite.guide_lookups.tf_run_events:

``tf_run_events`` — read a run timeline
=======================================

:ansplugin:`hashicorp.terraform.tf_run_events#lookup` returns the timeline of events for a run,
optionally filtered by ``action`` and a ``since`` / ``until`` time window:

.. code-block:: yaml

   - name: Get applied events since a timestamp
     ansible.builtin.set_fact:
       applied_events: "{{ lookup('hashicorp.terraform.tf_run_events',
                                  run_id='run-abc123', action='applied',
                                  since='2026-01-01T00:00:00Z') }}"

.. note::

   Lookups run on the controller during templating. Provide credentials with ``TFE_TOKEN`` (or the
   ``tfe_token`` argument). See
   :ref:`ansible_collections.hashicorp.terraform.docsite.guide_authentication`.
