# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/run_task.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.run_task import (
    _desired_payload,
    _fetch_run_task,
    _has_drift,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.run_task"


class TestFetchRunTask:
    def test_by_id(self):
        with patch(f"{MODULE_PATH}.get_run_task", return_value={"id": "task-1"}) as mock_get:
            assert _fetch_run_task(Mock(), {"run_task_id": "task-1"}) == {"id": "task-1"}
            mock_get.assert_called_once()

    def test_by_name(self):
        with patch(f"{MODULE_PATH}.get_run_task_by_name", return_value={"id": "task-1"}) as mock_get:
            assert _fetch_run_task(Mock(), {"organization": "org", "name": "scan"}) == {"id": "task-1"}
            mock_get.assert_called_once()

    def test_nothing_given(self):
        assert _fetch_run_task(Mock(), {}) is None


class TestDesiredPayload:
    def test_scalars(self):
        params = {"name": "scan", "url": "https://x", "category": "task", "description": "d", "enabled": True}
        payload = _desired_payload(params)
        assert payload == {"name": "scan", "url": "https://x", "category": "task", "description": "d", "enabled": True}

    def test_excludes_none(self):
        params = {"name": "scan", "url": None, "description": None, "hmac_key": None, "global_configuration": None}
        payload = _desired_payload(params)
        assert payload == {"name": "scan"}

    def test_agent_pool_and_global_config(self):
        params = {
            "agent_pool_id": "apool-1",
            "global_configuration": {"enabled": True, "stages": ["pre_plan"], "enforcement_level": "mandatory"},
        }
        payload = _desired_payload(params)
        assert payload["agent_pool"] == {"id": "apool-1"}
        assert payload["global_configuration"]["stages"] == ["pre_plan"]

    def test_hmac_key_included(self):
        assert _desired_payload({"hmac_key": "secret"}) == {"hmac_key": "secret"}


