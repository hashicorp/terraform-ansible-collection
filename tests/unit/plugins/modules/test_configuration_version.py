# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import tarfile
import tempfile

from pathlib import Path
from unittest.mock import ANY, Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.configuration_version import (
    create_configuration_version,
    get_configuration_version,
    main,
    state_archived,
    state_present,
    upload_configuration_version,
    validate_and_prepare_tar,
)


class EnhancedDummyModule:
    """A mock Ansible module for better inspection in tests."""

    def __init__(self, params=None):
        self.params = params or {}
        self.failed = False
        self.exit_args = None
        self.fail_args = None

    def fail_json(self, **kwargs):
        self.failed = True
        self.fail_args = kwargs
        raise AssertionError(kwargs.get("msg", "fail_json called with no message"))

    def exit_json(self, **kwargs):
        self.exit_args = kwargs
        raise SystemExit(kwargs)


class TestValidateAndPrepareTar:
    """Tests for validate_and_prepare_tar function."""

    def test_validate_prepare_tar_nonexistent_path(self):
        """Test that nonexistent path raises FileNotFoundError."""
        nonexistent_path = "/this/path/does/not/exist"

        with pytest.raises(FileNotFoundError) as exc_info:
            validate_and_prepare_tar(Path(nonexistent_path))

        assert "does not exist" in str(exc_info.value)

    def test_validate_prepare_tar_empty_directory(self):
        """Test handling of empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_and_prepare_tar(Path(temp_dir))

            # Verify it creates a valid tar file
            assert tarfile.is_tarfile(result)

            # Verify the tar file is empty (just the directory structure)
            with tarfile.open(result, "r:gz") as tar:
                members = tar.getnames()
                assert len(members) == 0 or all(name.endswith("/") for name in members)

            os.remove(result)

    def test_validate_prepare_tar_directory_with_subdirectories(self):
        """Test archiving directory with nested structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            subdir = os.path.join(temp_dir, "subdir")
            os.makedirs(subdir)

            with open(os.path.join(temp_dir, "main.tf"), "w") as f:
                f.write("# Main terraform file")

            with open(os.path.join(subdir, "variables.tf"), "w") as f:
                f.write("# Variables file")

            result = validate_and_prepare_tar(Path(temp_dir))

            # Verify structure is preserved
            with tarfile.open(result, "r:gz") as tar:
                names = tar.getnames()
                assert "main.tf" in names
                assert "subdir/variables.tf" in names

            # Cleanup
            os.remove(result)

    def test_validate_prepare_tar_valid_uncompressed_tar(self):
        """Test with valid uncompressed tar file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            # Create uncompressed tar
            tar_path = os.path.join(temp_dir, "test.tar")
            with tarfile.open(tar_path, "w") as tar:
                tar.add(test_file, arcname="test.txt")

            # Should raise TarError because it's not gzipped
            with pytest.raises(Exception) as exc_info:
                validate_and_prepare_tar(Path(tar_path))

            assert "bad gzip file" in str(exc_info.value).lower()

    def test_validate_prepare_tar_file_permission_error(self):
        """Test handling of permission errors when creating tar."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")

            # Mock tempfile.mkstemp to raise PermissionError
            with patch("tempfile.mkstemp", side_effect=PermissionError("Permission denied")):
                with pytest.raises(Exception) as exc_info:
                    validate_and_prepare_tar(Path(temp_dir))

                assert "Failed to create tar.gz" in str(exc_info.value)

    def test_validate_prepare_tar_with_testdata_directory(self):
        """Test using actual testdata directory from test suite."""
        testdata_dir = Path(__file__).parent.parent.parent / "testdata" / "testdir"

        # Verify testdata exists
        assert testdata_dir.exists(), f"Testdata directory not found: {testdata_dir}"
        assert (testdata_dir / "file.tf").exists(), "file.tf not found in testdata"

        result = validate_and_prepare_tar(testdata_dir)

        # Verify it creates a valid tar file
        assert tarfile.is_tarfile(result)

        # Verify content
        with tarfile.open(result, "r:gz") as tar:
            names = tar.getnames()
            assert "file.tf" in names

            # Extract and verify terraform content
            tf_content = tar.extractfile("file.tf").read().decode("utf-8")
            assert 'provider "aws"' in tf_content
            assert 'resource "aws_vpc"' in tf_content

        os.remove(result)

    def test_validate_prepare_tar_with_valid_testdata_archive(self):
        """Test validation using pre-made valid tar.gz from testdata."""
        testdata_file = Path(__file__).parent.parent.parent / "testdata" / "valid.tar.gz"

        # Verify testdata exists
        assert testdata_file.exists(), f"Testdata file not found: {testdata_file}"

        # The function should accept valid gzipped tar files
        result = validate_and_prepare_tar(testdata_file)

        # Should return the same file path since it's already valid
        assert result == str(testdata_file)

    def test_validate_prepare_tar_with_corrupt_testdata_archive(self):
        """Test error handling using corrupted tar.gz from testdata."""
        testdata_file = Path(__file__).parent.parent.parent / "testdata" / "corrupt.tar.gz"

        # Verify testdata exists
        assert testdata_file.exists(), f"Testdata file not found: {testdata_file}"

        # Should raise an exception for corrupt files
        with pytest.raises(Exception) as exc_info:
            validate_and_prepare_tar(testdata_file)

        # Should mention it's not a valid tar file
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["tar", "gzip", "archive", "format"])

    def test_validate_prepare_tar_with_unsupported_file_type(self):
        """Test rejection of non-terraform files using testdata."""
        testdata_file = Path(__file__).parent.parent.parent / "testdata" / "unsupported.txt"

        # Verify testdata exists
        assert testdata_file.exists(), f"Testdata file not found: {testdata_file}"

        # Should raise an exception for unsupported file types
        with pytest.raises(Exception) as exc_info:
            validate_and_prepare_tar(testdata_file)

        # Should indicate file type issue
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["directory", "tar", "supported", "invalid"])


