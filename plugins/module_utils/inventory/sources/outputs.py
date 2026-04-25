# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""OutputsSource: builds inventory by querying the HCP Terraform outputs API.

Uses the ``/state-version-outputs`` endpoint (via ``get_workspace_outputs``)
to list the current state version outputs for the target workspace.

Auto-detection mode (no ``hosts_from``)
-----------------------------------------
- ``dict`` output  → one host with the dict as host variables.
- ``list(dict)`` output → one host per element (indexed).
- All other shapes are silently skipped.

Explicit mode (``hosts_from`` configured)
------------------------------------------
Each ``hosts_from`` entry declares an HCL-style ``type:`` constraint. The
runtime value of the named output is mapped to host records as follows:

type expression                     →  behaviour
------------------------------------------------
``string`` / ``number`` / ``bool``  →  single host; raw value stored as ``value``;
                                       optional ``use_as`` mirrors it to the named var.
``object``                          →  single host; dict becomes host variables.
``list(<primitive>)`` /
``set(<primitive>)``                →  one indexed host per element; element stored
                                       as ``value`` (and as ``use_as`` if set).
``list(object)`` / ``set(object)``  →  one indexed host per element; element dict
                                       becomes host variables.
``map(<primitive>)``                →  one host per key; key becomes the resolved
                                       hostname and is stored in the ``key`` host
                                       variable; primitive stored as ``value``.
``map(object)``                     →  one host per key; key becomes the resolved
                                       hostname and is stored in ``key``; element
                                       dict becomes host variables.
``auto`` (default when type omitted) →  shape inferred at runtime from the value.
                                        Experimental.

``set`` is treated as a synonym for ``list`` (the outputs API serializes both
as JSON arrays — no distinction is possible at the wire level).

Unsupported expressions (``tuple``, nested collections such as
``map(list(...))``, ``object({...})``, etc.) are rejected at validation time.
Reshape the value in your Terraform output (``flatten()``, ``for`` expressions)
instead of trying to handle it in inventory.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.base import BaseInventorySource, HostRecord
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common import fetch_outputs, resolve_workspace


# Warning / debug hooks. Default to no-ops so this module remains importable
# from a module-execution context (where ansible.utils.display is forbidden by
# the sanity ``ansible-bad-module-import`` rule). The inventory plugin wires
# these up to ``Display.warning`` / ``Display.vvv`` at plugin-load time.
def _warn(msg: str) -> None:
    pass


def _debug(msg: str) -> None:
    pass


# ---------------------------------------------------------------------------
# hosts_from type expression parser
# ---------------------------------------------------------------------------

_TYPE_RE = re.compile(r"^\s*(auto|string|number|bool|object|list|set|map)\s*(?:\(\s*(string|number|bool|object)\s*\))?\s*$")

_SHAPES: Dict[Tuple[str, Optional[str]], str] = {
    ("auto", None): "auto",
    ("string", None): "primitive",
    ("number", None): "primitive",
    ("bool", None): "primitive",
    ("object", None): "object",
    ("list", "string"): "seq_primitive",
    ("list", "number"): "seq_primitive",
    ("list", "bool"): "seq_primitive",
    ("list", "object"): "seq_object",
    ("set", "string"): "seq_primitive",
    ("set", "number"): "seq_primitive",
    ("set", "bool"): "seq_primitive",
    ("set", "object"): "seq_object",
    ("map", "string"): "map_primitive",
    ("map", "number"): "map_primitive",
    ("map", "bool"): "map_primitive",
    ("map", "object"): "map_object",
}

_VALID_FORMS: Tuple[str, ...] = (
    "auto",
    "string",
    "number",
    "bool",
    "object",
    "list(string)",
    "list(number)",
    "list(bool)",
    "list(object)",
    "set(string)",
    "set(number)",
    "set(bool)",
    "set(object)",
    "map(string)",
    "map(number)",
    "map(bool)",
    "map(object)",
)

_OBJECT_SHAPES = {"object", "seq_object", "map_object"}


def parse_type(expr: Any) -> str:
    """Parse an HCL-style type expression and return the internal shape tag.

    Raises :class:`TerraformError` for empty / non-string inputs and for any
    unsupported expression. The error message lists the valid forms and points
    the user at Terraform-side reshaping for nested collections.
    """
    if not isinstance(expr, str) or not expr.strip():
        raise TerraformError("hosts_from 'type' must be a non-empty string. " f"Supported forms: {', '.join(_VALID_FORMS)}.")
    match = _TYPE_RE.match(expr)
    if match:
        key = (match.group(1), match.group(2))
        if key in _SHAPES:
            return _SHAPES[key]
    raise TerraformError(
        f"unsupported hosts_from type expression: {expr!r}. "
        f"Supported forms: {', '.join(_VALID_FORMS)}. "
        "Nested collections (tuple, map(list(...)), object({...}), etc.) "
        "are not supported — reshape the value in your Terraform output "
        "using flatten() or a for expression."
    )


