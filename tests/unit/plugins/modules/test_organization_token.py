# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/organization_token.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.organization_token import (
    _build_create_data,
    _fetch_organization_token,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.organization_token"


# ---------------------------------------------------------------------------
# _fetch_organization_token routing
# ---------------------------------------------------------------------------


class TestFetch:
    def test_default_token_uses_get_organization_token(self):
        """No token_type -> must route to get_organization_token (default read)."""
        adapter = Mock()
        with patch(f"{MODULE_PATH}.get_organization_token", return_value={"id": "at-1"}) as mock_get, patch(
            f"{MODULE_PATH}.get_organization_token_with_type"
        ) as mock_get_typed:
            result = _fetch_organization_token(adapter, {"organization": "my-org", "token_type": None})
        assert result == {"id": "at-1"}
        mock_get.assert_called_once_with(adapter, "my-org")
        mock_get_typed.assert_not_called()

    def test_audit_trails_uses_get_organization_token_with_type(self):
        """token_type='audit-trails' -> must route to get_organization_token_with_type."""
        adapter = Mock()
        with patch(f"{MODULE_PATH}.get_organization_token_with_type", return_value={"id": "at-audit"}) as mock_get_typed, patch(
            f"{MODULE_PATH}.get_organization_token"
        ) as mock_get:
            result = _fetch_organization_token(adapter, {"organization": "my-org", "token_type": "audit-trails"})
        assert result == {"id": "at-audit"}
        mock_get_typed.assert_called_once_with(adapter, "my-org", "audit-trails")
        mock_get.assert_not_called()

    def test_returns_none_when_not_found(self):
        with patch(f"{MODULE_PATH}.get_organization_token", return_value=None):
            assert _fetch_organization_token(Mock(), {"organization": "my-org", "token_type": None}) is None


# ---------------------------------------------------------------------------
# _build_create_data
# ---------------------------------------------------------------------------


class TestBuildCreateData:
    def test_empty_when_nothing_supplied(self):
        assert _build_create_data({"organization": "my-org"}) == {}

    def test_includes_expired_at(self):
        params = {"organization": "my-org", "expired_at": "2027-01-01T00:00:00Z"}
        assert _build_create_data(params) == {"expired_at": "2027-01-01T00:00:00Z"}

    def test_includes_token_type(self):
        params = {"organization": "my-org", "token_type": "audit-trails"}
        assert _build_create_data(params) == {"token_type": "audit-trails"}

    def test_includes_both(self):
        params = {"organization": "my-org", "expired_at": "2027-01-01T00:00:00Z", "token_type": "audit-trails"}
        assert _build_create_data(params) == {"expired_at": "2027-01-01T00:00:00Z", "token_type": "audit-trails"}

    def test_excludes_none_values(self):
        assert _build_create_data({"organization": "my-org", "expired_at": None, "token_type": None}) == {}


