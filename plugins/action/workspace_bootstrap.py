# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Day-0 workspace orchestration: workspace + variables + triggers + notifications.

Wraps pytfe-backed module_utils helpers to converge a full workspace baseline
with a single task. Re-running with the same desired state is a no-op.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.plugins.action import ActionBase

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.notification_configuration import (
    create_notification_configuration,
    delete_notification_configuration,
    get_notification_configuration_by_name,
    list_notification_configurations,
    update_notification_configuration,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.run_trigger import (
    create_run_trigger,
    delete_run_trigger,
    find_run_trigger,
    list_run_triggers,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff
from ansible_collections.hashicorp.terraform.plugins.module_utils.variable import (
    create_variable,
    delete_variable,
    get_variable_by_key,
    update_variable,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.variable_sets import (
    apply_to_workspaces,
    get_variable_set,
    get_variable_set_by_name,
    remove_from_workspaces,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.workspace import (
    create_workspace,
    get_workspace,
    get_workspace_by_id,
    update_workspace,
)

_WORKSPACE_DRIFT_KEYS = {"description", "execution_mode", "terraform_version", "working_directory", "auto_apply"}
_VAR_DRIFT_KEYS = {"value", "description", "category", "hcl", "sensitive"}


class ActionModule(ActionBase):

    _VALID_ARGS = frozenset(
        (
            "workspace_id",
            "workspace",
            "organization",
            "settings",
            "variables",
            "variable_sets",
            "run_triggers",
            "notifications",
            "reconcile",
            "tfe_token",
            "tfe_address",
            "tfe_timeout",
            "tfe_verify_tls",
            "tf_token",
            "tf_hostname",
        )
    )

    def _fail(self, result, msg, **extra):
        result.update({"failed": True, "changed": False, "msg": msg, **extra})
        return result

    # ------------------------------------------------------------------
    # Component reconcilers — each returns a per-component summary dict.
    # ------------------------------------------------------------------

    def _reconcile_workspace(self, adapter, args):
        workspace_id = args.get("workspace_id")
        organization = args.get("organization")
        name = args.get("workspace")
        settings = args.get("settings") or {}

        current = None
        if workspace_id:
            current = get_workspace_by_id(adapter, workspace_id)
        elif organization and name:
            current = get_workspace(adapter, organization, name)

        if current is None:
            if not (organization and name):
                raise ValueError("organization and workspace are required to create a new workspace.")
            created = create_workspace(adapter, organization, name=name, **settings)
            data = created.get("data", created)
            return {"changed": True, "id": data.get("id"), "action": "created"}, data.get("id")

        want = {k: v for k, v in settings.items() if v is not None and k in _WORKSPACE_DRIFT_KEYS}
        have = {k: current.get(k) for k in want.keys()}
        diff = dict_diff(have, want)
        if not diff:
            return {"changed": False, "id": current["id"], "action": "none"}, current["id"]

        update_workspace(adapter, current["id"], **diff)
        return {"changed": True, "id": current["id"], "action": "updated"}, current["id"]

    def _reconcile_variables(self, adapter, workspace_id, desired, reconcile):
        """Converge workspace-scoped variables. ``reconcile`` controls deletion of extras."""
        summary = {"changed": False, "created": [], "updated": [], "deleted": []}
        if desired is None:
            return summary

        desired_by_key = {(v["key"], v.get("category", "terraform")): v for v in desired}

        for (key, category), spec in desired_by_key.items():
            payload = {k: v for k, v in spec.items() if k in _VAR_DRIFT_KEYS | {"key"} and v is not None}
            payload.setdefault("key", key)
            payload.setdefault("category", category)

            current = get_variable_by_key(adapter, workspace_id, key, category=category)
            if current is None:
                create_variable(adapter, workspace_id, payload)
                summary["created"].append(key)
                summary["changed"] = True
                continue

            want = {k: v for k, v in payload.items() if k in _VAR_DRIFT_KEYS and v is not None}
            have = {k: current.get(k) for k in want.keys()}
            if want.get("sensitive") or current.get("sensitive"):
                have.pop("value", None)
                want.pop("value", None)
            diff = dict_diff(have, want)
            if diff:
                update_variable(adapter, workspace_id, current["id"], want)
                summary["updated"].append(key)
                summary["changed"] = True

        if reconcile:
            for v in _list_workspace_variables(adapter, workspace_id):
                k = (v.get("key"), v.get("category"))
                if k not in desired_by_key:
                    delete_variable(adapter, workspace_id, v["id"])
                    summary["deleted"].append(v.get("key"))
                    summary["changed"] = True

        return summary

    def _reconcile_variable_sets(self, adapter, workspace_id, organization, desired):
        """Attach/detach variable sets by ID or name. ``desired`` is the target set."""
        summary = {"changed": False, "attached": [], "detached": []}
        if desired is None:
            return summary

        target_ids = set()
        for spec in desired:
            if isinstance(spec, str):
                target_ids.add(spec)
            elif isinstance(spec, dict) and spec.get("id"):
                target_ids.add(spec["id"])
            elif isinstance(spec, dict) and spec.get("name") and organization:
                vs = get_variable_set_by_name(adapter, organization, spec["name"])
                if not vs:
                    raise ValueError(f"Variable set {spec['name']!r} not found.")
                target_ids.add(vs["id"])
            else:
                raise ValueError("Each variable_sets entry must be an id string or a dict with 'id' or 'name'.")

        for vs_id in target_ids:
            vs = get_variable_set(adapter, vs_id, include_relations=True) or {}
            attached_ws_ids = {w.get("id") for w in (vs.get("workspaces") or [])}
            if workspace_id not in attached_ws_ids:
                apply_to_workspaces(adapter, vs_id, [workspace_id])
                summary["attached"].append(vs_id)
                summary["changed"] = True

        return summary

    def _reconcile_run_triggers(self, adapter, workspace_id, desired, reconcile):
        """Converge inbound run triggers for the workspace."""
        summary = {"changed": False, "created": [], "deleted": []}
        if desired is None:
            return summary

        target_sourceables = set()
        for spec in desired:
            if isinstance(spec, str):
                target_sourceables.add(spec)
            elif isinstance(spec, dict) and spec.get("sourceable_id"):
                target_sourceables.add(spec["sourceable_id"])
            else:
                raise ValueError("Each run_triggers entry must be a sourceable workspace id or a dict with 'sourceable_id'.")

        for src_id in target_sourceables:
            if find_run_trigger(adapter, workspace_id, src_id) is None:
                create_run_trigger(adapter, workspace_id, src_id)
                summary["created"].append(src_id)
                summary["changed"] = True

        if reconcile:
            for trigger in list_run_triggers(adapter, workspace_id):
                src = (trigger.get("sourceable") or {}).get("id")
                if src and src not in target_sourceables:
                    delete_run_trigger(adapter, trigger["id"])
                    summary["deleted"].append(trigger["id"])
                    summary["changed"] = True

        return summary

    def _reconcile_notifications(self, adapter, workspace_id, desired, reconcile):
        """Converge notification configurations keyed by name."""
        summary = {"changed": False, "created": [], "updated": [], "deleted": []}
        if desired is None:
            return summary

        desired_by_name = {n["name"]: n for n in desired}
        for name, spec in desired_by_name.items():
            current = get_notification_configuration_by_name(adapter, workspace_id, name)
            if current is None:
                create_notification_configuration(adapter, workspace_id, spec)
                summary["created"].append(name)
                summary["changed"] = True
                continue
            want = {k: v for k, v in spec.items() if v is not None}
            have = {k: current.get(k) for k in want.keys()}
            diff = dict_diff(have, want)
            if diff:
                update_notification_configuration(adapter, current["id"], diff)
                summary["updated"].append(name)
                summary["changed"] = True

        if reconcile:
            for nc in list_notification_configurations(adapter, workspace_id):
                if nc.get("name") not in desired_by_name:
                    delete_notification_configuration(adapter, nc["id"])
                    summary["deleted"].append(nc.get("name"))
                    summary["changed"] = True

        return summary

    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars) or {}
        args = self._task.args or {}

        reconcile = bool(args.get("reconcile", True))
        components = {}
        try:
            with TerraformClient.from_mapping(args) as adapter:
                ws_summary, workspace_id = self._reconcile_workspace(adapter, args)
                components["workspace"] = ws_summary

                components["variables"] = self._reconcile_variables(
                    adapter, workspace_id, args.get("variables"), reconcile
                )
                components["variable_sets"] = self._reconcile_variable_sets(
                    adapter, workspace_id, args.get("organization"), args.get("variable_sets")
                )
                components["run_triggers"] = self._reconcile_run_triggers(
                    adapter, workspace_id, args.get("run_triggers"), reconcile
                )
                components["notifications"] = self._reconcile_notifications(
                    adapter, workspace_id, args.get("notifications"), reconcile
                )

            changed = any(c.get("changed") for c in components.values())
            result.update({"changed": changed, "workspace_id": workspace_id, "components": components})
            return result
        except ValueError as e:
            return self._fail(result, str(e), components=components)
        except Exception as e:
            return self._fail(result, f"workspace_bootstrap failed: {e}", components=components)


def _list_workspace_variables(adapter, workspace_id):
    # Local import to keep the top-level import list tidy and avoid a circular-ish
    # reference with action-plugin load order.
    from ansible_collections.hashicorp.terraform.plugins.module_utils.variable import list_variables

    return list_variables(adapter, workspace_id)
