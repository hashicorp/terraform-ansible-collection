# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/policy.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.policy import state_absent, state_present

MOD = "ansible_collections.hashicorp.terraform.plugins.modules.policy"


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def _base_params(self, **overrides):
        params = {
            "policy_id": None,
            "organization": "my-org",
            "name": "restrict-instance-type",
            "kind": None,
            "query": None,
            "description": None,
            "enforcement_level": "hard-mandatory",
            "policy_content": None,
            "state": "present",
            "check_mode": False,
        }
        params.update(overrides)
        return params

    def test_create_when_missing(self, adapter):
        params = self._base_params()
        with patch(f"{MOD}._fetch_policy", return_value=None), patch(
            f"{MOD}.create_policy", return_value={"id": "pol-1", "name": "restrict-instance-type"}
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)

        create_data = mock_create.call_args[0][2]
        assert create_data["kind"] == "sentinel"  # defaulted, not user-specified
        assert result["changed"] is True
        assert result["id"] == "pol-1"

    def test_create_check_mode(self, adapter):
        params = self._base_params(check_mode=True)
        with patch(f"{MOD}._fetch_policy", return_value=None), patch(f"{MOD}.create_policy") as mock_create:
            result = state_present(adapter, params, check_mode=True)

        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_create_uploads_content(self, adapter):
        params = self._base_params(policy_content="main = rule { true }")
        with patch(f"{MOD}._fetch_policy", return_value=None), patch(f"{MOD}.create_policy", return_value={"id": "pol-1"}), patch(
            f"{MOD}.upload_policy_content"
        ) as mock_upload:
            state_present(adapter, params, check_mode=False)

        mock_upload.assert_called_once_with(adapter, "pol-1", "main = rule { true }")

    def test_create_missing_enforcement_level_raises(self, adapter):
        params = self._base_params(enforcement_level=None)
        with patch(f"{MOD}._fetch_policy", return_value=None):
            with pytest.raises(ValueError, match="enforcement_level"):
                state_present(adapter, params, check_mode=False)

    def test_create_opa_without_query_raises(self, adapter):
        params = self._base_params(kind="opa")
        with patch(f"{MOD}._fetch_policy", return_value=None):
            with pytest.raises(ValueError, match="query"):
                state_present(adapter, params, check_mode=False)

    def test_kind_drift_raises_without_touching_kind_default(self, adapter):
        # Regression: kind has no argspec default, so an unset kind must never
        # be compared as if it were "sentinel".
        current = {"id": "pol-1", "name": "restrict-instance-type", "kind": "opa", "enforcement_level": "hard-mandatory"}
        params = self._base_params()  # kind left unset
        with patch(f"{MOD}._fetch_policy", return_value=current):
            result = state_present(adapter, params, check_mode=False)
        assert result["changed"] is False

    def test_kind_drift_explicit_raises(self, adapter):
        current = {"id": "pol-1", "name": "restrict-instance-type", "kind": "opa", "enforcement_level": "hard-mandatory"}
        params = self._base_params(kind="sentinel")
        with patch(f"{MOD}._fetch_policy", return_value=current):
            with pytest.raises(ValueError, match="immutable"):
                state_present(adapter, params, check_mode=False)

    def test_idempotent_no_diff(self, adapter):
        current = {"id": "pol-1", "name": "restrict-instance-type", "kind": "sentinel", "enforcement_level": "hard-mandatory"}
        params = self._base_params()
        with patch(f"{MOD}._fetch_policy", return_value=current), patch(f"{MOD}.update_policy") as mock_update:
            result = state_present(adapter, params, check_mode=False)

        mock_update.assert_not_called()
        assert result["changed"] is False

    def test_update_on_attr_drift(self, adapter):
        current = {"id": "pol-1", "name": "restrict-instance-type", "kind": "sentinel", "enforcement_level": "advisory"}
        params = self._base_params(enforcement_level="hard-mandatory")
        with patch(f"{MOD}._fetch_policy", return_value=current), patch(
            f"{MOD}.update_policy", return_value={"id": "pol-1", "enforcement_level": "hard-mandatory"}
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)

        mock_update.assert_called_once_with(adapter, "pol-1", {"enforcement_level": "hard-mandatory"})
        assert result["changed"] is True

    def test_content_drift_triggers_upload(self, adapter):
        current = {"id": "pol-1", "name": "restrict-instance-type", "kind": "sentinel", "enforcement_level": "hard-mandatory"}
        params = self._base_params(policy_content="main = rule { false }")
        with patch(f"{MOD}._fetch_policy", return_value=current), patch(f"{MOD}.download_policy_content", return_value="main = rule { true }"), patch(
            f"{MOD}.upload_policy_content"
        ) as mock_upload:
            result = state_present(adapter, params, check_mode=False)

        mock_upload.assert_called_once_with(adapter, "pol-1", "main = rule { false }")
        assert result["changed"] is True

    def test_content_no_diff_no_upload(self, adapter):
        current = {"id": "pol-1", "name": "restrict-instance-type", "kind": "sentinel", "enforcement_level": "hard-mandatory"}
        params = self._base_params(policy_content="main = rule { true }")
        with patch(f"{MOD}._fetch_policy", return_value=current), patch(f"{MOD}.download_policy_content", return_value="main = rule { true }"), patch(
            f"{MOD}.upload_policy_content"
        ) as mock_upload:
            result = state_present(adapter, params, check_mode=False)

        mock_upload.assert_not_called()
        assert result["changed"] is False


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_existing(self, adapter):
        current = {"id": "pol-1"}
        params = {"policy_id": "pol-1", "state": "absent", "check_mode": False}
        with patch(f"{MOD}._fetch_policy", return_value=current), patch(f"{MOD}.delete_policy") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)

        mock_delete.assert_called_once_with(adapter, "pol-1")
        assert result["changed"] is True

    def test_delete_absent_is_noop(self, adapter):
        params = {"policy_id": "pol-ghost", "state": "absent", "check_mode": False}
        with patch(f"{MOD}._fetch_policy", return_value=None):
            result = state_absent(adapter, params, check_mode=False)
        assert result["changed"] is False

    def test_delete_check_mode(self, adapter):
        current = {"id": "pol-1"}
        params = {"policy_id": "pol-1", "state": "absent", "check_mode": True}
        with patch(f"{MOD}._fetch_policy", return_value=current), patch(f"{MOD}.delete_policy") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)

        mock_delete.assert_not_called()
        assert result["changed"] is True
