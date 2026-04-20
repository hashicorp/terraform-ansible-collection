# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
name: inventory
plugin_type: inventory
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
      - This should always be V(hashicorp.terraform.inventory).
    required: true
    type: str
    choices: [hashicorp.terraform.inventory]
  source:
    description:
      - Data source backend to use.
      - V(statefile) (default) downloads the latest Terraform state version
        from HCP Terraform via the pytfe SDK, parses the C(resources[])
        section, and produces one Ansible host per matching resource instance.
        Requires no Terraform CLI, no backend credentials.  Inventory
        candidates are selected by provider and resource type; see
        O(provider_mapping) to extend the defaults.
      - V(outputs) queries the HCP Terraform state version outputs API
        endpoint and builds hosts from workspace output values.  Lighter weight
        when only named output values are needed.  By default only dict and
        list-of-dict outputs produce hosts.  Use O(hosts_from) to handle
        primitive shapes such as scalars, list(string), and map(string).
      - V(search) is reserved for future implementation and will raise an
        error if selected.
    type: str
    choices: [statefile, outputs, search]
    default: statefile
  tfe_token:
    description:
      - HCP Terraform or Terraform Enterprise API token.
      - Falls back to the E(TFE_TOKEN) environment variable when not set.
    type: str
    no_log: true
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
      - When set, auto-detection is disabled; only the listed outputs are
        processed according to their declared V(kind) and V(element_type).
      - Accepts a single mapping or a list of mappings.  Each entry requires
        V(output) (the output name), V(kind) (top-level structure — one of
        V(scalar), V(list), V(map), V(object)), and V(element_type) (per-element
        type — one of V(string), V(number), V(bool), V(object), V(map)).
      - For primitive element types, V(use_as) assigns each element value
        directly to the named Ansible host variable (e.g. V(ansible_host)).
      - For V(kind=map) the map key becomes the resolved hostname; the
        V(hostnames) preference list has no further effect for those records.
        The special variable V(key) is always set to the map key.
      - V(kind=scalar) produces one host; the raw value is stored as V(value).
      - Has no effect for V(source=statefile).
    type: raw
    default: null
  hostnames:
    description:
      - Ordered preference list for resolving the inventory hostname.
      - Each element can be a plain string or a dict with keys C(name)
        (required), C(prefix) (optional), and C(separator) (default V(_)).
      - For V(source=statefile):
        - A plain string is looked up in the resource instance attributes.
          Use V(tag:Name) to read the value of the V(Name) tag, or
          V(tag:Name=Value) to produce V(Name_Value) only when that exact
          tag value matches.
        - Fallback: V(<resource_type>_<resource_name>[_<index>]).
      - For V(source=outputs):
        - A plain string is matched against the output value mapping.
          Use the special token V(output_name) to use the Terraform output
          name itself.
        - Fallback: V(<workspace_name>_<output_name>[_<index>]).
    type: list
    elements: raw
    default: []
  include_filters:
    description:
      - List of key-value dicts. A host is included only when its variables
        match at least one dict (all key-value pairs within a given dict must
        match). An empty list means all hosts are included.
    type: list
    elements: dict
    default: []
  exclude_filters:
    description:
      - List of key-value dicts. A host is excluded when its variables match
        any dict (all key-value pairs within a given dict must match).
        Exclusion is evaluated before O(include_filters).
    type: list
    elements: dict
    default: []
"""

EXAMPLES = r"""
# ── statefile source (default) ────────────────────────────────────────────────

# Minimal: token from TFE_TOKEN, workspace by organization + name.
# Produces one host per matching resource instance (aws_instance, etc.)
# with all Terraform attributes as host vars.
- name: Build inventory from latest HCP Terraform state
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace

# Workspace by direct ID (avoids an extra org lookup)
- name: Inventory from workspace ID
  plugin: hashicorp.terraform.inventory
  source: statefile
  workspace_id: ws-xxxxxxxxxxxxxxxx

# Use the instance's public_ip as ansible_host
- name: Set ansible_host from public_ip
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  compose:
    ansible_host: public_ip

# Hostname from the value of the 'Name' tag
- name: Tag-based hostname
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  hostnames:
    - tag:Name       # e.g. tags = {Name = "web-1"} → host "web-1"

# Hostname with environment prefix from tags
- name: Prefixed hostname from tags
  plugin: hashicorp.terraform.inventory
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
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  hostnames:
    - public_dns     # e.g. "ec2-1-2-3-4.compute-1.amazonaws.com"
    - public_ip      # fallback to public_ip if DNS is empty

# Group by instance_state attribute (running / stopped / terminated)
- name: Group by instance state
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  keyed_groups:
    - key: instance_state
      prefix: state
  # Produces groups: state_running, state_stopped, etc.

# Include only running instances
- name: Filter to running instances
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  include_filters:
    - instance_state: running

# Also include child-module resources
- name: Include resources from child modules
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  search_child_modules: true

# Add DigitalOcean droplets (custom provider mapping)
- name: DigitalOcean inventory
  plugin: hashicorp.terraform.inventory
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
  plugin: hashicorp.terraform.inventory
  source: statefile
  tfe_address: https://terraform.example.com
  organization: my-org
  workspace: my-workspace

# ── outputs source ────────────────────────────────────────────────────────────

