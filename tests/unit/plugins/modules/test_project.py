# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.project import (
    fetch_project,
    fetch_project_tag_bindings,
    get_project_by_name,
    main,
    normalize_project_response,
    state_absent,
    state_present,
    state_update,
)


class EnhancedDummyModule:
    """A mock Ansible module for better inspection in tests."""

    def __init__(self, params=None):
        self.params = params or {}
        self.failed = False
        self.exit_args = None
        self.fail_args = None
        self.check_mode = False

    def fail_json(self, **kwargs):
        self.failed = True
        self.fail_args = kwargs
        raise AssertionError(kwargs.get("msg", "fail_json called with no message"))

    def fail_from_exception(self, exception):
        self.failed = True
        self.fail_args = {"msg": str(exception)}
        raise AssertionError(f"fail_from_exception called with: {exception}")

    def exit_json(self, **kwargs):
        self.exit_args = kwargs
        raise SystemExit(kwargs)


class TestProjectHelperFunctions:
    """Test cases for project helper functions."""

    def test_get_project_by_name_success(self):
        """Test successful project retrieval by name."""
        mock_client = Mock()
        organization = "test-org"
        name = "test-project"

        expected_response = {"data": [{"id": "prj-123abc456def", "type": "projects", "attributes": {"name": name}}]}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.list_projects") as mock_list:
            mock_list.return_value = expected_response

            result = get_project_by_name(mock_client, organization, name)

            assert result == expected_response["data"][0]
            mock_list.assert_called_once_with(mock_client, organization, query_params={"filter[names]": name})

    def test_fetch_project_tag_bindings_success(self):
        """Test successful tag bindings retrieval."""
        mock_client = Mock()
        project_id = "prj-123abc456def"

        mock_response = {
            "data": [
                {"type": "tag-bindings", "attributes": {"key": "Environment", "value": "Production"}},
                {"type": "tag-bindings", "attributes": {"key": "Team", "value": "Infrastructure"}},
            ]
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_tag_bindings") as mock_get:
            mock_get.return_value = mock_response

            result = fetch_project_tag_bindings(mock_client, project_id)

            expected = {"Environment": "Production", "Team": "Infrastructure"}
            assert result == expected
            mock_get.assert_called_once_with(mock_client, project_id)

    def test_fetch_project_tag_bindings_empty_response(self):
        """Test tag bindings retrieval with empty response."""
        mock_client = Mock()
        project_id = "prj-123abc456def"

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_tag_bindings") as mock_get:
            mock_get.return_value = {}

            result = fetch_project_tag_bindings(mock_client, project_id)

            assert result == {}

    def test_normalize_project_response(self):
        """Test project response normalization."""
        mock_client = Mock()
        project_id = "prj-123abc456def"

        response_data = {
            "data": {
                "id": project_id,
                "attributes": {
                    "name": "test-project",
                    "description": "Test project description",
                    "auto-destroy-activity-duration": "30d",
                    "execution-mode": "remote",
                    "default-agent-pool-id": "apool-123",
                    "setting-overwrites": {"auto_apply": True},
                },
            }
        }

        mock_tag_bindings = {"Environment": "Production"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.fetch_project_tag_bindings") as mock_fetch:
            mock_fetch.return_value = mock_tag_bindings

            result = normalize_project_response(response_data, mock_client, project_id)

            expected = {
                "name": "test-project",
                "description": "Test project description",
                "auto_destroy_activity_duration": "30d",
                "execution_mode": "remote",
                "default_agent_pool_id": "apool-123",
                "setting_overwrites": {"auto_apply": True},
                "tag_bindings": mock_tag_bindings,
            }

            assert result == expected
            mock_fetch.assert_called_once_with(mock_client, project_id)


class TestFetchProject:
    """Test cases for fetch_project function."""

    def test_fetch_project_by_id_success(self):
        """Test fetching project by ID when it exists."""
        mock_client = Mock()
        params = {"project_id": "prj-123abc456def"}

        expected_project = {"data": {"id": "prj-123abc456def", "attributes": {"name": "test-project"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_by_id") as mock_get:
            mock_get.return_value = expected_project

            result = fetch_project(mock_client, params)

            assert result == expected_project
            mock_get.assert_called_once_with(mock_client, "prj-123abc456def")

    def test_fetch_project_by_name_success(self):
        """Test fetching project by name when it exists."""
        mock_client = Mock()
        params = {"project": "test-project", "organization": "test-org"}

        existing_project = {"id": "prj-123abc456def"}
        expected_project = {"data": {"id": "prj-123abc456def", "attributes": {"name": "test-project"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_by_name") as mock_get_by_name, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_by_id"
        ) as mock_get_by_id:

            mock_get_by_name.return_value = existing_project
            mock_get_by_id.return_value = expected_project

            result = fetch_project(mock_client, params)

            assert result == expected_project
            mock_get_by_name.assert_called_once_with(mock_client, "test-org", "test-project")
            mock_get_by_id.assert_called_once_with(mock_client, "prj-123abc456def")

    def test_fetch_project_not_found(self):
        """Test fetching project when it doesn't exist."""
        mock_client = Mock()
        params = {"project": "nonexistent-project", "organization": "test-org"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_by_name") as mock_get:
            mock_get.return_value = None

            result = fetch_project(mock_client, params)

            assert result == {}


class TestStatePresent:
    """Test cases for state_present function."""

    def test_state_present_create_new_project(self):
        """Test creating a new project when it doesn't exist."""
        mock_client = Mock()
        params = {"project": "new-project", "organization": "test-org", "description": "New project description", "execution_mode": "remote"}

        expected_response = {
            "data": {"id": "prj-123abc456def", "type": "projects", "attributes": {"name": "new-project", "description": "New project description"}}
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.fetch_project") as mock_fetch, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.create_project"
        ) as mock_create, patch("ansible_collections.hashicorp.terraform.plugins.modules.project.ProjectRequest") as mock_request:

            mock_fetch.return_value = {}  # Project doesn't exist
            mock_create.return_value = expected_response
            mock_request.create.return_value.model_dump.return_value = {"data": {"type": "projects"}}

            result = state_present(mock_client, params, check_mode=False)

            assert result["changed"] is True
            assert result["id"] == "prj-123abc456def"
            mock_create.assert_called_once()

    def test_state_present_create_new_project_check_mode(self):
        """Test creating a new project in check mode."""
        mock_client = Mock()
        params = {"project": "new-project", "organization": "test-org", "description": "New project description", "execution_mode": "remote"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.fetch_project") as mock_fetch, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.create_project"
        ) as mock_create, patch("ansible_collections.hashicorp.terraform.plugins.modules.project.ProjectRequest") as mock_request:

            mock_fetch.return_value = {}  # Project doesn't exist
            mock_request.create.return_value.model_dump.return_value = {"data": {"type": "projects"}}

            result = state_present(mock_client, params, check_mode=True)

            assert result["changed"] is True
            assert "would be created" in result["msg"]
            assert "check mode" in result["msg"]
            mock_create.assert_not_called()

    def test_state_present_update_existing_project(self):
        """Test updating an existing project."""
        mock_client = Mock()
        params = {"project": "existing-project", "organization": "test-org", "description": "Updated description"}

        existing_project = {"data": {"id": "prj-123abc456def", "attributes": {"name": "existing-project"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.fetch_project") as mock_fetch, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.state_update"
        ) as mock_update:

            mock_fetch.return_value = existing_project
            mock_update.return_value = {"changed": True}

            result = state_present(mock_client, params, check_mode=False)

            assert result["changed"] is True
            mock_update.assert_called_once_with(mock_client, params, existing_project, False)


class TestStateUpdate:
    """Test cases for state_update function."""

    def test_state_update_with_changes(self):
        """Test updating project when there are changes."""
        mock_client = Mock()
        params = {"project": "test-project", "organization": "test-org", "description": "Updated description"}

        project = {"data": {"id": "prj-123abc456def", "attributes": {"name": "test-project", "description": "Old description"}}}

        expected_response = {"data": {"id": "prj-123abc456def", "attributes": {"name": "test-project", "description": "Updated description"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.normalize_project_response") as mock_normalize, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.dict_diff"
        ) as mock_diff, patch("ansible_collections.hashicorp.terraform.plugins.modules.project.update_project") as mock_update, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.ProjectRequest"
        ) as mock_request:

            mock_normalize.return_value = {"name": "test-project", "description": "Old description"}
            mock_diff.return_value = {"description": "Updated description"}  # Changes detected
            mock_update.return_value = expected_response
            mock_request.create.return_value.model_dump.return_value = {"data": {"type": "projects"}}

            result = state_update(mock_client, params, project, check_mode=False)

            assert result["changed"] is True
            mock_update.assert_called_once()

    def test_state_update_with_changes_check_mode(self):
        """Test updating project when there are changes in check mode."""
        mock_client = Mock()
        params = {"project": "test-project", "organization": "test-org", "description": "Updated description"}

        project = {"data": {"id": "prj-123abc456def", "attributes": {"name": "test-project", "description": "Old description"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.normalize_project_response") as mock_normalize, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.dict_diff"
        ) as mock_diff, patch("ansible_collections.hashicorp.terraform.plugins.modules.project.update_project") as mock_update, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.ProjectRequest"
        ) as mock_request:

            mock_normalize.return_value = {"name": "test-project", "description": "Old description"}
            mock_diff.return_value = {"description": "Updated description"}  # Changes detected
            mock_request.create.return_value.model_dump.return_value = {"data": {"type": "projects"}}

            result = state_update(mock_client, params, project, check_mode=True)

            assert result["changed"] is True
            assert "would be updated" in result["msg"]
            assert "check mode" in result["msg"]
            mock_update.assert_not_called()

    def test_state_update_no_changes(self):
        """Test updating project when there are no changes."""
        mock_client = Mock()
        params = {"project": "test-project", "organization": "test-org", "description": "Same description"}

        project = {"data": {"id": "prj-123abc456def", "attributes": {"name": "test-project", "description": "Same description"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.normalize_project_response") as mock_normalize, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.dict_diff"
        ) as mock_diff:

            mock_normalize.return_value = {"name": "test-project", "description": "Same description"}
            mock_diff.return_value = {}  # No changes detected

            result = state_update(mock_client, params, project, check_mode=False)

            assert result["changed"] is False


class TestStateAbsent:
    """Test cases for state_absent function."""

    def test_state_absent_with_project_id(self):
        """Test deleting project using project_id."""
        mock_client = Mock()
        params = {"project_id": "prj-123abc456def"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.delete_project") as mock_delete:
            result = state_absent(mock_client, params, check_mode=False)

            assert result["changed"] is True
            assert "has been deleted successfully" in result["msg"]
            mock_delete.assert_called_once_with(mock_client, "prj-123abc456def")

    def test_state_absent_with_project_id_check_mode(self):
        """Test deleting project using project_id in check mode."""
        mock_client = Mock()
        params = {"project_id": "prj-123abc456def"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.delete_project") as mock_delete:
            result = state_absent(mock_client, params, check_mode=True)

            assert result["changed"] is True
            assert "would be deleted" in result["msg"]
            assert "check mode" in result["msg"]
            mock_delete.assert_not_called()

    def test_state_absent_with_project_name(self):
        """Test deleting project using project name."""
        mock_client = Mock()
        params = {"project": "test-project", "organization": "test-org"}

        existing_project = {"data": {"id": "prj-123abc456def"}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.fetch_project") as mock_fetch, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.delete_project"
        ) as mock_delete:

            mock_fetch.return_value = existing_project

            result = state_absent(mock_client, params, check_mode=False)

            assert result["changed"] is True
            assert "has been deleted successfully" in result["msg"]
            mock_delete.assert_called_once_with(mock_client, "prj-123abc456def")

    def test_state_absent_project_not_found(self):
        """Test deleting project when it doesn't exist."""
        mock_client = Mock()
        params = {"project": "nonexistent-project", "organization": "test-org"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.fetch_project") as mock_fetch:
            mock_fetch.return_value = {}

            result = state_absent(mock_client, params, check_mode=False)

            assert result["changed"] is False
            assert "not found" in result["msg"]


class TestMainFunction:
    """Test cases for main function and module integration."""

    @pytest.mark.parametrize(
        "scenario,module_params,expected_behavior",
        [
            ("present_state", {"project": "test-project", "organization": "test-org", "state": "present"}, "success"),
            ("absent_state", {"project_id": "prj-123", "state": "absent"}, "success"),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project.TerraformClient")
    def test_main_success_scenarios(self, mock_tf_client, mock_module_class, scenario, module_params, expected_behavior):
        """Test main function success scenarios."""
        mock_module = EnhancedDummyModule(module_params)
        mock_module_class.return_value = mock_module

        mock_client = Mock()
        mock_tf_client.return_value = mock_client

        expected_result = {"changed": True, "id": "prj-123abc456def"}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.state_present") as mock_present, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.state_absent"
        ) as mock_absent:

            if module_params["state"] == "present":
                mock_present.return_value = expected_result
            else:
                mock_absent.return_value = expected_result

            with pytest.raises(SystemExit):
                main()

            assert mock_module.exit_args["changed"] is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project.TerraformClient")
    def test_main_exception_handling(self, mock_tf_client, mock_module_class):
        """Test main function exception handling."""
        mock_module = EnhancedDummyModule({"project": "test", "organization": "org", "state": "present"})
        mock_module_class.return_value = mock_module

        mock_tf_client.side_effect = Exception("Connection error")

        with pytest.raises(AssertionError):
            main()

        assert mock_module.failed is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project.AnsibleTerraformModule")
    def test_argument_spec_validation(self, mock_module_class):
        """Test that argument spec is properly configured."""
        main()

        # Get the call arguments to AnsibleTerraformModule
        call_args = mock_module_class.call_args[1]
        argument_spec = call_args["argument_spec"]

        # Verify all expected parameters are present
        expected_params = [
            "project_id",
            "project",
            "organization",
            "description",
            "auto_destroy_activity_duration",
            "execution_mode",
            "default_agent_pool_id",
            "setting_overwrites",
            "tag_bindings",
            "state",
        ]

        for param in expected_params:
            assert param in argument_spec

        # Verify specific configurations
        assert argument_spec["state"]["choices"] == ["present", "absent"]
        assert argument_spec["state"]["default"] == "present"

        # Verify validation rules
        assert call_args["required_together"] == [["project", "organization"]]
        assert len(call_args["required_if"]) == 2
        assert len(call_args["mutually_exclusive"]) == 1
        assert call_args["supports_check_mode"] is True


class TestProjectModuleEdgeCases:
    """Test edge cases and error conditions."""

    def test_fetch_project_tag_bindings_with_none_key(self):
        """Test tag bindings handling when key is None."""
        mock_client = Mock()
        project_id = "prj-123abc456def"

        mock_response = {
            "data": [
                {"type": "tag-bindings", "attributes": {"key": None, "value": "Production"}},
                {"type": "tag-bindings", "attributes": {"key": "Team", "value": "Infrastructure"}},
            ]
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.get_project_tag_bindings") as mock_get:
            mock_get.return_value = mock_response

            result = fetch_project_tag_bindings(mock_client, project_id)

            # Should only include the valid tag binding
            expected = {"Team": "Infrastructure"}
            assert result == expected

    def test_normalize_project_response_with_none_values(self):
        """Test normalization with None values in response."""
        mock_client = Mock()
        project_id = "prj-123abc456def"

        response_data = {
            "data": {
                "id": project_id,
                "attributes": {
                    "name": "test-project",
                    "description": None,
                    "auto-destroy-activity-duration": None,
                    "execution-mode": None,
                    "default-agent-pool-id": None,
                    "setting-overwrites": None,
                },
            }
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.fetch_project_tag_bindings") as mock_fetch:
            mock_fetch.return_value = {}

            result = normalize_project_response(response_data, mock_client, project_id)

            # Should include None values as they might be meaningful
            expected = {
                "name": "test-project",
                "description": None,
                "auto_destroy_activity_duration": None,
                "execution_mode": None,
                "default_agent_pool_id": None,
                "setting_overwrites": None,
                "tag_bindings": {},
            }

            assert result == expected

    def test_state_update_field_name_mapping(self):
        """Test that 'project' field is correctly mapped to 'name' in state_update."""
        mock_client = Mock()
        params = {"project": "new-name", "organization": "test-org", "description": "Test description"}  # This should be mapped to 'name'

        project = {"data": {"id": "prj-123abc456def", "attributes": {"name": "old-name", "description": "Test description"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.project.normalize_project_response") as mock_normalize, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.dict_diff"
        ) as mock_diff, patch("ansible_collections.hashicorp.terraform.plugins.modules.project.update_project") as mock_update, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project.ProjectRequest"
        ) as mock_request:

            mock_normalize.return_value = {"name": "old-name", "description": "Test description"}
            mock_diff.return_value = {"name": "new-name"}  # Should detect name change
            mock_update.return_value = {"data": {"id": "prj-123abc456def"}}
            mock_request.create.return_value.model_dump.return_value = {"data": {"type": "projects"}}

            result = state_update(mock_client, params, project, check_mode=False)

            assert result["changed"] is True
            # Verify that dict_diff was called with the correctly mapped field names
            mock_diff.assert_called_once()
            call_args = mock_diff.call_args[0]
            want_dict = call_args[1]  # Second argument is the 'want' dictionary
            assert "name" in want_dict
            assert want_dict["name"] == "new-name"
