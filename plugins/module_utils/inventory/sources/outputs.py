# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""OutputsSource: builds inventory by querying the HCP Terraform outputs API.

Uses the ``/state-version-outputs`` endpoint (via ``get_workspace_outputs``)
to list the current state version outputs for the target workspace.

Type-expression vocabulary mirrors Terraform's official type system —
https://developer.hashicorp.com/terraform/language/expressions/types — so any
expression valid as an output's ``type`` constraint is accepted here.

Host-vars data model
--------------------
Object-shape outputs (``object``, ``list(object)``, ``set(object)``,
``map(object)``) have their user dict fields **spread flat at the top level
of host_vars**, matching common Ansible inventory plugin conventions.
``compose``, ``hostnames``, and filter expressions reference fields by their
original Terraform names (``compose: {ansible_host: public_ip}``,
``hostnames: [name]``).

Primitive-shape outputs (``string`` / ``number`` / ``bool`` /
``list(<primitive>)`` / ``set(<primitive>)`` / ``map(<primitive>)``) expose
the scalar as a single host variable named ``value`` — matching the field
name returned by Terraform's own outputs API
(``{"name": "<output>", "value": "<scalar>"}``). ``value`` is distinct from
Ansible's loop variable ``item`` and lives in a different scope, so an
``hostvars | dict2items`` loop reads ``item.value.value`` cleanly.

For ``map(...)`` shapes the map key becomes the resolved hostname and is
available as ``inventory_hostname`` — no separate ``key`` host variable is
injected, so user dicts containing a field named ``key`` are preserved
as-is.

Reserved-name collisions: when a Terraform field collides with one of
Ansible's reserved host-var names (``name``, ``groups``, ``tags``,
``inventory_hostname``, …) the var is still set but Ansible emits an
informational warning. Use the inventory-level ``hostvars_prefix`` /
``hostvars_suffix`` options to namespace every spread field at once:
``hostvars_prefix: tf_`` turns a ``name`` field into ``tf_name`` and
silences the warning.

Default mode (no ``hosts_from``)
--------------------------------
When ``hosts_from`` is omitted, only the Terraform output named
``ansible_host`` is processed. The value is treated as ``type: dynamic`` and
uses the same shape rules listed below, except that a dict of primitives is
treated as a host map so map keys become inventory hostnames and values become
``ansible_host``. All other outputs are ignored, so unrelated object outputs
do not accidentally become inventory hosts.

Explicit mode (``hosts_from`` configured)
------------------------------------------
Each ``hosts_from`` entry declares a Terraform ``type:`` constraint:

type expression                              →  host_vars
---------------------------------------------------------
``string`` / ``number`` / ``bool``           →  ``{"value": scalar}``
``object`` / ``object({attr=type,...})``     →  user dict spread flat
``list(<primitive>)`` / ``set(<primitive>)`` →  one host per element; ``{"value": scalar}``
``list(object)`` / ``set(object)``           →  one host per element; user dict spread flat
``map(<primitive>)``                         →  one host per key; ``{"value": scalar}`` (key = inventory_hostname)
``map(object)``                              →  one host per key; user dict spread flat (key = inventory_hostname)
``tuple`` / ``tuple([...])``                 →  routed through dynamic detection (wire-level
                                                 indistinguishable from a JSON array)
``dynamic`` (default when type omitted)      →  shape inferred at runtime from the value

Wire-level synonyms (Terraform types whose JSON serialization is identical):

- ``set(T)`` ≡ ``list(T)`` (both serialize as JSON arrays)
- ``object({...})`` ≡ ``object`` (the schema body is informational; Terraform
  has already validated it)
- ``tuple([...])`` ≡ ``tuple`` ≡ ``dynamic`` for sequences (the element-types
  body is informational; we run runtime detection on the JSON array)

