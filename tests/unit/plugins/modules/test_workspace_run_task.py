# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/workspace_run_task.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.workspace_run_task import (
    _desired_payload,
    _fetch_workspace_run_task,
    _has_drift,
    _resolve_run_task_id,
    _resolve_workspace_id,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.workspace_run_task"


class TestResolveWorkspaceId:
    def test_by_id(self):
        assert _resolve_workspace_id(Mock(), {"workspace_id": "ws-1"}) == "ws-1"

    def test_by_name(self):
        with patch(f"{MODULE_PATH}.get_workspace", return_value={"id": "ws-9"}) as mock_get:
            assert _resolve_workspace_id(Mock(), {"organization": "org", "workspace": "w"}) == "ws-9"
            mock_get.assert_called_once()

    def test_by_name_not_found_raises(self):
        with patch(f"{MODULE_PATH}.get_workspace", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                _resolve_workspace_id(Mock(), {"organization": "org", "workspace": "w"})

    def test_missing_identifiers_raises(self):
        with pytest.raises(ValueError, match="required"):
            _resolve_workspace_id(Mock(), {})


class TestResolveRunTaskId:
    def test_by_id(self):
        assert _resolve_run_task_id(Mock(), {"run_task_id": "task-1"}) == "task-1"

    def test_by_name(self):
        with patch(f"{MODULE_PATH}.get_run_task_by_name", return_value={"id": "task-7"}) as mock_get:
            assert _resolve_run_task_id(Mock(), {"organization": "org", "run_task_name": "scan"}) == "task-7"
            mock_get.assert_called_once()

    def test_by_name_not_found_raises(self):
        with patch(f"{MODULE_PATH}.get_run_task_by_name", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                _resolve_run_task_id(Mock(), {"organization": "org", "run_task_name": "ghost"})

    def test_name_without_org_raises(self):
        with pytest.raises(ValueError, match="organization"):
            _resolve_run_task_id(Mock(), {"run_task_name": "scan"})

    def test_nothing_given(self):
        assert _resolve_run_task_id(Mock(), {}) is None


class TestFetchWorkspaceRunTask:
    def test_by_association_id(self):
        with patch(f"{MODULE_PATH}.get_workspace_run_task", return_value={"id": "wstask-1"}) as mock_get:
            assert _fetch_workspace_run_task(Mock(), "ws-1", {"workspace_run_task_id": "wstask-1"}) == {"id": "wstask-1"}
            mock_get.assert_called_once()

    def test_by_run_task(self):
        with patch(f"{MODULE_PATH}._resolve_run_task_id", return_value="task-1"), patch(
            f"{MODULE_PATH}.get_workspace_run_task_by_run_task", return_value={"id": "wstask-2"}
        ) as mock_get:
            assert _fetch_workspace_run_task(Mock(), "ws-1", {"run_task_id": "task-1"}) == {"id": "wstask-2"}
            mock_get.assert_called_once()

    def test_nothing_given(self):
        with patch(f"{MODULE_PATH}._resolve_run_task_id", return_value=None):
            assert _fetch_workspace_run_task(Mock(), "ws-1", {}) is None


class TestDesiredPayload:
    def test_create_includes_run_task(self):
        params = {"enforcement_level": "advisory", "stages": ["post_plan"]}
        payload = _desired_payload(params, run_task_id="task-1")
        assert payload == {
            "enforcement_level": "advisory",
            "stages": ["post_plan"],
            "run_task": {"id": "task-1"},
        }

    def test_update_excludes_run_task(self):
        params = {"enforcement_level": "mandatory"}
        payload = _desired_payload(params)
        assert payload == {"enforcement_level": "mandatory"}

    def test_excludes_none(self):
        params = {"enforcement_level": None, "stages": None}
        assert _desired_payload(params) == {}


class TestHasDrift:
    def test_enforcement_drift(self):
        assert _has_drift({"enforcement_level": "mandatory"}, {"enforcement_level": "advisory"}) is True

    def test_stages_drift(self):
        assert _has_drift({"stages": ["pre_plan"]}, {"stages": ["post_plan"]}) is True

    def test_stages_order_insensitive(self):
        current = {"stages": ["post_plan", "pre_plan"]}
        assert _has_drift({"stages": ["pre_plan", "post_plan"]}, current) is False

    def test_run_task_is_not_drift(self):
        current = {"enforcement_level": "advisory", "run_task": {"id": "task-1"}}
        assert _has_drift({"enforcement_level": "advisory", "run_task_id": "task-2"}, current) is False

    def test_no_drift_when_matching(self):
        current = {"enforcement_level": "advisory", "stages": ["post_plan"]}
        assert _has_drift({"enforcement_level": "advisory", "stages": ["post_plan"]}, current) is False

    def test_no_drift_when_unspecified(self):
        current = {"enforcement_level": "advisory", "stages": ["post_plan"]}
        assert _has_drift({}, current) is False


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_when_missing(self, adapter):
        params = {"workspace_id": "ws-1", "run_task_id": "task-1", "enforcement_level": "advisory"}
        with patch(f"{MODULE_PATH}._resolve_workspace_id", return_value="ws-1"), patch(f"{MODULE_PATH}._fetch_workspace_run_task", return_value=None), patch(
            f"{MODULE_PATH}._resolve_run_task_id", return_value="task-1"
        ), patch(f"{MODULE_PATH}.create_workspace_run_task", return_value={"id": "wstask-1", "enforcement_level": "advisory"}) as mock_create:
            result = state_present(adapter, params, check_mode=False)
            mock_create.assert_called_once()
            assert result["changed"] is True
            assert result["id"] == "wstask-1"

    def test_create_check_mode(self, adapter):
        params = {"workspace_id": "ws-1", "run_task_id": "task-1", "enforcement_level": "advisory"}
        with patch(f"{MODULE_PATH}._resolve_workspace_id", return_value="ws-1"), patch(f"{MODULE_PATH}._fetch_workspace_run_task", return_value=None), patch(
            f"{MODULE_PATH}._resolve_run_task_id", return_value="task-1"
        ), patch(f"{MODULE_PATH}.create_workspace_run_task") as mock_create:
            result = state_present(adapter, params, check_mode=True)
            mock_create.assert_not_called()
            assert result["changed"] is True
            assert "check mode" in result["msg"]

    def test_create_without_run_task_raises(self, adapter):
        params = {"workspace_id": "ws-1", "enforcement_level": "advisory"}
        with patch(f"{MODULE_PATH}._resolve_workspace_id", return_value="ws-1"), patch(f"{MODULE_PATH}._fetch_workspace_run_task", return_value=None), patch(
            f"{MODULE_PATH}._resolve_run_task_id", return_value=None
        ):
            with pytest.raises(ValueError, match="run_task"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_enforcement_raises(self, adapter):
        params = {"workspace_id": "ws-1", "run_task_id": "task-1"}
        with patch(f"{MODULE_PATH}._resolve_workspace_id", return_value="ws-1"), patch(f"{MODULE_PATH}._fetch_workspace_run_task", return_value=None), patch(
            f"{MODULE_PATH}._resolve_run_task_id", return_value="task-1"
        ):
            with pytest.raises(ValueError, match="enforcement_level"):
                state_present(adapter, params, check_mode=False)

    def test_idempotent_no_drift(self, adapter):
        current = {"id": "wstask-1", "enforcement_level": "advisory", "stages": ["post_plan"]}
        params = {"workspace_id": "ws-1", "run_task_id": "task-1", "enforcement_level": "advisory", "stages": ["post_plan"]}
        with patch(f"{MODULE_PATH}._resolve_workspace_id", return_value="ws-1"), patch(f"{MODULE_PATH}._fetch_workspace_run_task", return_value=current), patch(
            f"{MODULE_PATH}.update_workspace_run_task"
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
            mock_update.assert_not_called()
            assert result["changed"] is False
            assert result["id"] == "wstask-1"

    def test_update_on_drift(self, adapter):
        current = {"id": "wstask-1", "enforcement_level": "advisory"}
        params = {"workspace_id": "ws-1", "run_task_id": "task-1", "enforcement_level": "mandatory"}
        with patch(f"{MODULE_PATH}._resolve_workspace_id", return_value="ws-1"), patch(f"{MODULE_PATH}._fetch_workspace_run_task", return_value=current), patch(
            f"{MODULE_PATH}.update_workspace_run_task", return_value={"id": "wstask-1", "enforcement_level": "mandatory"}
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
            mock_update.assert_called_once()
            assert result["changed"] is True
            assert result["enforcement_level"] == "mandatory"

    def test_update_check_mode(self, adapter):
        current = {"id": "wstask-1", "enforcement_level": "advisory"}
        params = {"workspace_id": "ws-1", "run_task_id": "task-1", "enforcement_level": "mandatory"}
        with patch(f"{MODULE_PATH}._resolve_workspace_id", return_value="ws-1"), patch(f"{MODULE_PATH}._fetch_workspace_run_task", return_value=current), patch(
            f"{MODULE_PATH}.update_workspace_run_task"
        ) as mock_update:
            result = state_present(adapter, params, check_mode=True)
            mock_update.assert_not_called()
            assert result["changed"] is True
            assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_present(self, adapter):
        current = {"id": "wstask-1"}
        params = {"workspace_id": "ws-1", "workspace_run_task_id": "wstask-1"}
        with patch(f"{MODULE_PATH}._resolve_workspace_id", return_value="ws-1"), patch(f"{MODULE_PATH}._fetch_workspace_run_task", return_value=current), patch(
            f"{MODULE_PATH}.delete_workspace_run_task"
        ) as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
            mock_delete.assert_called_once_with(adapter, "ws-1", "wstask-1")
            assert result["changed"] is True
            assert "deleted" in result["msg"]

    def test_noop_when_absent(self, adapter):
        params = {"workspace_id": "ws-1", "run_task_id": "task-missing"}
        with patch(f"{MODULE_PATH}._resolve_workspace_id", return_value="ws-1"), patch(f"{MODULE_PATH}._fetch_workspace_run_task", return_value=None), patch(
            f"{MODULE_PATH}.delete_workspace_run_task"
        ) as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
            mock_delete.assert_not_called()
            assert result["changed"] is False
            assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        current = {"id": "wstask-1"}
        params = {"workspace_id": "ws-1", "workspace_run_task_id": "wstask-1"}
        with patch(f"{MODULE_PATH}._resolve_workspace_id", return_value="ws-1"), patch(f"{MODULE_PATH}._fetch_workspace_run_task", return_value=current), patch(
            f"{MODULE_PATH}.delete_workspace_run_task"
        ) as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
            mock_delete.assert_not_called()
            assert result["changed"] is True
            assert "check mode" in result["msg"]
