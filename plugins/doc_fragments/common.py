# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


class ModuleDocFragment:
    # Common parameters for all hashicorp.terraform modules
    # Use this with extends_doc_fragments: hashicorp.terraform.common
    DOCUMENTATION = r"""
options:
  tf_token:
    description:
      - The Terraform Enterprise/Cloud authentication token.
      - See the HCP documentation for more information about authentication tokens
        U(https://developer.hashicorp.com/terraform/cloud-docs/api-docs#authentication).
      - If this value is not set, the environment variable C(TF_TOKEN) environment variables will be tried.
      - If the environment variable is also unset, an exception will be raised and the task will fail.
      - The user should ensure that token being used has the correct permissions to perform the operations requested through the Ansible task.
    type: str
  tf_hostname:
    description:
      - The Terraform Enterprise hostname.
      - If this value is not set, the environment variable C(TF_HOSTNAME) environment variables will be tried.
      - If the environment variable is also unset, this will default to U(https://app.terraform.io).
    type: str
    default: "https://app.terraform.io"
  tf_validate_certs:
    description:
      - Determines whether to allow insecure connections to Terraform Enterprise/Cloud.
      - If C(no), SSL certificates will not be validated.
      - If this value is not set, the environment variable C(TF_VALIDATE_CERTS) environment variables will be tried.
      - If the environment variable is also unset, certificates will be validated.
    type: bool
    default: True
  tf_max_retries:
    description:
      - Specifies the total number of retries to allow for a request to TFE/C.
      - If this value is not set, the environment variable C(TF_MAX_RETRIES) will be tried.
      - If the environment variable is also unset, by default C(3) retries will be performed.
    type: int
    default: 3
  tf_timeout:
    description:
      - Specifies the timeout (in seconds) Ansible should use for requests sent to TFE/C.
      - If this value is not set, the environment variable C(TF_TIMEOUT) will be used.
      - If the environment variable is also unset, this value will default to 10s.
    type: int
    default: 10
notes:
  - B(Caution:) When run against a remote host, environment variables and files will be
    read from the Ansible 'host' context and not the 'controller' context.
    As such, files may need to be explicitly copied to the 'host' before the task is executed.
"""
