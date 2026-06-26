.. _ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting:

***************
Troubleshooting
***************

This guide covers the most common problems when using the ``hashicorp.terraform`` collection and
how to resolve them.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting.pytfe:

Missing ``pytfe`` library
=========================

The collection needs the ``pytfe`` SDK (``>= 1.2.0``) in the **same Python interpreter** that runs
the task. Because modules run on the play's host, that interpreter is usually the one on
``localhost``, not necessarily the one that launched ``ansible-playbook``.

.. code-block:: bash

   # confirm which interpreter Ansible uses, then install into it
   ansible localhost -m ansible.builtin.setup -a 'filter=ansible_python_version'
   python -m pip install 'pytfe>=1.2.0'

In an execution environment, add ``pytfe>=1.2.0`` to the EE's Python requirements — see
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_execution_environments`.

.. _ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting.auth:

Authentication failures
========================

- **"No token provided" / token errors** — set ``TFE_TOKEN`` or pass ``tfe_token``. See
  :ref:`ansible_collections.hashicorp.terraform.docsite.guide_authentication`.
- **401 Unauthorized** — the token is invalid or expired. Generate a new one in the HCP
  Terraform / TFE UI.
- **404 Not Found on a resource you can see in the UI** — the token often lacks permission for
  that organization, workspace, or operation, which the API reports as a 404. Use a token with
  sufficient scope (user, team, or organization token as appropriate).
- **Remote-host surprises** — when a task runs against a remote host rather than ``localhost``,
  ``TFE_TOKEN`` and files such as ``tfe_ca_bundle`` are read on that host. Copy them there, or run
  with ``connection: local``.

.. _ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting.tls:

TLS and proxy errors (Terraform Enterprise)
===========================================

- **Certificate verify failed** against a Terraform Enterprise instance with a private CA: set
  ``tfe_ca_bundle`` to the CA file (or ``SSL_CERT_FILE``). Avoid ``tfe_verify_tls: false`` outside
  of throwaway test environments.
- **Connection blocked by a corporate proxy**: set ``tfe_proxies`` (for example
  ``http://proxy.internal:3128``).
- **Wrong endpoint**: HCP Terraform is ``https://app.terraform.io`` (the default). For TFE set
  ``tfe_address`` / ``TFE_ADDRESS`` to your instance URL. A token from one will not work against
  the other.

.. _ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting.inventory_empty:

Dynamic inventory returns no hosts
==================================

When ``ansible-inventory --list`` is empty, work through these in order:

#. **Config filename** — the inventory file name must end with ``inventory.yml``,
   ``inventory.yaml``, ``terraform_inventory.yml``, ``terraform_inventory.yaml``,
   ``tfc_inv.yml``, or ``tfc_inv.yaml``. Any other name is declined and yields an empty
   inventory.
#. **Plugin enabled** — add ``hashicorp.terraform.tfc_inv`` to ``enable_plugins`` in the
   ``[inventory]`` section of ``ansible.cfg``, or set
   ``ANSIBLE_INVENTORY_ENABLED=hashicorp.terraform.tfc_inv``.
#. **Source vs data** — with ``source: statefile`` the workspace state must contain resources of a
   recognized provider/type (extend with ``provider_mapping``). With ``source: outputs`` and no
   ``hosts_from``, only an output named ``ansible_host`` is processed.
#. **Sensitive stripping** — fields Terraform marks sensitive are dropped, so a ``hostnames`` or
   ``compose`` reference to a sensitive attribute will not resolve. Use the ``outputs`` source for
   intentionally shaped data.
#. **Run verbosely** — ``ansible-inventory -i demo_inventory.yml --list -vvv`` shows the parse
   path and any warnings.

.. note::

   ``ansible-inventory`` exits ``0`` even when a source fails to parse. In CI, set
   ``ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED=true`` so an empty/failed inventory becomes a hard
   error instead of silently running against zero hosts.

In multi-workspace mode, a single broken workspace only produces a warning; the build continues.
Only when **every** matched workspace fails does the plugin raise. See
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.failure`.

.. _ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting.reserved:

"Found variable using reserved name"
====================================

This warning appears when a Terraform attribute or output field has the same name as an
Ansible-reserved host variable (``name``, ``tags``, ``groups``, ``inventory_hostname``, …). It is
harmless, but you can silence it by namespacing the user fields with ``hostvars_prefix`` (for
example ``tf_``) or ``hostvars_suffix``.

.. _ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting.idempotency:

A task always reports ``changed``
=================================

- **Sensitive variable values** cannot be read back from the API, so a module cannot tell whether
  a sensitive value changed. Manage sensitive values deliberately; see
  :ref:`ansible_collections.hashicorp.terraform.docsite.guide_variables`.
- **Server-normalized fields** — if you pass a value the API stores in a normalized form, the
  before/after comparison may differ. Use ``--diff`` to see exactly which keys the module
  considers changed.

.. _ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting.poll:

Runs time out while polling
===========================

:ansplugin:`hashicorp.terraform.run#module` and
:ansplugin:`hashicorp.terraform.configuration_version#module` poll for completion when asked to.
If a run needs longer (large plans, slow providers, manual apply approval), increase
``poll_timeout`` and ``poll_interval``, or set ``poll: false`` and check status later with
:ansplugin:`hashicorp.terraform.run_info#module`.

.. _ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting.debug:

Getting more detail
===================

- Add ``-vvv`` to ``ansible-playbook`` or ``ansible-inventory`` for verbose output.
- Read a module's own documentation and return values with ``ansible-doc``, for example
  ``ansible-doc hashicorp.terraform.run``.
- Use ``--diff`` to see what a module would change.
- For support options, see
  :ref:`ansible_collections.hashicorp.terraform.docsite.guide_compatibility`.
