.. _ansible_collections.hashicorp.terraform.docsite.guide_authentication:

**************
Authentication
**************

Every module, lookup, and the inventory plugin in this collection authenticate to HCP Terraform
or Terraform Enterprise with an API token and a small set of shared connection options. This
guide covers how to provide credentials, how to point at a self-hosted Terraform Enterprise
instance, and how to configure TLS, proxies, timeouts, and retries.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_authentication.token:

Providing the API token
=======================

You can authenticate in two ways. They are tried in this order:

#. The ``tfe_token`` parameter on the task (alias: ``tf_token``).
#. The ``TFE_TOKEN`` environment variable.

If neither is set, the task fails with a clear error. Prefer the environment variable or a
vaulted variable so the token never appears in plaintext playbooks or logs. The token is
marked ``no_log``, so it is redacted from Ansible output.

.. code-block:: bash

   export TFE_TOKEN="<your-token>"

.. code-block:: yaml

   - name: Token from a vaulted variable
     hashicorp.terraform.workspace:
       organization: my-org
       workspace: my-workspace
       tfe_token: "{{ vaulted_terraform_token }}"
       state: present

You can generate a user, team, or organization token in the HCP Terraform / TFE UI under
**Settings**. Make sure the token has permission to perform the operations your tasks request.
See the `HCP Terraform API authentication docs
<https://developer.hashicorp.com/terraform/cloud-docs/api-docs#authentication>`__.

.. warning::

   When a task runs against a *remote* host (not ``localhost``), environment variables and
   files such as a CA bundle are read on that host, not on the controller. Copy them to the
   host first, or run the tasks with ``connection: local``.

.. _ansible_collections.hashicorp.terraform.docsite.guide_authentication.module_defaults:

Setting credentials once with ``module_defaults``
=================================================

All modules are part of the ``hashicorp.terraform.terraform`` action group. Use
``module_defaults`` to set the token (and any other shared option) for every task in a play:

.. code-block:: yaml

   ---
   - name: Manage Terraform
     hosts: localhost
     connection: local
     gather_facts: false
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_token: "{{ terraform_cloud_token }}"
     tasks:
       - hashicorp.terraform.workspace:
           organization: my-org
           workspace: app
           state: present
       - hashicorp.terraform.project:
           organization: my-org
           project: platform
           state: present

.. note::

   ``module_defaults`` applies to modules. The :ansplugin:`hashicorp.terraform.tfc_inv#inventory`
   inventory plugin and the ``tf_*`` lookups are configured separately (in the inventory YAML or
   the lookup call), but both honor the same ``TFE_TOKEN`` and ``TFE_ADDRESS`` environment
   variables.

.. _ansible_collections.hashicorp.terraform.docsite.guide_authentication.endpoint:

Targeting Terraform Enterprise (self-hosted)
============================================

By default the collection talks to HCP Terraform at ``https://app.terraform.io``. To target a
self-hosted Terraform Enterprise instance, set ``tfe_address`` (or the ``TFE_ADDRESS``
environment variable):

.. code-block:: yaml

   module_defaults:
     group/hashicorp.terraform.terraform:
       tfe_token: "{{ tfe_token }}"
       tfe_address: https://terraform.example.com

.. _ansible_collections.hashicorp.terraform.docsite.guide_authentication.tls:

TLS, private CAs, proxies, timeouts, and retries
================================================

The shared connection options below are available on every module (they come from the
collection's common documentation fragment). Each one also has an environment-variable
fallback, which is convenient with ``module_defaults`` or execution environments.

.. list-table::
   :header-rows: 1
   :widths: 22 14 14 50

   * - Option
     - Default
     - Env fallback
     - Purpose
   * - ``tfe_token``
     - *(none)*
     - ``TFE_TOKEN``
     - API token (alias ``tf_token``).
   * - ``tfe_address``
     - ``https://app.terraform.io``
     - ``TFE_ADDRESS``
     - Base API URL; set for Terraform Enterprise.
   * - ``tfe_timeout``
     - ``30.0``
     - ``TFE_TIMEOUT``
     - HTTP request timeout in seconds.
   * - ``tfe_verify_tls``
     - ``true``
     - ``TFE_VERIFY_TLS``
     - Verify TLS certificates. Set ``false`` only for self-signed test instances.
   * - ``tfe_max_retries``
     - ``5``
     - ``TFE_MAX_RETRIES``
     - Automatic retries for transient HTTP failures.
   * - ``tfe_ca_bundle``
     - *(none)*
     - ``SSL_CERT_FILE``
     - Path to a CA bundle for private/internal CAs.
   * - ``tfe_proxies``
     - *(none)*
     - *(none)*
     - HTTP/HTTPS proxy URL, for example ``http://proxy.internal:3128``.

A Terraform Enterprise instance behind a private CA and a corporate proxy:

.. code-block:: yaml

   module_defaults:
     group/hashicorp.terraform.terraform:
       tfe_token: "{{ tfe_token }}"
       tfe_address: https://terraform.example.com
       tfe_ca_bundle: /etc/pki/tls/certs/internal-ca.pem
       tfe_proxies: http://proxy.internal:3128
       tfe_timeout: 60.0
       tfe_max_retries: 8

.. warning::

   Disabling TLS verification (``tfe_verify_tls: false``) is not recommended for production.
   Prefer providing the internal CA with ``tfe_ca_bundle`` instead.

.. _ansible_collections.hashicorp.terraform.docsite.guide_authentication.inventory_lookups:

Inventory and lookup authentication
===================================

The inventory plugin reads its token from the ``tfe_token`` option in the inventory file or
from ``TFE_TOKEN``, and its endpoint from ``tfe_address`` / ``TFE_ADDRESS``:

.. code-block:: yaml

   # demo.tfc_inv.yml  (filename must end in inventory.yml/.yaml or terraform_inventory.yml/.yaml)
   plugin: hashicorp.terraform.tfc_inv
   organization: my-org
   workspace: my-workspace
   # tfe_token omitted on purpose — taken from the TFE_TOKEN environment variable

The ``tf_*`` lookups read the token from their ``token`` argument or from ``TFE_TOKEN``:

.. code-block:: yaml

   - ansible.builtin.debug:
       msg: "{{ lookup('hashicorp.terraform.tf_output', name='vpc_id',
                       organization='my-org', workspace='my-workspace') }}"

See :ref:`ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory` and
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_lookups` for details.
