# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/hyok_configuration.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.hyok_configuration import (
    _build_desired_state,
    state_absent,
    state_present,
)

MOD = "ansible_collections.hashicorp.terraform.plugins.modules.hyok_configuration"


@pytest.fixture(autouse=True)
def no_sleep():
    with patch(f"{MOD}.time.sleep"):
        yield


class TestBuildDesiredState:
    def test_strips_plumbing(self):
        params = {
            "name": "prod-key",
            "kek_id": "kek-1",
            "organization": "my-org",
            "hyok_configuration_id": None,
            "state": "present",
            "check_mode": False,
            "test": False,
            "wait": True,
            "timeout": 300,
            "poll_interval": 5,
            "primary": None,
        }
        assert _build_desired_state(params) == {"name": "prod-key", "kek_id": "kek-1"}


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def _base_params(self, **overrides):
        params = {
            "organization": "my-org",
            "name": "prod-key",
            "kek_id": "kek-1",
            "agent_pool_id": "apool-1",
            "oidc_configuration_id": "aoidc-1",
            "oidc_configuration_type": "aws",
            "primary": None,
            "kms_options": None,
            "hyok_configuration_id": None,
            "test": False,
            "wait": True,
            "timeout": 300,
            "poll_interval": 5,
            "state": "present",
            "check_mode": False,
        }
        params.update(overrides)
        return params

    def test_create_when_missing(self, adapter):
        params = self._base_params()
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=None), patch(
            f"{MOD}.create_hyok_configuration", return_value={"id": "hyokc-1", "name": "prod-key", "status": "untested"}
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)

        mock_create.assert_called_once()
        assert mock_create.call_args[0][1] == "my-org"
        assert result["changed"] is True
        assert result["id"] == "hyokc-1"

    def test_create_check_mode(self, adapter):
        params = self._base_params(check_mode=True)
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=None), patch(f"{MOD}.create_hyok_configuration") as mock_create:
            result = state_present(adapter, params, check_mode=True)

        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_missing_required_raises(self, adapter):
        params = self._base_params(kek_id=None)
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=None):
            with pytest.raises(ValueError, match="kek_id"):
                state_present(adapter, params, check_mode=False)

    def test_idempotent_no_diff(self, adapter):
        current = {
            "id": "hyokc-1",
            "name": "prod-key",
            "kek_id": "kek-1",
            "agent_pool_id": "apool-1",
            "oidc_configuration_id": "aoidc-1",
            # The wire value the API actually reports - not the short argspec
            # choice ("aws") the caller supplies. _base_params() defaults
            # oidc_configuration_type to "aws"; state_present must map it to
            # this wire value before comparing, or every re-run would falsely
            # detect drift on this field (regression: previously compared
            # "aws" directly against "aws-oidc-configurations").
            "oidc_configuration_type": "aws-oidc-configurations",
            "status": "available",
        }
        params = self._base_params()
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=current), patch(f"{MOD}.create_hyok_configuration") as mock_create:
            result = state_present(adapter, params, check_mode=False)

        mock_create.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "hyokc-1"

    def test_drift_raises(self, adapter):
        current = {
            "id": "hyokc-1",
            "name": "prod-key",
            "kek_id": "kek-OLD",
            "agent_pool_id": "apool-1",
            "oidc_configuration_id": "aoidc-1",
            "oidc_configuration_type": "aws-oidc-configurations",
            "status": "available",
        }
        params = self._base_params(kek_id="kek-NEW")
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=current):
            with pytest.raises(ValueError, match="immutable"):
                state_present(adapter, params, check_mode=False)

    def test_test_action_success_on_create(self, adapter):
        params = self._base_params(test=True)
        created = {"id": "hyokc-1", "name": "prod-key", "status": "untested"}
        polled = {"id": "hyokc-1", "name": "prod-key", "status": "available"}
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=None), patch(f"{MOD}.create_hyok_configuration", return_value=created), patch(
            f"{MOD}.run_hyok_configuration_test"
        ) as mock_test, patch(f"{MOD}.get_hyok_configuration", return_value=polled):
            result = state_present(adapter, params, check_mode=False)

        mock_test.assert_called_once_with(adapter, "hyokc-1")
        assert result["status"] == "available"
        assert result["changed"] is True

    def test_test_action_failure_raises(self, adapter):
        params = self._base_params(test=True)
        created = {"id": "hyokc-1", "name": "prod-key", "status": "untested"}
        polled = {"id": "hyokc-1", "name": "prod-key", "status": "test_failed", "error": "kms access denied"}
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=None), patch(f"{MOD}.create_hyok_configuration", return_value=created), patch(
            f"{MOD}.run_hyok_configuration_test"
        ), patch(f"{MOD}.get_hyok_configuration", return_value=polled):
            with pytest.raises(ValueError, match="test failed"):
                state_present(adapter, params, check_mode=False)

    def test_test_action_no_wait_returns_immediately(self, adapter):
        params = self._base_params(test=True, wait=False)
        created = {"id": "hyokc-1", "name": "prod-key", "status": "untested"}
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=None), patch(f"{MOD}.create_hyok_configuration", return_value=created), patch(
            f"{MOD}.run_hyok_configuration_test"
        ) as mock_test, patch(f"{MOD}.get_hyok_configuration") as mock_get:
            result = state_present(adapter, params, check_mode=False)

        mock_test.assert_called_once()
        mock_get.assert_not_called()
        assert result["changed"] is True
        assert "wait=false" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def _params(self, **overrides):
        params = {
            "hyok_configuration_id": "hyokc-1",
            "organization": None,
            "name": None,
            "wait": True,
            "timeout": 300,
            "poll_interval": 5,
            "state": "absent",
            "check_mode": False,
        }
        params.update(overrides)
        return params

    def test_delete_absent_is_noop(self, adapter):
        params = self._params()
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=None):
            result = state_absent(adapter, params, check_mode=False)

        assert result["changed"] is False

    def test_delete_check_mode(self, adapter):
        current = {"id": "hyokc-1", "status": "available"}
        params = self._params(check_mode=True)
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=current), patch(f"{MOD}.revoke_hyok_configuration") as mock_revoke, patch(
            f"{MOD}.delete_hyok_configuration"
        ) as mock_delete:
            result = state_absent(adapter, params, check_mode=True)

        mock_revoke.assert_not_called()
        mock_delete.assert_not_called()
        assert result["changed"] is True

    def test_already_revoked_deletes_directly(self, adapter):
        current = {"id": "hyokc-1", "status": "revoked"}
        params = self._params()
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=current), patch(f"{MOD}.revoke_hyok_configuration") as mock_revoke, patch(
            f"{MOD}.delete_hyok_configuration"
        ) as mock_delete:
            result = state_absent(adapter, params, check_mode=False)

        mock_revoke.assert_not_called()
        mock_delete.assert_called_once_with(adapter, "hyokc-1")
        assert result["changed"] is True

    def test_revoke_then_wait_then_delete(self, adapter):
        current = {"id": "hyokc-1", "status": "available"}
        polled = {"id": "hyokc-1", "status": "revoked"}
        params = self._params()
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=current), patch(f"{MOD}.revoke_hyok_configuration") as mock_revoke, patch(
            f"{MOD}.get_hyok_configuration", return_value=polled
        ), patch(f"{MOD}.delete_hyok_configuration") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)

        mock_revoke.assert_called_once_with(adapter, "hyokc-1")
        mock_delete.assert_called_once_with(adapter, "hyokc-1")
        assert result["changed"] is True

    def test_revoke_wait_false_skips_delete(self, adapter):
        current = {"id": "hyokc-1", "status": "available"}
        params = self._params(wait=False)
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=current), patch(f"{MOD}.revoke_hyok_configuration") as mock_revoke, patch(
            f"{MOD}.delete_hyok_configuration"
        ) as mock_delete, patch(f"{MOD}.get_hyok_configuration") as mock_get:
            result = state_absent(adapter, params, check_mode=False)

        mock_revoke.assert_called_once()
        mock_get.assert_not_called()
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "wait=false" in result["msg"]

    def test_revoke_timeout_raises(self, adapter):
        current = {"id": "hyokc-1", "status": "available"}
        stuck = {"id": "hyokc-1", "status": "revoking"}
        params = self._params(timeout=0)
        with patch(f"{MOD}._fetch_hyok_configuration", return_value=current), patch(f"{MOD}.revoke_hyok_configuration"), patch(
            f"{MOD}.get_hyok_configuration", return_value=stuck
        ), patch(f"{MOD}.delete_hyok_configuration") as mock_delete:
            with pytest.raises(ValueError, match="Timed out"):
                state_absent(adapter, params, check_mode=False)

        mock_delete.assert_not_called()
