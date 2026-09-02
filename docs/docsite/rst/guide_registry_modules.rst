.. _ansible_collections.hashicorp.terraform.docsite.guide_registry_modules:

***************************
Private registry modules
***************************

The HCP Terraform / Terraform Enterprise private registry lets your organization publish and
share reusable Terraform modules internally.
:ansplugin:`hashicorp.terraform.registry_module#module` manages these modules declaratively;
use :ansplugin:`hashicorp.terraform.registry_module_info#module` to read them.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_registry_modules.intent:

Declarative intent model
========================

The ``registry_module`` module infers the intended operation from the fields you supply:

- Supply ``version`` → ensure that specific version exists (publish it if missing).
- Supply ``vcs_repo`` → ensure a VCS-connected module exists.
- Supply neither → ensure a plain no-VCS module exists and reconcile ``no_code`` drift.

You never need to set an ``operation`` parameter — the module decides what to do based on what
you provide.

.. _ansible_collections.hashicorp.terraform.docsite.guide_registry_modules.no_vcs:

Creating a no-VCS module
========================

A no-VCS module is created with ``organization``, ``name``, and ``provider``. Versions are
published separately (see below):

.. code-block:: yaml

   - name: Create a private registry module without VCS
     hashicorp.terraform.registry_module:
       organization: my-org
       name: vpc
       provider: aws
       state: present
     register: module_result

   - ansible.builtin.debug:
       msg: "Module {{ module_result.name }}/{{ module_result.provider }} created with id {{ module_result.id }}"

Re-running with the same parameters reports ``changed: false``:

.. code-block:: yaml

   - name: Idempotent re-run
     hashicorp.terraform.registry_module:
       organization: my-org
       name: vpc
       provider: aws
       state: present
   # "changed": false

Enable no-code provisioning by setting ``no_code: true``:

.. code-block:: yaml

   - name: Enable no-code on an existing module
     hashicorp.terraform.registry_module:
       organization: my-org
       name: vpc
       provider: aws
       no_code: true
       state: present

.. _ansible_collections.hashicorp.terraform.docsite.guide_registry_modules.versions:

Publishing module versions
==========================

Publish a new version by supplying ``version`` in semantic-version format. When the version does
not exist yet the module creates it; when it already exists the task is a no-op:

.. code-block:: yaml

   - name: Publish version 1.0.0
     hashicorp.terraform.registry_module:
       organization: my-org
       name: vpc
       provider: aws
       version: "1.0.0"
       state: present
     register: version_result

Upload a ``tar.gz`` archive at the same time with ``archive``:

.. code-block:: yaml

   - name: Publish version 1.0.1 and upload the module archive
     hashicorp.terraform.registry_module:
       organization: my-org
       name: vpc
       provider: aws
       version: "1.0.1"
       archive: /path/to/module.tar.gz
       state: present
     register: upload_result

.. note::

   If the version already exists the archive upload is skipped and ``changed`` is ``false``.
   Archive uploads are not idempotent — a new upload URL is generated per version.

Read the status of a specific version:

.. code-block:: yaml

   - name: Read a specific module version
     hashicorp.terraform.registry_module_info:
       organization: my-org
       name: vpc
       provider: aws
       version: "1.0.0"
     register: version_info

   - ansible.builtin.debug:
       msg: "Version {{ version_info.registry_module_version.version }} status: {{ version_info.registry_module_version.status }}"

.. _ansible_collections.hashicorp.terraform.docsite.guide_registry_modules.vcs:

Creating a VCS-connected module
================================

A VCS-connected module is linked to a source repository. Version tags in the repository
automatically publish new versions:

.. code-block:: yaml

   - name: Create a VCS-connected registry module
     hashicorp.terraform.registry_module:
       organization: my-org
       name: vpc
       provider: aws
       vcs_repo:
         identifier: my-org/terraform-aws-vpc
         oauth_token_id: ot-abc123
         display_identifier: my-org/terraform-aws-vpc
       state: present
     register: vcs_module

If ``name`` and ``provider`` are not supplied, the module derives them from the repository name
(``terraform-<provider>-<name>`` convention). Supplying them explicitly enables an idempotency
pre-check so re-running returns ``changed: false`` when the module already exists.

Read an existing module's metadata:

.. code-block:: yaml

   - name: Read registry module metadata
     hashicorp.terraform.registry_module_info:
       organization: my-org
       name: vpc
       provider: aws
     register: module_info

   - ansible.builtin.debug:
       msg: "Module {{ module_info.registry_module.name }} status: {{ module_info.registry_module.status }}"

.. _ansible_collections.hashicorp.terraform.docsite.guide_registry_modules.delete:

Deleting a module, provider, or version
========================================

Use ``delete_scope`` to control the granularity of deletion. ``state: absent`` requires
``delete_scope`` and ``organization``; ``name`` and ``provider`` are required for all scopes:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - ``delete_scope``
     - Effect
   * - ``version``
     - Delete one specific version (requires ``version``, ``name``, ``provider``).
   * - ``provider``
     - Delete a specific provider and all its versions (requires ``name``, ``provider``).
   * - ``module``
     - Delete the entire module across all providers (requires ``name``, ``provider``).

All three scopes are idempotent: if the target is already absent the task reports
``changed: false``.

.. code-block:: yaml

   - name: Delete version 1.0.0 only
     hashicorp.terraform.registry_module:
       organization: my-org
       name: vpc
       provider: aws
       version: "1.0.0"
       delete_scope: version
       state: absent

   - name: Delete the aws provider and all its versions
     hashicorp.terraform.registry_module:
       organization: my-org
       name: vpc
       provider: aws
       delete_scope: provider
       state: absent

   - name: Delete the entire vpc module (all providers)
     hashicorp.terraform.registry_module:
       organization: my-org
       name: vpc
       provider: aws
       delete_scope: module
       state: absent

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_workspaces_projects` — workspaces
     and projects that consume registry modules.
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_runs` — drive runs that use
     modules from the private registry.
