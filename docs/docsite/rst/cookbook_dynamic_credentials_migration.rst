.. _ansible_collections.hashicorp.terraform.docsite.cookbook_dynamic_credentials_migration:

*********************************************
Migrate a workspace to dynamic credentials
*********************************************

This cookbook migrates an AWS-backed HCP Terraform workspace from long-lived access keys to
run-specific credentials obtained through workload identity.

.. code-block:: text

   cloud OIDC trust -> HCP variable set -> remove static workspace keys -> speculative run
                                                                       | pass
                                                                       v
                                                               retain dynamic auth
                                                                       | fail
                                                                       v
                                                        detach set + restore protected keys

Use the corresponding HCP Terraform environment variables and cloud trust for Azure, GCP, Vault,
Kubernetes, or another supported provider.

.. important::

   The collection's ``aws_oidc_configuration``, ``azure_oidc_configuration``,
   ``gcp_oidc_configuration``, and ``vault_oidc_configuration`` modules manage OIDC records for
   HYOK. They are not generic dynamic-provider-credential modules. Generic provider credentials
   are configured through cloud-side trust plus HCP Terraform workspace or variable-set values.

.. contents::
   :local:
   :depth: 2

Prerequisites
=============

- Configure the cloud-side OIDC identity provider, trust policy, and least-privilege role before
  running the playbook. Use the relevant AWS/Azure/GCP/Vault Ansible collection to manage that
  side declaratively.
- Restrict the trust policy by HCP Terraform organization, project, workspace, and run phase where
  appropriate.
- Keep the legacy credentials in an encrypted Automation Controller credential or Ansible Vault
  until the migration succeeds. Terraform never returns sensitive variable values.
- Pause normal runs on the canary workspace while credentials are changing.
- The HCP Terraform token needs permission to manage variable sets and workspace variables and to
  queue speculative runs.

Example protected input
=======================

The following values should come from protected credentials, not a plaintext variables file:

.. code-block:: yaml

   terraform_organization: acme
   canary_workspace: payments-dev
   aws_run_role_arn: arn:aws:iam::111122223333:role/hcp-terraform-payments-dev
   legacy_aws_access_key_id: "{{ vault_legacy_aws_access_key_id }}"
   legacy_aws_secret_access_key: "{{ vault_legacy_aws_secret_access_key }}"
   run_poll_timeout: 900

Complete canary migration
=========================

Save this as ``migrate-dynamic-credentials.yml``:

.. code-block:: yaml

   ---
   - name: Migrate one HCP Terraform workspace to AWS dynamic credentials
     hosts: localhost
     connection: local
     gather_facts: false
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Resolve the canary workspace
         hashicorp.terraform.workspace_info:
           organization: "{{ terraform_organization }}"
           workspace: "{{ canary_workspace }}"
         register: canary

       - name: Create and attach the dynamic-credentials variable set
         hashicorp.terraform.variable_sets:
           organization: "{{ terraform_organization }}"
           name: aws-dynamic-credentials-payments
           description: AWS workload identity for the payments workspaces
           global: false
           priority: true
           workspace_ids:
             - "{{ canary.workspace.id }}"
           state: present
         register: dynamic_set

       - name: Enable HCP Terraform AWS provider authentication
         hashicorp.terraform.variable:
           variable_set_id: "{{ dynamic_set.id }}"
           key: TFC_AWS_PROVIDER_AUTH
           value: "true"
           category: env
           description: Enable run-specific AWS credentials
           state: present

       - name: Configure the workload identity role
         hashicorp.terraform.variable:
           variable_set_id: "{{ dynamic_set.id }}"
           key: TFC_AWS_RUN_ROLE_ARN
           value: "{{ aws_run_role_arn }}"
           category: env
           description: Least-privilege role for plan and apply
           state: present

       - name: Remove the legacy access-key identifier from the workspace
         hashicorp.terraform.variable:
           workspace_id: "{{ canary.workspace.id }}"
           key: AWS_ACCESS_KEY_ID
           state: absent

       - name: Remove the legacy secret access key from the workspace
         hashicorp.terraform.variable:
           workspace_id: "{{ canary.workspace.id }}"
           key: AWS_SECRET_ACCESS_KEY
           state: absent

       - name: Test provider authentication with a speculative run
         hashicorp.terraform.run:
           workspace_id: "{{ canary.workspace.id }}"
           run_message: Validate AWS dynamic provider credentials
           plan_only: true
           poll: true
           poll_interval: 10
           poll_timeout: "{{ run_poll_timeout }}"
           state: present
         register: credential_test
         ignore_errors: true

       - name: Detach dynamic credentials after a failed test
         hashicorp.terraform.variable_sets:
           variable_set_id: "{{ dynamic_set.id }}"
           workspace_ids: []
           state: present
         when: credential_test.failed | default(false)

       - name: Restore the legacy access-key identifier after a failed test
         hashicorp.terraform.variable:
           workspace_id: "{{ canary.workspace.id }}"
           key: AWS_ACCESS_KEY_ID
           value: "{{ legacy_aws_access_key_id }}"
           category: env
           sensitive: true
           description: "Rollback credential {{ rollback_revision | default('1') }}"
           state: present
         no_log: true
         when: credential_test.failed | default(false)

       - name: Restore the legacy secret after a failed test
         hashicorp.terraform.variable:
           workspace_id: "{{ canary.workspace.id }}"
           key: AWS_SECRET_ACCESS_KEY
           value: "{{ legacy_aws_secret_access_key }}"
           category: env
           sensitive: true
           description: "Rollback credential {{ rollback_revision | default('1') }}"
           state: present
         no_log: true
         when: credential_test.failed | default(false)

       - name: Report the migration result
         ansible.builtin.assert:
           that:
             - not (credential_test.failed | default(false))
           success_msg: >-
             {{ canary_workspace }} authenticated through workload identity; its static
             AWS workspace variables remain absent.
           fail_msg: >-
             Dynamic authentication failed. The variable set was detached and the protected
             legacy credentials were restored. Inspect the speculative run before retrying.

Roll out safely
===============

After the canary succeeds, repeat the sequence in bounded batches:

#. Attach the same variable set to the exact approved workspace-ID list. Remember that
   ``variable_sets.workspace_ids`` reconciles the complete attachment list.
#. Remove legacy credentials from each workspace.
#. Queue a speculative run for every workspace and collect run IDs.
#. Detach failed workspaces and restore their own protected legacy credentials.
#. Remove the old credentials from the secret manager only after all workspaces have completed
   at least one successful plan and apply with dynamic credentials.

Use separate plan and apply roles when the cloud provider supports them. Test both phases before
retiring static access.

Idempotency and sensitive values
================================

Variable-set metadata and non-sensitive dynamic credential settings converge idempotently.
Sensitive variable values are write-only. The module cannot detect a value-only rotation, so the
rollback tasks change ``description`` with ``rollback_revision`` as an explicit rotation marker.

Never print variable results, cache sensitive facts, or place old keys in job artifacts. Once the
migration is stable, revoke the cloud access keys rather than merely deleting their Terraform
variables.

.. seealso::

   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_variables`
   - :ansplugin:`hashicorp.terraform.variable_sets#module`
   - :ansplugin:`hashicorp.terraform.variable#module`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_authentication`
