# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
name: tf_org_tags
short_description: List organization tags in Terraform Cloud/Enterprise
version_added: "2.1.0"
author: "Sivaselvan I (@isivaselvan)"
description:
  - Retrieve all organization-scoped tags from HashiCorp Terraform Cloud or Terraform Enterprise.
  - Returns a list of tag objects, each containing C(id), C(name), and C(instance_count).
  - Optionally filter results by partial tag name using the I(query) parameter.
options:
  organization:
    description:
      - Name of the organization to list tags from.
    type: str
    required: true
  query:
    description:
      - Partial name string used to filter returned tags.
      - Only tags whose name contains the query string are returned.
      - Maps to the C(?q=) URL parameter on the HCP Terraform API.
    type: str
  filter_exclude_taggable_id:
    description:
      - ID of a workspace (or other taggable resource) whose already-associated tags
        should be excluded from the results.
      - Useful for discovering which organization tags are not yet applied to a given
        workspace — for example, to populate a list of available tags before calling
        the M(hashicorp.terraform.organization_tags) module.
      - Maps to the C(?filter[exclude][taggable][id]=) URL parameter on the HCP Terraform API.
    type: str
  tfe_address:
    description:
      - Terraform Cloud/Enterprise API address.
      - Falls back to the C(TFE_ADDRESS) environment variable when not set.
      - Defaults to C(https://app.terraform.io) for HCP Terraform.
    type: str
    default: https://app.terraform.io
  tfe_token:
    description:
      - Terraform Cloud/Enterprise API token.
      - Falls back to the C(TFE_TOKEN) environment variable when not set.
      - The C(tf_token) alias is kept for compatibility with older collection releases.
    type: str
    required: false
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
      - Set to I(false) to disable certificate verification for self-signed Terraform Enterprise
        deployments (not recommended for production).
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
- name: List all organization tags
  ansible.builtin.set_fact:
    all_tags: "{{ lookup('hashicorp.terraform.tf_org_tags', organization='my-org', tfe_token=my_token) }}"

- name: Filter tags by partial name
  ansible.builtin.set_fact:
    env_tags: "{{ lookup('hashicorp.terraform.tf_org_tags', organization='my-org', query='env', tfe_token=my_token) }}"

- name: Assert a specific tag exists
  ansible.builtin.assert:
    that:
      - all_tags | selectattr('name', 'equalto', 'env:prod') | list | length == 1

- name: Find tags not yet on a specific workspace
  ansible.builtin.set_fact:
    available_tags: "{{ lookup('hashicorp.terraform.tf_org_tags', organization='my-org',
                               filter_exclude_taggable_id='ws-abc123', tfe_token=my_token) }}"
"""

RETURN = r"""
  _list:
    description: List of tag objects from the organization.
    type: list
    elements: dict
    contains:
      id:
        description: Opaque tag identifier.
        type: str
        sample: "tag-abc123"
      name:
        description: Human-readable tag name.
        type: str
        sample: "env:prod"
      instance_count:
        description: Number of workspaces that carry this tag.
        type: int
        sample: 3
"""

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.organization_tags import list_organization_tags


class LookupModule(LookupBase):
    """Lookup plugin that lists organization tags from HCP Terraform / Terraform Enterprise."""

    def run(self, terms, variables=None, **kwargs):
        """Return a single-element list whose sole item is the list of tag dicts."""
        organization = kwargs.get("organization")
        if not organization:
            raise AnsibleError("'organization' is required for tf_org_tags lookup")

        query = kwargs.get("query")
        filter_exclude_taggable_id = kwargs.get("filter_exclude_taggable_id")

        try:
            with TerraformClient.from_mapping(kwargs) as adapter:
                tags = list_organization_tags(adapter, organization, query, filter_exclude_taggable_id)
        except Exception as e:
            raise AnsibleError(f"tf_org_tags lookup failed: {str(e)}")

        return [tags]
