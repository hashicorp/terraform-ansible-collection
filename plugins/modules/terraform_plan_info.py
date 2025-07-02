#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Red Hat <redhat@redhat.com>
# GNU General Public License v3.0+ (see COPYING or 
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: plan_info
version_added: "1.0.0"
short_description: Retrieve information about Terraform Cloud/Enterprise plans
description:
  - This module retrieves information about a Terraform execution plan from HashiCorp Terraform Cloud/Enterprise.
  - It can be used to check plan status, resource changes, and execution details.
  - Supports both Terraform Cloud and Terraform Enterprise deployments.
options:
  plan_id:
    description:
      - The ID of the plan to retrieve information for.
      - Plan IDs can be found in the relationships.plan property of a run object.
    type: str
    aliases: ['id']
extends_documentation_fragment:
  - hashicorp.terraform.auth
"""

EXAMPLES = r"""
- name: Retrieve plan information
  hashicorp.terraform.terraform_plan_info:
    plan_id: "plan-8F5JFydVYAmtTjET"
    token: "{{ tf_token }}"
  register: plan_result

- name: Display plan status
  debug:
    msg: "Plan status: {{ plan_result.plan_info.status }}"

- name: Check if plan has changes
  debug:
    msg: "Plan has changes: {{ plan_result.plan_info.has_changes }}"

- name: Show resource summary
  debug:
    msg: >
      Resources: +{{ plan_result.plan_info.resource_additions }}
      ~{{ plan_result.plan_info.resource_changes }}
      -{{ plan_result.plan_info.resource_destructions }}

- name: Access detailed plan via JSON output URL
  uri:
    url: "{{ tf_hostname }}{{ plan_result.plan_info.links['json_output'] }}"
    headers:
      Authorization: "Bearer {{ tf_token }}"
  when: plan_result.plan_info.has_changes
"""

RETURN = r"""
plan_info:
  type: dict
  description: Complete information about the Terraform plan
  returned: always
  contains:
    id:
      type: str
      description: The unique identifier of the plan
      returned: always
    status:
      type: str
      description: Current status of the plan execution (pending, managed_queued, queued, running, errored, canceled, finished, unreachable)
      returned: always
    has_changes:
      type: bool
      description: Whether the plan contains any changes to infrastructure
      returned: always
    generated_configuration:
      type: bool
      description: Whether the plan includes generated configuration
      returned: always
    resource_additions:
      type: int
      description: Number of resources to be created
      returned: always
    resource_changes:
      type: int
      description: Number of resources to be modified
      returned: always
    resource_destructions:
      type: int
      description: Number of resources to be destroyed
      returned: always
    resource_imports:
      type: int
      description: Number of resources to be imported
      returned: always
    structured_run_output_enabled:
      type: bool
      description: Whether structured run output is enabled for this plan
      returned: always
    execution_details:
      type: dict
      description: Details about how the plan was executed
      returned: always
      contains:
        mode:
          type: str
          description: Execution mode used for the plan (remote, agent, or local)
          returned: always
        agent_id:
          type: str
          description: ID of the agent used (only present when mode is 'agent')
          returned: when mode is 'agent'
        agent_name:
          type: str
          description: Name of the agent used (only present when mode is 'agent')
          returned: when mode is 'agent'
        agent_pool_id:
          type: str
          description: ID of the agent pool used (only present when mode is 'agent')
          returned: when mode is 'agent'
        agent_pool_name:
          type: str
          description: Name of the agent pool used (only present when mode is 'agent')
          returned: when mode is 'agent'
    status_timestamps:
      type: dict
      description: Important timestamps in the plan lifecycle
      returned: always
      contains:
        agent_queued_at:
          type: str
          description: When the plan was queued for agent execution
          returned: when available
        started_at:
          type: str
          description: When the plan execution started
          returned: when available
        finished_at:
          type: str
          description: When the plan execution completed
          returned: when available
    log_read_url:
      type: str
      description: URL to read the plan execution logs
      returned: always
    actions:
      type: dict
      description: Available actions for this plan
      returned: always
      contains:
        is_exportable:
          type: bool
          description: Whether the plan can be exported
          returned: always
    permissions:
      type: dict
      description: User permissions for this plan
      returned: always
      contains:
        can_export:
          type: bool
          description: Whether the user can export this plan
          returned: always
    links:
      type: dict
      description: Related API endpoints
      returned: always
      contains:
        self:
          type: str
          description: API endpoint for this plan
          returned: always
        json_output:
          type: str
          description: API endpoint for JSON output
          returned: always
        json_output_redacted:
          type: str
          description: API endpoint for redacted JSON output
          returned: always
        json_schema:
          type: str
          description: API endpoint for JSON schema
          returned: always
changed:
  type: bool
  description: Whether any changes were made (always False for info modules)
  returned: always
failed:
  type: bool
  description: Whether the module execution failed
  returned: always
"""