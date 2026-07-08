# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/registry_module.py."""

from unittest.mock import Mock, mock_open, patch

import pytest

MOD_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.registry_module"


@pytest.fixture
def mock_adapter():
    return Mock()


class TestFetchRegistryModule:
    @patch(f"{MOD_PATH}.get_registry_module")
    def test_fetch_by_name_and_provider(self, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import _fetch_registry_module

        mock_get.return_value = {"id": "mod-1", "name": "vpc", "provider": "aws"}
        params = {"organization": "my-org", "name": "vpc", "provider": "aws"}

        result = _fetch_registry_module(mock_adapter, params)

        assert result == {"id": "mod-1", "name": "vpc", "provider": "aws"}
        mock_get.assert_called_once()

    @patch(f"{MOD_PATH}.get_registry_module")
    def test_fetch_returns_none_when_missing_params(self, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import _fetch_registry_module

        params = {"organization": "my-org", "name": "vpc"}  # missing provider
        result = _fetch_registry_module(mock_adapter, params)

        assert result is None
        mock_get.assert_not_called()


class TestHasDrift:
    def test_no_drift_when_no_code_matches(self):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import _has_drift

        params = {"no_code": True}
        current = {"id": "mod-1", "no_code": True}
        assert _has_drift(params, current) is False

    def test_drift_when_no_code_differs(self):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import _has_drift

        params = {"no_code": True}
        current = {"id": "mod-1", "no_code": False}
        assert _has_drift(params, current) is True

    def test_no_drift_when_no_code_not_specified(self):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import _has_drift

        params = {}
        current = {"id": "mod-1", "no_code": False}
        assert _has_drift(params, current) is False


class TestStatePresent:
    @patch(f"{MOD_PATH}._fetch_registry_module")
    @patch(f"{MOD_PATH}.create_registry_module")
    def test_create_operation_when_not_exists(self, mock_create, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        mock_fetch.return_value = None
        mock_create.return_value = {"id": "mod-1", "name": "vpc", "provider": "aws"}
        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "operation": "create",
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        assert result["id"] == "mod-1"
        mock_create.assert_called_once()

    @patch(f"{MOD_PATH}._fetch_registry_module")
    @patch(f"{MOD_PATH}.create_registry_module")
    def test_create_operation_when_exists_idempotent(self, mock_create, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        existing = {"id": "mod-1", "name": "vpc", "provider": "aws"}
        mock_fetch.return_value = existing
        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "operation": "create",
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is False
        assert result["id"] == "mod-1"
        mock_create.assert_not_called()

    @patch(f"{MOD_PATH}._fetch_registry_module")
    @patch(f"{MOD_PATH}.create_registry_module")
    def test_create_operation_check_mode(self, mock_create, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        mock_fetch.return_value = None
        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "operation": "create",
        }

        result = state_present(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "would be created" in result["msg"]
        mock_create.assert_not_called()

    @patch(f"{MOD_PATH}._fetch_registry_module")
    @patch(f"{MOD_PATH}.create_registry_module_with_vcs")
    def test_create_with_vcs_operation_when_not_exists(self, mock_create_vcs, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        mock_fetch.return_value = None
        mock_create_vcs.return_value = {"id": "mod-1", "name": "vpc"}
        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "operation": "create_with_vcs",
            "vcs_repo": {"identifier": "org/repo", "oauth_token_id": "ot-123"},
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        mock_create_vcs.assert_called_once()

    @patch(f"{MOD_PATH}._fetch_registry_module")
    @patch(f"{MOD_PATH}.create_registry_module_with_vcs")
    def test_create_with_vcs_operation_when_exists_idempotent(self, mock_create_vcs, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        existing = {"id": "mod-1", "name": "vpc", "provider": "aws"}
        mock_fetch.return_value = existing
        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "operation": "create_with_vcs",
            "vcs_repo": {"identifier": "org/repo", "oauth_token_id": "ot-123"},
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is False
        mock_create_vcs.assert_not_called()

    @patch(f"{MOD_PATH}.create_registry_module_with_vcs")
    def test_create_with_vcs_missing_vcs_repo_raises(self, mock_create_vcs, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        params = {
            "organization": "my-org",
            "operation": "create_with_vcs",
        }

        with pytest.raises(ValueError, match="vcs_repo.*required"):
            state_present(mock_adapter, params, check_mode=False)

    @patch(f"{MOD_PATH}.get_registry_module_version")
    @patch(f"{MOD_PATH}.create_registry_module_version")
    def test_create_version_operation_when_not_exists(self, mock_create_version, mock_get_version, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        mock_get_version.return_value = None
        mock_create_version.return_value = {"id": "modver-1", "version": "1.0.0", "links": {}}
        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "version": "1.0.0",
            "operation": "create_version",
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        assert result["version"] == "1.0.0"
        mock_create_version.assert_called_once()

    @patch(f"{MOD_PATH}.get_registry_module_version")
    @patch(f"{MOD_PATH}.create_registry_module_version")
    def test_create_version_operation_when_exists_idempotent(self, mock_create_version, mock_get_version, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        existing_version = {"id": "modver-1", "version": "1.0.0"}
        mock_get_version.return_value = existing_version
        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "version": "1.0.0",
            "operation": "create_version",
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is False
        assert result["version"] == "1.0.0"
        mock_create_version.assert_not_called()

    @patch(f"{MOD_PATH}.get_registry_module_version")
    @patch(f"{MOD_PATH}.create_registry_module_version")
    @patch(f"{MOD_PATH}.upload_registry_module_version")
    @patch("builtins.open", new_callable=mock_open, read_data=b"archive content")
    @patch("os.path.exists")
    def test_create_version_with_archive_upload(self, mock_exists, mock_file, mock_upload, mock_create_version, mock_get_version, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        mock_exists.return_value = True
        mock_get_version.return_value = None
        mock_create_version.return_value = {
            "id": "modver-1",
            "version": "1.0.0",
            "links": {"upload": "https://example.com/upload"},
        }
        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "version": "1.0.0",
            "archive": "/path/to/archive.tar.gz",
            "operation": "create_version",
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        mock_create_version.assert_called_once()
        mock_upload.assert_called_once_with(mock_adapter, "https://example.com/upload", b"archive content")

    @patch(f"{MOD_PATH}.get_registry_module_version")
    @patch(f"{MOD_PATH}.create_registry_module_version")
    def test_create_version_missing_version_raises(self, mock_create_version, mock_get_version, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "operation": "create_version",
        }

        with pytest.raises(ValueError, match="version.*required"):
            state_present(mock_adapter, params, check_mode=False)

    @patch(f"{MOD_PATH}.update_registry_module")
    @patch(f"{MOD_PATH}._fetch_registry_module")
    @patch(f"{MOD_PATH}._has_drift")
    def test_update_operation_with_drift(self, mock_has_drift, mock_fetch, mock_update, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        mock_fetch.return_value = {"id": "mod-1", "name": "vpc", "no_code": False}
        mock_has_drift.return_value = True
        mock_update.return_value = {"id": "mod-1", "name": "vpc", "no_code": True}

        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "no_code": True,
            "operation": "update",
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        mock_update.assert_called_once()

    @patch(f"{MOD_PATH}._fetch_registry_module")
    @patch(f"{MOD_PATH}._has_drift")
    def test_update_operation_no_drift(self, mock_has_drift, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_present

        current = {"id": "mod-1", "name": "vpc", "no_code": True}
        mock_fetch.return_value = current
        mock_has_drift.return_value = False

        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "no_code": True,
            "operation": "update",
        }

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is False
        assert result["id"] == "mod-1"


class TestStateAbsent:
    @patch(f"{MOD_PATH}.delete_registry_module_version")
    def test_delete_version(self, mock_delete_version, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_absent

        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "version": "1.0.0",
            "delete_scope": "version",
        }

        result = state_absent(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        assert "deleted successfully" in result["msg"]
        mock_delete_version.assert_called_once()

    @patch(f"{MOD_PATH}.delete_registry_module_version")
    def test_delete_version_check_mode(self, mock_delete_version, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_absent

        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "version": "1.0.0",
            "delete_scope": "version",
        }

        result = state_absent(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "would be deleted" in result["msg"]
        mock_delete_version.assert_not_called()

    @patch(f"{MOD_PATH}.delete_registry_module_provider")
    @patch(f"{MOD_PATH}._fetch_registry_module")
    def test_delete_provider(self, mock_fetch, mock_delete_provider, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_absent

        mock_fetch.return_value = {"id": "mod-1", "name": "vpc", "provider": "aws"}
        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "delete_scope": "provider",
        }

        result = state_absent(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        mock_delete_provider.assert_called_once()

    @patch(f"{MOD_PATH}._fetch_registry_module")
    def test_delete_provider_already_absent(self, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_absent

        mock_fetch.return_value = None
        params = {
            "organization": "my-org",
            "name": "vpc",
            "provider": "aws",
            "delete_scope": "provider",
        }

        result = state_absent(mock_adapter, params, check_mode=False)

        assert result["changed"] is False
        assert "already absent" in result["msg"]

    @patch(f"{MOD_PATH}.delete_registry_module_by_name")
    def test_delete_module(self, mock_delete_module, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_module import state_absent

        params = {
            "organization": "my-org",
            "name": "vpc",
            "delete_scope": "module",
        }

        result = state_absent(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        mock_delete_module.assert_called_once()
