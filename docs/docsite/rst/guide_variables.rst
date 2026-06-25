.. _ansible_collections.hashicorp.terraform.docsite.guide_variables:

******************************
Variables and variable sets
******************************

This guide covers managing Terraform input and environment variables — both **workspace** variables
and **variable-set** variables — with :ansplugin:`hashicorp.terraform.variable#module`, and
managing variable sets themselves with :ansplugin:`hashicorp.terraform.variable_sets#module`.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_variables.scope:

Choosing a scope (required)
===========================

A single module, :ansplugin:`hashicorp.terraform.variable#module`, manages variables in either
scope — mirroring the Terraform ``tfe_variable`` provider resource, which distinguishes a workspace
variable from a variable-set variable by which parent ID you set. **Exactly one parent scope is
required** (the options are mutually exclusive):

- :ansopt:`hashicorp.terraform.variable#module:workspace_id` — a workspace variable, by workspace ID; **or**
- :ansopt:`hashicorp.terraform.variable#module:workspace` plus
  :ansopt:`hashicorp.terraform.variable#module:organization` — a workspace variable, by name; **or**
- :ansopt:`hashicorp.terraform.variable#module:variable_set_id` — a variable-set variable.

A scope is required even when you target an existing variable by
:ansopt:`hashicorp.terraform.variable#module:variable_id`, because the API is scoped to the parent.

.. _ansible_collections.hashicorp.terraform.docsite.guide_variables.workspace_vars:

Workspace variables
===================

Set :ansopt:`hashicorp.terraform.variable#module:category` to ``terraform`` for input variables or
``env`` for environment variables. The module is idempotent — an identical re-run is
``changed: false``.

.. code-block:: yaml

   - name: Create a Terraform input variable
     hashicorp.terraform.variable:
       organization: my-org
       workspace: my-workspace
       key: region
       value: us-east-1
       category: terraform
       description: Default application region
       state: present

   - name: Set an environment variable
     hashicorp.terraform.variable:
       organization: my-org
       workspace: my-workspace
       key: APP_API_ENDPOINT
       value: https://api.example.com
       category: env
       state: present

.. _ansible_collections.hashicorp.terraform.docsite.guide_variables.varset_vars:

Variable-set variables
======================

Set :ansopt:`hashicorp.terraform.variable#module:variable_set_id` to manage a variable inside a
variable set instead of a workspace:

.. code-block:: yaml

   - name: Create a Terraform input variable in a variable set
     hashicorp.terraform.variable:
       variable_set_id: varset-7tRVyqGbvrF1RmWQ
       key: region
       value: us-east-1
       category: terraform
       state: present

.. note::

   In earlier development of this collection there was a separate ``variable_set_variable`` module.
   It has been merged into :ansplugin:`hashicorp.terraform.variable#module` (via
   :ansopt:`hashicorp.terraform.variable#module:variable_set_id`) before the 2.1.0 release, matching
   the Terraform provider's single-``tfe_variable``-resource design.

.. _ansible_collections.hashicorp.terraform.docsite.guide_variables.sensitive:

Sensitive values
================

Mark secrets with :ansopt:`hashicorp.terraform.variable#module:sensitive`. The API is write-only for
sensitive values — it never returns them — so the module **cannot detect a change to the value
alone**. Updating only a sensitive value reports ``changed: false``. To rotate a sensitive value,
change another tracked attribute as well, or delete and recreate the variable.

.. code-block:: yaml

   - name: Create a sensitive environment variable (write-only)
     hashicorp.terraform.variable:
       organization: my-org
       workspace: my-workspace
       key: APP_API_TOKEN
       value: "{{ app_api_token }}"
       category: env
       sensitive: true
       state: present

.. _ansible_collections.hashicorp.terraform.docsite.guide_variables.delete:

Deleting variables
==================

Delete by ID (precise) or by ``(scope, key)``:

.. code-block:: yaml

   - name: Delete by ID
     hashicorp.terraform.variable:
       workspace_id: ws-abc123
       variable_id: var-xyz789
       state: absent

   - name: Delete by key within a scope
     hashicorp.terraform.variable:
       organization: my-org
       workspace: my-workspace
       key: region
       category: terraform   # disambiguates when the same key exists in env and terraform
       state: absent

.. _ansible_collections.hashicorp.terraform.docsite.guide_variables.variable_sets:

Managing variable sets
======================

:ansplugin:`hashicorp.terraform.variable_sets#module` creates and updates variable sets and attaches
them to workspaces. A *global* set applies to every workspace; a *priority* set overrides
workspace-level variables.

.. code-block:: yaml

   - name: Create a variable set and attach it to workspaces
     hashicorp.terraform.variable_sets:
       organization: my-org
       name: shared-platform-defaults
       description: Shared platform defaults for application workspaces
       global: false
       priority: false
       workspace_ids:
         - ws-abc123
         - ws-def456
       state: present

A variable set can also inherit its parent organization by name via
:ansopt:`hashicorp.terraform.variable_sets#module:parent_organization_name`.

.. _ansible_collections.hashicorp.terraform.docsite.guide_variables.reading:

Reading variable-set values
===========================

To read the variables in a set (for example, to reuse platform defaults in a play), use the
:ansplugin:`hashicorp.terraform.tf_variable_set_vars#lookup` lookup:

.. code-block:: yaml

   - ansible.builtin.set_fact:
       platform_vars: "{{ lookup('hashicorp.terraform.tf_variable_set_vars',
                                 name='shared-platform-defaults', organization='my-org') }}"

See :ref:`ansible_collections.hashicorp.terraform.docsite.guide_lookups`.
