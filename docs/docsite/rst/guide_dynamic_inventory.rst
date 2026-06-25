.. _ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory:

*****************
Dynamic inventory
*****************

The :ansplugin:`hashicorp.terraform.tfc_inv#inventory` plugin builds an Ansible inventory
directly from HCP Terraform / Terraform Enterprise. It talks to the Terraform API through the
``pytfe`` SDK, so it needs **no Terraform CLI and no direct access to a state backend** (S3,
AzureRM, GCS, …) — only an API token and network access to HCP Terraform or your TFE instance.

There are two data sources, selected with the :ansopt:`hashicorp.terraform.tfc_inv#inventory:source`
option:

- ``statefile`` (default) — downloads the latest Terraform **state version** and produces one
  host per matching resource instance (``aws_instance``, ``azurerm_linux_virtual_machine``, …).
- ``outputs`` — reads workspace **output values** and builds hosts from them. Lighter weight and
  fully under your control via the shape of the Terraform output.

.. contents::
   :local:
   :depth: 2

.. _ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.enabling:

Enabling the plugin and naming the config file
==============================================

Enable the plugin in ``ansible.cfg`` (it is not enabled by default because it is a
non-core plugin):

.. code-block:: ini

   [inventory]
   enable_plugins = hashicorp.terraform.tfc_inv, host_list, auto

The inventory configuration is a YAML file whose name **must end with one of**:
``inventory.yml``, ``inventory.yaml``, ``terraform_inventory.yml``, or
``terraform_inventory.yaml``. A file that does not match (for example ``my_hosts.yml``) is
silently declined by the plugin and produces an empty inventory.

.. code-block:: yaml

   # demo.tfc_inv.yml is INVALID — rename to e.g. demo_inventory.yml
   # tfc.inventory.yml, prod_inventory.yaml, terraform_inventory.yml are all VALID
   plugin: hashicorp.terraform.tfc_inv
   organization: my-org
   workspace: my-workspace

Run it with:

.. code-block:: bash

   export TFE_TOKEN="<your-token>"
   ansible-inventory -i demo_inventory.yml --list
   ansible-inventory -i demo_inventory.yml --graph

.. _ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.selecting:

Selecting a workspace
=====================

Point at a single workspace either by organization plus name, or by workspace ID:

.. code-block:: yaml

   # by organization + workspace name
   plugin: hashicorp.terraform.tfc_inv
   organization: my-org
   workspace: my-workspace

.. code-block:: yaml

   # by workspace ID (skips an org lookup; mutually exclusive with organization/workspace)
   plugin: hashicorp.terraform.tfc_inv
   workspace_id: ws-xxxxxxxxxxxxxxxx

To merge several workspaces at once, use
:ansopt:`hashicorp.terraform.tfc_inv#inventory:workspace_filters` (see
:ref:`ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.multi`).

.. _ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.statefile:

The ``statefile`` source
========================

The default source downloads the latest state version and emits a host for every resource
instance whose provider/type is recognized. AWS, AzureRM, and Google resource types are
recognized out of the box.

.. code-block:: yaml

   plugin: hashicorp.terraform.tfc_inv
   source: statefile
   organization: my-org
   workspace: my-workspace
   compose:
     ansible_host: public_ip      # use the instance public IP for SSH

Each host gets the resource instance's attributes as host variables. The default hostname is
``<resource_type>_<resource_name>[_<index>]`` (for example ``aws_instance_web_0``); override it
with :ansopt:`hashicorp.terraform.tfc_inv#inventory:hostnames`.

.. _ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.sensitive:

Sensitive attributes are stripped
---------------------------------

Any attribute that Terraform marks sensitive (via the instance's ``sensitive_attributes``
metadata) is **dropped entirely** — not masked — before host variables are produced. Stripped
fields are unavailable to ``hostnames``, ``compose``, ``groups``, ``keyed_groups``, and filters;
references to them simply do not resolve. This protects provider-flagged secrets from leaking
into inventory output. For intentionally shaped, always-safe inventory data, prefer the
``outputs`` source.

Custom providers and child modules
----------------------------------

Extend the recognized providers with
:ansopt:`hashicorp.terraform.tfc_inv#inventory:provider_mapping`, and include resources defined
in child modules with :ansopt:`hashicorp.terraform.tfc_inv#inventory:search_child_modules`:

.. code-block:: yaml

   plugin: hashicorp.terraform.tfc_inv
   source: statefile
   organization: my-org
   workspace: my-workspace
   search_child_modules: true
   provider_mapping:
     - provider_name: registry.terraform.io/digitalocean/digitalocean
       types:
         - digitalocean_droplet

Hostnames from tags and attributes
----------------------------------

The :ansopt:`hashicorp.terraform.tfc_inv#inventory:hostnames` option is an ordered preference
list. For the ``statefile`` source you can read attributes or tags:

