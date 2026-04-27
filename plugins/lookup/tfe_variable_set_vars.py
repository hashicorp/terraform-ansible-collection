# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
name: tfe_variable_set_vars
short_description: Retrieve variables owned by a Terraform Cloud/Enterprise variable set
version_added: "2.0.0"
author: "Prabuddha Chakraborty (@iam404)"
description:
  - Returns the list of variables that belong to the given variable set.
  - Sensitive values are masked by default; pass I(display_sensitive=true) to return raw values.
  - Variables can optionally be resolved by (organization, name) when the variable set ID is not known.
options:
  variable_set_id:
    description:
      - The unique identifier of the variable set (e.g. C(varset-...)).
      - Mutually exclusive with I(name)/I(organization) lookup.
    type: str
  name:
    description:
      - The name of the variable set. Requires I(organization).
    type: str
  organization:
    description:
      - The organization that owns the variable set. Required with I(name).
    type: str
  display_sensitive:
    description:
      - When I(true), return raw values for sensitive variables.
      - When I(false) (default), sensitive values are replaced with C(<sensitive>).
    type: bool
    default: false
  tfe_address:
    description:
      - Terraform Cloud/Enterprise API address.
      - Falls back to the C(TFE_ADDRESS) environment variable when not set.
    type: str
    default: https://app.terraform.io
  tfe_token:
    description:
      - Terraform Cloud/Enterprise API token.
      - Falls back to the C(TFE_TOKEN) environment variable when not set.
      - The C(tf_token) alias is kept for compatibility with older collection releases.
    type: str
    required: true
    aliases: ['tf_token']
  tfe_timeout:
    description:
      - HTTP request timeout in seconds used by the underlying pytfe SDK.
      - Falls back to the C(TFE_TIMEOUT) environment variable when not set.
    type: float
    default: 30.0
  tfe_verify_tls:
    description:
      - Whether to verify TLS certificates when talking to the Terraform Cloud/Enterprise API.
      - Falls back to the C(TFE_VERIFY_TLS) environment variable when not set.
    type: bool
    default: true
  tfe_max_retries:
    description:
      - Maximum number of automatic retries the pytfe SDK performs for transient HTTP failures.
      - Falls back to the C(TFE_MAX_RETRIES) environment variable when not set.
    type: int
    default: 5
  tfe_ca_bundle:
    description:
      - Path to a CA bundle file used to verify TLS certificates.
      - Falls back to the C(SSL_CERT_FILE) environment variable when not set.
    type: path
  tfe_proxies:
    description:
      - HTTP/HTTPS proxy URL passed through to the pytfe SDK.
    type: str
"""

EXAMPLES = r"""
- name: Fetch platform defaults from a variable set
  ansible.builtin.debug:
    msg: "{{ lookup('hashicorp.terraform.tfe_variable_set_vars', variable_set_id='varset-abc123') }}"

- name: Fetch variables by variable-set name
  ansible.builtin.set_fact:
    platform_vars: "{{ lookup('hashicorp.terraform.tfe_variable_set_vars',
                             name='platform-defaults',
                             organization='my-org',
                             display_sensitive=false) }}"
"""

RETURN = r"""
_raw:
  description:
    - List of variable payloads owned by the variable set.
    - Each item contains at minimum I(id), I(key), I(value), I(category), I(sensitive), I(hcl).
    - Sensitive values are C(<sensitive>) unless I(display_sensitive=true).
  type: list
  elements: dict
"""

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.variable_set_variable import (
    list_variable_set_variables,
    mask_sensitive,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.variable_sets import get_variable_set_by_name


class LookupModule(LookupBase):
    def _resolve_variable_set_id(self, adapter, variable_set_id, name, organization):
        if variable_set_id:
            if name or organization:
                raise AnsibleError("variable_set_id is mutually exclusive with name/organization.")
            return variable_set_id
        if not (name and organization):
            raise AnsibleError("Either variable_set_id, or both name and organization, must be provided.")
        vs = get_variable_set_by_name(adapter, organization, name)
        if not vs:
            raise AnsibleError(f"Variable set {name!r} not found in organization {organization!r}.")
        return vs["id"]

    def run(self, terms, variables=None, **kwargs):
        variable_set_id = kwargs.get("variable_set_id")
        name = kwargs.get("name")
        organization = kwargs.get("organization")
        display_sensitive = bool(kwargs.get("display_sensitive", False))
        kwargs.setdefault("tfe_address", "https://app.terraform.io")

        try:
            with TerraformClient.from_mapping(kwargs) as adapter:
                vs_id = self._resolve_variable_set_id(adapter, variable_set_id, name, organization)
                variables_list = list_variable_set_variables(adapter, vs_id)
        except AnsibleError:
            raise
        except Exception as e:
            raise AnsibleError(f"tfe_variable_set_vars lookup failed: {e}")

        return mask_sensitive(variables_list, display_sensitive=display_sensitive)
