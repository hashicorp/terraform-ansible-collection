# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Source backend registry and factory function."""

from typing import Dict

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.outputs import OutputsSource
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.search import SearchSource
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.statefile import StatefileSource

#: Registry mapping source name → backend class.
SOURCES: Dict[str, type] = {
    StatefileSource.NAME: StatefileSource,
    OutputsSource.NAME: OutputsSource,
    SearchSource.NAME: SearchSource,
}


def get_source_backend(source_name: str) -> type:
    """Return the source backend class for *source_name*.

    Raises ``AnsibleParserError`` for unrecognised names.
    """
    try:
        return SOURCES[source_name]
    except KeyError:
        raise TerraformError(f"Unknown source '{source_name}'. Valid choices are: {', '.join(sorted(SOURCES))}.")
