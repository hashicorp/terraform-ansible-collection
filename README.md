# Hashicorp Terraform Collection

This repository contains the `hashicorp.terraform` Ansible Collection.

## Requirements

Some modules and plugins require external libraries. Please check the
requirements for each plugin or module you use in the documentation to find out
which requirements are needed.

<!--start requires_ansible-->
## Ansible version compatibility

This collection has been tested against the following Ansible versions: **>=2.16.0**.

Plugins and modules within a collection may be tested with only specific Ansible versions.
A collection may contain metadata that identifies these versions.
PEP440 is the schema used to describe the versions of Ansible.
<!--end requires_ansible-->

## Included content

<!--start collection content-->
<!--end collection content-->

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

WIP


## Testing

WIP

## Support

As Red Hat Ansible Certified Content, this collection is entitled to support through the Ansible Automation Platform (AAP) using the **Create issue** button on the top right corner. If a support case cannot be opened with Red Hat and the collection has been obtained either from Galaxy or GitHub, there may community help available on the [Ansible Forum](https://forum.ansible.com/).

## Release Notes and Roadmap

See the
[changelog](https://github.com/ansible-collections/hashicorp.terraform/tree/main/CHANGELOG.rst).


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
