#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Collection-local copy of the project module for integration tests.
This mirrors plugins/modules/project.py at repository root so the collection
can be discovered by ansible-playbook when using ANSIBLE_COLLECTIONS_PATHS.
"""

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.project import (
    create_project,
    delete_project,
    get_project_by_id,
    get_project_tag_bindings,
    list_projects,
    update_project,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff

def main():
    module = AnsibleTerraformModule(
        argument_spec=dict(
            project_id=dict(type='str'),
            name=dict(type='str', aliases=['project']),
            organization=dict(type='str'),
            description=dict(type='str'),
            state=dict(type='str', choices=['present','absent'], default='present'),
            tag_bindings=dict(type='list', elements='dict')
        ),
        supports_check_mode=True,
    )

    # Create a Terraform client wrapper. Older module layouts may not provide
    # a `client` attribute on the wrapper object, so construct one explicitly
    # from the module parameters when needed.
    try:
        client = module.client
    except AttributeError:
        client = TerraformClient(**module.params)
    params = module.params

    # Validate required parameters early to avoid making API calls with
    # missing configuration. If `organization` is empty, fail with a clear
    # message guiding the user how to provide it (env var or extra-var).
    if params.get('state') == 'present' and not params.get('organization'):
        module.fail_json(msg=(
            "The 'organization' parameter is empty or undefined. "
            "Provide it via `-e organization=...` when running the playbook, "
            "or export TFC_ORGANIZATION in your environment."
        ))

    # Simple orchestration for integration tasks
    try:
        if params['state'] == 'present':
            if params.get('project_id'):
                result = update_project(
                    client,
                    params.get('project_id'),
                    name=params.get('name'),
                    description=params.get('description'),
                    tag_bindings=params.get('tag_bindings'),
                )
            else:
                result = create_project(
                    client,
                    params.get('organization'),
                    params.get('name'),
                    description=params.get('description'),
                    tag_bindings=params.get('tag_bindings'),
                )
            module.exit_json(changed=True, result=result)
        else:
            delete_project(client, params.get('project_id'))
            module.exit_json(changed=True)
    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == '__main__':
    main()
