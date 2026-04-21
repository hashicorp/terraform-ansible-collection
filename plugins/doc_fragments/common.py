# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
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
      - If this value is not set, the environment variable C(TFE_TOKEN) environment variables will be tried.
      - If the environment variable is also unset, an exception will be raised and the task will fail.
      - The user should ensure that token being used has the correct permissions to perform the operations requested through the Ansible task.
    type: str
    aliases:
      - tf_token
  tfe_address:
    description:
      - The Terraform Enterprise/Cloud API address.
      - If this value is not set, the environment variable C(TFE_ADDRESS) will be tried.
      - If the environment variable is also unset, this will default to U(https://app.terraform.io).
    type: str
    default: "https://app.terraform.io"
notes:
  - B(Caution:) When run against a remote host, environment variables and files will be
    read from the Ansible 'host' context and not the 'controller' context.
    As such, files may need to be explicitly copied to the 'host' before the task is executed.
"""
