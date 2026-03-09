"""Expose the repo's top-level `plugins` directory as the collection's plugins package.

This shim makes imports like
`ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions`
resolve to the repository's `plugins/` directory during local tests.
"""
import os

# Compute path to the repository's top-level `plugins` directory.
_this_dir = os.path.dirname(__file__)
# /collections/ansible_collections/hashicorp/terraform/plugins -> go up 5 to repo root
_repo_plugins = os.path.abspath(os.path.join(_this_dir, '..', '..', '..', '..', '..', 'plugins'))
if os.path.isdir(_repo_plugins) and _repo_plugins not in __path__:
    __path__.insert(0, _repo_plugins)
