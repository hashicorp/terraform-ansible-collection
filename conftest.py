# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Root pytest configuration for Terraform collection tests.
"""

import sys
from pathlib import Path

# Ensure the installed collection location is in sys.path
ansible_collections_path = Path.home() / ".ansible" / "collections"
if str(ansible_collections_path) not in sys.path:
    sys.path.insert(0, str(ansible_collections_path))
