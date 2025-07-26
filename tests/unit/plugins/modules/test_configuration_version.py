
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import ANY, Mock, patch, mock_open

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules import configuration_version as configuration_module
from ansible_collections.hashicorp.terraform.plugins.modules.configuration_version import (
    create_configuration_version,
    get_configuration_version,
    upload_configuration_version,
    validate_and_prepare_tar,
    state_present,
    state_archived,
    main,
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


# Tests for validate_and_prepare_tar

def test_validate_prepare_tar_nonexistent_path():
    """Test that nonexistent path raises FileNotFoundError."""
    nonexistent_path = "/this/path/does/not/exist"
    
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_and_prepare_tar(Path(nonexistent_path))
    
    assert "does not exist" in str(exc_info.value)


def test_validate_prepare_tar_empty_directory():
    """Test handling of empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        result = validate_and_prepare_tar(Path(temp_dir))
        
        # Verify it creates a valid tar file
        assert tarfile.is_tarfile(result)
        
        # Verify the tar file is empty (just the directory structure)
        with tarfile.open(result, 'r:gz') as tar:
            members = tar.getnames()
            assert len(members) == 0 or all(name.endswith('/') for name in members)
        
        # Cleanup
        os.remove(result)


def test_validate_prepare_tar_directory_with_subdirectories():
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
        with tarfile.open(result, 'r:gz') as tar:
            names = tar.getnames()
            assert "main.tf" in names
            assert "subdir/variables.tf" in names
        
        # Cleanup
        os.remove(result)


def test_validate_prepare_tar_valid_uncompressed_tar():
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


def test_validate_prepare_tar_file_permission_error():
    """Test handling of permission errors when creating tar."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")
        
        # Mock tempfile.mkstemp to raise PermissionError
        with patch('tempfile.mkstemp', side_effect=PermissionError("Permission denied")):
            with pytest.raises(Exception) as exc_info:
                validate_and_prepare_tar(Path(temp_dir))
            
            assert "Failed to create tar.gz" in str(exc_info.value)


# Tests for create_configuration_version

def test_create_configuration_version_missing_data():
    """Test that function handles missing data gracefully using .get() method."""
    mock_client = Mock()
    params = {
        "workspace_id": "ws-123",
        "auto_queue_runs": True,
        "speculative": False,
        "provisional": False
    }

    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_config') as mock_create:
        mock_create.return_value = {"data": {}}  # Missing 'id' and 'attributes'

        # Should NOT raise KeyError because original implementation uses .get()
        config_id, upload_url = create_configuration_version(mock_client, params)
        
        # Should return None values since .get() returns None for missing keys
        assert config_id is None
        assert upload_url is None


def test_create_configuration_version_with_all_options():
    """Test configuration version creation with all boolean options set."""
    mock_client = Mock()
    params = {
        "workspace_id": "ws-456",
        "auto_queue_runs": False,
        "speculative": True,
        "provisional": True
    }
    
    mock_response = {
        "data": {
            "id": "cv-456",
            "attributes": {
                "upload-url": "https://example.com/upload"
            }
        }
    }
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_config') as mock_create:
        mock_create.return_value = mock_response
        
        config_id, upload_url = create_configuration_version(mock_client, params)
        
        assert config_id == "cv-456"
        assert upload_url == "https://example.com/upload"
        
        # Verify the attributes were passed correctly
        mock_create.assert_called_once_with(
            mock_client,
            "ws-456",
            {
                "auto-queue-runs": False,
                "speculative": True,
                "provisional": True
            }
        )


# Tests for upload_configuration_version

def test_upload_configuration_version_success():
    """Test successful upload with 200 status."""
    mock_client = Mock()
    upload_url = "https://example.com/upload"
    config_path = "/fake/path.tar.gz"
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_config') as mock_upload:
        mock_upload.return_value = {"status": 200}
        
        result = upload_configuration_version(mock_client, upload_url, config_path)
        
        assert result == 200
        mock_upload.assert_called_once_with(mock_client, upload_url=upload_url, configuration_files_path=config_path)


def test_upload_configuration_version_different_status_codes():
    """Test upload with various HTTP status codes."""
    mock_client = Mock()
    upload_url = "https://example.com/upload"
    config_path = "/fake/path.tar.gz"
    
    status_codes = [201, 204, 400, 403, 404, 500]
    
    for status_code in status_codes:
        with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_config') as mock_upload:
            mock_upload.return_value = {"status": status_code}
            
            result = upload_configuration_version(mock_client, upload_url, config_path)
            assert result == status_code


# Tests for get_configuration_version

