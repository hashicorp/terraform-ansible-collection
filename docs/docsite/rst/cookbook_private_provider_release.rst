.. _ansible_collections.hashicorp.terraform.docsite.cookbook_private_provider_release:

**********************************
Publish a signed private provider
**********************************

This cookbook publishes a pre-built, signed Terraform provider release to the HCP Terraform or
Terraform Enterprise private registry, including multiple operating-system and architecture
platforms.

.. code-block:: text

   build + scan + sign -> provider -> version -> checksums + signature
                                  -> platform records -> provider binaries -> verification run

The collection creates and reads registry records. HCP Terraform returns short-lived upload URLs;
``ansible.builtin.uri`` sends the already-built artifacts to those URLs.

.. contents::
   :local:
   :depth: 2

Prerequisites and release contract
==================================

- Build provider archives using a reproducible, trusted pipeline. This playbook does not compile
  source code.
- Scan every archive, generate a SHA256SUMS file, and create its detached GPG signature.
- Register the signing key with the private registry and provide its key ID.
- Run this playbook from an execution environment that can reach both the HCP Terraform/TFE API
  and the object-storage upload URLs it returns. For air-gapped Terraform Enterprise, validate the
  equivalent internal endpoints.
- The token needs private-registry management permission.
- Version and platform records are immutable release coordinates. Publish a new semantic version
  rather than replacing bytes for an existing release.

Example release manifest
========================

Save this as ``vars/provider-release.yml``:

.. code-block:: yaml

   ---
   terraform_organization: acme
   provider_namespace: acme
   provider_name: payments
   provider_version: "1.4.0"
   provider_key_id: ABCDEF1234567890
   provider_protocols:
     - "5.0"

   shasums_file: "{{ playbook_dir }}/dist/terraform-provider-payments_1.4.0_SHA256SUMS"
   shasums_signature_file: >-
     {{ playbook_dir }}/dist/terraform-provider-payments_1.4.0_SHA256SUMS.sig

   provider_platforms:
     - os: linux
       arch: amd64
       filename: terraform-provider-payments_1.4.0_linux_amd64.zip
       artifact: "{{ playbook_dir }}/dist/terraform-provider-payments_1.4.0_linux_amd64.zip"
       shasum: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
     - os: linux
       arch: arm64
       filename: terraform-provider-payments_1.4.0_linux_arm64.zip
       artifact: "{{ playbook_dir }}/dist/terraform-provider-payments_1.4.0_linux_arm64.zip"
       shasum: fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210

Complete publication playbook
=============================

Save this as ``publish-provider.yml``:

