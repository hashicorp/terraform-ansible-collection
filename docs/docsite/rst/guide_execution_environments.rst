.. _ansible_collections.hashicorp.terraform.docsite.guide_execution_environments:

**********************
Execution environments
**********************

To use this collection in Ansible Automation Platform (Automation Controller / AWX) or with
``ansible-navigator``, package it in an `execution environment
<https://docs.ansible.com/ansible/latest/getting_started_ee/index.html>`__ (EE) — a container image
that bundles ``ansible-core``, the collection, and its Python dependencies. This guide shows how to
build one with ``ansible-builder``, how to pull from a private Automation Hub, how to supply
credentials at run time, and how to use the image in Automation Controller.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_execution_environments.when:

When you need a custom EE
=========================

- Running ad-hoc on a control node with the ``ansible`` / ``ansible-playbook`` CLI does **not**
  require an EE — just install the collection and ``pytfe`` into your Python environment (see
  :ref:`ansible_collections.hashicorp.terraform.docsite.guide_getting_started`).
- Running in **Automation Controller, AWX, or ``ansible-navigator``** *does* require an EE, because
  those runtimes execute playbooks inside a container image rather than your local environment.

.. _ansible_collections.hashicorp.terraform.docsite.guide_execution_environments.auto_deps:

Automatic dependency installation
=================================

This collection declares its single controller-side Python dependency, ``pytfe>=1.2.0``, in
``meta/execution-environment.yml`` (which points at the collection's ``requirements.txt``). When you
include the collection in an EE, **Ansible Builder installs** ``pytfe`` **automatically** — you do
not have to list it yourself. You can confirm this for any collection with:

.. code-block:: bash

   ansible-builder introspect ~/.ansible/collections
   # python:
   # - 'pytfe>=1.2.0  # from collection hashicorp.terraform'

``pytfe`` is a pure-Python package and needs no system (C) libraries, so a ``bindep.txt`` is not
required for this collection.

.. _ansible_collections.hashicorp.terraform.docsite.guide_execution_environments.build:

Building an execution environment
=================================

Create an ``ansible-builder`` v3 definition. Use a certified ``ee-minimal`` base image matching your
Automation Platform version (the example below targets AAP 2.6; adjust the tag to your environment —
``registry.redhat.io`` images require authentication with ``podman login``):

``execution-environment.yml``:

.. code-block:: yaml

   ---
   version: 3
   images:
     base_image:
       name: registry.redhat.io/ansible-automation-platform-26/ee-minimal-rhel9:latest
   dependencies:
     galaxy: requirements.yml
     # python: requirements.txt   # optional — see note below
   options:
     package_manager_path: /usr/bin/microdnf

``requirements.yml`` (pin the released collection version):

.. code-block:: yaml

   ---
   collections:
     - name: hashicorp.terraform
       version: "2.1.0"

A ``requirements.txt`` is **optional**: ``pytfe`` is already pulled in via the collection's
metadata (see above). Add one only to pin a stricter ``pytfe`` version or to declare *extra* Python
packages your own roles need:

.. code-block:: text

   pytfe>=1.2.0

Build the image:

.. code-block:: bash

   ansible-builder build \
     --tag hashicorp-terraform-ee:2.1.0 \
     --container-runtime podman

.. _ansible_collections.hashicorp.terraform.docsite.guide_execution_environments.private_hub:

Pulling from a private Automation Hub
=====================================

To install the collection from Red Hat Automation Hub (or a private Automation Hub) instead of
public Galaxy, add an ``ansible.cfg`` to the build context and reference it from the definition:

``ansible.cfg``:

.. code-block:: ini

   [galaxy]
   server_list = automation_hub

   [galaxy_server.automation_hub]
   url = https://console.redhat.com/api/automation-hub/content/published/
   auth_url = https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token
   token = <offline-token>

Add it to the EE definition so it is present during the Galaxy install phase:

.. code-block:: yaml

   ---
   version: 3
   images:
     base_image:
       name: registry.redhat.io/ansible-automation-platform-26/ee-minimal-rhel9:latest
   dependencies:
     galaxy: requirements.yml
   options:
     package_manager_path: /usr/bin/microdnf
   additional_build_files:
     - src: ansible.cfg
       dest: configs
   additional_build_steps:
     prepend_galaxy:
       - COPY _build/configs/ansible.cfg /etc/ansible/ansible.cfg

.. warning::

   Do **not** commit a real Automation Hub token. Keep ``ansible.cfg`` out of source control (or
   template the token in at build time), and obtain an offline token from
   `Connect to Hub <https://console.redhat.com/ansible/automation-hub/token>`__. If your Hub uses a
   private CA, add the CA to the build and configure ``ansible-galaxy`` to trust it rather than using
   ``--ignore-certs``.

.. _ansible_collections.hashicorp.terraform.docsite.guide_execution_environments.verify:

Verifying the image
===================

Confirm the collection and SDK are present inside the built image:

.. code-block:: bash

   podman run --rm hashicorp-terraform-ee:2.1.0 ansible-doc hashicorp.terraform.workspace | head
   podman run --rm hashicorp-terraform-ee:2.1.0 python -c "import pytfe; print(pytfe.__version__)"

.. _ansible_collections.hashicorp.terraform.docsite.guide_execution_environments.credentials:

Supplying the token at run time
===============================

Do **not** bake the API token into the image. Provide it at run time:

- In **Automation Controller / AWX**, create a credential that injects the ``TFE_TOKEN`` environment
  variable (a custom credential type works well) and attach it to the job template. The collection
  reads ``TFE_TOKEN`` automatically.
- For a self-hosted Terraform Enterprise endpoint, also inject ``TFE_ADDRESS`` (or set
  :ansopt:`hashicorp.terraform.workspace#module:tfe_address` via ``module_defaults``).
- For private CAs or proxies, inject ``SSL_CERT_FILE`` (consumed by
  :ansopt:`hashicorp.terraform.workspace#module:tfe_ca_bundle`) or set
  :ansopt:`hashicorp.terraform.workspace#module:tfe_proxies`.

See :ref:`ansible_collections.hashicorp.terraform.docsite.guide_authentication` for all
authentication and connection options.

.. _ansible_collections.hashicorp.terraform.docsite.guide_execution_environments.controller:

Using the image in Automation Controller
========================================

#. Push the built image to a registry your Controller can reach:

   .. code-block:: bash

      podman tag hashicorp-terraform-ee:2.1.0 registry.example.com/ee/hashicorp-terraform-ee:2.1.0
      podman push registry.example.com/ee/hashicorp-terraform-ee:2.1.0

#. In Controller, create an **Execution Environment** pointing at that image (and a registry
   credential if the registry is private).