def test_get_configuration_version_immediate_success():
    """Test when configuration is immediately in uploaded state."""
    mock_client = Mock()
    params = {"poll_interval": 1, "poll_timeout": 5}
    config_id = "cv-123"
    
    mock_response = {
        "data": {
            "attributes": {
                "status": "uploaded"
            }
        }
    }
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config') as mock_get:
        mock_get.return_value = mock_response
        
        result = get_configuration_version(mock_client, params, config_id)
        
        assert result == mock_response
        mock_get.assert_called_once_with(mock_client, config_version_id=config_id)


def test_get_configuration_version_timeout_behavior():
    """Test timeout-based polling behavior."""
    mock_client = Mock()
    params = {"poll_interval": 0.1, "poll_timeout": 0.3}  # Very short timeout
    config_id = "cv-timeout"
    
    mock_response = {
        "data": {
            "attributes": {
                "status": "pending"  # Never reaches "uploaded"
            }
        }
    }
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config') as mock_get:
        with patch('time.sleep'):  # Speed up the test
            mock_get.return_value = mock_response
            
            result = get_configuration_version(mock_client, params, config_id)
            
            # Should return the response even though status is not 'uploaded'
            assert result == mock_response
            # Should have been called multiple times due to polling
            assert mock_get.call_count > 1


def test_get_configuration_version_eventual_success():
    """Test polling until eventual success."""
    mock_client = Mock()
    params = {"poll_interval": 0.1, "poll_timeout": 1}
    config_id = "cv-eventual"
    
    # Mock progression from pending to uploaded
    responses = [
        {"data": {"attributes": {"status": "pending"}}},
        {"data": {"attributes": {"status": "pending"}}},
        {"data": {"attributes": {"status": "uploaded"}}}
    ]
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config') as mock_get:
        with patch('time.sleep'):  # Speed up the test
            mock_get.side_effect = responses
            
            result = get_configuration_version(mock_client, params, config_id)
            
            # Should return the final successful response
            assert result == responses[-1]
            assert result["data"]["attributes"]["status"] == "uploaded"


# Tests for state_present

def test_state_present_full_flow():
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
        "poll_timeout": 3
    }
    
    final_response = {
        "data": {
            "id": "cv-123",
            "attributes": {
                "status": "uploaded"
            }
        }
    }
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.validate_and_prepare_tar') as mock_validate, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_configuration_version') as mock_create, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_configuration_version') as mock_upload, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_configuration_version') as mock_get:
        
        mock_validate.return_value = "/tmp/config.tar.gz"
        mock_create.return_value = ("cv-123", "https://upload.url")
        mock_upload.return_value = 200
        mock_get.return_value = final_response
        
        result = state_present(mock_tf_client, mock_archivist_client, params)
        
        assert result["changed"] is True
        assert result["id"] == "cv-123"
        assert "status" in result["attributes"]


def test_state_present_upload_failure():
    """Test state_present when upload fails."""
    mock_tf_client = Mock()
    mock_archivist_client = Mock()
    params = {
        "configuration_files_path": "/fake/path",
        "workspace_id": "ws-123",
        "auto_queue_runs": True,
        "speculative": False,
        "provisional": False
    }
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.validate_and_prepare_tar') as mock_validate, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_configuration_version') as mock_create, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_configuration_version') as mock_upload:
        
        mock_validate.return_value = "/tmp/config.tar.gz"
        mock_create.return_value = ("cv-123", "https://upload.url")
        mock_upload.side_effect = Exception("Upload failed")
        
        with pytest.raises(Exception) as exc_info:
            state_present(mock_tf_client, mock_archivist_client, params)
        
        assert "Upload failed" in str(exc_info.value)


def test_state_present_final_status_not_uploaded():
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
        "poll_timeout": 3
    }
    
    final_response = {
        "data": {
            "id": "cv-123",
            "attributes": {
                "status": "errored"
            }
        }
    }
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.validate_and_prepare_tar') as mock_validate, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_configuration_version') as mock_create, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_configuration_version') as mock_upload, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_configuration_version') as mock_get:
        
        mock_validate.return_value = "/tmp/config.tar.gz"
        mock_create.return_value = ("cv-123", "https://upload.url")
        mock_upload.return_value = 200
        mock_get.return_value = final_response
        
        result = state_present(mock_tf_client, mock_archivist_client, params)
        
        assert result["failed"] is True
        assert "could not transition to uploaded state" in result["msg"]


# Tests for state_archived

def test_state_archived_success():
    """Test successful archiving of configuration version."""
    mock_client = Mock()
    config_id = "cv-archive-me"
    
    mock_response = {
        "data": {
            "attributes": {
                "status": "uploaded"
            }
        }
    }
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config') as mock_get, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.archive_config') as mock_archive:
        
        mock_get.return_value = mock_response
        mock_archive.return_value = {"status": "success"}
        
        result = state_archived(mock_client, config_id)
        
        assert result["changed"] is True
        assert "archived successfully" in result["msg"]
        mock_archive.assert_called_once_with(mock_client, config_id)