# ---------------------------------------------------------------------------
# state_present
# ---------------------------------------------------------------------------


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    # --- create when absent (default token) ---
    def test_create_default_token_when_absent(self, adapter):
        params = {"organization": "my-org", "token_type": None}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=None), patch(
            f"{MODULE_PATH}.create_organization_token",
            return_value={"id": "at-1", "created_at": "2024-01-01T00:00:00+00:00", "token": "new-secret"},
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once_with(adapter, "my-org", {})
        assert result["changed"] is True
        assert result["id"] == "at-1"
        assert result["token"] == "new-secret"

    # --- create when absent (audit-trails token) ---
    def test_create_audit_trails_token_when_absent(self, adapter):
        params = {"organization": "my-org", "token_type": "audit-trails"}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=None), patch(
            f"{MODULE_PATH}.create_organization_token",
            return_value={"id": "at-audit", "created_at": "2024-01-01T00:00:00+00:00"},
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once_with(adapter, "my-org", {"token_type": "audit-trails"})
        assert result["changed"] is True
        assert result["id"] == "at-audit"

    # --- check mode (create path) ---
    def test_create_check_mode_when_absent(self, adapter):
        params = {"organization": "my-org", "token_type": None}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=None), patch(f"{MODULE_PATH}.create_organization_token") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]
        assert "created" in result["msg"]

    # --- idempotent when token already exists ---
    def test_idempotent_default_token_when_exists(self, adapter):
        current = {"id": "at-1", "created_at": "2024-01-01T00:00:00+00:00"}
        params = {"organization": "my-org", "token_type": None}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=current), patch(f"{MODULE_PATH}.create_organization_token") as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "at-1"

    def test_idempotent_audit_trails_token_when_exists(self, adapter):
        current = {"id": "at-audit", "created_at": "2024-01-01T00:00:00+00:00"}
        params = {"organization": "my-org", "token_type": "audit-trails"}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=current), patch(f"{MODULE_PATH}.create_organization_token") as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "at-audit"

    # --- expired_at does not rotate when token already exists ---
    def test_expired_at_does_not_rotate_existing_token(self, adapter):
        current = {"id": "at-1", "created_at": "2024-01-01T00:00:00+00:00"}
        params = {"organization": "my-org", "token_type": None, "expired_at": "2027-01-01T00:00:00Z"}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=current), patch(f"{MODULE_PATH}.create_organization_token") as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_not_called()
        assert result["changed"] is False

    # --- create with expired_at (token is absent) ---
    def test_create_with_expired_at(self, adapter):
        params = {"organization": "my-org", "expired_at": "2027-01-01T00:00:00Z", "token_type": None}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=None), patch(
            f"{MODULE_PATH}.create_organization_token",
            return_value={"id": "at-1", "created_at": "2024-01-01T00:00:00+00:00"},
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once_with(adapter, "my-org", {"expired_at": "2027-01-01T00:00:00Z"})
        assert result["changed"] is True

    # --- audit-trails create with token_type and expired_at ---
    def test_audit_trails_create_with_token_type_and_expired_at(self, adapter):
        """Verify combined payload: token_type + expired_at both reach create_organization_token."""
        params = {
            "organization": "my-org",
            "token_type": "audit-trails",
            "expired_at": "2027-01-01T00:00:00Z",
        }
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=None), patch(
            f"{MODULE_PATH}.create_organization_token",
            return_value={"id": "at-audit-exp", "created_at": "2024-01-01T00:00:00+00:00"},
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once_with(adapter, "my-org", {"token_type": "audit-trails", "expired_at": "2027-01-01T00:00:00Z"})
        assert result["changed"] is True
        assert result["id"] == "at-audit-exp"


# ---------------------------------------------------------------------------
# state_absent
# ---------------------------------------------------------------------------


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    # --- delete default token ---
    def test_delete_default_token_when_present(self, adapter):
        current = {"id": "at-1"}
        params = {"organization": "my-org", "token_type": None}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=current), patch(f"{MODULE_PATH}.delete_organization_token") as mock_delete, patch(
            f"{MODULE_PATH}.delete_organization_token_with_type"
        ) as mock_delete_typed:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "my-org")
        mock_delete_typed.assert_not_called()
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    # --- delete audit-trails token ---
    def test_delete_audit_trails_token_when_present(self, adapter):
        current = {"id": "at-audit"}
        params = {"organization": "my-org", "token_type": "audit-trails"}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=current), patch(
            f"{MODULE_PATH}.delete_organization_token_with_type"
        ) as mock_delete_typed, patch(f"{MODULE_PATH}.delete_organization_token") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete_typed.assert_called_once_with(adapter, "my-org", "audit-trails")
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    # --- no-op when absent ---
    def test_noop_when_already_absent(self, adapter):
        params = {"organization": "my-org", "token_type": None}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=None), patch(f"{MODULE_PATH}.delete_organization_token") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_noop_audit_trails_when_already_absent(self, adapter):
        params = {"organization": "my-org", "token_type": "audit-trails"}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=None), patch(
            f"{MODULE_PATH}.delete_organization_token_with_type"
        ) as mock_delete_typed:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete_typed.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    # --- check mode (default token) ---
    def test_delete_check_mode(self, adapter):
        current = {"id": "at-1"}
        params = {"organization": "my-org", "token_type": None}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=current), patch(f"{MODULE_PATH}.delete_organization_token") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    # --- check mode (audit-trails token) ---
    def test_delete_audit_trails_check_mode(self, adapter):
        current = {"id": "at-audit"}
        params = {"organization": "my-org", "token_type": "audit-trails"}
        with patch(f"{MODULE_PATH}._fetch_organization_token", return_value=current), patch(
            f"{MODULE_PATH}.delete_organization_token_with_type"
        ) as mock_delete_typed, patch(f"{MODULE_PATH}.delete_organization_token") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete_typed.assert_not_called()
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]
