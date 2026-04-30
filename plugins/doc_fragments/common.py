# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


class ModuleDocFragment:
    # Common parameters for all hashicorp.terraform modules
    # Use this with extends_doc_fragments: hashicorp.terraform.common
    DOCUMENTATION = r"""
options:
  tfe_token:
    description:
      - The Terraform Enterprise/Cloud authentication token.
      - See the HCP documentation for more information about authentication tokens
        U(https://developer.hashicorp.com/terraform/cloud-docs/api-docs#authentication).
      - If this value is not set, the environment variable C(TFE_TOKEN) will be tried.
      - If the environment variable is also unset, an exception will be raised and the task will fail.
      - The user should ensure that token being used has the correct permissions to perform the operations requested through the Ansible task.
      - The C(tf_token) alias is kept for compatibility with older collection releases.
    type: str
    required: true
    aliases:
      - tf_token
  tfe_address:
    description:
      - The Terraform Enterprise/Cloud API address.
      - If this value is not set, the environment variable C(TFE_ADDRESS) will be tried.
      - If the environment variable is also unset, this will default to U(https://app.terraform.io).
    type: str
    default: "https://app.terraform.io"
  tfe_timeout:
    description:
      - HTTP request timeout in seconds used by the underlying pytfe SDK.
      - Falls back to the C(TFE_TIMEOUT) environment variable when not set.
    type: float
    default: 30.0
  tfe_verify_tls:
    description:
      - Whether to verify TLS certificates when talking to the Terraform Enterprise/Cloud API.
      - Set to C(false) to skip verification for self-signed Terraform Enterprise deployments (not recommended for production).
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
      - Useful when connecting to a Terraform Enterprise instance that uses a private/internal CA.
      - Falls back to the C(SSL_CERT_FILE) environment variable when not set.
    type: path
  tfe_proxies:
    description:
      - HTTP/HTTPS proxy URL passed through to the pytfe SDK.
      - Accepts any value understood by the underlying HTTP transport (for example C(http://proxy.internal:3128)).
    type: str
notes:
  - B(Caution:) When run against a remote host, environment variables and files will be
    read from the Ansible 'host' context and not the 'controller' context.
    As such, files may need to be explicitly copied to the 'host' before the task is executed.
"""