def test_state_archived_already_archived():
    """Test archiving when configuration is already archived."""
    mock_client = Mock()
    config_id = "cv-already-archived"
    
    mock_response = {
        "data": {
            "attributes": {
                "status": "archived"
            }
        }
    }
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config') as mock_get:
        mock_get.return_value = mock_response
        
        result = state_archived(mock_client, config_id)
        
        assert result["changed"] is False
        assert "is already archived" in result["msg"]


def test_state_archived_not_found():
    """Test archiving when configuration version doesn't exist."""
    mock_client = Mock()
    config_id = "cv-nonexistent"
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config') as mock_get:
        mock_get.return_value = None
        
        result = state_archived(mock_client, config_id)
        
        assert result["changed"] is False
        assert "was not found" in result["msg"]


# Tests for main function edge cases

def test_main_workspace_not_found():
    """Test main when workspace lookup fails."""
    params = {
        "state": "present",
        "workspace": "nonexistent-workspace",
        "organization": "test-org",
        "configuration_files_path": "/fake/path",
        "auto_queue_runs": True,
        "speculative": False,
        "provisional": False,
        "poll_timeout": 5
    }
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule') as mock_module_class, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient'), \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.ArchivistClient'), \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_workspace') as mock_get_ws:
        
        mock_module = Mock()
        mock_module.params = params
        mock_module_class.return_value = mock_module
        mock_get_ws.return_value = None
        
        # Mock fail_json to raise AssertionError
        mock_module.fail_json.side_effect = AssertionError("Workspace was not found")
        
        with pytest.raises(AssertionError) as exc_info:
            main()
        
        assert "was not found" in str(exc_info.value)


def test_main_exception_handling():
    """Test that main properly handles and reports exceptions."""
    params = {
        "state": "present",
        "workspace_id": "ws-123",
        "configuration_files_path": "/fake/path",
        "poll_timeout": 5
    }
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule') as mock_module_class, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient') as mock_client_class:
        
        mock_module = Mock()
        mock_module.params = params
        mock_module_class.return_value = mock_module
        mock_client_class.side_effect = Exception("Connection failed")
        
        # Mock fail_json to raise AssertionError with the exception message
        mock_module.fail_json.side_effect = AssertionError("Connection failed")
        
        with pytest.raises(AssertionError) as exc_info:
            main()
        
        assert "Connection failed" in str(exc_info.value)


def test_main_workspace_id_keyerror():
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
        "poll_timeout": 5
        # Note: No workspace_id key at all
    }

    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule') as mock_module_class, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient'), \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.ArchivistClient'):

        mock_module = Mock()
        mock_module.params = params.copy()
        mock_module_class.return_value = mock_module

        # Mock fail_json to capture the KeyError
        def capture_fail(**kwargs):
            raise AssertionError(kwargs.get('msg', 'Unknown error'))
        
        mock_module.fail_json.side_effect = capture_fail

        with pytest.raises(AssertionError) as exc_info:
            main()

        # Should fail due to KeyError when accessing params["workspace_id"]
        assert "'workspace_id'" in str(exc_info.value)


# Integration-style tests

def test_full_integration_present_with_workspace_id():
    """Test full integration of present state with workspace_id provided."""
    params = {
        "state": "present",
        "workspace_id": "ws-direct-123",
        "configuration_files_path": "/fake/path",
        "auto_queue_runs": False,
        "speculative": True,
        "provisional": False,
        "poll_interval": 1,
        "poll_timeout": 5
    }

    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule') as mock_module_class, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient'), \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.ArchivistClient'), \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.state_present') as mock_state:

        mock_module = Mock()
        mock_module.params = params.copy()
        mock_module_class.return_value = mock_module

        mock_state.return_value = {
            "changed": True,
            "id": "cv-123",
            "attributes": {"status": "uploaded"}
        }

        mock_module.exit_json.side_effect = SystemExit({"changed": True})

        with pytest.raises(SystemExit):
            main()

        mock_state.assert_called_once()
        # Verify workspace_id was passed correctly
        call_args = mock_state.call_args[0][2]  # params argument
        assert call_args["workspace_id"] == "ws-direct-123"


def test_full_integration_archived_state():
    """Test full integration of archived state."""
    params = {
        "state": "archived",
        "configuration_version_id": "cv-to-archive",
        "poll_timeout": 5
    }
    
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule') as mock_module_class, \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient'), \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.ArchivistClient'), \
         patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.state_archived') as mock_state:
        
        mock_module = Mock()
        mock_module.params = params
        mock_module_class.return_value = mock_module
        
        mock_state.return_value = {"changed": True, "msg": "Archived successfully"}
        
        # Mock exit_json to raise SystemExit to simulate module exit
        mock_module.exit_json.side_effect = SystemExit({"changed": True})
        
        with pytest.raises(SystemExit):
            main()
        
        mock_state.assert_called_once_with(ANY, "cv-to-archive")
