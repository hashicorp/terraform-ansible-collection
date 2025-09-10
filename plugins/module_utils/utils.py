# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from .exceptions import (
    TerraformError,
)


def sort_list(val):
    if isinstance(val, list):
        if len(val) == 0:
            return val
        if isinstance(val[0], dict):
            sorted_keys = [tuple(sorted(dict_.keys())) for dict_ in val]
            # All keys should be identical
            if len(set(sorted_keys)) != 1:
                raise ValueError("dictionaries do not match")

            return sorted(val, key=lambda d: tuple(d[k] for k in sorted_keys[0]))
        return sorted(val)
    return val


def dict_diff(base, comparable):
    """Generate a dict object of differences

    This function will compare two dict objects and return the difference
    between them as a dict object.  For scalar values, the key will reflect
    the updated value.  If the key does not exist in `comparable`, then then no
    key will be returned.  For lists, the value in comparable will wholly replace
    the value in base for the key.  For dicts, the returned value will only
    return keys that are different.

    :param base: dict object to base the diff on
    :param comparable: dict object to compare against base

    :returns: new dict object with differences
    """
    if not isinstance(base, dict):
        raise TerraformError("`base` must be of type <dict>")
    if not isinstance(comparable, dict):
        if comparable is None:
            comparable = {}
        else:
            raise TerraformError("`comparable` must be of type <dict>")

    updates = {}

    for key, value in base.items():
        if isinstance(value, dict):
            item = comparable.get(key)
            if item is not None:
                sub_diff = dict_diff(value, comparable[key])
                if sub_diff:
                    updates[key] = sub_diff
        else:
            comparable_value = comparable.get(key)
            if comparable_value is not None:
                if sort_list(base[key]) != sort_list(comparable_value):
                    updates[key] = comparable_value

    for key in set(comparable.keys()).difference(base.keys()):
        updates[key] = comparable.get(key)

    return updates
