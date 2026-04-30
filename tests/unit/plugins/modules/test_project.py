# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.project import (
    _build_desired_state,
    _create_update_response,
    _filter_current_state,
    _filter_tag_binding_updates,
    _normalize_tag_bindings,
    fetch_project,
    main,
    normalize_project_response,
    state_absent,
    state_present,
    state_update,
)


class TestProjectHelpers:
    """Test helper functions used by project module state logic."""

    def test_normalize_tag_bindings(self):
        result = _normalize_tag_bindings(
            [
                {"key": "env", "value": "prod"},
                {"key": "team", "value": "platform"},
            ]
        )
        assert result == {"env": "prod", "team": "platform"}

    def test_build_desired_state_maps_project_name(self):
        params = {
            "project": "my-project",
            "description": "desc",
            "default_execution_mode": "remote",
            "tag_bindings": [{"key": "env", "value": "dev"}],
        }

        result = _build_desired_state(params)

        assert result["name"] == "my-project"
        assert "project" not in result
        assert result["tag_bindings"] == {"env": "dev"}

    def test_filter_current_state(self):
        have = {
            "name": "my-project",
            "description": None,
            "setting_overwrites": {},
            "extra": "drop-me",
            "default_execution_mode": "remote",
        }
        want = {
            "name": "my-project",
            "default_execution_mode": "local",
        }

        result = _filter_current_state(have, want)

        assert result == {
            "name": "my-project",
            "default_execution_mode": "remote",
        }

    def test_filter_tag_binding_updates(self):
        updates = {
            "description": "new",
            "tag_bindings": {"env": "prod"},
        }
        have = {"description": "old"}

        result = _filter_tag_binding_updates(updates, have)

        assert result == {"description": "new"}