class TestHasDrift:
    def test_name_drift(self):
        assert _has_drift({"name": "b"}, {"name": "a"}) is True

    def test_url_drift(self):
        assert _has_drift({"url": "https://new"}, {"url": "https://old"}) is True

    def test_enabled_drift(self):
        assert _has_drift({"enabled": False}, {"enabled": True}) is True

    def test_no_drift_when_matching(self):
        current = {"id": "task-1", "name": "scan", "url": "https://x", "enabled": True}
        assert _has_drift({"name": "scan", "url": "https://x", "enabled": True}, current) is False

    def test_hmac_key_never_drifts(self):
        # hmac_key is write-only and excluded from drift detection.
        current = {"id": "task-1", "name": "scan"}
        assert _has_drift({"name": "scan", "hmac_key": "secret"}, current) is False

    def test_global_config_enabled_drift(self):
        current = {"global_configuration": {"enabled": False, "stages": [], "enforcement_level": "advisory"}}
        assert _has_drift({"global_configuration": {"enabled": True}}, current) is True

    def test_global_config_stages_drift(self):
        current = {"global_configuration": {"enabled": True, "stages": ["pre_plan"], "enforcement_level": "advisory"}}
        assert _has_drift({"global_configuration": {"stages": ["post_plan"]}}, current) is True

    def test_global_config_no_drift(self):
        current = {"global_configuration": {"enabled": True, "stages": ["pre_plan"], "enforcement_level": "mandatory"}}
        params = {"global_configuration": {"enabled": True, "stages": ["pre_plan"], "enforcement_level": "mandatory"}}
        assert _has_drift(params, current) is False

    def test_agent_pool_drift(self):
        assert _has_drift({"agent_pool_id": "apool-new"}, {"agent_pool": {"id": "apool-old"}}) is True

    def test_agent_pool_no_drift(self):
        assert _has_drift({"agent_pool_id": "apool-1"}, {"agent_pool": {"id": "apool-1"}}) is False

    def test_no_drift_when_unspecified(self):
        current = {"id": "task-1", "name": "scan", "enabled": True}
        assert _has_drift({"name": "scan"}, current) is False


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_when_missing(self, adapter):
        params = {"organization": "org", "name": "scan", "url": "https://x", "category": "task"}
        with patch(f"{MODULE_PATH}._fetch_run_task", return_value=None), patch(
            f"{MODULE_PATH}.create_run_task", return_value={"id": "task-1", "name": "scan"}
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)
            mock_create.assert_called_once()
            assert result["changed"] is True
            assert result["id"] == "task-1"

    def test_create_check_mode(self, adapter):
        params = {"organization": "org", "name": "scan", "url": "https://x"}
        with patch(f"{MODULE_PATH}._fetch_run_task", return_value=None), patch(f"{MODULE_PATH}.create_run_task") as mock_create:
            result = state_present(adapter, params, check_mode=True)
            mock_create.assert_not_called()
            assert result["changed"] is True
            assert "check mode" in result["msg"]

    def test_create_without_organization_raises(self, adapter):
        params = {"name": "scan", "url": "https://x"}
        with patch(f"{MODULE_PATH}._fetch_run_task", return_value=None):
            with pytest.raises(ValueError, match="organization"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_name_raises(self, adapter):
        params = {"organization": "org", "url": "https://x"}
        with patch(f"{MODULE_PATH}._fetch_run_task", return_value=None):
            with pytest.raises(ValueError, match="name"):
                state_present(adapter, params, check_mode=False)

    def test_create_without_url_raises(self, adapter):
        params = {"organization": "org", "name": "scan"}
        with patch(f"{MODULE_PATH}._fetch_run_task", return_value=None):
            with pytest.raises(ValueError, match="url"):
                state_present(adapter, params, check_mode=False)

    def test_idempotent_no_drift(self, adapter):
        current = {"id": "task-1", "name": "scan", "url": "https://x", "enabled": True}
        params = {"organization": "org", "name": "scan", "url": "https://x", "enabled": True}
        with patch(f"{MODULE_PATH}._fetch_run_task", return_value=current), patch(f"{MODULE_PATH}.update_run_task") as mock_update:
            result = state_present(adapter, params, check_mode=False)
            mock_update.assert_not_called()
            assert result["changed"] is False
            assert result["id"] == "task-1"

    def test_update_on_drift(self, adapter):
        current = {"id": "task-1", "name": "scan", "url": "https://old"}
        params = {"organization": "org", "name": "scan", "url": "https://new"}
        with patch(f"{MODULE_PATH}._fetch_run_task", return_value=current), patch(
            f"{MODULE_PATH}.update_run_task", return_value={"id": "task-1", "url": "https://new"}
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)
            mock_update.assert_called_once()
            assert result["changed"] is True
            assert result["url"] == "https://new"

    def test_update_check_mode(self, adapter):
        current = {"id": "task-1", "name": "scan", "url": "https://old"}
        params = {"organization": "org", "name": "scan", "url": "https://new"}
        with patch(f"{MODULE_PATH}._fetch_run_task", return_value=current), patch(f"{MODULE_PATH}.update_run_task") as mock_update:
            result = state_present(adapter, params, check_mode=True)
            mock_update.assert_not_called()
            assert result["changed"] is True
            assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_present(self, adapter):
        current = {"id": "task-1", "name": "scan"}
        params = {"run_task_id": "task-1"}
        with patch(f"{MODULE_PATH}._fetch_run_task", return_value=current), patch(f"{MODULE_PATH}.delete_run_task") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
            mock_delete.assert_called_once_with(adapter, "task-1")
            assert result["changed"] is True
            assert "deleted" in result["msg"]

    def test_noop_when_absent(self, adapter):
        params = {"run_task_id": "task-missing"}
        with patch(f"{MODULE_PATH}._fetch_run_task", return_value=None), patch(f"{MODULE_PATH}.delete_run_task") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
            mock_delete.assert_not_called()
            assert result["changed"] is False
            assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        current = {"id": "task-1", "name": "scan"}
        params = {"run_task_id": "task-1"}
        with patch(f"{MODULE_PATH}._fetch_run_task", return_value=current), patch(f"{MODULE_PATH}.delete_run_task") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
            mock_delete.assert_not_called()
            assert result["changed"] is True
            assert "check mode" in result["msg"]