.. code-block:: yaml

   ---
   - name: Publish a signed private Terraform provider release
     hosts: localhost
     connection: local
     gather_facts: false
     vars_files:
       - vars/provider-release.yml
     module_defaults:
       group/hashicorp.terraform.terraform:
         tfe_address: >-
           {{ lookup('ansible.builtin.env', 'TFE_ADDRESS')
              | default('https://app.terraform.io', true) }}
     tasks:
       - name: Verify release files exist locally
         ansible.builtin.stat:
           path: "{{ item }}"
           checksum_algorithm: sha256
         loop: >-
           {{ [shasums_file, shasums_signature_file]
              + (provider_platforms | map(attribute='artifact') | list) }}
         register: release_files

       - name: Refuse an incomplete release manifest
         ansible.builtin.assert:
           that:
             - release_files.results | rejectattr('stat.exists') | list | length == 0

       - name: Create the private provider namespace entry
         hashicorp.terraform.registry_provider:
           organization: "{{ terraform_organization }}"
           namespace: "{{ provider_namespace }}"
           name: "{{ provider_name }}"
           registry_name: private
           state: present

       - name: Create the immutable provider version record
         hashicorp.terraform.registry_provider_version:
           organization_name: "{{ terraform_organization }}"
           namespace: "{{ provider_namespace }}"
           name: "{{ provider_name }}"
           version: "{{ provider_version }}"
           key_id: "{{ provider_key_id }}"
           protocols: "{{ provider_protocols }}"
           state: present
         register: version_record

       - name: Upload the checksum manifest for a new version
         ansible.builtin.uri:
           url: "{{ version_record.links['shasums-upload'] }}"
           method: PUT
           src: "{{ shasums_file }}"
           follow_redirects: all
           status_code:
             - 200
             - 201
         when: version_record.changed
         no_log: true

       - name: Upload the checksum signature for a new version
         ansible.builtin.uri:
           url: "{{ version_record.links['shasums-sig-upload'] }}"
           method: PUT
           src: "{{ shasums_signature_file }}"
           follow_redirects: all
           status_code:
             - 200
             - 201
         when: version_record.changed
         no_log: true

       - name: Create every provider platform record
         hashicorp.terraform.registry_provider_platform:
           organization: "{{ terraform_organization }}"
           provider_name: "{{ provider_name }}"
           namespace: "{{ provider_namespace }}"
           registry_name: private
           version: "{{ provider_version }}"
           os: "{{ item.os }}"
           arch: "{{ item.arch }}"
           shasum: "{{ item.shasum }}"
           filename: "{{ item.filename }}"
           state: present
         loop: "{{ provider_platforms }}"
         loop_control:
           label: "{{ item.os }}/{{ item.arch }}"
         register: platform_records

       - name: Upload binaries for newly created platforms
         ansible.builtin.uri:
           url: "{{ item.links['provider-binary-upload'] }}"
           method: PUT
           src: "{{ item.item.artifact }}"
           follow_redirects: all
           status_code:
             - 200
             - 201
         loop: "{{ platform_records.results }}"
         loop_control:
           label: "{{ item.item.os }}/{{ item.item.arch }}"
         when: item.changed
         no_log: true

       - name: Verify the checksum uploads are recorded
         hashicorp.terraform.registry_provider_version_info:
           organization_name: "{{ terraform_organization }}"
           namespace: "{{ provider_namespace }}"
           name: "{{ provider_name }}"
           version: "{{ provider_version }}"
         register: published_version

       - name: Verify every provider binary is recorded
         hashicorp.terraform.registry_provider_platform_info:
           organization: "{{ terraform_organization }}"
           provider_name: "{{ provider_name }}"
           namespace: "{{ provider_namespace }}"
           registry_name: private
           version: "{{ provider_version }}"
           os: "{{ item.os }}"
           arch: "{{ item.arch }}"
         loop: "{{ provider_platforms }}"
         loop_control:
           label: "{{ item.os }}/{{ item.arch }}"
         register: published_platforms

       - name: Require a complete registry release
         ansible.builtin.assert:
           that:
             - published_version.registry_provider_version.shasums_uploaded
             - published_version.registry_provider_version.shasums_sig_uploaded
             - >-
               published_platforms.results
               | map(attribute='registry_provider_platform.provider_binary_uploaded')
               | min

Reruns and failure recovery
===========================

On a rerun, existing version and platform records are no-ops and no new upload URLs are required.
If an upload fails after its record was created, inspect the record and API-provided links before
retrying. Do not delete and silently republish a version that consumers may already have used.
Follow the organization's failed-release or version-revocation procedure instead.

After publication, queue a speculative run in a private-agent canary workspace that pins the exact
provider source and version. Publication proves artifact completeness; only Terraform init and
plan prove that the intended execution environment can install and use it.

Supply-chain hardening
======================

- Generate provenance, SBOM, vulnerability results, checksums, and signatures in the build job.
- Keep signing keys outside the Ansible project and use a hardware-backed or isolated signer.
- Compare manifest SHA256 values with ``stat.checksum`` before upload in a production role.
- Publish only approved OS/architecture combinations and test each on matching agents.
- Restrict egress from private agents to approved registries and provider APIs.

.. seealso::

   - :ansplugin:`hashicorp.terraform.registry_provider#module`
   - :ansplugin:`hashicorp.terraform.registry_provider_version#module`
   - :ansplugin:`hashicorp.terraform.registry_provider_platform#module`
   - :ref:`ansible_collections.hashicorp.terraform.docsite.guide_registry_modules`

