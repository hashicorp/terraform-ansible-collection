.. _ansible_collections.hashicorp.terraform.docsite.guide_getting_started:

***************
Getting started
***************

The ``hashicorp.terraform`` collection lets you manage `HCP Terraform <https://app.terraform.io>`__
(formerly Terraform Cloud) and `Terraform Enterprise <https://developer.hashicorp.com/terraform/enterprise>`__
from Ansible. You can create and update workspaces and projects, upload configuration
versions, queue and apply runs, read state outputs, manage variables and teams, and build
a dynamic inventory directly from Terraform state — all without the Terraform CLI or direct
access to a state backend.

This guide gets you from a fresh control node to your first successful task.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_getting_started.requirements:

Requirements
============

- **Ansible**: ``ansible-core >= 2.16.0``.
- **Python**: 3.10 or later, in the interpreter that runs the tasks (usually on ``localhost``).
- **pytfe**: the `pytfe <https://pypi.org/project/pytfe/>`__ Python SDK, version ``1.2.0`` or
  later. Every module, lookup, and the inventory plugin in this collection talk to the
  Terraform API through ``pytfe``.
- **An API token** for HCP Terraform or Terraform Enterprise. See
  :ref:`ansible_collections.hashicorp.terraform.docsite.guide_authentication`.

.. note::

   The modules run on the Ansible *host* (the target of the play), not the controller. For
   most workflows you target ``localhost`` with ``connection: local``, so ``pytfe`` must be
   installed in the same Python interpreter Ansible uses there. See
   :ref:`ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting` if a task
   reports that ``pytfe`` is missing.

.. _ansible_collections.hashicorp.terraform.docsite.guide_getting_started.install:

Installing the collection
=========================

Install the collection from Ansible Galaxy or Automation Hub:

.. code-block:: bash

   ansible-galaxy collection install hashicorp.terraform

Or pin it in a ``requirements.yml`` and install with
``ansible-galaxy collection install -r requirements.yml``:

.. code-block:: yaml

   ---
   collections:
     - name: hashicorp.terraform

Install the Python dependency into the interpreter Ansible will use:

.. code-block:: bash

   python -m pip install 'pytfe>=1.2.0'

.. _ansible_collections.hashicorp.terraform.docsite.guide_getting_started.first_playbook:

Your first playbook
===================

Export your token so you do not have to put it in the playbook:

.. code-block:: bash

   export TFE_TOKEN="<your-hcp-terraform-or-tfe-token>"

The following play reads information about a workspace and prints it. Because it only reads,
it is safe to run against an existing workspace:

.. code-block:: yaml

   ---
   - name: First HCP Terraform task
     hosts: localhost
     connection: local
     gather_facts: false
     tasks:
       - name: Look up a workspace
         hashicorp.terraform.workspace_info:
           organization: my-org
           workspace: my-workspace
         register: ws

       - name: Show the workspace ID
         ansible.builtin.debug:
           msg: >-
             Workspace {{ ws.workspace.name }}
             has ID {{ ws.workspace.id }}

Run it:

.. code-block:: bash

   ansible-playbook first.yml

The :ansplugin:`hashicorp.terraform.workspace_info#module` module returns a single
:ansretval:`hashicorp.terraform.workspace_info#module:workspace` dictionary with the workspace's
fields flattened at the top level (``id``, ``name``, ``execution_mode``, ``outputs``, and so on).

.. _ansible_collections.hashicorp.terraform.docsite.guide_getting_started.module_defaults:

Avoiding credential repetition with ``module_defaults``
=======================================================

Every module in this collection belongs to the ``hashicorp.terraform.terraform`` action group,
so you can set authentication (and other shared connection options) once for the whole play
using ``module_defaults`` instead of repeating them on every task:

.. code-block:: yaml

   ---
   - name: Manage Terraform with shared credentials
     hosts: localhost
     connection: local
     gather_facts: false
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_token: "{{ terraform_cloud_token }}"
         # tfe_address: https://terraform.example.com   # for Terraform Enterprise
     tasks:
       - name: Create a workspace
         hashicorp.terraform.workspace:
           organization: my-org
           workspace: my-workspace
           state: present

See :ref:`ansible_collections.hashicorp.terraform.docsite.guide_authentication` for all the
ways to provide credentials and connection settings.

.. _ansible_collections.hashicorp.terraform.docsite.guide_getting_started.next:

Where to go next
================

- :ref:`ansible_collections.hashicorp.terraform.docsite.guide_authentication` — tokens, TLS,
  proxies, and self-hosted Terraform Enterprise.
- :ref:`ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects` — create
  and manage workspaces and projects.
- :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs` — upload configuration and
  drive runs.
- :ref:`ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory` — build an
  Ansible inventory from Terraform state.
- The full per-module reference is available with ``ansible-doc``, for example
  ``ansible-doc hashicorp.terraform.workspace``.
