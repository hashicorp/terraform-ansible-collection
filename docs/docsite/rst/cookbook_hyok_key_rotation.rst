.. _ansible_collections.hashicorp.terraform.docsite.cookbook_hyok_key_rotation:

*********************************
Rotate an HCP Terraform HYOK key
*********************************

This cookbook configures a new AWS KMS key for HCP Terraform Hold Your Own Key encryption, tests
access through a private agent pool, makes the new configuration primary, and retires the old
configuration only after an explicit second approval.

.. code-block:: text

   new KMS key + OIDC role -> HCP OIDC record -> HYOK test -> new primary
                                                            -> verify -> revoke old -> delete old

The cloud-side KMS key, OIDC provider, IAM role, and trust policy are managed with AWS automation.
The modules in this collection manage the HCP Terraform-side OIDC and HYOK records.

.. contents::
   :local:
   :depth: 2

Prerequisites and irreversible boundaries
=========================================

- HYOK requires the appropriate HCP Terraform entitlement, an agent pool with request forwarding,
  and supported agent and Terraform versions.
- Create the new KMS key and IAM/OIDC trust before running this playbook. Restrict the trust
  subject to the organization and intended HYOK configuration name.
- Validate that the agent hosts can reach KMS and that their environment resolves the intended
  AWS region.
- Persist every returned OIDC configuration ID. The HCP API cannot search AWS OIDC records by a
  caller-defined name, so omitting the ID on a rerun creates another record.
- Do not schedule deletion of the old KMS key as part of this playbook. Keep it enabled through
  the organization's recovery and audit window.
- Revocation of the old HYOK configuration is a separate, explicitly approved phase.

Example input
=============

Save non-secret identifiers as ``vars/hyok-rotation.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   hyok_agent_pool_id: apool-hyok123

   new_hyok_name: primary-key-2026-09
   new_kms_key_arn: arn:aws:kms:us-east-1:111122223333:key/new-key-id
   new_kms_region: us-east-1
   new_oidc_role_arn: arn:aws:iam::111122223333:role/hcp-terraform-hyok-2026-09

   # Empty only for the first creation job. Persist the returned value afterward.
   new_aws_oidc_configuration_id: ""

   old_hyok_configuration_id: hyokc-old123
   old_aws_oidc_configuration_id: oidc-old123
   retire_old_configuration: false
   rotation_timeout: 1200

Complete rotation playbook
==========================

Save this as ``rotate-hyok.yml``:

.. code-block:: yaml

   ---
   - name: Create, test, and optionally complete an AWS HYOK rotation
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/hyok-rotation.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Create or update the HCP-side AWS OIDC record
         hashicorp.terraform.aws_oidc_configuration:
           oidc_configuration_id: >-
             {{ new_aws_oidc_configuration_id | default(omit, true) }}
           organization: "{{ terraform_organization }}"
           role_arn: "{{ new_oidc_role_arn }}"
           state: present
         register: new_oidc

       - name: Create the new primary HYOK configuration and test key access
         hashicorp.terraform.hyok_configuration:
           organization: "{{ terraform_organization }}"
           name: "{{ new_hyok_name }}"
           kek_id: "{{ new_kms_key_arn }}"
           agent_pool_id: "{{ hyok_agent_pool_id }}"
           oidc_configuration_id: "{{ new_oidc.id }}"
           oidc_configuration_type: aws
           primary: true
           kms_options:
             key_region: "{{ new_kms_region }}"
           test: true
           wait: true
           timeout: "{{ rotation_timeout }}"
           poll_interval: 10
           state: present
         register: new_hyok

       - name: Re-read the new HYOK configuration authoritatively
         hashicorp.terraform.hyok_configuration_info:
           hyok_configuration_id: "{{ new_hyok.id }}"
         register: new_hyok_info

       - name: Require a tested primary before retiring anything
         ansible.builtin.assert:
           that:
             - new_hyok_info.hyok_configuration.primary | bool
             - >-
               new_hyok_info.hyok_configuration.status
               in ['available', 'active']
           fail_msg: >-
             The new HYOK configuration is not a healthy primary. Keep the old key and
             configuration active.

       - name: Publish identifiers for the protected automation record
         ansible.builtin.set_stats:
           data:
             new_aws_oidc_configuration_id: "{{ new_oidc.id }}"
             new_hyok_configuration_id: "{{ new_hyok.id }}"
             new_hyok_status: "{{ new_hyok_info.hyok_configuration.status }}"
           per_host: false

       - name: Report readiness for the separately approved retirement phase
         ansible.builtin.debug:
           msg: >-
             The new primary is healthy. The old configuration remains active until the
             separately approved retirement continuation runs.
         when: not retire_old_configuration | bool

       - name: End successfully before retirement when it is not approved
         ansible.builtin.meta: end_play
         when: not retire_old_configuration | bool

       - name: Revoke and delete the old HYOK configuration
         hashicorp.terraform.hyok_configuration:
           hyok_configuration_id: "{{ old_hyok_configuration_id }}"
           wait: true
           timeout: "{{ rotation_timeout }}"
           poll_interval: 10
           state: absent

       - name: Delete the old HCP-side OIDC record after HYOK retirement
         hashicorp.terraform.aws_oidc_configuration:
           oidc_configuration_id: "{{ old_aws_oidc_configuration_id }}"
           state: absent

Two-phase controller workflow
=============================

Run creation and retirement as separate jobs:

#. The first job creates the OIDC and HYOK records, tests KMS access, verifies ``primary``, and
   publishes the non-secret IDs. It stops with the old configuration intact.
#. Operators confirm new runs and encrypted artifacts remain healthy and retain evidence.
#. An approval node authorizes a continuation with ``retire_old_configuration: true`` and the
   exact old and new IDs.
#. The continuation re-tests the new primary, then revokes and deletes the old HYOK record.

The ``hyok_configuration`` module automatically waits for the old configuration to reach
``revoked`` before deletion. If migration or revocation does not complete, it fails rather than
deleting the record prematurely.

Failure, rollback, and idempotency
==================================

Before old-key revocation, rollback means keeping the old configuration and correcting or
removing the new one under a separate change. After revocation, follow the HCP Terraform HYOK
recovery procedure; do not disable or destroy KMS keys in an attempt to force rollback.

HYOK configurations are immutable. A changed key, pool, OIDC ID, or KMS option requires an
explicit replacement. OIDC updates are idempotent only when ``new_aws_oidc_configuration_id`` is
supplied. Persist it immediately after first creation.

.. seealso::

   - :ansplugin:`hashicorp.terraform.aws_oidc_configuration#module`
   - :ansplugin:`hashicorp.terraform.hyok_configuration#module`
   - :ansplugin:`hashicorp.terraform.hyok_configuration_info#module`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.cookbook_agent_pool_blue_green`