# ---------------------------------------------------------------------------
# Auto-detection of shape from runtime value
# ---------------------------------------------------------------------------


def _detect_auto_shape(value: Any, output_name: str) -> Optional[str]:
    """Return the internal shape tag detected from *value*, or ``None`` to skip."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "primitive"
    if isinstance(value, (str, int, float)):
        return "primitive"
    if isinstance(value, dict):
        if not value:
            _debug(f"hosts_from auto: output {output_name!r} is an empty dict; skipping")
            return None
        if all(isinstance(v, dict) for v in value.values()):
            return "map_object"
        return "object"
    if isinstance(value, list):
        if not value:
            _debug(f"hosts_from auto: output {output_name!r} is an empty list; skipping")
            return None
        if all(isinstance(item, dict) for item in value):
            return "seq_object"
        if all(isinstance(item, (str, int, float, bool)) for item in value):
            return "seq_primitive"
        _warn(
            f"hosts_from auto: output {output_name!r} is a list of mixed types; skipping. "
            + "Declare type explicitly or reshape in Terraform if all elements should produce hosts."
        )
        return None
    _warn(f"hosts_from auto: output {output_name!r} has unsupported value type {type(value).__name__}; skipping.")
    return None


# ---------------------------------------------------------------------------
# Per-shape record builders
# ---------------------------------------------------------------------------


def _record(output_name: str, workspace_name: str, host_vars: Dict[str, Any], **extra: Any) -> HostRecord:
    record: HostRecord = {
        "output_name": output_name,
        "workspace_name": workspace_name,
        "host_vars": host_vars,
        "index": None,
    }
    record.update(extra)
    return record


def _records_for_primitive(value: Any, output_name: str, workspace_name: str, use_as: Optional[str]) -> List[HostRecord]:
    host_vars: Dict[str, Any] = {"value": value}
    if use_as:
        host_vars[use_as] = value
    return [_record(output_name, workspace_name, host_vars)]


def _records_for_object(value: Any, output_name: str, workspace_name: str) -> List[HostRecord]:
    if not isinstance(value, dict):
        return []
    return [_record(output_name, workspace_name, value)]


def _records_for_seq_primitive(value: Any, output_name: str, workspace_name: str, use_as: Optional[str]) -> List[HostRecord]:
    if not isinstance(value, list):
        return []
    records: List[HostRecord] = []
    for idx, item in enumerate(value):
        host_vars: Dict[str, Any] = {"value": item}
        if use_as:
            host_vars[use_as] = item
        records.append(_record(output_name, workspace_name, host_vars, index=idx))
    return records


def _records_for_seq_object(value: Any, output_name: str, workspace_name: str) -> List[HostRecord]:
    if not isinstance(value, list):
        return []
    records: List[HostRecord] = []
    for idx, item in enumerate(value):
        if isinstance(item, dict):
            records.append(_record(output_name, workspace_name, item, index=idx))
    return records


def _records_for_map_primitive(value: Any, output_name: str, workspace_name: str, use_as: Optional[str]) -> List[HostRecord]:
    if not isinstance(value, dict):
        return []
    records: List[HostRecord] = []
    for key, item in value.items():
        host_vars: Dict[str, Any] = {"value": item, "key": key}
        if use_as:
            host_vars[use_as] = item
        records.append(_record(output_name, workspace_name, host_vars, resolved_hostname=key))
    return records


def _records_for_map_object(value: Any, output_name: str, workspace_name: str) -> List[HostRecord]:
    if not isinstance(value, dict):
        return []
    records: List[HostRecord] = []
    for key, obj in value.items():
        if isinstance(obj, dict):
            host_vars = dict(obj)
            host_vars["key"] = key
            records.append(_record(output_name, workspace_name, host_vars, resolved_hostname=key))
    return records


# ---------------------------------------------------------------------------
# hosts_from spec processor
# ---------------------------------------------------------------------------


def _collect_hosts_from_spec(
    spec: Dict[str, Any],
    outputs_map: Dict[str, Any],
    workspace_name: str,
) -> List[HostRecord]:
    """Return :class:`HostRecord` entries for one ``hosts_from`` spec.

    *outputs_map* is ``{output_name: value}`` built from the raw outputs list.
    Returns an empty list when the named output is absent or the runtime value
    does not match the declared shape (or when ``type: auto`` cannot pick a
    supported shape from the value).
    """
    output_name: str = spec.get("output", "")
    type_expr: str = spec.get("type") or "auto"
    use_as: Optional[str] = spec.get("use_as")

    if output_name not in outputs_map:
        return []

    shape = parse_type(type_expr)
    value = outputs_map[output_name]

    if shape == "auto":
        detected = _detect_auto_shape(value, output_name)
        if detected is None:
            return []
        shape = detected

    if shape == "primitive":
        return _records_for_primitive(value, output_name, workspace_name, use_as)
    if shape == "object":
        return _records_for_object(value, output_name, workspace_name)
    if shape == "seq_primitive":
        return _records_for_seq_primitive(value, output_name, workspace_name, use_as)
    if shape == "seq_object":
        return _records_for_seq_object(value, output_name, workspace_name)
    if shape == "map_primitive":
        return _records_for_map_primitive(value, output_name, workspace_name, use_as)
    if shape == "map_object":
        return _records_for_map_object(value, output_name, workspace_name)
    return []


# ---------------------------------------------------------------------------
# Source backend
# ---------------------------------------------------------------------------


class OutputsSource(BaseInventorySource):
    """Reads current state version outputs via the HCP Terraform outputs API."""

    NAME = "outputs"

    @classmethod
    def validate_options(cls, options: Dict[str, Any]) -> None:
        workspace_id = options.get("workspace_id")
        organization = options.get("organization")
        workspace = options.get("workspace")
        if not workspace_id and not (organization and workspace):
            raise TerraformError("source 'outputs' requires either 'workspace_id' or both 'organization' and 'workspace'.")

        cls._validate_hosts_from(options.get("hosts_from"))

    @staticmethod
    def _validate_hosts_from(hosts_from: Any) -> None:
        if hosts_from is None:
            return
        if isinstance(hosts_from, dict):
            specs: List[Any] = [hosts_from]
        elif isinstance(hosts_from, list):
            specs = hosts_from
        else:
            raise TerraformError(f"hosts_from must be a mapping or a list of mappings; got {type(hosts_from).__name__}.")

        for idx, spec in enumerate(specs):
            if not isinstance(spec, dict):
                raise TerraformError(f"hosts_from[{idx}] must be a mapping; got {type(spec).__name__}.")
            output_name = spec.get("output")
            if not isinstance(output_name, str) or not output_name:
                raise TerraformError(f"hosts_from[{idx}] requires a non-empty 'output' string.")
            type_expr = spec.get("type", "auto")
            shape = parse_type(type_expr)
            use_as = spec.get("use_as")
            if use_as is not None and not isinstance(use_as, str):
                raise TerraformError(f"hosts_from[{idx}] 'use_as' must be a string; got {type(use_as).__name__}.")
            if use_as and shape in _OBJECT_SHAPES:
                _warn(
                    f"hosts_from[{idx}] (output {output_name!r}): 'use_as' is ignored for object shapes "
                    + f"(type={type_expr!r}); object fields are exposed as host variables directly."
                )

    def collect_hosts(self) -> List[HostRecord]:
        workspace_id_opt = self.options.get("workspace_id")
        organization = self.options.get("organization")
        workspace = self.options.get("workspace")

        hosts_from_opt = self.options.get("hosts_from") or []
        if isinstance(hosts_from_opt, dict):
            hosts_from_opt = [hosts_from_opt]

        resolved_id, workspace_name = resolve_workspace(self.client, workspace_id_opt, organization, workspace)
        outputs = fetch_outputs(self.client, resolved_id)

        if hosts_from_opt:
            outputs_map: Dict[str, Any] = {o.get("name", ""): o.get("value") for o in outputs if isinstance(o, dict)}
            records: List[HostRecord] = []
            for spec in hosts_from_opt:
                records.extend(_collect_hosts_from_spec(spec, outputs_map, workspace_name))
            return records

        # Plugin-level auto-detection (when hosts_from is entirely absent).
        # Intentionally narrower than per-spec ``type: auto``: only dict and
        # list(dict) produce hosts. Broadening this would risk surprise hosts
        # from outputs never meant for inventory.
        records = []
        for output in outputs:
            output_name: str = output.get("name") or "unknown"
            value = output.get("value")

            if isinstance(value, dict):
                records.append(
                    {
                        "output_name": output_name,
                        "workspace_name": workspace_name,
                        "host_vars": value,
                        "index": None,
                    }
                )
            elif isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                for idx, item in enumerate(value):
                    records.append(
                        {
                            "output_name": output_name,
                            "workspace_name": workspace_name,
                            "host_vars": item,
                            "index": idx,
                        }
                    )

        return records
