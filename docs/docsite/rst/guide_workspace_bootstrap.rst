.. _ansible_collections.hashicorp.terraform.docsite.guide_workspace_bootstrap:

*******************
Workspace bootstrap
*******************

:ansplugin:`hashicorp.terraform.workspace_bootstrap#module` is a convenience module that creates or
updates a workspace **and** its variables, variable-set attachments, run triggers, and notification
configurations in a single, idempotent task. It is ideal for a baseline "new workspace" workflow
where you would otherwise chain several modules together.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_workspace_bootstrap.example:

A complete bootstrap
====================

.. code-block:: yaml

   - name: Bootstrap a workspace
     hashicorp.terraform.workspace_bootstrap:
       organization: my-org
       workspace: app-prod
       settings:
         execution_mode: remote
         terraform_version: "1.9.5"
         auto_apply: false
       variables:
         - key: APP_REGION
           value: us-east-1
           category: env
         - key: replicas
           value: "3"
           category: terraform
       variable_sets:
         - name: shared-platform-defaults
       run_triggers:
         - ws-upstream-dep
       notifications:
         - name: ops-webhook
           destination_type: generic
           url: https://hooks.example.com/tfc
           triggers:
             - "run:errored"
             - "run:needs_attention"
     register: bootstrap

.. _ansible_collections.hashicorp.terraform.docsite.guide_workspace_bootstrap.sections:

What each section does
======================

- :ansopt:`hashicorp.terraform.workspace_bootstrap#module:settings` — the workspace attributes
  (execution mode, Terraform version, auto-apply, …), equivalent to
  :ansplugin:`hashicorp.terraform.workspace#module`.
- :ansopt:`hashicorp.terraform.workspace_bootstrap#module:variables` — workspace variables, each
  with ``key``, ``value``, and ``category`` (``env`` or ``terraform``), equivalent to
  :ansplugin:`hashicorp.terraform.variable#module`.
- :ansopt:`hashicorp.terraform.workspace_bootstrap#module:variable_sets` — variable sets to attach
  by name.
- :ansopt:`hashicorp.terraform.workspace_bootstrap#module:run_triggers` — source workspaces whose
  applies should queue a run here, equivalent to
  :ansplugin:`hashicorp.terraform.run_trigger#module`.
- :ansopt:`hashicorp.terraform.workspace_bootstrap#module:notifications` — notification
  configurations, equivalent to
  :ansplugin:`hashicorp.terraform.notification_configuration#module`.

.. _ansible_collections.hashicorp.terraform.docsite.guide_workspace_bootstrap.when:

When to use it (and when not)
=============================

Use ``workspace_bootstrap`` to stand up a workspace's baseline configuration declaratively in one
place. For ongoing, granular lifecycle management — rotating a single variable, changing one access
grant, driving runs — prefer the dedicated modules so changes stay small and auditable.

The module is idempotent: re-running with the same definition reports ``changed: false``. Sensitive
variable values follow the same write-only caveat described in
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_variables.sensitive`.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_variables`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs`