#. Attach the EE to a **Job Template**, along with a credential that supplies ``TFE_TOKEN``.
#. Run the job; the playbook executes inside the EE with the collection and ``pytfe`` available.

.. _ansible_collections.hashicorp.terraform.docsite.guide_execution_environments.dev_branch:

Building from an unreleased branch (development only)
=====================================================

.. note::

   The pattern below is for testing an **unreleased** branch and should not be used for production
   images. Production EEs should pin a released collection version from Galaxy or Automation Hub as
   shown above.

To test changes from a Git branch before release, point ``requirements.yml`` at the branch:

.. code-block:: yaml

   ---
   collections:
     - name: https://github.com/hashicorp/terraform-ansible-collection.git
       type: git
       version: next-2.1.0

When building from a branch whose ``meta/execution-environment.yml`` is not yet published, list the
Python dependency explicitly in ``requirements.txt`` (``pytfe>=1.2.0``) so it is installed.

.. _ansible_collections.hashicorp.terraform.docsite.guide_execution_environments.troubleshooting:

Troubleshooting
===============

- **"Failed to import the required Python library (pytfe)"** inside the EE — the image was built
  without ``pytfe``. Confirm the collection is in ``requirements.yml`` (so the metadata pulls
  ``pytfe`` in) or add ``pytfe>=1.2.0`` to ``requirements.txt``, then rebuild.
- **Wrong Python version** — use a current ``ee-minimal`` base image; the collection needs Python
  ``>= 3.10``.
- **Galaxy/Hub install failures** — verify the ``ansible.cfg`` server URL, token validity, and CA
  trust. See the private Hub section above.
- **No ``TFE_TOKEN`` at run time** — attach a credential that injects it to the job template.

For general runtime issues see
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting`.
