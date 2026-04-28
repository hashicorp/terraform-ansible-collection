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
  - Does not support caching.
extends_documentation_fragment:
  - constructed
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
        when only named output values are needed.  By default only dict and
        list-of-dict outputs produce hosts.  Use O(hosts_from) to handle
        primitive shapes such as scalars, list(string), and map(string).
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
      - When set, plugin-level dynamic-detection is disabled; only the listed
        outputs are processed, each according to its declared V(type).
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
        declare V(type: map(string)) explicitly when you want the map semantics."
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

# Build inventory from workspace outputs (dict/list-of-dict values only)
- name: Inventory from workspace outputs API
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  compose:
    ansible_host: public_ip

# Hostname from the output name itself
- name: Use Terraform output name as hostname
  plugin: hashicorp.terraform.tfc_inv
  source: outputs
  organization: my-org
  workspace: my-workspace
  hostnames:
    - output_name

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
"""

from typing import Any, Dict, Iterable, List, Optional

from ansible.errors import AnsibleParserError
from ansible.module_utils._text import to_text
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable
from ansible.utils.display import Display

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError, TerraformTokenNotFoundError
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources import outputs as _outputs_module
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.base import HostRecord
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common import get_preferred_hostname, passes_filters
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.factory import get_source_backend


def _wire_outputs_display() -> None:
    """Wire the controller's Display into the outputs source backend so its
    hosts_from validation/dynamic-detection warnings surface to the user."""
    display = Display()
    _outputs_module._warn = display.warning
    _outputs_module._debug = display.vvv


_wire_outputs_display()


class InventoryModule(BaseInventoryPlugin, Constructable):  # type: ignore[misc]
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
    # idiom.
    _PLUGIN_INJECTED_VARS = frozenset({"ansible_host", "value"})

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
    ) -> None:
        """Apply filtering and register each record as an Ansible host.

        Sources that perform their own hostname resolution (e.g.
        ``StatefileSource``) pre-populate ``resolved_hostname`` on each record.
        When that key is present it is used directly; otherwise the
        outputs-style ``get_preferred_hostname`` fallback applies.
        """
        for record in records:
            host_vars: Dict[str, Any] = record["host_vars"]
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

            if hostname:
                self._add_host(
                    hostname,
                    host_vars,
                    resolution_view,
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

        source_options: Dict[str, Any] = {
            "workspace_id": self.get_option("workspace_id"),
            "organization": self.get_option("organization"),
            "workspace": self.get_option("workspace"),
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

        try:
            source_cls = get_source_backend(source)
            source_cls.validate_options(source_options)

            with self._build_client({"tfe_token": tfe_token, "tfe_address": tfe_address}) as client:
                records = source_cls(client, source_options).collect_hosts()

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
                )
        except TerraformError as exc:
            raise AnsibleParserError(str(exc)) from exc
        except TerraformTokenNotFoundError as exc:
            raise AnsibleParserError(f"Authentication error: {exc}") from exc
        except Exception as exc:
            raise AnsibleParserError(f"Failed to build inventory from HCP Terraform: {exc}") from exc
