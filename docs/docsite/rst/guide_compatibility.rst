.. _ansible_collections.hashicorp.terraform.docsite.guide_compatibility:

***************************
Compatibility and support
***************************

This guide summarizes the supported versions, the platforms the collection talks to, and where to
get help.

.. contents::
   :local:
   :depth: 1

.. _ansible_collections.hashicorp.terraform.docsite.guide_compatibility.versions:

Supported versions
==================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Component
     - Requirement
   * - ``ansible-core``
     - ``>= 2.16.0``
   * - Python
     - ``>= 3.10`` (in the interpreter that runs the tasks)
   * - ``pytfe``
     - ``>= 1.2.0``

Individual plugins may add their own ``version_added`` metadata; check a plugin's documentation
with ``ansible-doc`` for option-level details.

.. _ansible_collections.hashicorp.terraform.docsite.guide_compatibility.platforms:

Supported platforms
===================

The collection works against both:

- **HCP Terraform** (formerly Terraform Cloud) at ``https://app.terraform.io`` — the default
  endpoint.
- **Terraform Enterprise** (self-hosted) — set ``tfe_address`` / ``TFE_ADDRESS`` to your instance
  URL. See :ref:`ansible_collections.hashicorp.terraform.docsite.guide_authentication`.

It uses the public Terraform API through the ``pytfe`` SDK, so it does not require the Terraform CLI
or direct access to a state backend.

.. _ansible_collections.hashicorp.terraform.docsite.guide_compatibility.pytfe:

About the ``pytfe`` requirement
===============================

Every module, lookup, and the inventory plugin depend on ``pytfe``. Newer collection features rely
on SDK surfaces added in ``pytfe`` 1.2.0, so older SDK versions are not supported even if a subset
of modules happens to import. Always install ``pytfe>=1.2.0`` into the interpreter Ansible uses, and
pin it in execution environments — see
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_execution_environments`.

.. _ansible_collections.hashicorp.terraform.docsite.guide_compatibility.support:

Getting support
===============

As Red Hat Ansible Certified Content, this collection is eligible for support through the
`Ansible Automation Platform <https://www.redhat.com/en/technologies/management/ansible>`__. If a
support case cannot be opened with Red Hat and you obtained the collection from Galaxy or GitHub,
community help is available on the `Ansible Forum <https://forum.ansible.com/c/help/6>`__.

Report bugs and request features on the
`project issue tracker <https://github.com/hashicorp/terraform-ansible-collection/issues>`__.

.. _ansible_collections.hashicorp.terraform.docsite.guide_compatibility.changelog:

Release notes
=============

See the project
`changelog <https://github.com/hashicorp/terraform-ansible-collection/blob/main/CHANGELOG.rst>`__
for the per-release list of changes.
