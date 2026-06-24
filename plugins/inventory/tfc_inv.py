# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
name: tfc_inv
author:
  - Prabuddha Chakraborty (@iam404)
short_description: Unified dynamic inventory plugin for HCP Terraform / Terraform Enterprise.
description:
  - A single inventory plugin entry-point that supports multiple data sources
    from HCP Terraform or Terraform Enterprise via the pytfe SDK.
  - Select the data source with the O(source) option.
  - Does not require the Terraform CLI or direct access to a Terraform backend
    (S3, AzureRM, etc.).
  - Authentication is via O(tfe_token) or the E(TFE_TOKEN) environment variable.
  - Uses a YAML configuration file whose name ends with C(inventory.yml),
    C(inventory.yaml), C(terraform_inventory.yml), or
    C(terraform_inventory.yaml).
extends_documentation_fragment:
  - constructed
  - inventory_cache
version_added: "2.0.0"
options:
  plugin:
    description:
      - The name of the Inventory Plugin.
      - This should always be V(hashicorp.terraform.tfc_inv).
    required: true
    type: str
    choices: [hashicorp.terraform.tfc_inv]
  source:
    description:
      - Data source backend to use.
      - V(statefile) (default) downloads the latest Terraform state version
        from HCP Terraform via the pytfe SDK, parses the C(resources[])
        section, and produces one Ansible host per matching resource instance.
        Requires no Terraform CLI, no backend credentials.  Inventory
        candidates are selected by provider and resource type; see
        O(provider_mapping) to extend the defaults.
      - "B(Sensitive attributes are stripped before host vars are emitted):
        any path listed in an instance's Terraform C(sensitive_attributes)
        metadata is dropped entirely (not masked), so values that
        Terraform/its providers flag as sensitive cannot leak into inventory
        output.  Stripped fields are unavailable to O(hostnames),
        O(compose), O(groups), O(keyed_groups), and filters; references to
        them simply will not resolve.  This protection only covers
        provider-flagged sensitive attributes — for intentionally shaped,
        always-safe inventory data, prefer V(source=outputs)."
      - V(outputs) queries the HCP Terraform state version outputs API
        endpoint and builds hosts from workspace output values.  Lighter weight
        when only named output values are needed.  By default, when
        O(hosts_from) is omitted, only the Terraform output named
        V(ansible_host) is processed.  Use O(hosts_from) to target any other
        output name or to declare an explicit Terraform type expression.
    type: str
    choices: [statefile, outputs]
    default: statefile
  tfe_token:
    description:
      - HCP Terraform or Terraform Enterprise API token.
      - Falls back to the E(TFE_TOKEN) environment variable when not set.
    type: str
    env:
      - name: TFE_TOKEN
  tfe_address:
    description:
      - Base URL of the HCP Terraform or Terraform Enterprise instance.
      - Falls back to E(TFE_ADDRESS) when not set.
    type: str
    default: https://app.terraform.io
    env:
      - name: TFE_ADDRESS
  organization:
    description:
      - Name of the Terraform organization.
      - Required together with O(workspace) unless O(workspace_id) is provided.
      - Used by V(source=statefile) and V(source=outputs).
    type: str
  workspace:
    description:
      - Name of the Terraform workspace within O(organization).
      - Required together with O(organization) unless O(workspace_id) is
        provided.
      - Used by V(source=statefile) and V(source=outputs).
    type: str
  workspace_id:
    description:
      - Direct workspace ID (for example V(ws-xxxxxxxxxxxxxxxx)).
      - Mutually exclusive with O(organization) and O(workspace).
      - Used by V(source=statefile) and V(source=outputs).
    type: str
  workspace_filters:
    description:
      - Mapping of selection criteria for B(multi-workspace mode). When set,
        the plugin enumerates every matching workspace via the HCP Terraform
        Workspaces list API and merges inventory across them.
      - Requires O(organization). Mutually exclusive with O(workspace_id) and
        O(workspace) — when used, the plugin operates in multi-workspace mode.
      - Every host produced in this mode is stamped with the auto-injected
        variables V(tfc_workspace_id) and V(tfc_workspace_name).
      - Empty-string filter values are treated as unset (no API filter).
      - "Project name resolution is intentionally not supported. Pass
        V(project_id) as the project ID starting with V(prj-) — look it up via
        the HCP Terraform UI or projects API."
    type: dict
    default: {}
    version_added: "2.1.0"
    suboptions:
      project_id:
        description:
          - Restrict to workspaces in the given project. Must be a project ID
            starting with V(prj-).
        type: str
      name_search:
        description: Substring match on workspace name (search[name]).
        type: str
      tags:
        description: Comma-separated tags to include (search[tags]).
        type: str
      exclude_tags:
        description: Comma-separated tags to exclude (search[exclude-tags]).
        type: str
      wildcard_name:
        description: Wildcard pattern on workspace name, e.g. V("*prod*").
        type: str
      current_run_status:
        description: Filter by current-run status (filter[current-run][status]).
        type: str
      sort:
        description: Sort field for workspace listing.
        type: str
      page_size:
        description: Page size hint for the workspace list API.
        type: int
  enable_parallel_processing:
    description:
      - When V(true), workspaces matched by O(workspace_filters) are fetched
        concurrently. Has no effect in single-workspace mode.
      - Each worker constructs its own pytfe client so HTTP sessions are not
        shared across threads. Ansible inventory mutation always happens on
        the main thread.
    type: bool
    default: false
    version_added: "2.1.0"
  concurrency:
    description:
      - Maximum number of concurrent workspace fetches when
        O(enable_parallel_processing) is V(true).
      - Hard capped at V(10) to keep memory and API rate-limit pressure
        bounded. Values outside V([1, 10]) raise a parser error.
    type: int
    default: 5
    version_added: "2.1.0"
  search_child_modules:
    description:
      - When V(source=statefile), include resources defined inside Terraform
        child modules in addition to root-module resources.
      - Has no effect for other sources.
    type: bool
    default: false
  provider_mapping:
    description:
      - Additional provider / resource-type mappings for V(source=statefile).
      - Each entry extends the built-in set of supported providers
        (AWS, AzureRM, Google) with a custom provider name and the resource
        types that should produce inventory hosts.
      - Has no effect for other sources.
    type: list
    elements: dict
    default: []
    suboptions:
      provider_name:
        description:
          - Fully-qualified Terraform provider registry name, e.g.
            V(registry.terraform.io/digitalocean/digitalocean).
        type: str
        required: true
      types:
        description:
          - List of Terraform resource types from this provider that should
            produce inventory hosts, e.g. V(digitalocean_droplet).
        type: list
        elements: str
        required: true
  hosts_from:
    description:
      - Explicit output-to-host mapping for V(source=outputs).
      - When unset, V(source=outputs) processes only the Terraform output
        named V(ansible_host), using default output-shape detection.  When
        set, only the listed outputs are processed, each according to its
        declared V(type).
      - Accepts a single mapping or a list of mappings.  Each entry requires
        V(output) (the Terraform output name) and accepts V(type) (a Terraform
        type expression, default V(dynamic)).
      - "The V(type) vocabulary mirrors Terraform's official type system —
        see U(https://developer.hashicorp.com/terraform/language/expressions/types)."
      - "Object-shape outputs (V(object), V(list(object)), V(set(object)),
        V(map(object))) have their user dict fields B(spread flat) at the
        top level of host_vars, matching common Ansible inventory plugin
        conventions. Reference fields directly:
        V(compose: {ansible_host: public_ip}), V(hostnames: [name]),
        V(keyed_groups: [{key: env}]) — no V(item.<field>) ceremony."
      - "Primitive-shape outputs (V(string) / V(number) / V(bool) /
        V(list(<primitive>)) / V(set(<primitive>)) / V(map(<primitive>)))
        expose the scalar as a single host variable named V(value), matching
        the field name returned by Terraform's outputs API
        (V({\"name\": \"<output>\", \"value\": \"<scalar>\"})). V(value) is
        distinct from Ansible's loop variable V(item) and lives in a
        different scope, so an V(hostvars | dict2items) loop reads
        V(item.value.value) cleanly."
      - "For V(map(...)) shapes the map key becomes the resolved hostname and
        is available as V(inventory_hostname) — no separate V(key) host
        variable is injected, so a user dict containing a field named V(key)
        is preserved as-is."
      - "Supported V(type) expressions:
        V(string), V(number), V(bool) → one host, V(host_vars = {value: scalar});
        V(object) and V(object({...})) → one host, user dict spread flat at
        top level (the schema body of V(object({...})) is informational and
        ignored — Terraform has already validated it);
        V(list(string)), V(list(number)), V(list(bool)) → N indexed hosts,
        each V(host_vars = {value: scalar});
        V(list(object)) → N indexed hosts, each user dict spread flat;
        V(set(...)) → wire-level synonym for V(list(...)) (both serialize as
        JSON arrays);
        V(map(string)), V(map(number)), V(map(bool)) → one host per key,
        V(host_vars = {value: scalar}), map key becomes V(inventory_hostname);
        V(map(object)) → one host per key, user dict spread flat, map key
        becomes V(inventory_hostname);
        V(tuple) and V(tuple([...])) → routed through dynamic detection (a
        tuple is a JSON array on the wire, indistinguishable from a list);
        V(dynamic) (default when V(type) is omitted) → shape inferred at
        runtime from the value, mirroring Terraform's plugin-framework
        U(https://developer.hashicorp.com/terraform/plugin/framework/handling-data/types/dynamic) type."
      - "Auto-V(ansible_host): when the inventory's V(compose) option is
        empty, primitive shapes additionally set V(ansible_host) to the
        scalar. This makes V(hosts_from)
        V({output: ips, type: list(string)}) usable with no further config.
        Setting any V(compose) entry suppresses this default — V(compose) is
        then the single source of host-var assignment."
      - For V(map(...)) shapes the map key becomes the resolved hostname; the
        V(hostnames) preference list has no further effect for those records.
      - "Reserved-name collisions: when a Terraform field name collides with
        an Ansible-reserved host variable (V(name), V(groups), V(tags),
        V(inventory_hostname), …) Ansible emits an informational warning.
        Set O(hostvars_prefix) (e.g. V(tf_)) to namespace every spread field
        and silence the warning."
      - "V(type=dynamic) detection rules: a B(dict) of dicts is treated as
        V(map(object)); any other dict (including a dict of primitives) is
        treated as V(object); a B(list) of dicts is treated as V(list(object));
        a B(list) of all primitives is treated as V(list(<primitive>));
        primitive scalars are treated as their matching primitive type;
        empty collections, V(None), and mixed-type lists are skipped (mixed
        lists with a warning). Note that a dict of primitives is ambiguous
        between V(object) and V(map(string)) — V(dynamic) picks V(object);
        declare V(type: map(string)) explicitly when you want the map semantics.
        The no-O(hosts_from) default is a special case: a Terraform output
        named V(ansible_host) whose value is a dict of primitives is treated
        as V(map(<primitive>)) so map keys become inventory hostnames."
      - Nested collections (V(map(list(...))), V(list(map(...))), etc.) are
        rejected at validation time with a clear message. Reshape such values
        in your Terraform output using C(flatten()) or C(for) expressions;
        inventory is the wrong layer for nested-collection transformation.
      - Has no effect for V(source=statefile).
    type: raw
    default: null
  hostnames:
    description:
      - Ordered preference list for resolving the inventory hostname.
      - Each element can be a plain string or a dict with keys C(name)
        (required), C(prefix) (optional), and C(separator) (default V(_)).
      - "For V(source=statefile): a plain string is looked up in the resource
        instance attributes. Use V(tag:Name) to read the value of the V(Name)
        tag, or V(tag:Name=Value) to produce V(Name_Value) only when that exact
        tag value matches. Fallback: V(<resource_type>_<resource_name>[_<index>])."
      - "For V(source=outputs): a string is resolved as a host-var name
        lookup, with dotted paths walking nested user dicts (e.g.
        V(tags.role) reads V(host_vars[tags][role])). Use the special token
        V(output_name) to use the Terraform output name itself. When a
        preference does not resolve in this record's host vars, the next
        preference is tried; if none resolve, the
        V(<workspace_name>_<output_name>[_<index>]) default is used. Plain
        strings are B(not) treated as literal hostnames — set a static
        hostname via V(compose) instead."
    type: list
    elements: raw
    default: []
  include_filters:
    description:
      - List of key-value dicts. A host is included only when its variables
        match at least one dict (all key-value pairs within a given dict must
        match). An empty list means all hosts are included.
      - "For V(source=outputs), keys may use dotted paths to read into nested
        user-data dicts (e.g. V({tags.role: web}) when V(tags) is itself a
        Terraform object)."
    type: list
    elements: dict
    default: []
  exclude_filters:
    description:
      - List of key-value dicts. A host is excluded when its variables match
        any dict (all key-value pairs within a given dict must match).
        Exclusion is evaluated before O(include_filters).
      - "For V(source=outputs), keys may use dotted paths to read into nested
        user-data dicts (e.g. V({tags.role: web}) when V(tags) is itself a
        Terraform object)."
    type: list
    elements: dict
    default: []
  hostvars_prefix:
    description:
      - String prepended to every host variable name sourced from user data
        before it is registered with the inventory.
      - Use this when Terraform output field names collide with Ansible's
        reserved host-var namespace (V(name), V(groups), V(tags),
        V(inventory_hostname), …) — for example V(hostvars_prefix=tf_)
        renames a V(name) field to V(tf_name) and silences the
        "Found variable using reserved name" warning.
      - The plugin-injected variables V(ansible_host) and V(value) (the
        primitive-shape host var) are never renamed.
      - "V(compose), V(keyed_groups), V(groups), V(hostnames), and filter
        keys can reference B(either) the original Terraform field name
        B(or) the prefixed/suffixed name — both resolve to the same value.
        For example, with V(hostvars_prefix=tf_), both
        V(compose={ansible_host=public_ip}) and
        V(compose={ansible_host=tf_public_ip}) work. The renamed name is
        what is actually B(stored) on the host; the original is available
        only at config-resolution time."
    type: str
    default: ""
  hostvars_suffix:
    description:
      - String appended to every host variable name sourced from user data,
        with the same scope and exclusions as O(hostvars_prefix).
    type: str
    default: ""
  cache_validate_current_state_version:
    description:
      - Opt-in cache-freshness mode that validates a cache entry against the
        workspace's current Terraform state version ID before reusing it.
      - When V(false) (default), caching is the standard Ansible
        timeout-based contract from O(cache) — cache hits
        make zero API calls and are fully offline-capable within
        O(cache_timeout). Use V(--flush-cache) to force a
        refresh after a Terraform apply.
      - When V(true), each cache hit triggers a lightweight
        C(state-versions/current) lookup. If the cached entry's recorded
        state version ID matches the workspace's current state version ID,
        the heavy state download or outputs fetch is skipped. If they
        differ, fresh data is fetched and the cache entry is overwritten.
      - This mode is not offline-friendly. It requires HCP/TFE
        connectivity on every run; if the validation API call fails the
        plugin raises a parser error rather than serve potentially stale
        cache.
      - Has no effect when O(cache) is V(false).
    type: bool
    default: false
    version_added: "2.1.0"
"""

EXAMPLES = r"""
# ── statefile source (default) ────────────────────────────────────────────────

# Minimal: token from TFE_TOKEN, workspace by organization + name.
# Produces one host per matching resource instance (aws_instance, etc.)
# with Terraform attributes as host vars.  Attributes flagged as sensitive
# in the state (sensitive_attributes) are dropped before being exposed.
- name: Build inventory from latest HCP Terraform state
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  organization: my-org
  workspace: my-workspace

# Workspace by direct ID (avoids an extra org lookup)
- name: Inventory from workspace ID
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  workspace_id: ws-xxxxxxxxxxxxxxxx

# Use the instance's public_ip as ansible_host
- name: Set ansible_host from public_ip
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  organization: my-org
  workspace: my-workspace
  compose:
    ansible_host: public_ip

# Hostname from the value of the 'Name' tag
- name: Tag-based hostname
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  organization: my-org
  workspace: my-workspace
  hostnames:
    - tag:Name       # e.g. tags = {Name = "web-1"} → host "web-1"

# Hostname with environment prefix from tags
- name: Prefixed hostname from tags
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  organization: my-org
  workspace: my-workspace
  hostnames:
    - name: tag:Name
      prefix: tag:Environment
      separator: "-"
  # e.g. tags = {Name = "web-1", Environment = "prod"} → host "prod-web-1"

# Hostname from a plain attribute value, falling back to the resource name
- name: Hostname from attribute
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  organization: my-org
  workspace: my-workspace
  hostnames:
    - public_dns     # e.g. "ec2-1-2-3-4.compute-1.amazonaws.com"
    - public_ip      # fallback to public_ip if DNS is empty

# Group by instance_state attribute (running / stopped / terminated)
- name: Group by instance state
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  organization: my-org
  workspace: my-workspace
  keyed_groups:
    - key: instance_state
      prefix: state
  # Produces groups: state_running, state_stopped, etc.

# Include only running instances
- name: Filter to running instances
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  organization: my-org
  workspace: my-workspace
  include_filters:
    - instance_state: running

# Also include child-module resources
- name: Include resources from child modules
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  organization: my-org
  workspace: my-workspace
  search_child_modules: true

# Add DigitalOcean droplets (custom provider mapping)
- name: DigitalOcean inventory
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  organization: my-org
  workspace: my-workspace
  provider_mapping:
    - provider_name: registry.terraform.io/digitalocean/digitalocean
      types:
        - digitalocean_droplet
  hostnames:
    - tag:Name
    - name

# Target a self-hosted Terraform Enterprise instance
- name: TFE on-prem inventory
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  tfe_address: https://terraform.example.com
  organization: my-org
  workspace: my-workspace

# ── outputs source ────────────────────────────────────────────────────────────

# Default mode processes only Terraform output "ansible_host".
# Terraform: output "ansible_host" { value = ["10.0.0.1", "10.0.0.2"] }
- name: Inventory from default ansible_host output
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace

# Terraform: output "ansible_host" { value = { web1 = "10.0.0.1", web2 = "10.0.0.2" } }
# The map keys become inventory hostnames; values become ansible_host.
- name: Inventory from ansible_host map output
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace

# Use hosts_from for any output name other than "ansible_host".
- name: Inventory from custom hosts output
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: hosts
    type: list(object)
  hostnames:
    - name
  compose:
    ansible_host: public_ip

# Exclude staging hosts from outputs inventory
- name: Exclude staging from outputs
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  exclude_filters:
    - env: staging

# ── hosts_from: Terraform type expressions ────────────────────────────────────
# Object shapes (object, list(object), set(object), map(object)) spread the
# user dict at the top level of host_vars — reference fields directly as
# `name`, `public_ip`, etc.
# Primitive shapes expose the scalar as `value`. For map(...) shapes the map
# key becomes inventory_hostname (no separate `key` host var).
# When `compose` is empty, primitive shapes auto-set `ansible_host` to the
# scalar — so the simplest configurations need no compose at all.
# Nested collections (map(list(...)) etc.) are not supported — reshape with
# Terraform's flatten()/for if needed.

# list(string): no compose needed — each IP auto-becomes ansible_host
# Terraform: output "instance_ips" { value = ["1.2.3.4", "5.6.7.8"] }
# Hosts: my-ws_instance_ips_0, my-ws_instance_ips_1, … (ansible_host = the IP)
- name: Inventory from list-of-string IPs (zero compose)
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: instance_ips
    type: list(string)

# Same shape, but use the IP itself as the Ansible hostname.
- name: IP-as-hostname from list(string)
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: instance_ips
    type: list(string)
  hostnames:
    - ansible_host    # auto-assigned IP becomes the Ansible hostname

# list(string) with custom compose — auto-ansible_host is suppressed by the
# presence of any compose entry, so re-assign explicitly using `value`.
- name: list(string) with custom compose
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: instance_ips
    type: list(string)
  compose:
    ansible_host: value
    ansible_user: '"ec2-user"'

# map(string): key becomes the hostname; primitive auto-becomes ansible_host
# Terraform: output "host_map" { value = { "web-1" = "1.2.3.4", "web-2" = "5.6.7.8" } }
- name: Map-keyed IP inventory
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: host_map
    type: map(string)

# map(string) using `value` (the scalar) and `inventory_hostname` (the map key)
# to compose a richer host_var.
- name: map(string) with composed environment
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: host_map
    type: map(string)
  compose:
    ansible_host: value
    env_short: inventory_hostname | regex_replace('-.*', '')

# map(object): key = hostname, user dict spread flat at top level. Reference
# fields directly from compose / hostnames / filters.
# Terraform: output "web_hosts" { value = { "web-1" = { public_ip = "…", env = "prod" } } }
- name: Structured map-keyed inventory
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: web_hosts
    type: map(object)
  compose:
    ansible_host: public_ip
  keyed_groups:
    - key: env
      prefix: env

# list(object) with reserved-name avoidance: hostvars_prefix namespaces every
# spread field, silencing the "Found variable using reserved name" warning
# when a Terraform field is named e.g. `name` or `tags`.
- name: list(object) with hostvars_prefix
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: web_hosts
    type: list(object)
  hostvars_prefix: tf_                # name → tf_name, public_ip → tf_public_ip
  hostnames:
    - tf_name                         # reference the prefixed name
  compose:
    ansible_host: tf_public_ip

# set(object) — same JSON wire format as list(object); accepted as a synonym.
- name: Inventory from set(object)
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: node_set
    type: set(object)
  hostnames:
    - name

# Scalar: number output → one host, primitive stored as `value`. With no
# compose, `ansible_host = value` automatically.
# Terraform: output "host_count" { value = 3 }
- name: Scalar inventory
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: host_count
    type: number

# type: dynamic — shape inferred from the runtime value (mirrors Terraform's
# plugin-framework "dynamic" type — see
# https://developer.hashicorp.com/terraform/plugin/framework/handling-data/types/dynamic).
# Note: a dict of primitives is treated as `object` (one host with the dict
# spread flat). To get map(string) semantics from a dict of primitives,
# declare `type: map(string)` explicitly.
- name: Inventory with dynamic-detected types
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    - output: web_hosts        # dict of dicts → map(object)
      type: dynamic
    - output: db_ips           # list of strings → list(string), auto ansible_host
      type: dynamic

# Multiple outputs combined — hosts_from accepts a list of specs mixing
# primitive and object shapes. Note: any compose entry suppresses the auto-
# ansible_host default for primitive specs, so when mixing shapes, set
# `compose: ansible_host` to a Jinja that picks up either a field name (for
# the object specs) or `value` (for the primitive specs).
- name: Multi-output inventory
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    - output: web_hosts
      type: map(object)        # ansible_host pulled from public_ip via compose
    - output: db_ips
      type: list(string)       # ansible_host = value via compose
    - output: bastion_ip
      type: string             # ansible_host = value via compose
  compose:
    ansible_host: public_ip | default(value)

# Per-run in-memory cache (no persistence across ansible-inventory invocations).
# Cache entries are keyed by the current Terraform state version ID, so a new
# apply automatically refreshes inventory even if cache_timeout has not expired.
- name: Inventory with in-memory cache
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  cache: true
  cache_timeout: 300

# Persistent cross-run cache via the jsonfile cache plugin. Setting
# cache_prefix lets multiple tfc_inv inventories share a backend without
# colliding (mirrors aws_ec2 / azure_rm / k8s convention).
- name: Inventory with persistent jsonfile cache
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  workspace_id: ws-abc123
  cache: true
  cache_plugin: jsonfile
  cache_connection: ~/.ansible/cache/tfc_inv
  cache_prefix: tfc_inv
  cache_timeout: 300

# Freshness-validated cache (apply-aware): each run resolves the workspace's
# current Terraform state version and only reuses cached data whose recorded
# state_version_id matches. Heavy state download / outputs fetch is skipped
# when validated. NOT offline-friendly — requires HCP/TFE connectivity on
# every run; a failed validation API call raises rather than serving stale
# cache.
- name: Inventory with apply-aware freshness validation
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  cache: true
  cache_timeout: 3600
  cache_validate_current_state_version: true

# ── multi-workspace mode ──────────────────────────────────────────────────────

# Merge inventory from every workspace in a project. Hosts gain
# tfc_workspace_id / tfc_workspace_name host vars so playbooks can route by
# origin. Parallel fetch is opt-in via enable_parallel_processing.
- name: All workspaces in a project
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace_filters:
    project_id: prj-abc123def456
  enable_parallel_processing: true
  concurrency: 5

# Combine multiple filters. Filters compose at the HCP Terraform API level —
# returned workspaces must satisfy every set criterion.
- name: Production workspaces with prod tag, exclude deprecated
  plugin: hashicorp.terraform.tfc_inv
  source: statefile
  organization: my-org
  workspace_filters:
    tags: prod,linux
    exclude_tags: deprecated
    current_run_status: applied
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ansible.errors import AnsibleParserError
from ansible.module_utils._text import to_text
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable
from ansible.utils.display import Display

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError, TerraformTokenNotFoundError
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources import outputs as _outputs_module
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.base import HostRecord
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common import (
    get_preferred_hostname,
    list_workspaces,
    passes_filters,
    resolve_current_state_version_id,
    resolve_workspace,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.factory import get_source_backend

# Bumped whenever the per-workspace cache blob shape changes; older entries are ignored.
_CACHE_SCHEMA = "tfc_inv_cache_v1"

# Bumped whenever the selector cache blob shape changes; older entries are ignored.
_SELECTOR_CACHE_SCHEMA = "tfc_inv_selector_v1"

# Hard cap on concurrent workspace fetches. Larger values create memory and
# rate-limit pressure that is rarely worth it for inventory builds.
_CONCURRENCY_MAX = 10


def _wire_outputs_display() -> None:
    """Wire the controller's Display into the outputs source backend so its
    hosts_from validation/dynamic-detection warnings surface to the user."""
    display = Display()
    _outputs_module._warn = display.warning
    _outputs_module._debug = display.vvv


_wire_outputs_display()


def _fetch_workspace_records(
    ws_id: str,
    ws_name: str,
    source_options: Dict[str, Any],
    source_cls: Any,
    tfe_token: str,
    tfe_address: str,
    cached_blob: Optional[Dict[str, Any]],
    validate_sv: bool,
) -> Dict[str, Any]:
    """Fetch one workspace's records. Safe to run in a worker thread.

    Returns a dict with keys: ``records``, ``blob`` (new blob to write, or
    None), ``ws_id``, ``ws_name``, ``warning`` (optional), ``skipped`` (bool).
    Never touches ``InventoryData`` or the cache plugin — all state mutation
    happens in the main thread.
    """
    per_ws_options = dict(source_options)
    per_ws_options["workspace_id"] = ws_id
    per_ws_options["organization"] = None
    per_ws_options["workspace"] = None

    # Default mode + cache hit: serve entirely from blob, no client needed.
    if cached_blob is not None and not validate_sv:
        src = source_cls(None, per_ws_options)
        src._cached_blob = cached_blob
        return {
            "records": src.collect_hosts(),
            "blob": None,
            "ws_id": ws_id,
            "ws_name": ws_name,
            "skipped": False,
        }

    try:
        client_cm = TerraformClient.from_mapping({"tfe_token": tfe_token, "tfe_address": tfe_address})
    except TerraformTokenNotFoundError as exc:
        return {
            "records": [],
            "blob": None,
            "ws_id": ws_id,
            "ws_name": ws_name,
            "warning": f"authentication error for workspace {ws_name} ({ws_id}): {exc}",
            "skipped": True,
        }

    with client_cm as client:
        if validate_sv:
            try:
                sv = client.client.state_versions.read_current(ws_id)
                current_sv_id = getattr(sv, "id", None)
            except Exception as exc:  # noqa: BLE001 — pytfe surfaces several error types here
                return {
                    "records": [],
                    "blob": None,
                    "ws_id": ws_id,
                    "ws_name": ws_name,
                    "warning": (f"validation-mode: skipping workspace {ws_name} ({ws_id}): " f"could not resolve current state version: {exc}"),
                    "skipped": True,
                }

            if cached_blob is not None and cached_blob.get("state_version_id") == current_sv_id:
                src = source_cls(None, per_ws_options)
                src._cached_blob = cached_blob
                return {
                    "records": src.collect_hosts(),
                    "blob": None,
                    "ws_id": ws_id,
                    "ws_name": ws_name,
                    "skipped": False,
                }

            src = source_cls(client, per_ws_options)
            src._validation_ctx = {
                "workspace_id": ws_id,
                "workspace_name": ws_name,
                "state_version_id": current_sv_id,
            }
        else:
            src = source_cls(client, per_ws_options)
            # Skip the source's own resolve_workspace() — we already know the
            # workspace identity from the dispatcher.
            src._validation_ctx = {
                "workspace_id": ws_id,
                "workspace_name": ws_name,
                "state_version_id": None,
            }

        try:
            records = src.collect_hosts()
        except TerraformError as exc:
            msg = str(exc).lower()
            if "no current state version" in msg or "no applied runs" in msg:
                # Workspace has no state — common in filter mode (bootstrap /
                # never-applied workspaces). Cache an empty sentinel blob so
                # subsequent runs skip the failing API call.
                empty_data: Any = [] if source_cls.NAME == "outputs" else {"version": 4, "resources": [], "outputs": {}}
                return {
                    "records": [],
                    "blob": {
                        "schema": _CACHE_SCHEMA,
                        "source": source_cls.NAME,
                        "workspace_name": ws_name,
                        "workspace_id": ws_id,
                        "state_version_id": None,
                        "data": empty_data,
                    },
                    "ws_id": ws_id,
                    "ws_name": ws_name,
                    "skipped": False,
                    "warning": str(exc),  # downgraded to vvv in the dispatcher
                }
            raise

        return {
            "records": records,
            "blob": getattr(src, "_fetched_blob", None),
            "ws_id": ws_id,
            "ws_name": ws_name,
            "skipped": False,
        }


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):  # type: ignore[misc]
    NAME = "hashicorp.terraform.tfc_inv"

    _VALID_SUFFIXES = (
        "inventory.yaml",
        "inventory.yml",
        "terraform_inventory.yaml",
        "terraform_inventory.yml",
    )

    def verify_file(self, path: str) -> bool:
        valid = False
        if super().verify_file(path):
            if path.endswith(self._VALID_SUFFIXES):
                valid = True
        return valid

    # ------------------------------------------------------------------
    # Private utilities
    # ------------------------------------------------------------------

    def _build_client(self, options: Dict[str, Any]) -> TerraformClient:
        try:
            return TerraformClient.from_mapping(options)
        except TerraformTokenNotFoundError as exc:
            raise AnsibleParserError(f"Authentication error: {exc}") from exc

    def _sanitize_hostname(self, hostname: str) -> str:
        txt = to_text(hostname)
        if ":" in txt:
            return str(self._sanitize_group_name(txt))
        return str(txt)

    # Plugin-injected host variable names that must NEVER be renamed by
    # ``hostvars_prefix`` / ``hostvars_suffix``. ``ansible_host`` is reserved
    # by Ansible itself; ``value`` is this plugin's contract for primitive
    # shapes and renaming it would break the ``compose: {ansible_host: value}``
    # idiom. ``tfc_workspace_id`` / ``tfc_workspace_name`` are auto-stamped in
    # multi-workspace mode so playbooks can route hosts by origin.
    _PLUGIN_INJECTED_VARS = frozenset({"ansible_host", "value", "tfc_workspace_id", "tfc_workspace_name"})

    def _build_resolution_view(
        self,
        host_vars: Dict[str, Any],
        hostvars_prefix: str,
        hostvars_suffix: str,
    ) -> Dict[str, Any]:
        """Return a dict containing BOTH original and renamed user-field names.

        ``hostnames``, ``compose``, ``keyed_groups``, ``groups``, and filter
        keys all resolve names against this view, so users can reference
        either ``public_ip`` or ``tf_public_ip`` (when ``hostvars_prefix=tf_``)
        and both will work. Mirrors the dict-update pattern used by
        common inventory plugins that keep both raw and renamed variables
        available while resolving constructed configuration.

        Plugin-injected vars (``ansible_host``, ``value``) are never renamed.
        """
        if not (hostvars_prefix or hostvars_suffix):
            return host_vars
        view: Dict[str, Any] = dict(host_vars)
        for key, value in host_vars.items():
            if key in self._PLUGIN_INJECTED_VARS:
                continue
            view[f"{hostvars_prefix}{key}{hostvars_suffix}"] = value
        return view

    def _add_host(
        self,
        hostname: str,
        host_vars: Dict[str, Any],
        resolution_view: Dict[str, Any],
        compose: Dict[str, str],
        keyed_groups: List[Dict[str, Any]],
        groups: Dict[str, Any],
        strict: bool,
        hostvars_prefix: str = "",
        hostvars_suffix: str = "",
    ) -> None:
        hostname = self._sanitize_hostname(hostname)
        self.inventory.add_host(hostname)
        rename = hostvars_prefix or hostvars_suffix
        for key, value in host_vars.items():
            if rename and key not in self._PLUGIN_INJECTED_VARS:
                var_name = f"{hostvars_prefix}{key}{hostvars_suffix}"
            else:
                var_name = key
            self.inventory.set_variable(hostname, var_name, value)
        # ``compose`` / ``keyed_groups`` / ``groups`` receive the resolution
        # view containing BOTH original and prefixed/suffixed field names, so
        # user expressions can reference either form consistently regardless
        # of whether ``hostvars_prefix`` is set.
        self._set_composite_vars(compose, resolution_view, hostname, strict=strict)
        self._add_host_to_keyed_groups(keyed_groups, resolution_view, hostname, strict=strict)
        self._add_host_to_composed_groups(groups, resolution_view, hostname, strict=strict)

    def _populate_from_host_records(
        self,
        records: Iterable[HostRecord],
        hostnames: List[Any],
        compose: Dict[str, str],
        keyed_groups: List[Dict[str, Any]],
        groups: Dict[str, Any],
        strict: bool,
        include_filters: List[Dict],
        exclude_filters: List[Dict],
        hostvars_prefix: str = "",
        hostvars_suffix: str = "",
        stamp_workspace_vars: bool = False,
    ) -> None:
        """Apply filtering and register each record as an Ansible host.

        Sources that perform their own hostname resolution (e.g.
        ``StatefileSource``) pre-populate ``resolved_hostname`` on each record.
        When that key is present it is used directly; otherwise the
        outputs-style ``get_preferred_hostname`` fallback applies.

        When *stamp_workspace_vars* is ``True`` (multi-workspace mode), each
        host gets the auto-injected ``tfc_workspace_id`` / ``tfc_workspace_name``
        vars sourced from the record's metadata. These names live in
        ``_PLUGIN_INJECTED_VARS`` so they survive ``hostvars_prefix`` /
        ``hostvars_suffix`` renaming.

        Hostname resolution and registration run in two passes so that, in
        multi-workspace mode, a hostname produced by more than one workspace can
        be disambiguated (by appending the workspace name) instead of silently
        collapsing onto a single Ansible host.
        """
        resolved: List[Dict[str, Any]] = []
        hostname_workspaces: Dict[str, set] = {}
        for record in records:
            host_vars: Dict[str, Any] = dict(record["host_vars"])
            ws_id = record.get("workspace_id")
            ws_name = record.get("workspace_name")
            if stamp_workspace_vars:
                if ws_id:
                    host_vars["tfc_workspace_id"] = ws_id
                if ws_name:
                    host_vars["tfc_workspace_name"] = ws_name

            resolution_view = self._build_resolution_view(host_vars, hostvars_prefix, hostvars_suffix)

            if not passes_filters(resolution_view, include_filters, exclude_filters):
                continue

            if "resolved_hostname" in record:
                hostname: Optional[str] = record["resolved_hostname"]
            else:
                output_name: str = record["output_name"]
                workspace_name: str = record["workspace_name"]
                index = record.get("index")
                hostname = get_preferred_hostname(output_name, workspace_name, resolution_view, hostnames, index)

            if not hostname:
                continue

            resolved.append(
                {
                    "hostname": hostname,
                    "host_vars": host_vars,
                    "resolution_view": resolution_view,
                    "ws_id": ws_id,
                    "ws_name": ws_name,
                }
            )
            if stamp_workspace_vars:
                hostname_workspaces.setdefault(hostname, set()).add(ws_id)

        # Hostnames claimed by more than one distinct workspace would otherwise
        # collapse onto a single Ansible host (last writer wins), silently
        # dropping hosts and overwriting their ``tfc_workspace_*`` stamps.
        colliding = {h for h, workspaces in hostname_workspaces.items() if len(workspaces) > 1}
        if colliding:
            Display().warning(
                f"Multi-workspace inventory: hostname(s) {', '.join(sorted(colliding))} are produced by "
                "more than one workspace; disambiguating by appending the workspace name. Set 'hostnames' "
                "or 'compose' to control inventory hostnames deterministically."
            )

        for item in resolved:
            hostname = item["hostname"]
            if hostname in colliding:
                suffix = item["ws_name"] or item["ws_id"]
                if suffix:
                    hostname = f"{hostname}_{suffix}"
            self._add_host(
                hostname,
                item["host_vars"],
                item["resolution_view"],
                compose,
                keyed_groups,
                groups,
                strict,
                hostvars_prefix=hostvars_prefix,
                hostvars_suffix=hostvars_suffix,
            )

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def _cache_key(
        self,
        source: str,
        workspace_id: Optional[str],
        organization: Optional[str],
        workspace: Optional[str],
    ) -> str:
        """Build a static cache key from inventory config — no API calls.

        Keys differ for different ``(source, workspace)`` tuples; a single
        inventory config keeps a stable key so subsequent runs hit the cache
        cleanly. Components are restricted to filesystem-safe characters
        (letters, digits, ``.``, ``-``, ``_``) so file-backed cache plugins
        like ``jsonfile`` can use the key directly as a filename.

        Cross-endpoint isolation is the user's job via ``cache_prefix`` /
        ``cache_connection`` rather than encoded in the key.
        """
        ws_part = workspace_id or "{0}/{1}".format(organization or "", workspace or "")
        raw = "_".join([self.NAME, source, ws_part])
        return re.sub(r"[^A-Za-z0-9._-]", "_", raw)

    def _selector_cache_key(
        self,
        source: str,
        organization: str,
        filters: Dict[str, Any],
    ) -> str:
        """Build a filesystem-safe selector cache key for multi-workspace mode.

        Filters are normalized via ``json.dumps(..., sort_keys=True)`` so YAML
        key order doesn't change the key. ``tfe_address`` is deliberately
        excluded — matches ``_cache_key`` for the same filesystem-safety
        reason; cross-endpoint isolation belongs to ``cache_prefix`` /
        ``cache_connection``.
        """
        normalized = json.dumps(filters or {}, sort_keys=True, default=str)
        raw = "_".join([self.NAME, "selector", source, organization or "", normalized])
        return re.sub(r"[^A-Za-z0-9._-]", "_", raw)

    def parse(self, inventory, loader, path, cache=False):  # type: ignore[override]
        super().parse(inventory, loader, path, cache=cache)
        raw = self._read_config_data(path)

        tfe_token: str = self.get_option("tfe_token") or ""
        tfe_address: str = self.get_option("tfe_address")
        source: str = self.get_option("source")
        hostnames: List[Any] = self.get_option("hostnames") or []
        include_filters: List[Dict] = self.get_option("include_filters") or []
        exclude_filters: List[Dict] = self.get_option("exclude_filters") or []
        compose: Dict[str, str] = self.get_option("compose") or {}
        keyed_groups: List[Dict] = self.get_option("keyed_groups") or []
        groups: Dict[str, Any] = self.get_option("groups") or {}
        strict: bool = bool(self.get_option("strict"))
        hostvars_prefix: str = self.get_option("hostvars_prefix") or ""
        hostvars_suffix: str = self.get_option("hostvars_suffix") or ""

        workspace_filters: Dict[str, Any] = self.get_option("workspace_filters") or {}
        enable_parallel: bool = bool(self.get_option("enable_parallel_processing"))
        concurrency_opt = self.get_option("concurrency")
        concurrency: int = int(concurrency_opt) if concurrency_opt is not None else 1

        workspace_id_opt = self.get_option("workspace_id")
        workspace_opt = self.get_option("workspace")
        organization_opt = self.get_option("organization")

        # Mode dispatch + validation. Multi-workspace mode is triggered by a
        # non-empty workspace_filters; exact workspace options must not be
        # mixed with it (fail loud rather than silently fall back).
        multi_mode = bool(workspace_filters)
        if multi_mode and (workspace_id_opt or workspace_opt):
            raise AnsibleParserError(
                "workspace_filters is mutually exclusive with workspace_id and " "workspace. Pick exact-workspace mode OR filter mode, not both."
            )
        if multi_mode and not organization_opt:
            raise AnsibleParserError("workspace_filters requires 'organization' to be set.")
        if concurrency < 1 or concurrency > _CONCURRENCY_MAX:
            raise AnsibleParserError(f"concurrency must be between 1 and {_CONCURRENCY_MAX}; got {concurrency}.")
        if enable_parallel and not multi_mode:
            Display().warning("enable_parallel_processing has no effect without workspace_filters; " "running in single-workspace mode.")

        source_options: Dict[str, Any] = {
            "workspace_id": workspace_id_opt,
            "organization": organization_opt,
            "workspace": workspace_opt,
            # Passed through to StatefileSource; ignored by OutputsSource.
            "search_child_modules": self.get_option("search_child_modules"),
            "provider_mapping": self.get_option("provider_mapping") or [],
            # StatefileSource resolves hostnames internally; passing here
            # avoids reading options a second time inside collect_hosts.
            "hostnames": hostnames,
            # OutputsSource explicit output-shape mapping; ignored by StatefileSource.
            # Read directly from raw config: type: raw option parsing is unreliable
            # across Ansible versions and may return None even when the key is set.
            "hosts_from": (raw or {}).get("hosts_from") if isinstance(raw, dict) else self.get_option("hosts_from"),
            # OutputsSource uses this to decide whether to auto-assign
            # ansible_host for primitive shapes (off when compose is non-empty).
            "compose": compose,
        }

        if not tfe_token:
            raise AnsibleParserError("A Terraform API token is required. Set 'tfe_token' in the inventory config or the TFE_TOKEN environment variable.")

        # Cache contract:
        # ``self.get_option("cache")`` reflects the user's inventory YAML opt-in.
        # ``cache`` (parameter) reflects the runtime gate — Ansible passes ``False``
        # when ``--flush-cache`` is in effect, so reads must be skipped that run.
        # Writes are still allowed to refresh the entry.
        user_cache_opt = bool(self.get_option("cache"))
        cache_read_ok = user_cache_opt and bool(cache)
        cache_write_ok = user_cache_opt
        # Opt-in apply-aware freshness mode. When True, every run resolves the
        # workspace's current state version and only reuses cached data whose
        # ``state_version_id`` matches. Not offline-friendly — see option docs.
        validate_sv = user_cache_opt and bool(self.get_option("cache_validate_current_state_version"))

        try:
            source_cls = get_source_backend(source)
            if not multi_mode:
                source_cls.validate_options(source_options)

            if multi_mode:
                records = self._parse_multi(
                    source=source,
                    source_cls=source_cls,
                    source_options=source_options,
                    organization=organization_opt,
                    workspace_filters=workspace_filters,
                    tfe_token=tfe_token,
                    tfe_address=tfe_address,
                    cache_read_ok=cache_read_ok,
                    cache_write_ok=cache_write_ok,
                    validate_sv=validate_sv,
                    enable_parallel=enable_parallel,
                    concurrency=concurrency,
                )
            else:
                records = self._parse_single(
                    source=source,
                    source_cls=source_cls,
                    source_options=source_options,
                    tfe_token=tfe_token,
                    tfe_address=tfe_address,
                    cache_read_ok=cache_read_ok,
                    cache_write_ok=cache_write_ok,
                    validate_sv=validate_sv,
                )

            self._populate_from_host_records(
                records,
                hostnames,
                compose,
                keyed_groups,
                groups,
                strict,
                include_filters,
                exclude_filters,
                hostvars_prefix=hostvars_prefix,
                hostvars_suffix=hostvars_suffix,
                stamp_workspace_vars=multi_mode,
            )
        except TerraformError as exc:
            raise AnsibleParserError(str(exc)) from exc
        except TerraformTokenNotFoundError as exc:
            raise AnsibleParserError(f"Authentication error: {exc}") from exc
        except AnsibleParserError:
            raise
        except Exception as exc:
            raise AnsibleParserError(f"Failed to build inventory from HCP Terraform: {exc}") from exc

    # ------------------------------------------------------------------
    # Single-workspace path (unchanged logic, extracted for clarity)
    # ------------------------------------------------------------------

    def _parse_single(
        self,
        source: str,
        source_cls: Any,
        source_options: Dict[str, Any],
        tfe_token: str,
        tfe_address: str,
        cache_read_ok: bool,
        cache_write_ok: bool,
        validate_sv: bool,
    ) -> List[HostRecord]:
        user_cache_opt = cache_write_ok  # write_ok already encodes the user opt-in
        cache_key: Optional[str] = None
        if user_cache_opt:
            cache_key = self._cache_key(
                source,
                source_options.get("workspace_id"),
                source_options.get("organization"),
                source_options.get("workspace"),
            )

        if not validate_sv:
            cached_blob: Any = None
            if cache_read_ok and cache_key is not None:
                try:
                    candidate = self._cache[cache_key]
                except KeyError:
                    candidate = None
                if isinstance(candidate, dict) and candidate.get("schema") == _CACHE_SCHEMA:
                    cached_blob = candidate

            if cached_blob is not None:
                source_instance = source_cls(None, source_options)
                source_instance._cached_blob = cached_blob
                return source_instance.collect_hosts()

            with self._build_client({"tfe_token": tfe_token, "tfe_address": tfe_address}) as client:
                source_instance = source_cls(client, source_options)
                records = source_instance.collect_hosts()
                if cache_write_ok and cache_key is not None:
                    blob = getattr(source_instance, "_fetched_blob", None)
                    if blob is not None:
                        self._cache[cache_key] = blob
                return records

        # Validation mode (single workspace).
        with self._build_client({"tfe_token": tfe_token, "tfe_address": tfe_address}) as client:
            resolved_id, workspace_name = resolve_workspace(
                client,
                source_options.get("workspace_id"),
                source_options.get("organization"),
                source_options.get("workspace"),
            )
            current_sv_id = resolve_current_state_version_id(client, resolved_id)
            if current_sv_id is None:
                raise AnsibleParserError(
                    "cache_validate_current_state_version=true requires HCP/TFE "
                    "connectivity to validate the cache. Could not resolve the "
                    f"current state version ID for workspace '{workspace_name}' "
                    f"({resolved_id}). Disable validation mode to serve cached "
                    "data offline within cache_timeout."
                )

            cached_blob = None
            if cache_read_ok and cache_key is not None:
                try:
                    candidate = self._cache[cache_key]
                except KeyError:
                    candidate = None
                if isinstance(candidate, dict) and candidate.get("schema") == _CACHE_SCHEMA and candidate.get("state_version_id") == current_sv_id:
                    cached_blob = candidate

            source_instance = source_cls(client, source_options)
            if cached_blob is not None:
                source_instance._cached_blob = cached_blob
            else:
                source_instance._validation_ctx = {
                    "workspace_id": resolved_id,
                    "workspace_name": workspace_name,
                    "state_version_id": current_sv_id,
                }
            records = source_instance.collect_hosts()

            if cache_write_ok and cache_key is not None and cached_blob is None:
                blob = getattr(source_instance, "_fetched_blob", None)
                if blob is not None:
                    self._cache[cache_key] = blob
            return records

    # ------------------------------------------------------------------
    # Multi-workspace path
    # ------------------------------------------------------------------

    def _resolve_targets(
        self,
        source: str,
        organization: str,
        workspace_filters: Dict[str, Any],
        tfe_token: str,
        tfe_address: str,
        cache_read_ok: bool,
        cache_write_ok: bool,
    ) -> List[Tuple[str, str]]:
        """Return ``[(workspace_id, workspace_name), ...]`` from selector cache
        or a live ``workspaces.list()`` call. The selector cache eliminates the
        workspace-list API call on warm runs.
        """
        selector_key = self._selector_cache_key(source, organization, workspace_filters)

        if cache_read_ok:
            try:
                candidate = self._cache[selector_key]
            except KeyError:
                candidate = None
            if isinstance(candidate, dict) and candidate.get("schema") == _SELECTOR_CACHE_SCHEMA:
                targets = candidate.get("targets") or []
                if isinstance(targets, list):
                    return [(str(t[0]), str(t[1])) for t in targets if isinstance(t, (list, tuple)) and len(t) >= 2]

        with self._build_client({"tfe_token": tfe_token, "tfe_address": tfe_address}) as client:
            targets = list_workspaces(client, organization, workspace_filters)

        if cache_write_ok:
            try:
                self._cache[selector_key] = {
                    "schema": _SELECTOR_CACHE_SCHEMA,
                    "targets": [[ws_id, ws_name] for ws_id, ws_name in targets],
                }
            except Exception as exc:
                Display().warning(f"failed to write selector cache: {exc}")

        return targets

    def _read_per_workspace_cache(self, source: str, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Read a per-workspace cache blob if shape-valid. Main-thread only."""
        cache_key = self._cache_key(source, workspace_id, None, None)
        try:
            candidate = self._cache[cache_key]
        except KeyError:
            return None
        if isinstance(candidate, dict) and candidate.get("schema") == _CACHE_SCHEMA:
            return candidate
        return None

    def _write_per_workspace_cache(self, source: str, workspace_id: str, blob: Dict[str, Any]) -> None:
        """Write a per-workspace cache blob; warn on failure. Main-thread only."""
        cache_key = self._cache_key(source, workspace_id, None, None)
        try:
            self._cache[cache_key] = blob
        except Exception as exc:
            Display().warning(f"failed to write per-workspace cache for {workspace_id}: {exc}")

    def _parse_multi(
        self,
        source: str,
        source_cls: Any,
        source_options: Dict[str, Any],
        organization: str,
        workspace_filters: Dict[str, Any],
        tfe_token: str,
        tfe_address: str,
        cache_read_ok: bool,
        cache_write_ok: bool,
        validate_sv: bool,
        enable_parallel: bool,
        concurrency: int,
    ) -> List[HostRecord]:
        targets = self._resolve_targets(
            source,
            organization,
            workspace_filters,
            tfe_token,
            tfe_address,
            cache_read_ok,
            cache_write_ok,
        )
        if not targets:
            Display().warning(f"workspace_filters matched zero workspaces in organization {organization!r}.")
            return []

        # Validate options once with a placeholder workspace_id; per-workspace
        # options are derived from this base in the worker.
        base_options = dict(source_options)
        base_options["workspace_id"] = targets[0][0]
        base_options["organization"] = None
        base_options["workspace"] = None
        source_cls.validate_options(base_options)

        # Pre-read every per-workspace cache blob on the main thread. Cache
        # plugins are not documented thread-safe; this also keeps the worker
        # signature simple.
        pre_blobs: Dict[str, Optional[Dict[str, Any]]] = {}
        for ws_id, _ws_name in targets:
            pre_blobs[ws_id] = self._read_per_workspace_cache(source, ws_id) if cache_read_ok else None

        def _fetch_one(ws_id: str, ws_name: str) -> Dict[str, Any]:
            return _fetch_workspace_records(
                ws_id=ws_id,
                ws_name=ws_name,
                source_options=source_options,
                source_cls=source_cls,
                tfe_token=tfe_token,
                tfe_address=tfe_address,
                cached_blob=pre_blobs.get(ws_id),
                validate_sv=validate_sv,
            )

        display = Display()

        def _emit_worker_error(ws_id: str, ws_name: str, exc: BaseException) -> None:
            """Route per-workspace failures to the right severity.

            Workspaces with no applied state are common in filter mode (bootstrap
            workspaces, never-applied workspaces) — those are not failures from
            the operator's perspective, so they go to verbose-only output.
            Real errors (auth, permission, network, etc.) stay as warnings.
            """
            msg = str(exc)
            if "no current state version" in msg.lower() or "no applied runs" in msg.lower():
                display.vvv(f"skipping workspace {ws_name} ({ws_id}): {msg}")
            else:
                display.warning(f"failed to fetch workspace {ws_name} ({ws_id}): {msg}")

        results: List[Dict[str, Any]] = []
        if enable_parallel and concurrency > 1:
            with ThreadPoolExecutor(max_workers=min(concurrency, _CONCURRENCY_MAX)) as pool:
                futures = {pool.submit(_fetch_one, ws_id, ws_name): (ws_id, ws_name) for ws_id, ws_name in targets}
                for fut in as_completed(futures):
                    try:
                        results.append(fut.result())
                    except Exception as exc:
                        ws_id, ws_name = futures[fut]
                        _emit_worker_error(ws_id, ws_name, exc)
        else:
            for ws_id, ws_name in targets:
                try:
                    results.append(_fetch_one(ws_id, ws_name))
                except Exception as exc:
                    _emit_worker_error(ws_id, ws_name, exc)

        all_records: List[HostRecord] = []
        for r in results:
            if r.get("warning"):
                _emit_worker_error(r["ws_id"], r["ws_name"], Exception(r["warning"]))
            if r.get("skipped"):
                continue
            for rec in r["records"]:
                # Records from cache-hits may already carry workspace_id; the
                # worker always restamps from the dispatch context, so this is
                # idempotent.
                rec["workspace_id"] = r["ws_id"]
                rec["workspace_name"] = r["ws_name"]
            all_records.extend(r["records"])
            if cache_write_ok and r.get("blob") is not None:
                self._write_per_workspace_cache(source, r["ws_id"], r["blob"])

        return all_records
