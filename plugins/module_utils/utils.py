# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from typing import Any, Dict

from pytfe.errors import AuthError, NotFound, ServerError, TFEError

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


def handle_error(error: Exception, context: str = "") -> None:
    """Translate and re-raise SDK exceptions with additional context.

    Args:
        error: Exception from SDK
        context: Additional context about the operation

    Raises:
        TerraformError: Wrapped exception with context
    """
    error_msg = str(error)

    if context:
        error_msg = f"{context}: {error_msg}"

    # TFE-specific error handling
    if isinstance(error, NotFound):
        error_msg = f"Resource not found: {error_msg}"
    elif isinstance(error, AuthError):
        error_msg = f"Authentication error: {error_msg}"
    elif isinstance(error, ServerError):
        error_msg = f"Server error: {error_msg}"
    elif isinstance(error, TFEError):
        # Generic TFE error - extract additional details if available
        details = getattr(error, "details", None)
        if details:
            error_msg = f"{error_msg} - Details: {details}"

    raise TerraformError(error_msg) from error


def safe_api_call(operation, *args, **kwargs) -> Any:
    """Execute API operation with error handling.

    Args:
        operation: Callable API operation
        *args: Positional arguments for the operation
        **kwargs: Keyword arguments for the operation (error_context is extracted)

    Returns:
        Result from the API operation

    Raises:
        TerraformError: If operation fails
    """
    # Extract error_context before calling operation
    error_context = kwargs.pop("error_context", str(operation))

    try:
        return operation(*args, **kwargs)
    except TFEError as e:
        handle_error(e, context=error_context)
    except Exception as e:
        raise TerraformError(f"Unexpected error: {str(e)}") from e


def format_response(response: Any) -> Dict[str, Any]:
    """Format SDK response for Ansible output.

    Args:
        response: Response object from SDK

    Returns:
        Dictionary formatted for Ansible
    """
    # Convert SDK response to dictionary with JSON-serializable types
    return response.model_dump(mode="json", exclude_none=True)
