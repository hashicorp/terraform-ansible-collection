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
  - V(statefile) (default) downloads the raw Terraform state file and reads
    its C(outputs) section.
  - V(outputs) queries the HCP Terraform state version outputs API endpoint,
    the lighter-weight path when only named output values are needed.
  - V(search) is reserved for a future release.
  - Uses a YAML configuration file whose name ends with C(inventory.yml),
    C(inventory.yaml), C(terraform_inventory.yml), or
    C(terraform_inventory.yaml).
  - Does not require the Terraform CLI.
  - For both V(statefile) and V(outputs):
    - Each workspace output whose value is a mapping produces one host, with
      the mapping's keys as host variables.
    - Each workspace output whose value is a list of mappings produces one
      host per list element, indexed as
      V(<workspace>_<output>_0), V(<workspace>_<output>_1), etc.
    - Outputs whose values are neither mappings nor lists of mappings are
      silently skipped.
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
      - V(statefile) (default) downloads the raw Terraform state file
        (C(.tfstate) JSON) from HCP Terraform and reads its C(outputs)
        section directly.  Works even when the outputs API endpoint is
        unavailable or when you need access to the full state structure.
      - V(outputs) queries the HCP Terraform state version outputs API
        endpoint.  This is the faster, lighter-weight path when only
        named output values are required.
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
      - Required together with O(workspace) unless O(workspace_id) is
        provided.
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
  hostnames:
    description:
      - Ordered preference list for resolving the inventory hostname.
      - Each element is either a plain string or a dict with sub-keys C(name),
        C(prefix) (optional), and C(separator) (default V(_)).
      - A plain string is matched against the host's variable dict; when the
        key exists its value is used as the hostname.
      - Use the literal value V(output_name) to use the Terraform output name.
      - When a dict entry is used, C(name) and C(prefix) follow the same
        resolution rules as a plain string, and the final hostname becomes
        V(<prefix><separator><name>).
      - If no preference resolves to a non-empty string the hostname defaults
        to V(<workspace_name>_<output_name>) for mapping outputs or
        V(<workspace_name>_<output_name>_<index>) for list outputs.
    type: list
    elements: raw
    default: []
  search_child_modules:
    description:
      - Reserved for future use. Currently has no effect.
    type: bool
    default: false
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
# Minimal — statefile source, workspace by organization + name; token from TFE_TOKEN
- name: Build inventory from downloaded state file
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace

# Use the outputs API instead of downloading the state file
- name: Build inventory from workspace outputs API
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace

# Workspace identified by ID; explicit token
- name: Build inventory from workspace ID (statefile)
  plugin: hashicorp.terraform.inventory
  source: statefile
  tfe_token: "{{ lookup('env', 'TFE_TOKEN') }}"
  workspace_id: ws-xxxxxxxxxxxxxxxx

# Given a Terraform workspace that publishes:
#
#   output "web_server" {
#     value = {
#       name       = "web-1"
#       public_ip  = "1.2.3.4"
#       private_ip = "10.0.0.1"
#       env        = "prod"
#     }
#   }
#
# Running: ansible-inventory -i inventory.yml --graph --vars
#
# @all:
# |--@ungrouped:
# |  |--my-workspace_web_server
# |  |  |--{env = prod}
# |  |  |--{name = web-1}
# |  |  |--{private_ip = 10.0.0.1}
# |  |  |--{public_ip = 1.2.3.4}

# Use compose to derive ansible_host from an output field
- name: Set ansible_host from public_ip
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  compose:
    ansible_host: public_ip

# Use the 'name' field inside each output value as the inventory hostname
- name: Hostname from output field
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  hostnames:
    - name

# Use the Terraform output name itself as the hostname
- name: Hostname is the output name
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  hostnames:
    - output_name

# Hostname with prefix and custom separator
- name: Prefixed hostname
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace
  hostnames:
    - name: public_ip
      prefix: env
      separator: "-"
  # Produces: prod-1.2.3.4

# Group hosts dynamically by a variable value
- name: Group by environment
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  keyed_groups:
    - key: env
      prefix: env
  # Produces groups: env_prod, env_staging, etc.

# Group using a Jinja2 conditional expression
- name: Group production hosts
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace
  groups:
    production: env == 'prod'

# Include only production hosts
- name: Filter to production
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  include_filters:
    - env: prod

# Exclude staging hosts
- name: Exclude staging
  plugin: hashicorp.terraform.inventory
  source: outputs
  organization: my-org
  workspace: my-workspace
  exclude_filters:
    - env: staging

# A list-typed Terraform output expands to one host per element:
#
#   output "web_servers" {
#     value = [
#       { name = "web-1", public_ip = "1.2.3.4" },
#       { name = "web-2", public_ip = "1.2.3.5" },
#     ]
#   }
#
# Produces: my-workspace_web_servers_0, my-workspace_web_servers_1
- name: List output to multiple hosts
  plugin: hashicorp.terraform.inventory
  source: statefile
  organization: my-org
  workspace: my-workspace
  hostnames:
    - name   # resolves to web-1 and web-2 respectively

# Target a self-hosted Terraform Enterprise instance
- name: TFE instance
  plugin: hashicorp.terraform.inventory
  source: outputs
  tfe_address: https://terraform.example.com
  organization: my-org
  workspace: my-workspace
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
        for record in records:
            output_name: str = record["output_name"]
            workspace_name: str = record["workspace_name"]
            host_vars: Dict[str, Any] = record["host_vars"]
            index: Optional[int] = record.get("index")

            if not passes_filters(host_vars, include_filters, exclude_filters):
                continue

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
        self._read_config_data(path)

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
