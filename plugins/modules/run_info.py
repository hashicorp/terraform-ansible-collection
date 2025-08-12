# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: run_info
version_added: 1.0.0
short_description: Retrieve information about a run in Terraform Enterprise/Cloud.
author: "Abhishek Chaudhary (@abchaudh)"
description:
  - This module retrieves information about a given run in Terraform Enterprise/Cloud.
  - If I(run_id) is provided, the module will return information about that specific run.
  - If the run does not exist, the module will fail with an error message.
extends_documentation_fragment: hashicorp.terraform.common
options:
  run_id:
    description:
      - The unique identifier of the run to retrieve information about.
    type: str
    required: true
"""
EXAMPLES = r"""
- name: Retrieve information about a run by ID
  hashicorp.terraform.run_info:
    run_id: "run-sample-12345"
  register: run_info
"""

RETURN = r"""
run:
  type: dict
  description: A dictionary containing the run information.
  returned: on success
  contains:
    id:
      type: str
      returned: always
      description: The unique identifier of the run.
      sample: "run-sample-12345"
    type:
      type: str
      returned: always
      description: The type of the resource (always "runs").
      sample: "runs"
    attributes:
      type: dict
      returned: always
      description: The attributes of the run.
    relationships:
      type: dict
      returned: always
      description: Relationships to other resources.
    links:
      type: dict
      returned: always
      description: Links related to the run.
      contains:
        self:
          type: str
          returned: always
          description: API endpoint for this run.
"""