.. code-block:: yaml

   hostnames:
     - tag:Name                # value of the Name tag, e.g. "web-1"
     - public_dns              # fall back to an attribute
     - public_ip               # then to another

   # or build a compound name from two tags:
   hostnames:
     - name: tag:Name
       prefix: tag:Environment
       separator: "-"          # -> "prod-web-1"

.. _ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.outputs:

The ``outputs`` source
======================

The ``outputs`` source builds hosts from workspace output values. With no
:ansopt:`hashicorp.terraform.tfc_inv#inventory:hosts_from`, it processes only the Terraform
output named ``ansible_host``:

.. code-block:: hcl

   # Terraform
   output "ansible_host" {
     value = { web1 = "10.0.0.1", web2 = "10.0.0.2" }
   }

.. code-block:: yaml

   # Ansible — map keys become hostnames, values become ansible_host
   plugin: hashicorp.terraform.tfc_inv
   source: outputs
   organization: my-org
   workspace: my-workspace

To use any other output, declare it with ``hosts_from``. Each entry needs an ``output`` name and
an optional ``type`` (a Terraform type expression; default ``dynamic``):

.. code-block:: yaml

   plugin: hashicorp.terraform.tfc_inv
   source: outputs
   organization: my-org
   workspace: my-workspace
   hosts_from:
     output: web_hosts
     type: list(object)        # see the type table below
   hostnames:
     - name
   compose:
     ansible_host: public_ip

Output shapes (the ``type`` vocabulary)
---------------------------------------

The ``type`` mirrors `Terraform's type system
<https://developer.hashicorp.com/terraform/language/expressions/types>`__. The shape controls
how many hosts are produced and how their variables are laid out:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``type``
     - Result
   * - ``string`` / ``number`` / ``bool``
     - One host; the scalar is stored as ``value``.
   * - ``object`` / ``object({...})``
     - One host; the user dict is **spread flat** at the top level of host vars.
   * - ``list(string|number|bool)``
     - N indexed hosts; each stores the scalar as ``value``.
   * - ``list(object)``
     - N indexed hosts; each user dict spread flat.
   * - ``set(...)``
     - Wire-level synonym for ``list(...)``.
   * - ``map(string|number|bool)``
     - One host per key; the map **key becomes the hostname**; scalar stored as ``value``.
   * - ``map(object)``
     - One host per key; key becomes the hostname; user dict spread flat.
   * - ``dynamic`` (default)
     - Shape inferred from the runtime value.

Two conveniences make the common cases zero-config:

- **Object shapes spread flat**, so you reference fields directly — ``compose: {ansible_host:
  public_ip}``, ``hostnames: [name]`` — with no ``item.<field>`` ceremony.
- When :ansopt:`hashicorp.terraform.tfc_inv#inventory:compose` is empty, **primitive shapes
  auto-set** ``ansible_host`` to the scalar. So a ``list(string)`` of IPs needs no ``compose`` at
  all. Setting any ``compose`` entry suppresses this default.

.. code-block:: hcl

   # Terraform — a plain list of IPs
   output "instance_ips" { value = ["1.2.3.4", "5.6.7.8"] }

.. code-block:: yaml

   # Ansible — each IP auto-becomes ansible_host; no compose needed
   plugin: hashicorp.terraform.tfc_inv
   source: outputs
   organization: my-org
   workspace: my-workspace
   hosts_from:
     output: instance_ips
     type: list(string)

.. note::

   Nested collections (``map(list(...))``, ``list(map(...))``, …) are rejected with a clear
   message. Reshape such values in Terraform with ``flatten()`` or ``for`` expressions — inventory
   is the wrong layer for that transformation.

.. _ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.constructed:

Grouping and composing (shared ``constructed`` features)
========================================================

The plugin supports the standard ``constructed`` options for both sources:
:ansopt:`hashicorp.terraform.tfc_inv#inventory:compose`,
:ansopt:`hashicorp.terraform.tfc_inv#inventory:groups`,
:ansopt:`hashicorp.terraform.tfc_inv#inventory:keyed_groups`, and ``strict``. It also adds
:ansopt:`hashicorp.terraform.tfc_inv#inventory:include_filters` and
:ansopt:`hashicorp.terraform.tfc_inv#inventory:exclude_filters` for host selection.

.. code-block:: yaml

   plugin: hashicorp.terraform.tfc_inv
   source: statefile
   organization: my-org
   workspace: my-workspace
   compose:
     ansible_host: public_ip
   keyed_groups:
     - key: instance_state      # -> groups state_running, state_stopped
       prefix: state
     - key: tags.env            # -> groups env_prod, env_dev
       prefix: env
   groups:
     web: "'web' in (tags.Name | default(''))"
   include_filters:
     - instance_state: running  # keep only running instances
   exclude_filters:
     - tags.env: staging        # drop staging

Reserved host-variable names
----------------------------

