.. _ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects:

************************
Workspaces and projects
************************

Workspaces and projects are the core organizational units of HCP Terraform / Terraform
Enterprise. This guide shows how to create, update, inspect, and safely delete them, and how to
apply tags.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects.workspaces:

Managing workspaces
====================

Use :ansplugin:`hashicorp.terraform.workspace#module` to create and update workspaces. The module
is idempotent: re-running with identical settings reports ``changed: false``.

.. code-block:: yaml

   - name: Create or update a workspace
     hashicorp.terraform.workspace:
       organization: my-org
       workspace: app-prod
       description: Managed by Ansible
       execution_mode: remote
       auto_apply: true
       terraform_version: "1.12.2"
       tag_bindings:
         env: prod
         owner: platform-team
       state: present
     register: ws

Lock a workspace during maintenance with the ``locked`` state, and unlock it by returning it to
``present``:

.. code-block:: yaml

   - name: Lock during maintenance
     hashicorp.terraform.workspace:
       workspace_id: "{{ ws.id }}"
       lock_reason: Maintenance in progress
       state: locked

.. _ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects.safe_delete:

Deleting workspaces safely
--------------------------

Delete by ID when you can, so you never accidentally match the wrong workspace by name:

.. code-block:: yaml

   - name: Delete a workspace
     hashicorp.terraform.workspace:
       workspace_id: "{{ ws.id }}"
       state: absent

.. note::

   ``state: absent`` deletes the workspace and its state. Guard destructive tasks with
   ``--check`` / ``--diff`` and CI approvals. To inspect before deleting, use
   :ansplugin:`hashicorp.terraform.workspace_info#module`.

.. _ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects.workspace_info:

Inspecting workspaces
---------------------

:ansplugin:`hashicorp.terraform.workspace_info#module` returns a single workspace by name or ID:

.. code-block:: yaml

   - name: Look up a workspace
     hashicorp.terraform.workspace_info:
       organization: my-org
       workspace: app-prod
     register: info

   - ansible.builtin.debug:
       msg: "{{ info.workspace.id }} ({{ info.workspace.execution_mode }})"

.. _ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects.projects:

Managing projects
=================

:ansplugin:`hashicorp.terraform.project#module` manages projects, which group related workspaces
and carry default settings:

.. code-block:: yaml

   - name: Create or update a project
     hashicorp.terraform.project:
       organization: my-org
       project: platform
       description: Platform infrastructure project
       default_execution_mode: remote
       auto_destroy_activity_duration: "14d"
       tag_bindings:
         - key: env
           value: production
       state: present
     register: project

   - name: Delete the project by ID
     hashicorp.terraform.project:
       project_id: "{{ project.id }}"
       state: absent

Use :ansplugin:`hashicorp.terraform.project_info#module` to list or look up projects.

.. _ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects.tags:

Tagging
=======

There are two complementary tagging mechanisms:

- **Tag bindings** set directly on a workspace or project via ``tag_bindings`` (shown above) are
  the recommended way to attach key/value tags as you create resources.
- :ansplugin:`hashicorp.terraform.organization_tags#module` associates existing organization tags
  (by tag ID) with multiple workspaces at once, and deletes tags by ID:

.. code-block:: yaml

   - name: Associate workspaces with an existing tag
     hashicorp.terraform.organization_tags:
       organization: my-org
       tag_id: tag-7tRVyqGbvrF1RmWQ
       workspace_ids:
         - ws-abc123
         - ws-def456
       state: present

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs` — drive runs in a workspace.
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_workspace_bootstrap` — create a
     workspace with variables, triggers, and notifications in one task.
