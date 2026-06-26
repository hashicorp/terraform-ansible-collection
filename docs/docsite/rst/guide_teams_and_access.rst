.. _ansible_collections.hashicorp.terraform.docsite.guide_teams_and_access:

****************
Teams and access
****************

This guide covers managing teams and their access grants to projects and workspaces, plus reading
team and user information.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_teams_and_access.teams:

Managing teams
==============

:ansplugin:`hashicorp.terraform.team#module` creates and updates teams, including visibility,
organization-level access, and SSO mapping. It is idempotent by team name within an organization,
and can also update a team by ID.

.. code-block:: yaml

   - name: Create or update a team
     hashicorp.terraform.team:
       organization: my-org
       name: platform-team
       visibility: organization
       allow_member_token_management: true
       organization_access:
         manage_workspaces: true
         read_projects: true
       state: present

   - name: Create a secret team mapped to SSO
     hashicorp.terraform.team:
       organization: my-org
       name: admin-team
       visibility: secret
       sso_team_id: team-123-sso
       organization_access:
         manage_teams: true
         manage_policies: true
       state: present

To update an existing team by ID (for example to rename it), pass
:ansopt:`hashicorp.terraform.team#module:team_id`:

.. code-block:: yaml

   - name: Rename a team by ID
     hashicorp.terraform.team:
       team_id: team-abc123xyz
       name: platform-team-renamed

.. _ansible_collections.hashicorp.terraform.docsite.guide_teams_and_access.team_info:

Looking up teams
================

:ansplugin:`hashicorp.terraform.team_info#module` reads a team by ID, by organization plus name, or
lists every team in an organization:

.. code-block:: yaml

   - name: Get a team by name
     hashicorp.terraform.team_info:
       organization: my-org
       name: platform-team
     register: team

   - name: List all teams in an organization
     hashicorp.terraform.team_info:
       organization: my-org
     register: all_teams

.. _ansible_collections.hashicorp.terraform.docsite.guide_teams_and_access.project_access:

Project access
==============

:ansplugin:`hashicorp.terraform.team_project_access#module` grants a team access to a project. Use a
named access level (``read``, ``write``, ``maintain``, ``admin``) or ``custom`` for fine-grained
control:

.. code-block:: yaml

   - name: Grant read access to a project
     hashicorp.terraform.team_project_access:
       team_id: team-abc123
       project_id: prj-xyz789
       access: read
       state: present

   - name: Fine-grained custom access
     hashicorp.terraform.team_project_access:
       team_id: team-abc123
       project_id: prj-xyz789
       access: custom
       project_settings: read
       project_teams: none
       workspace_runs: apply
       workspace_variables: write
       workspace_state_versions: read-outputs
       state: present

.. _ansible_collections.hashicorp.terraform.docsite.guide_teams_and_access.workspace_access:

Workspace access
================

:ansplugin:`hashicorp.terraform.team_workspace_access#module` grants a team access to a single
workspace, with the same named/custom access model:

.. code-block:: yaml

   - name: Grant a team write access to a workspace
     hashicorp.terraform.team_workspace_access:
       team_id: team-abc123
       workspace_id: ws-xyz789
       access: write
       state: present

.. note::

   For ``state: present`` you must provide the ``team_id`` together with the ``project_id`` or
   ``workspace_id`` so the module can create the grant if it does not already exist. Identifying a
   grant only by its access-grant ID is supported for ``state: absent``.

.. _ansible_collections.hashicorp.terraform.docsite.guide_teams_and_access.user_info:

Reading user information
========================

:ansplugin:`hashicorp.terraform.user_info#module` returns a user by ID, or the currently
authenticated user:

.. code-block:: yaml

   - name: Get a user by ID
     hashicorp.terraform.user_info:
       user_id: user-XXXXXXXXXXXX
     register: u

   - name: Get the current authenticated user
     hashicorp.terraform.user_info:
       current: true
     register: me

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects` — the
     projects and workspaces these grants apply to.