class TestProjectStatePresentAndUpdate:
    """Test project present/update flow."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    @pytest.fixture
    def present_params(self):
        return {
            "project": "demo-project",
            "organization": "demo-org",
            "description": "demo",
            "default_execution_mode": "remote",
            "state": "present",
        }

    def test_fetch_project_by_id(self, mock_adapter):
        params = {"project_id": "prj-123"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_by_id") as mock_get:
            mock_get.return_value = {"id": "prj-123", "name": "demo"}

            result = fetch_project(mock_adapter, params)

            assert result["id"] == "prj-123"
            mock_get.assert_called_once_with(mock_adapter, "prj-123")

    def test_fetch_project_by_name(self, mock_adapter):
        params = {"project": "demo", "organization": "demo-org"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_by_name") as mock_by_name, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_by_id"
        ) as mock_by_id:
            mock_by_name.return_value = {"id": "prj-1", "name": "demo"}
            mock_by_id.return_value = {"id": "prj-1", "name": "demo", "description": "d"}

            result = fetch_project(mock_adapter, params)

            assert result["id"] == "prj-1"
            mock_by_name.assert_called_once_with(mock_adapter, "demo-org", "demo")
            mock_by_id.assert_called_once_with(mock_adapter, "prj-1")

    def test_state_present_create(self, mock_adapter, present_params):
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.fetch_project") as mock_fetch, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.create_project"
        ) as mock_create:
            mock_fetch.return_value = {}
            mock_create.return_value = {"id": "prj-123", "name": "demo-project"}

            result = state_present(mock_adapter, present_params, check_mode=False)

            assert result["changed"] is True
            assert result["id"] == "prj-123"
            mock_create.assert_called_once()

    def test_state_present_create_check_mode(self, mock_adapter, present_params):
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.fetch_project") as mock_fetch:
            mock_fetch.return_value = {}

            result = state_present(mock_adapter, present_params, check_mode=True)

            assert result["changed"] is True
            assert "would be created" in result["msg"]

    def test_state_present_update_path(self, mock_adapter, present_params):
        existing = {"id": "prj-123", "name": "demo-project"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.fetch_project") as mock_fetch, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.state_update"
        ) as mock_update:
            mock_fetch.return_value = existing
            mock_update.return_value = {"changed": False}

            result = state_present(mock_adapter, present_params, check_mode=False)

            assert result == {"changed": False}
            mock_update.assert_called_once_with(mock_adapter, present_params, existing, False)

    def test_create_update_response_check_mode(self, mock_adapter):
        result = _create_update_response(
            mock_adapter,
            "prj-1",
            {"name": "demo"},
            {"organization": "demo-org"},
            check_mode=True,
        )

        assert result["changed"] is True
        assert "would be updated" in result["msg"]

    def test_state_update_no_changes(self, mock_adapter):
        params = {
            "project": "demo-project",
            "organization": "demo-org",
            "description": "same",
        }
        existing = {
            "id": "prj-1",
            "name": "demo-project",
            "description": "same",
            "default_execution_mode": "remote",
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_tag_bindings") as mock_tags:
            mock_tags.return_value = []
            result = state_update(mock_adapter, params, existing, check_mode=False)

        assert result == {"changed": False}

    def test_state_update_with_changes(self, mock_adapter):
        params = {
            "project": "demo-project",
            "organization": "demo-org",
            "description": "updated",
        }
        existing = {
            "id": "prj-1",
            "name": "demo-project",
            "description": "old",
            "default_execution_mode": "remote",
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_tag_bindings") as mock_tags, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.update_project"
        ) as mock_update:
            mock_tags.return_value = []
            mock_update.return_value = {
                "id": "prj-1",
                "name": "demo-project",
                "description": "updated",
            }

            result = state_update(mock_adapter, params, existing, check_mode=False)

            assert result["changed"] is True
            assert result["description"] == "updated"
            mock_update.assert_called_once()


class TestProjectStateAbsent:
    """Test project absent state."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    def test_state_absent_by_id(self, mock_adapter):
        params = {"project_id": "prj-123"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.delete_project") as mock_delete:
            result = state_absent(mock_adapter, params, check_mode=False)

            assert result["changed"] is True
            assert "deleted successfully" in result["msg"]
            mock_delete.assert_called_once_with(mock_adapter, "prj-123")

    def test_state_absent_check_mode(self, mock_adapter):
        params = {"project_id": "prj-123"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.delete_project") as mock_delete:
            result = state_absent(mock_adapter, params, check_mode=True)

            assert result["changed"] is True
            assert "would be deleted" in result["msg"]
            mock_delete.assert_not_called()

    def test_state_absent_not_found(self, mock_adapter):
        params = {"project": "missing", "organization": "demo-org"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.fetch_project") as mock_fetch:
            mock_fetch.return_value = {}

            result = state_absent(mock_adapter, params, check_mode=False)

            assert result == {"changed": False, "msg": "Project not found"}


class TestNormalizeProjectResponse:
    """Test project response normalization for idempotency."""

    def test_normalize_project_response_with_tag_bindings(self):
        mock_adapter = Mock()
        response_data = {
            "id": "prj-1",
            "name": "demo",
            "description": "demo desc",
            "auto_destroy_activity_duration": "14d",
            "default_execution_mode": "remote",
            "setting_overwrites": {"execution_mode": True},
            "default_agent_pool": {"id": "apool-1"},
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_tag_bindings") as mock_tags:
            mock_tags.return_value = [{"key": "env", "value": "dev"}]

            result = normalize_project_response(response_data, mock_adapter, "prj-1")

            assert result["name"] == "demo"
            assert result["default_agent_pool_id"] == "apool-1"
            assert result["tag_bindings"] == {"env": "dev"}


class TestProjectMainFunction:
    """Test project module main function orchestration."""

    @pytest.fixture
    def test_module(self, enhanced_dummy_module):
        enhanced_dummy_module.params = {
            "project": "demo-project",
            "organization": "demo-org",
            "state": "present",
            "description": "demo",
        }
        return enhanced_dummy_module

    def test_main_present(self, test_module):
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.project.state_present", return_value={"changed": True, "id": "prj-1"}):
            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert test_module.exit_args["id"] == "prj-1"

    def test_main_absent(self, test_module):
        test_module.params["state"] = "absent"
        test_module.params["project_id"] = "prj-1"

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.AnsibleTerraformModule", return_value=test_module), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.TerraformClient"
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.project.state_absent", return_value={"changed": True, "msg": "deleted"}):
            with pytest.raises(SystemExit):
                main()

            assert test_module.exit_args["changed"] is True
            assert test_module.exit_args["msg"] == "deleted"

    def test_main_exception(self, test_module):
        test_module.client = lambda: (i for i in ()).throw(Exception("boom"))
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.AnsibleTerraformModule", return_value=test_module):
            with pytest.raises(AssertionError) as exc_info:
                main()

            assert "boom" in str(exc_info.value)
