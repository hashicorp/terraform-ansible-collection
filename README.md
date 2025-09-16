# Hashicorp Terraform Collection

This repository contains the `hashicorp.terraform` Ansible Collection.

# Description

The primary purpose of this collection is to provide seamless integration between Ansible Automation Platform and Terraform Cloud/Enterprise. It contains modules and plugins that support creating runs, uploading new configuration versions, viewing plans, retrieving information about workspaces, projects, etc.

Being Red Hat Ansible Certified Content, this collection is eligible for support through the [Ansible Automation Platform](https://www.redhat.com/en/technologies/management/ansible).

## Requirements

This collection requires `requests` and `pydantic>=2.0.0` libraries to be installed.

Some modules and plugins may require other external libraries. Please check the
requirements for each plugin or module you use in the documentation to check the
requirements.

## Ansible version compatibility

This collection has been tested against the following Ansible versions: **>=2.16.0**.

Plugins and modules within a collection may be tested with only specific Ansible versions.
A collection may contain metadata that identifies these versions.
PEP440 is the schema used to describe the versions of Ansible.

## Installation

To install this collection from Automation Hub, the following needs to be added to `ansible.cfg`:

```ini
[galaxy]
server_list=automation_hub

[galaxy_server.automation_hub]
url=https://console.redhat.com/api/automation-hub/content/published/
auth_url=https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token
token=<SuperSecretToken>
```

To download contents from Automation Hub using `ansible-galaxy` CLI, you would need to generate and use an offline token.
If you already have a token, please ensure that it has not expired. Visit [Connect to Hub](https://console.redhat.com/ansible/automation-hub/token) to obtain the necessary token.

With this configured, simply run the following command:

```bash
    ansible-galaxy collection install hashicorp.terraform
```

You can also include it in a `requirements.yml` file and install it via
`ansible-galaxy collection install -r requirements.yml` using the format:

```yaml
collections:
  - name: hashicorp.terraform
```

To upgrade the collection to the latest available version, run the following
command:

```bash
ansible-galaxy collection install hashicorp.terraform --upgrade
```

You can also install a specific version of the collection, for example, if you
need to downgrade when something is broken in the latest version (please report
an issue in this repository). Use the following syntax where `X.Y.Z` can be any
[available version](https://galaxy.ansible.com/hashicorp/terraform):

```bash
ansible-galaxy collection install hashicorp.terraform:==X.Y.Z
```

See
[Ansible Using Collections](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html)
for more details.

## Use Cases

Modules in this collection can be used for various operations on Terraform Cloud/Enterprise. Currently the collection supports:

- Creating, uploading and archiving configuration versions
- Creating, applying, and discarding runs

These modules can be called by their Fully Qualified Collection Name (FQCN), such as `hashicorp.terraform.configuration_version`, or by their short name if you list the `hashicorp.terraform` collection in the playbook's collections keyword.
For examples on how to use modules included in this collection, please refer to their documentation.

```yaml
---
- name: Playbook using hashicorp.terraform collection
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Create a new configuration version
      hashicorp.terraform.configuration_version:
        workspace_id: "{{ workspace_id }}"
        state: present
        configuration_files_path: "{{ configuration_files }}"
        poll_interval: 3
        poll_timeout: 15
        tf_token: "{{ terraform_cloud_token }}"
```

## Testing

GitHub Actions workflows are used to run tests for the `hashicorp.terraform` collection. These workflows include jobs to run the unit tests, integration tests, sanity tests, linters, changelog check and doc related checks. The following table lists the python and ansible versions against which these jobs are run.

| Jobs | Description | Python Versions | Ansible Versions |
| ------ |-------| ------ | -----------|
| changelog | Checks for the presence of Changelog fragments | 3.12 | N/A |
| build-import | Builds collection and runs galaxy_importer  | 3.12 | latest ansible-core release |
| ansible-lint | Runs latest ansible-lint in production profile | 3.12 | latest ansible-core release |
| Linters | Runs `black`, `flake8` and `isort` on plugins and tests | 3.11 | N/A |
| Sanity | Runs ansible-test sanity | 3.10, 3.11, 3.12, 3.13 | stable-2.16, stable-2.17, stable-2.18, stable-2.19, devel, milestone |
| Unit tests | Executes the unit test cases | 3.10, 3.11, 3.12, 3.13 | stable-2.16, stable-2.17, stable-2.18, stable-2.19, devel, milestone |
| Integration tests | Executes the integration test suite | 3.12, 3.13 | devel, stable-2.19, stable-2.16 |

**Note:** Not all listed Python versions are applicable to all ansible-core versions. The actual compatibility depends on ansible-core supported Python versions for a given release.

## Support

As Red Hat Ansible Certified Content, this collection is entitled to support through the Ansible Automation Platform (AAP) using the **Create issue** button on the top right corner. If a support case cannot be opened with Red Hat and the collection has been obtained either from Galaxy or GitHub, there may community help available on the [Ansible Forum](https://forum.ansible.com/).

## Release Notes and Roadmap

### Latest Release: 1.0.0

#### Release Summary

This marks the first release of the `hashicorp.terraform` collection.

#### New Modules

- `configuration_version` — Manage configuration versions in Terraform Enterprise/Cloud.
- `run` — Manage Terraform Cloud/Enterprise runs (create, apply, cancel, discard).

## Related Information

- [Ansible collection development forum](https://forum.ansible.com/c/project/collection-development/27)
- [Ansible User guide](https://docs.ansible.com/ansible/devel/user_guide/index.html)
- [Ansible Developer guide](https://docs.ansible.com/ansible/devel/dev_guide/index.html)
- [Ansible Collections Checklist](https://docs.ansible.com/ansible/devel/community/collection_contributors/collection_requirements.html)
- [Ansible Community code of conduct](https://docs.ansible.com/ansible/devel/community/code_of_conduct.html)
- [The Bullhorn (the Ansible Contributor newsletter)](https://docs.ansible.com/ansible/devel/community/communication.html#the-bullhorn)
- [News for Maintainers](https://forum.ansible.com/tag/news-for-maintainers)

## Licensing Information

GNU General Public License v3.0 or later.

See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.txt) to see the full text.