# Build inventory from workspace outputs (dict/list-of-dict values only)
- name: Inventory from workspace outputs API
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace
  compose:
    ansible_host: public_ip

# Hostname from the output name itself
- name: Use Terraform output name as hostname
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace
  hostnames:
    - output_name

# Exclude staging hosts from outputs inventory
- name: Exclude staging from outputs
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace
  exclude_filters:
    - env: staging

# ── hosts_from: handle primitive and map-keyed output shapes ─────────────────

# list(string) output → one auto-named host per IP; IP assigned to ansible_host
# Terraform: output "instance_ips" { value = aws_instance.ec2[*].public_ip }
# Hosts: my-ws_instance_ips_0, my-ws_instance_ips_1, …
- name: Inventory from list-of-string IPs
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: instance_ips
    kind: list
    element_type: string
    use_as: ansible_host

# Use the IP value itself as the hostname
- name: IP-as-hostname from list(string)
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: instance_ips
    kind: list
    element_type: string
    use_as: ansible_host
  hostnames:
    - ansible_host    # e.g. "52.10.0.1" becomes the Ansible hostname

# map(string) → key = hostname, string value → ansible_host
# Terraform: output "host_map" { value = { "web-1" = "1.2.3.4", "web-2" = "5.6.7.8" } }
- name: Map-keyed IP inventory
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: host_map
    kind: map
    element_type: string
    use_as: ansible_host

# map(object) → key = hostname, object value = host variables (best structured format)
# Terraform: output "ec2_hosts" { value = { "web-1" = { public_ip = "…", env = "prod" } } }
- name: Structured map-keyed inventory
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    output: ec2_hosts
    kind: map
    element_type: object
  compose:
    ansible_host: public_ip

# Multiple outputs combined — hosts_from accepts a list of specs
- name: Multi-output inventory
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace
  hosts_from:
    - output: web_hosts
      kind: map
      element_type: object
    - output: db_ips
      kind: list
      element_type: string
      use_as: ansible_host
"""

from typing import Any, Dict, Iterable, List, Optional

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.module_utils._text import to_text
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable

from ansible_collections.hashicorp.terraform.plugins.inventory.utils.base import HostRecord
from ansible_collections.hashicorp.terraform.plugins.inventory.utils.common import get_preferred_hostname, passes_filters
from ansible_collections.hashicorp.terraform.plugins.inventory.utils.factory import get_source_backend
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformTokenNotFoundError


class InventoryModule(BaseInventoryPlugin, Constructable):  # type: ignore[misc]
    NAME = "hashicorp.terraform.inventory"

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

    def _build_client(self, tfe_token: str, tfe_address: str) -> TerraformClient:
        try:
            return TerraformClient(tfe_token=tfe_token, tfe_address=tfe_address)
        except TerraformTokenNotFoundError as exc:
            raise AnsibleParserError(f"Authentication error: {exc}") from exc

    def _sanitize_hostname(self, hostname: str) -> str:
        txt = to_text(hostname)
        if ":" in txt:
            return str(self._sanitize_group_name(txt))
        return str(txt)

    def _add_host(
        self,
        hostname: str,
        host_vars: Dict[str, Any],
        compose: Dict[str, str],
        keyed_groups: List[Dict[str, Any]],
        groups: Dict[str, Any],
        strict: bool,
    ) -> None:
        hostname = self._sanitize_hostname(hostname)
        self.inventory.add_host(hostname)
        for key, value in host_vars.items():
            self.inventory.set_variable(hostname, key, value)
        self._set_composite_vars(compose, host_vars, hostname, strict=strict)
        self._add_host_to_keyed_groups(keyed_groups, host_vars, hostname, strict=strict)
        self._add_host_to_composed_groups(groups, host_vars, hostname, strict=strict)

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
    ) -> None:
        """Apply filtering and register each record as an Ansible host.

        Sources that perform their own hostname resolution (e.g.
        ``StatefileSource``) pre-populate ``resolved_hostname`` on each record.
        When that key is present it is used directly; otherwise the
        outputs-style ``get_preferred_hostname`` fallback applies.
        """
        for record in records:
            host_vars: Dict[str, Any] = record["host_vars"]

            if not passes_filters(host_vars, include_filters, exclude_filters):
                continue

            if "resolved_hostname" in record:
                hostname: Optional[str] = record["resolved_hostname"]
            else:
                output_name: str = record["output_name"]
                workspace_name: str = record["workspace_name"]
                index = record.get("index")
                hostname = get_preferred_hostname(
                    output_name, workspace_name, host_vars, hostnames, index
                )

            if hostname:
                self._add_host(hostname, host_vars, compose, keyed_groups, groups, strict)

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
        }

        if not tfe_token:
            raise AnsibleParserError(
                "A Terraform API token is required. "
                "Set 'tfe_token' in the inventory config or the TFE_TOKEN environment variable."
            )

        try:
            source_cls = get_source_backend(source)
            source_cls.validate_options(source_options)

            client = self._build_client(tfe_token, tfe_address)
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
            )
        except (AnsibleParserError, AnsibleError):
            raise
        except TerraformTokenNotFoundError as exc:
            raise AnsibleParserError(f"Authentication error: {exc}") from exc
        except Exception as exc:
            raise AnsibleParserError(
                f"Failed to build inventory from HCP Terraform: {exc}"
            ) from exc