If a Terraform field collides with an Ansible-reserved host variable (``name``, ``tags``,
``groups``, ``inventory_hostname``, …), Ansible prints a ``Found variable using reserved name``
warning. Namespace every user field with
:ansopt:`hashicorp.terraform.tfc_inv#inventory:hostvars_prefix` (or
:ansopt:`hashicorp.terraform.tfc_inv#inventory:hostvars_suffix`) to silence it:

.. code-block:: yaml

   hostvars_prefix: tf_         # name -> tf_name, tags -> tf_tags
   hostnames:
     - tf_name                  # original or prefixed name both resolve in config

.. _ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.multi:

Multi-workspace mode
====================

Set :ansopt:`hashicorp.terraform.tfc_inv#inventory:workspace_filters` to enumerate every matching
workspace and merge their inventory. This requires ``organization`` and is mutually exclusive
with ``workspace`` / ``workspace_id``. Every host produced in this mode is stamped with
``tfc_workspace_id`` and ``tfc_workspace_name`` host variables so playbooks can route by origin,
and host names are disambiguated per workspace so identical resources in two workspaces never
collapse into one host.

.. code-block:: yaml

   plugin: hashicorp.terraform.tfc_inv
   source: outputs
   organization: my-org
   workspace_filters:
     project_id: prj-abc123def456     # must be a project ID (prj-...)
     tags: prod,linux                 # include workspaces with both tags
     exclude_tags: deprecated
     wildcard_name: "*prod*"          # wildcard on workspace name
     current_run_status: applied
   enable_parallel_processing: true   # fetch workspaces concurrently
   concurrency: 5                     # 1..10 (hard cap 10)

Filters compose at the API level: a workspace must satisfy **every** criterion you set. Empty
string values are treated as unset. Enable
:ansopt:`hashicorp.terraform.tfc_inv#inventory:enable_parallel_processing` for faster fetches;
each worker uses its own ``pytfe`` client and all inventory mutation happens on the main thread.

.. _ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.cache:

Caching
=======

The plugin supports the standard Ansible inventory cache (the ``inventory_cache`` fragment):
:ansopt:`hashicorp.terraform.tfc_inv#inventory:cache`,
:ansopt:`hashicorp.terraform.tfc_inv#inventory:cache_plugin`,
:ansopt:`hashicorp.terraform.tfc_inv#inventory:cache_timeout`,
:ansopt:`hashicorp.terraform.tfc_inv#inventory:cache_connection`, and
:ansopt:`hashicorp.terraform.tfc_inv#inventory:cache_prefix`.

.. code-block:: yaml

   # persistent cross-run cache via the jsonfile backend
   plugin: hashicorp.terraform.tfc_inv
   source: statefile
   workspace_id: ws-abc123
   cache: true
   cache_plugin: jsonfile
   cache_connection: ~/.ansible/cache/tfc_inv
   cache_prefix: tfc_inv
   cache_timeout: 300

Within ``cache_timeout`` a cache hit makes **zero API calls** and works fully offline. After a
Terraform apply, force a refresh with ``ansible-inventory --flush-cache``.

Apply-aware freshness
---------------------

For long ``cache_timeout`` values, opt into
:ansopt:`hashicorp.terraform.tfc_inv#inventory:cache_validate_current_state_version` to revalidate
cache entries against the workspace's current state version on each run. A cheap
``state-versions/current`` lookup decides whether to reuse the cached data or refetch — so you get
both a long cache window and apply-accurate inventory. This mode is **not** offline-friendly: it
requires connectivity every run and raises a parser error if the validation call fails rather than
serving potentially stale data.

.. code-block:: yaml

   cache: true
   cache_timeout: 3600
   cache_validate_current_state_version: true

.. note::

   Cache keys are isolated by endpoint, so the same ``cache_prefix`` will not cross-contaminate
   between HCP Terraform and a Terraform Enterprise instance pointed at by a different
   ``tfe_address``.

.. _ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.failure:

Failure behavior
================

- **Single-workspace mode**: any hard error (bad token, missing workspace, network failure) fails
  the parse.
- **Multi-workspace mode**: per-workspace failures are tolerated — the plugin warns and continues
  so one broken workspace does not sink the whole run. If **every** matched workspace fails (for
  example a bad token affecting all of them), the plugin raises instead of returning an empty
  inventory, so you are not silently left with zero hosts.

.. warning::

   By default ``ansible-inventory`` and playbook runs exit ``0`` even when an inventory source
   fails to parse, which can mean "zero hosts" passes unnoticed. Set
   ``ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED=true`` (or ``any_unparsed_is_failed = true`` in the
   ``[inventory]`` section of ``ansible.cfg``) in CI to make a failed parse a hard error.

See :ref:`ansible_collections.hashicorp.terraform.docsite.guide_troubleshooting` for diagnosing an
empty inventory.

.. _ansible_collections.hashicorp.terraform.docsite.guide_dynamic_inventory.more:

More examples
=============

The plugin ships an extensive set of examples covering every output shape, caching mode, and
multi-workspace filter. View them with:

.. code-block:: bash

   ansible-doc -t inventory hashicorp.terraform.tfc_inv