``dynamic`` mirrors Terraform's plugin-framework "dynamic" type
(https://developer.hashicorp.com/terraform/plugin/framework/handling-data/types/dynamic):
the value's shape is determined at runtime from the JSON payload rather than
declared at the type-expression level.

Auto-``ansible_host`` for primitive shapes: when the inventory's ``compose``
option is empty, primitive shapes additionally set ``ansible_host`` to the
scalar value. This makes ``hosts_from: {output: ips, type: list(string)}``
work without any further config. Setting *any* ``compose`` entry suppresses
the auto-assignment — the user is then in full control.

Unsupported expressions — nested collections such as ``map(list(...))``,
``list(map(...))``, etc. — are rejected at validation time. Reshape the value
in your Terraform output (``flatten()``, ``for`` expressions) instead of
trying to handle it in inventory.
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
#
# Accepts every Terraform type expression from
# https://developer.hashicorp.com/terraform/language/expressions/types — the
# wire format coming back from the outputs API is JSON, so several Terraform
# types collapse to the same handler:
#
#   - ``set(T)`` is treated as ``list(T)`` (both serialize as JSON arrays)
#   - ``object({...})`` is treated as ``object`` (the schema body is
#     informational; Terraform already validated it)
#   - ``tuple`` and ``tuple([...])`` route through ``dynamic`` runtime
#     detection — element shapes are inspected per record
#
# ``dynamic`` mirrors Terraform's plugin-framework
# (https://developer.hashicorp.com/terraform/plugin/framework/handling-data/types/dynamic)
# "type determined at runtime" — when ``type`` is omitted it defaults to
# ``dynamic``.
# ---------------------------------------------------------------------------

_COLLECTION_SHAPES: Dict[Tuple[str, str], str] = {
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

# Bare type tokens (no parentheses) → internal shape tag.
_BARE_SHAPES: Dict[str, str] = {
    "dynamic": "dynamic",
    "string": "primitive",
    "number": "primitive",
    "bool": "primitive",
    "object": "object",
    "tuple": "dynamic",
}

_VALID_FORMS: Tuple[str, ...] = (
    "dynamic",
    "string",
    "number",
    "bool",
    "object",
    "object({...})",
    "tuple",
    "tuple([...])",
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

_TERRAFORM_TYPES_DOC_URL = "https://developer.hashicorp.com/terraform/language/expressions/types"

# A bare type head, optionally followed by a parenthesized body. The body's
# allowed contents depend on the head and are validated procedurally below.
_TYPE_RE = re.compile(
    r"""^\s*
        (?P<head>[A-Za-z]+)
        (?:\s*\(\s*(?P<body>.*?)\s*\)\s*)?
        \s*$""",
    re.VERBOSE | re.DOTALL,
)


def parse_type(expr: Any) -> str:
    """Parse a Terraform type expression and return the internal shape tag.

    Raises :class:`TerraformError` for empty / non-string inputs and for any
    unsupported expression. The error message lists the valid forms and links
    the user at Terraform's official type system docs.
    """
    if not isinstance(expr, str) or not expr.strip():
        raise TerraformError("hosts_from 'type' must be a non-empty string. " f"Supported forms: {', '.join(_VALID_FORMS)}. " f"See {_TERRAFORM_TYPES_DOC_URL}")

    match = _TYPE_RE.match(expr)
    if match:
        head = match.group("head")
        body = match.group("body")

        # Bare type with no body
        if body is None and head in _BARE_SHAPES:
            return _BARE_SHAPES[head]

        if body is not None:
            # object({...}) — schema body informational, treat as object
            if head == "object" and body.startswith("{") and body.endswith("}"):
                return "object"
            # tuple([...]) — element-types body informational, treat as dynamic
            if head == "tuple" and body.startswith("[") and body.endswith("]"):
                return "dynamic"
            # list/set/map(<primitive|object>)
            if (head, body) in _COLLECTION_SHAPES:
                return _COLLECTION_SHAPES[(head, body)]

    raise TerraformError(
        f"unsupported hosts_from type expression: {expr!r}. "
        f"Supported forms: {', '.join(_VALID_FORMS)}. "
        "Nested collections (map(list(...)), list(map(...)), etc.) are not "
        "supported — reshape the value in your Terraform output using "
        "flatten() or a for expression. "
        f"See {_TERRAFORM_TYPES_DOC_URL}"
    )


# ---------------------------------------------------------------------------
# Dynamic-detection of shape from runtime value
# ---------------------------------------------------------------------------


def _detect_dynamic_shape(value: Any, output_name: str) -> Optional[str]:
    """Return the internal shape tag detected from *value*, or ``None`` to skip."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "primitive"
    if isinstance(value, (str, int, float)):
        return "primitive"
    if isinstance(value, dict):
        if not value:
            _debug(f"hosts_from dynamic: output {output_name!r} is an empty dict; skipping")
            return None
        if all(isinstance(v, dict) for v in value.values()):
            return "map_object"
        return "object"
    if isinstance(value, list):
        if not value:
            _debug(f"hosts_from dynamic: output {output_name!r} is an empty list; skipping")
            return None
        if all(isinstance(item, dict) for item in value):
            return "seq_object"
        if all(isinstance(item, (str, int, float, bool)) for item in value):
            return "seq_primitive"
        _warn(
            f"hosts_from dynamic: output {output_name!r} is a list of mixed types; skipping. "
            + "Declare type explicitly or reshape in Terraform if all elements should produce hosts."
        )
        return None
    _warn(f"hosts_from dynamic: output {output_name!r} has unsupported value type {type(value).__name__}; skipping.")
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


def _primitive_host_vars(scalar: Any, auto_ansible_host: bool) -> Dict[str, Any]:
    host_vars: Dict[str, Any] = {"value": scalar}
    if auto_ansible_host:
        host_vars["ansible_host"] = scalar
    return host_vars


def _records_for_primitive(value: Any, output_name: str, workspace_name: str, auto_ansible_host: bool) -> List[HostRecord]:
    return [_record(output_name, workspace_name, _primitive_host_vars(value, auto_ansible_host))]


def _records_for_object(value: Any, output_name: str, workspace_name: str) -> List[HostRecord]:
    if not isinstance(value, dict):
        return []
    return [_record(output_name, workspace_name, dict(value))]


def _records_for_seq_primitive(value: Any, output_name: str, workspace_name: str, auto_ansible_host: bool) -> List[HostRecord]:
    if not isinstance(value, list):
        return []
    records: List[HostRecord] = []
    for idx, scalar in enumerate(value):
        records.append(_record(output_name, workspace_name, _primitive_host_vars(scalar, auto_ansible_host), index=idx))
    return records


def _records_for_seq_object(value: Any, output_name: str, workspace_name: str) -> List[HostRecord]:
    if not isinstance(value, list):
        return []
    records: List[HostRecord] = []
    for idx, element in enumerate(value):
        if isinstance(element, dict):
            records.append(_record(output_name, workspace_name, dict(element), index=idx))
    return records


def _records_for_map_primitive(value: Any, output_name: str, workspace_name: str, auto_ansible_host: bool) -> List[HostRecord]:
    if not isinstance(value, dict):
        return []
    records: List[HostRecord] = []
    for map_key, scalar in value.items():
        records.append(_record(output_name, workspace_name, _primitive_host_vars(scalar, auto_ansible_host), resolved_hostname=map_key))
    return records


def _records_for_map_object(value: Any, output_name: str, workspace_name: str) -> List[HostRecord]:
    if not isinstance(value, dict):
        return []
    records: List[HostRecord] = []
    for map_key, obj in value.items():
        if not isinstance(obj, dict):
            continue
        records.append(_record(output_name, workspace_name, dict(obj), resolved_hostname=map_key))
    return records


# ---------------------------------------------------------------------------
# hosts_from spec processor
# ---------------------------------------------------------------------------


def _collect_hosts_from_spec(
    spec: Dict[str, Any],
    outputs_map: Dict[str, Any],
    workspace_name: str,
    compose_active: bool = False,
) -> List[HostRecord]:
    """Return :class:`HostRecord` entries for one ``hosts_from`` spec.

    *outputs_map* is ``{output_name: value}`` built from the raw outputs list.
    *compose_active* indicates whether the user has any inventory ``compose``
    entries set; when ``False``, primitive shapes auto-assign ``ansible_host``
    to the primitive value. Object shapes never auto-assign.

    Returns an empty list when the named output is absent or the runtime value
    does not match the declared shape (or when ``type: dynamic`` cannot pick a
    supported shape from the value).
    """
    output_name: str = spec.get("output", "")
    type_expr: str = spec.get("type") or "dynamic"

    if output_name not in outputs_map:
        return []

    shape = parse_type(type_expr)
    value = outputs_map[output_name]

    if shape == "dynamic":
        detected = _detect_dynamic_shape(value, output_name)
        if detected is None:
            return []
        shape = detected

    auto_ah = not compose_active

    if shape == "primitive":
        return _records_for_primitive(value, output_name, workspace_name, auto_ah)
    if shape == "object":
        return _records_for_object(value, output_name, workspace_name)
    if shape == "seq_primitive":
        return _records_for_seq_primitive(value, output_name, workspace_name, auto_ah)
    if shape == "seq_object":
        return _records_for_seq_object(value, output_name, workspace_name)
    if shape == "map_primitive":
        return _records_for_map_primitive(value, output_name, workspace_name, auto_ah)
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
            if "use_as" in spec:
                raise TerraformError(
                    f"hosts_from[{idx}]: 'use_as' is no longer supported. "
                    "Use the inventory-level 'compose' option instead "
                    "(e.g. 'compose: {ansible_host: value}'). For primitive shapes, "
                    "'ansible_host' is now set automatically when 'compose' is empty."
                )
            if "item" in spec:
                raise TerraformError(
                    f"hosts_from[{idx}]: 'item' is not a recognised spec key. "
                    "If you meant the host variable for primitive elements, it is now "
                    "named 'value' (matching Terraform's outputs API). Reference it as "
                    "'value' in compose / hostnames / templates."
                )
            if "key" in spec:
                raise TerraformError(
                    f"hosts_from[{idx}]: 'key' is not a recognised spec key. "
                    "For map(...) shapes the map key is exposed as 'inventory_hostname' "
                    "(no separate 'key' host variable is injected). Reference it as "
                    "'inventory_hostname' in compose / templates."
                )
            output_name = spec.get("output")
            if not isinstance(output_name, str) or not output_name:
                raise TerraformError(f"hosts_from[{idx}] requires a non-empty 'output' string.")
            type_expr = spec.get("type", "dynamic")
            parse_type(type_expr)

    def collect_hosts(self) -> List[HostRecord]:
        workspace_id_opt = self.options.get("workspace_id")
        organization = self.options.get("organization")
        workspace = self.options.get("workspace")

        hosts_from_opt = self.options.get("hosts_from") or []
        if isinstance(hosts_from_opt, dict):
            hosts_from_opt = [hosts_from_opt]

        compose_opt = self.options.get("compose") or {}
        compose_active = bool(compose_opt)

        resolved_id, workspace_name = resolve_workspace(self.client, workspace_id_opt, organization, workspace)

        # Cache-aware fetch: the inventory plugin may set ``_cached_payload`` to
        # a previously fetched outputs list to skip the download. After a live
        # fetch we expose the payload via ``_fetched_payload`` so the plugin
        # can write it to the cache.
        cached_payload = getattr(self, "_cached_payload", None)
        if cached_payload is not None:
            outputs = cached_payload
        else:
            outputs = fetch_outputs(self.client, resolved_id)
            self._fetched_payload = outputs

        if hosts_from_opt:
            outputs_map: Dict[str, Any] = {o.get("name", ""): o.get("value") for o in outputs if isinstance(o, dict)}
            records: List[HostRecord] = []
            for spec in hosts_from_opt:
                records.extend(_collect_hosts_from_spec(spec, outputs_map, workspace_name, compose_active))
            return records

        # Default mode is intentionally narrow: only a Terraform output named
        # ``ansible_host`` is treated as inventory. A dict of primitives is
        # interpreted as a host map (map keys are hostnames, values become
        # ansible_host); users can opt into any other output name or force a
        # single-object interpretation with explicit ``hosts_from``.
        outputs_map = {o.get("name", ""): o.get("value") for o in outputs if isinstance(o, dict)}
        ansible_host_value = outputs_map.get("ansible_host")
        if isinstance(ansible_host_value, dict) and ansible_host_value and all(isinstance(v, (str, int, float, bool)) for v in ansible_host_value.values()):
            return _collect_hosts_from_spec(
                {"output": "ansible_host", "type": "map(string)"},
                outputs_map,
                workspace_name,
                compose_active,
            )
        return _collect_hosts_from_spec(
            {"output": "ansible_host", "type": "dynamic"},
            outputs_map,
            workspace_name,
            compose_active,
        )
