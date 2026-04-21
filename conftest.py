# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Root pytest configuration for Terraform collection tests.
"""

import os
import sys
from pathlib import Path

# Ensure the local collections directory is discoverable by Ansible's collection finder.
# This is needed when running with --ansible-unit-inject-only, which uses
# ANSIBLE_COLLECTIONS_PATH instead of sys.path to locate collections.
_local_collections = str(Path(__file__).parent / "collections")
_existing = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "")
if _local_collections not in _existing.split(os.pathsep):
    os.environ["ANSIBLE_COLLECTIONS_PATH"] = (
        _local_collections + os.pathsep + _existing if _existing else _local_collections
    )

# Also ensure the collections directory is on sys.path for direct imports.
if _local_collections not in sys.path:
    sys.path.insert(0, _local_collections)