class TestConfigurationVersionOperations:
    """Tests for configuration version CRUD operations."""

    def test_create_configuration_version_missing_data(self):
        """Test that function handles missing data gracefully using .get() method."""
        mock_client = Mock()
        params = {"workspace_id": "ws-123", "auto_queue_runs": True, "speculative": False, "provisional": False}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_config") as mock_create:
            mock_create.return_value = {"data": {}}  # Missing 'id' and 'attributes'

            # Should NOT raise KeyError because original implementation uses .get()
            config_id, upload_url = create_configuration_version(mock_client, params)

            # Should return None values since .get() returns None for missing keys
            assert config_id is None
            assert upload_url is None

    def test_create_configuration_version_with_all_options(self):
        """Test configuration version creation with all boolean options set."""
        mock_client = Mock()
        params = {"workspace_id": "ws-456", "auto_queue_runs": False, "speculative": True, "provisional": True}

        mock_response = {"data": {"id": "cv-456", "attributes": {"upload-url": "https://example.com/upload"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_config") as mock_create:
            mock_create.return_value = mock_response

            config_id, upload_url = create_configuration_version(mock_client, params)

            assert config_id == "cv-456"
            assert upload_url == "https://example.com/upload"

            # Verify the attributes were passed correctly
            mock_create.assert_called_once_with(mock_client, "ws-456", {"auto-queue-runs": False, "speculative": True, "provisional": True})

    def test_upload_configuration_version_success(self):
        """Test successful upload with 200 status."""
        mock_client = Mock()
        upload_url = "https://example.com/upload"
        config_path = "/fake/path.tar.gz"

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_config") as mock_upload:
            mock_upload.return_value = {"status": 200}

            result = upload_configuration_version(mock_client, upload_url, config_path)

            assert result == 200
            mock_upload.assert_called_once_with(mock_client, upload_url=upload_url, configuration_files_path=config_path)

    def test_upload_configuration_version_different_status_codes(self):
        """Test upload with various HTTP status codes."""
        mock_client = Mock()
        upload_url = "https://example.com/upload"
        config_path = "/fake/path.tar.gz"

        status_codes = [201, 204, 400, 403, 404, 500]

        for status_code in status_codes:
            with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_config") as mock_upload:
                mock_upload.return_value = {"status": status_code}

                result = upload_configuration_version(mock_client, upload_url, config_path)
                assert result == status_code


class TestConfigurationVersionPolling:
    """Tests for configuration version status polling."""

    def test_get_configuration_version_immediate_success(self):
        """Test when configuration is immediately in uploaded state."""
        mock_client = Mock()
        params = {"poll_interval": 1, "poll_timeout": 5}
        config_id = "cv-123"

        mock_response = {"data": {"attributes": {"status": "uploaded"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config") as mock_get:
            mock_get.return_value = mock_response

            result = get_configuration_version(mock_client, params, config_id)

            assert result == mock_response
            mock_get.assert_called_once_with(mock_client, config_version_id=config_id)

    def test_get_configuration_version_timeout_behavior(self):
        """Test timeout-based polling behavior."""
        mock_client = Mock()
        params = {"poll_interval": 0.1, "poll_timeout": 0.3}  # Very short timeout
        config_id = "cv-timeout"

        mock_response = {"data": {"attributes": {"status": "pending"}}}  # Never reaches "uploaded"

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config") as mock_get:
            with patch("time.sleep"):  # Speed up the test
                mock_get.return_value = mock_response

                result = get_configuration_version(mock_client, params, config_id)

                # Should return the response even though status is not 'uploaded'
                assert result == mock_response
                # Should have been called multiple times due to polling
                assert mock_get.call_count > 1

    def test_get_configuration_version_eventual_success(self):
        """Test polling until eventual success."""
        mock_client = Mock()
        params = {"poll_interval": 0.1, "poll_timeout": 1}
        config_id = "cv-eventual"

        # Mock progression from pending to uploaded
        responses = [
            {"data": {"attributes": {"status": "pending"}}},
            {"data": {"attributes": {"status": "pending"}}},
            {"data": {"attributes": {"status": "uploaded"}}},
        ]

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config") as mock_get:
            with patch("time.sleep"):  # Speed up the test
                mock_get.side_effect = responses

                result = get_configuration_version(mock_client, params, config_id)

                # Should return the final successful response
                assert result == responses[-1]
                assert result["data"]["attributes"]["status"] == "uploaded"


class TestStateOperations:
    """Tests for state_present and state_archived operations."""

    def test_state_present_full_flow(self):
        """Test complete state_present flow with successful outcome."""
        mock_tf_client = Mock()
        mock_archivist_client = Mock()
        params = {
            "configuration_files_path": "/fake/path",
            "workspace_id": "ws-123",
            "auto_queue_runs": True,
            "speculative": False,
            "provisional": False,
            "poll_interval": 1,
            "poll_timeout": 3,
            "check_mode": False,
        }

        final_response = {"data": {"id": "cv-123", "attributes": {"status": "uploaded"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.validate_and_prepare_tar") as mock_validate, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_configuration_version",
        ) as mock_create, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_configuration_version",
        ) as mock_upload, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_configuration_version",
        ) as mock_get:

            mock_validate.return_value = "/tmp/config.tar.gz"
            mock_create.return_value = ("cv-123", "https://upload.url")
            mock_upload.return_value = 200
            mock_get.return_value = final_response

            result = state_present(mock_tf_client, mock_archivist_client, params)

            assert result["changed"] is True
            assert result["id"] == "cv-123"
            assert "status" in result["attributes"]

    def test_state_present_upload_failure(self):
        """Test state_present when upload fails."""
        mock_tf_client = Mock()
        mock_archivist_client = Mock()
        params = {
            "configuration_files_path": "/fake/path",
            "workspace_id": "ws-123",
            "auto_queue_runs": True,
            "speculative": False,
            "provisional": False,
            "check_mode": False,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.validate_and_prepare_tar") as mock_validate, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_configuration_version",
        ) as mock_create, patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_configuration_version") as mock_upload:

            mock_validate.return_value = "/tmp/config.tar.gz"
            mock_create.return_value = ("cv-123", "https://upload.url")
            mock_upload.side_effect = Exception("Upload failed")

            with pytest.raises(Exception) as exc_info:
                state_present(mock_tf_client, mock_archivist_client, params)

            assert "Upload failed" in str(exc_info.value)

    def test_state_present_final_status_not_uploaded(self):
        """Test when final status is not 'uploaded'."""
        mock_tf_client = Mock()
        mock_archivist_client = Mock()
        params = {
            "configuration_files_path": "/fake/path",
            "workspace_id": "ws-123",
            "auto_queue_runs": True,
            "speculative": False,
            "provisional": False,
            "poll_interval": 1,
            "poll_timeout": 3,
            "check_mode": False,
        }

        final_response = {"data": {"id": "cv-123", "attributes": {"status": "errored"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.validate_and_prepare_tar") as mock_validate, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_configuration_version",
        ) as mock_create, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_configuration_version",
        ) as mock_upload, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_configuration_version",
        ) as mock_get:

            mock_validate.return_value = "/tmp/config.tar.gz"
            mock_create.return_value = ("cv-123", "https://upload.url")
            mock_upload.return_value = 200
            mock_get.return_value = final_response

            result = state_present(mock_tf_client, mock_archivist_client, params)

            assert result["failed"] is True
            assert "could not transition to uploaded state" in result["msg"]

    def test_state_archived_success(self):
        """Test successful archiving of configuration version."""
        mock_client = Mock()
        config_id = "cv-archive-me"

        mock_response = {"data": {"attributes": {"status": "uploaded"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config") as mock_get, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.archive_config",
        ) as mock_archive:

            mock_get.return_value = mock_response
            mock_archive.return_value = {"status": "success"}

            result = state_archived(mock_client, config_id)

            assert result["changed"] is True
            assert "archived successfully" in result["msg"]
            mock_archive.assert_called_once_with(mock_client, config_id)

    def test_state_archived_already_archived(self):
        """Test archiving when configuration is already archived."""
        mock_client = Mock()
        config_id = "cv-already-archived"

        mock_response = {"data": {"attributes": {"status": "archived"}}}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config") as mock_get:
            mock_get.return_value = mock_response

            result = state_archived(mock_client, config_id)

            assert result["changed"] is False
            assert "is already archived" in result["msg"]

    def test_state_archived_not_found(self):
        """Test archiving when configuration version doesn't exist."""
        mock_client = Mock()
        config_id = "cv-nonexistent"

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config") as mock_get:
            mock_get.return_value = None

            result = state_archived(mock_client, config_id)

            assert result["changed"] is False
            assert "was not found" in result["msg"]


class TestMainFunctionBehavior:
    """Tests for main function edge cases and error handling."""

    def test_main_workspace_not_found(self):
        """Test main when workspace lookup fails."""
        params = {
            "state": "present",
            "workspace": "nonexistent-workspace",
            "organization": "test-org",
            "workspace_id": None,  # Explicitly set to None to trigger workspace lookup
            "configuration_files_path": "/fake/path",
            "auto_queue_runs": True,
            "speculative": False,
            "provisional": False,
            "poll_timeout": 5,
            "check_mode": False,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.ArchivistClient"), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_workspace",
        ) as mock_get_ws:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module
            # Fixed: Use empty dict {} instead of None to match actual get_workspace behavior
            mock_get_ws.return_value = {}

            main()

            # The ValueError should be caught and fail_json should be called
            mock_module.fail_json.assert_called_once()
            call_args = mock_module.fail_json.call_args[1]  # kwargs
            assert "was not found" in call_args["msg"]

    def test_main_exception_handling(self):
        """Test that main properly handles and reports exceptions."""
        params = {"state": "present", "workspace_id": "ws-123", "configuration_files_path": "/fake/path", "poll_timeout": 5, "check_mode": False}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient",
        ) as mock_client_class:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module
            mock_client_class.side_effect = Exception("Connection failed")

            # Mock fail_json to raise AssertionError with the exception message
            mock_module.fail_json.side_effect = AssertionError("Connection failed")

            with pytest.raises(AssertionError) as exc_info:
                main()

            assert "Connection failed" in str(exc_info.value)

    def test_main_workspace_id_keyerror(self):
        """Test that main raises KeyError when workspace_id is missing from params."""
        params = {
            "state": "present",
            "workspace": "test-workspace",
            "organization": "test-org",
            "configuration_files_path": "/fake/path",
            "auto_queue_runs": False,
            "speculative": True,
            "provisional": False,
            "poll_interval": 1,
            "poll_timeout": 5,
            "check_mode": False,
            # Note: No workspace_id key at all
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.ArchivistClient"):

            mock_module = Mock()
            mock_module.params = params.copy()
            mock_module_class.return_value = mock_module

            # Mock fail_json to capture the KeyError
            def capture_fail(**kwargs):
                raise AssertionError(kwargs.get("msg", "Unknown error"))

            mock_module.fail_json.side_effect = capture_fail

            with pytest.raises(AssertionError) as exc_info:
                main()

            # Should fail due to KeyError when accessing params["workspace_id"]
            assert "'workspace_id'" in str(exc_info.value)


class TestIntegrationFlows:
    """End-to-end integration-style tests."""

    def test_full_integration_present_with_workspace_id(self):
        """Test full integration of present state with workspace_id provided."""
        params = {
            "state": "present",
            "workspace_id": "ws-direct-123",
            "configuration_files_path": "/fake/path",
            "auto_queue_runs": False,
            "speculative": True,
            "provisional": False,
            "poll_interval": 1,
            "poll_timeout": 5,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.ArchivistClient"), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.state_present",
        ) as mock_state:

            mock_module = Mock()
            mock_module.params = params.copy()
            mock_module_class.return_value = mock_module

            mock_state.return_value = {"changed": True, "id": "cv-123", "attributes": {"status": "uploaded"}}

            mock_module.exit_json.side_effect = SystemExit({"changed": True})

            with pytest.raises(SystemExit):
                main()

            mock_state.assert_called_once()
            # Verify workspace_id was passed correctly
            call_args = mock_state.call_args[0][2]  # params argument
            assert call_args["workspace_id"] == "ws-direct-123"

    def test_full_integration_archived_state(self):
        """Test full integration of archived state."""
        params = {"state": "archived", "configuration_version_id": "cv-to-archive", "poll_timeout": 5}

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.ArchivistClient"), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.state_archived",
        ) as mock_state:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            mock_state.return_value = {"changed": True, "msg": "Archived successfully"}

            # Mock exit_json to raise SystemExit to simulate module exit
            mock_module.exit_json.side_effect = SystemExit({"changed": True})

            with pytest.raises(SystemExit):
                main()

            mock_state.assert_called_once_with(ANY, "cv-to-archive", params["check_mode"])

    def test_main_workspace_lookup_successful(self):
        """Test main when workspace lookup succeeds and workspace_id is set."""
        params = {
            "state": "present",
            "workspace": "test-workspace",
            "organization": "test-org",
            "workspace_id": None,  # Explicitly set to None to trigger workspace lookup
            "configuration_files_path": "/fake/path",
            "auto_queue_runs": True,
            "speculative": False,
            "provisional": False,
            "poll_timeout": 5,
            "check_mode": False,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.ArchivistClient"), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_workspace",
        ) as mock_get_ws, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.state_present",
        ) as mock_state:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            # Mock get_workspace to return valid workspace data
            mock_get_ws.return_value = {"data": {"id": "ws-from-name-123", "type": "workspaces"}, "status": 200}

            mock_state.return_value = {"changed": True, "msg": "Created successfully"}

            # Mock exit_json to raise SystemExit to simulate module exit
            mock_module.exit_json.side_effect = SystemExit({"changed": True})

            with pytest.raises(SystemExit):
                main()

            # Verify get_workspace was called with correct parameters
            mock_get_ws.assert_called_once_with(ANY, "test-org", "test-workspace")

            # Verify state_present was called and workspace_id was set correctly
            mock_state.assert_called_once()
            call_args = mock_state.call_args[0][2]  # params argument
            assert call_args["workspace_id"] == "ws-from-name-123"

    def test_main_workspace_lookup_not_found_empty_dict(self):
        """Test main when workspace lookup returns empty dict (404 case)."""
        params = {
            "state": "present",
            "workspace": "nonexistent-workspace",
            "organization": "test-org",
            "workspace_id": None,
            "configuration_files_path": "/fake/path",
            "auto_queue_runs": True,
            "speculative": False,
            "provisional": False,
            "poll_timeout": 5,
            "check_mode": False,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule") as mock_module_class, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient",
        ), patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.ArchivistClient"), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_workspace",
        ) as mock_get_ws:

            mock_module = Mock()
            mock_module.params = params
            mock_module_class.return_value = mock_module

            # Mock get_workspace to return empty dict (actual 404 behavior)
            mock_get_ws.return_value = {}

            main()

            # The ValueError should be caught and fail_json should be called
            mock_module.fail_json.assert_called_once()
            call_args = mock_module.fail_json.call_args[1]  # kwargs
            assert "The workspace nonexistent-workspace in test-org organization was not found." in call_args["msg"]

            # Verify get_workspace was called with correct parameters
            mock_get_ws.assert_called_once_with(ANY, "test-org", "nonexistent-workspace")


class TestCheckMode:
    """
    These tests focus specifically on verifying check mode.
    """

    def setup_method(self):
        """Set up common test fixtures."""
        self.mock_tf_client = Mock()
        self.mock_archivist_client = Mock()

    def test_state_present_check_mode(self):
        """Test return value structure when running in check mode."""
        params = {
            "configuration_files_path": "/fake/path/config.tar.gz",
            "workspace_id": "ws-12345",
            "auto_queue_runs": True,
            "speculative": False,
            "provisional": False,
            "poll_interval": 2,
            "poll_timeout": 10,
            "check_mode": True,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.validate_and_prepare_tar") as mock_validate:
            mock_validate.return_value = "/tmp/check_mode_validated.tar.gz"

            result = state_present(self.mock_tf_client, self.mock_archivist_client, params)

            # Verify the exact structure and content of check mode return
            assert isinstance(result, dict)
            assert result["changed"] is True
            assert "msg" in result
            assert "The configuration_files_path /tmp/check_mode_validated.tar.gz was validated" in result["msg"]
            assert "but configuration version creation was skipped due to check mode" in result["msg"]

            # Verify that no API-related keys are present in check mode
            assert "id" not in result
            assert "type" not in result
            assert "attributes" not in result
            assert "links" not in result
            assert "relationships" not in result
            assert "failed" not in result

    def test_state_archived_check_mode_configuration_version_not_found(self):
        """Test return value when configuration version is not found and check_mode=True."""
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config") as mock_get_config:
            # Mock that configuration version is not found
            mock_get_config.return_value = None
            test_config_version_id = "cv-test-12345"

            result = state_archived(self.mock_tf_client, test_config_version_id, check_mode=True)

            # Verify the exact structure and content for not found scenario
            assert isinstance(result, dict)
            assert result["changed"] is False
            assert "msg" in result
            assert f"Configuration version '{test_config_version_id}' was not found." in result["msg"]

            # Verify no other keys are present
            expected_keys = {"changed", "msg"}
            assert set(result.keys()) == expected_keys

    def test_check_mode_true_already_archived(self):
        """Test return value when configuration version is already archived and check_mode=True."""
        test_config_version_id = "cv-test-12345"
        mock_config_response = {
            "data": {
                "id": test_config_version_id,
                "type": "configuration-versions",
                "attributes": {
                    "status": "archived",
                    "auto-queue-runs": True,
                    "speculative": False,
                    "provisional": False,
                    "source": "tfe-api",
                },
            },
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config") as mock_get_config:
            mock_get_config.return_value = mock_config_response

            result = state_archived(self.mock_tf_client, test_config_version_id, check_mode=True)

            # Verify the exact structure and content for already archived scenario
            assert isinstance(result, dict)
            assert result["changed"] is False
            assert "msg" in result
            assert f"Configuration version '{test_config_version_id}' is already archived." in result["msg"]

            # Verify no other keys are present
            expected_keys = {"changed", "msg"}
            assert set(result.keys()) == expected_keys

    def test_check_mode_true_needs_archiving(self):
        """Test return value when configuration version needs archiving and check_mode=True."""
        test_config_version_id = "cv-test-12345"
        mock_config_response = {
            "data": {
                "id": test_config_version_id,
                "type": "configuration-versions",
                "attributes": {
                    "status": "uploaded",
                    "auto-queue-runs": True,
                    "speculative": False,
                    "provisional": False,
                    "source": "tfe-api",
                    "status-timestamps": {
                        "uploaded-at": "2025-01-15T10:30:00Z",
                    },
                },
                "links": {
                    "self": f"https://app.terraform.io/api/v2/configuration-versions/{test_config_version_id}",
                    "download": f"https://app.terraform.io/api/v2/configuration-versions/{test_config_version_id}/download",
                },
            },
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config") as mock_get_config, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.archive_config",
        ) as mock_archive_config:

            mock_get_config.return_value = mock_config_response

            result = state_archived(self.mock_tf_client, test_config_version_id, check_mode=True)

            # Verify the exact structure and content for successful archiving in check mode
            assert isinstance(result, dict)
            assert result["changed"] is True
            assert "msg" in result
            assert (f"Configuration version {test_config_version_id} found and in archivable state. " "Skipped archiving due to check mode.") in result["msg"]

            # Verify archive_config was NOT called in check mode
            mock_archive_config.assert_not_called()

            # Verify no other keys are present
            expected_keys = {"changed", "msg"}
            assert set(result.keys()) == expected_keys
