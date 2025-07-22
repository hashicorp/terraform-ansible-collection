import os
import pytest
import tempfile
import shutil
import tarfile
import gzip
from unittest.mock import patch, MagicMock, ANY
from ansible_collections.hashicorp.terraform.plugins.modules import (
    configuration_version as configuration_module,
)
from ansible_collections.hashicorp.terraform.plugins.modules.configuration_version import (
    create_configuration_version,
    upload_configuration_version,
    validate_and_prepare_tar,
    get_configuration_version,
)


# <<< IMPROVEMENT: A more robust dummy module to inspect call arguments.
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
        # Raise a specific exception to make catching it more reliable.
        raise AssertionError(kwargs.get("msg", "fail_json called with no message"))

    def exit_json(self, **kwargs):
        self.exit_args = kwargs
        # Ansible modules exit, so we simulate this to stop execution.
        raise SystemExit(kwargs)


# <<< IMPROVEMENT: Fixtures are more robust and self-contained.
@pytest.fixture
def temp_dir_with_files():
    """Create a temporary directory with a dummy file, ensuring cleanup."""
    path = tempfile.mkdtemp()
    with open(os.path.join(path, "main.tf"), "w") as f:
        f.write('resource "null_resource" "test" {}')
    yield path
    shutil.rmtree(path)


@pytest.fixture
def valid_tar_file(temp_dir_with_files):
    """Create a valid gzipped tar file for testing, ensuring cleanup."""
    tar_path = os.path.join(tempfile.gettempdir(), f"valid_{os.path.basename(temp_dir_with_files)}.tar.gz")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(temp_dir_with_files, arcname=os.path.basename(temp_dir_with_files))
    yield tar_path
    if os.path.exists(tar_path):
        os.remove(tar_path)


@pytest.fixture
def corrupt_tar_file():
    """Create a file that is not a valid tar archive, ensuring cleanup."""
    fd, path = tempfile.mkstemp(suffix=".tar.gz")
    with os.fdopen(fd, "wb") as f:
        f.write(b"this is not a tar file")
    yield path
    os.remove(path)

###
# Tests for validate_and_prepare_tar
###

def test_validate_prepare_tar_from_directory(temp_dir_with_files):
    """Verify that a directory is correctly archived into a tar.gz file."""
    module = EnhancedDummyModule()
    tar_path = validate_and_prepare_tar(temp_dir_with_files, module)
    assert tarfile.is_tarfile(tar_path)
    # Ensure cleanup of the generated tarball
    os.remove(tar_path)


def test_validate_prepare_tar_with_valid_archive(valid_tar_file):
    """Verify that a pre-existing valid tar.gz file is accepted."""
    module = EnhancedDummyModule()
    result = validate_and_prepare_tar(valid_tar_file, module)
    # Use Path.resolve() to handle symlinks like /var -> /private/var on macOS
    from pathlib import Path
    assert Path(result).resolve() == Path(valid_tar_file).resolve()


@pytest.mark.parametrize(
    "file_fixture, expected_error_msg",
    [
        ("corrupt_tar_file", "not a valid tar.gz archive"),
        (None, "does not exist"), # Special case for non-existent path
    ],
)
def test_validate_prepare_tar_failures(file_fixture, expected_error_msg, request):
    """Verify failure modes for invalid inputs."""
    module = EnhancedDummyModule()
    path = request.getfixturevalue(file_fixture) if file_fixture else "/nonexistent/path"

    with pytest.raises(AssertionError) as exc_info:
        validate_and_prepare_tar(path, module)

    assert expected_error_msg in str(exc_info.value)
    assert module.failed is True


###
# Tests for individual functions
###

def test_create_configuration_version_success():
    """Verify successful creation of a configuration version."""
    module = EnhancedDummyModule()
    mock_return = {
        "data": {"data": {"id": "cv-123", "attributes": {"upload-url": "https://upload.url"}}}
    }
    params = {"workspace_id": "ws-123", "auto_queue_runs": False, "speculative": False, "provisional": False}

    # Mock the create_config function that's actually called
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_config') as mock_create_config:
        mock_create_config.return_value = mock_return
        
        config_id, upload_url = create_configuration_version(None, params, module)

        assert config_id == "cv-123"
        assert upload_url == "https://upload.url"


def test_create_configuration_version_api_failure():
    """Verify failure when the API returns an error or unexpected structure."""
    module = EnhancedDummyModule()
    params = {"workspace_id": "invalid-id", "auto_queue_runs": False, "speculative": False, "provisional": False}
    
    # Mock the create_config function that's actually called
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_config') as mock_create_config:
        mock_create_config.side_effect = Exception("API Error: Workspace not found")
        
        with pytest.raises(AssertionError) as exc_info:
            create_configuration_version(None, params, module)

        assert "API Error: Workspace not found" in str(exc_info.value)
        assert module.failed is True


def test_upload_configuration_version_failure(tmp_path):
    """Verify that a non-200 status code from upload fails the module."""
    module = EnhancedDummyModule()
    
    # Create a temporary file to avoid file not found errors
    test_file = tmp_path / "test.tar.gz"
    test_file.write_text("test content")
    
    # Mock the upload_config function that's actually called
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_config') as mock_upload_config:
        mock_upload_config.return_value = {"status": 403, "message": "Forbidden"}
        
        with pytest.raises(AssertionError) as exc_info:
            upload_configuration_version(None, {}, module, "https://fake.upload.url", str(test_file))

        assert module.failed is True
        # <<< IMPROVEMENT: Assert the exact message passed to fail_json.
        assert module.fail_args["msg"] == "Forbidden"


# <<< IMPROVEMENT: Parameterize to test multiple success scenarios concisely.
@pytest.mark.parametrize("retries_needed", [0, 2])
def test_get_configuration_version_success(retries_needed):
    """Verify polling for 'uploaded' status succeeds immediately and after retries."""
    module = EnhancedDummyModule()
    params = {"interval": 0.01, "tf_max_retries": 5}  # Shorter interval for faster tests
    config_version_id = "cv-123"

    # Create a sequence of responses: 'pending' then 'uploaded'.
    responses = [{"data": {"data": {"attributes": {"status": "pending"}}}}] * retries_needed
    responses.append({"data": {"data": {"attributes": {"status": "uploaded"}}}})

    # Mock the get_config function that's actually called
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config') as mock_get_config:
        mock_get_config.side_effect = responses
        
        status = get_configuration_version(None, params, module, config_version_id)

        assert status == "uploaded"
        assert mock_get_config.call_count == retries_needed + 1
        assert not module.failed


def test_get_configuration_version_timeout_failure():
    """Verify failure when max retries are exceeded before status is 'uploaded'."""
    module = EnhancedDummyModule()
    params = {"interval": 0.01, "tf_max_retries": 3}  # Shorter interval for faster tests
    config_version_id = "cv-123"
    
    # Mock the get_config function that's actually called
    with patch('ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_config') as mock_get_config:
        mock_get_config.return_value = {"data": {"data": {"attributes": {"status": "pending"}}}}

        with pytest.raises(AssertionError) as exc_info:
            get_configuration_version(None, params, module, config_version_id)

        assert "did not reach 'uploaded' after 3 retries" in str(exc_info.value)
        assert mock_get_config.call_count == 3
        assert module.failed


###
# Tests for main() function logic
###

@pytest.fixture
def mocked_main_dependencies(mocker):
    """A fixture to mock all external dependencies for main()."""
    mock_tf_module = mocker.patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformModule")
    mock_tf_client = mocker.patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.TerraformClient")
    mock_arc_client = mocker.patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.ArchivistClient")
    mocker.patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.validate_and_prepare_tar", return_value="/fake/archive.tar.gz")
    mocker.patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.create_configuration_version", return_value=("cv-123", "https://upload.url"))
    mocker.patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.upload_configuration_version", return_value=200)
    mocker.patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_configuration_version", return_value="uploaded")
    mocker.patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.get_workspace", return_value={"data": {"data": {"id": "ws-123"}}})
    mocker.patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version.archive_config", return_value={"status": "ok"})

    # Set up the mocked TerraformClient to return max_retries
    mock_tf_client.return_value.session_args = {"tf_max_retries": 5}

    return mock_tf_module


def test_main_present_success(mocked_main_dependencies):
    """Verify the happy path for state=present."""
    params = {
        "state": "present",
        "configuration_files_path": "/fake/path",
        "workspace_id": "ws-123",
        "auto_queue_runs": True,
        "speculative": False, "provisional": False, "interval": 1,
        "tf_hostname": "app.terraform.io", "tf_token": "token"
    }
    mocked_main_dependencies.return_value = EnhancedDummyModule(params=params)

    with pytest.raises(SystemExit) as exc_info:
        configuration_module.main()

    result = exc_info.value.args[0]
    assert result["changed"] is True
    assert result["configuration_version_id"] == "cv-123"
    assert result["upload_response"] == 200
    assert result["config_status"] == "uploaded"


def test_main_present_workspace_name_lookup(mocked_main_dependencies):
    """Verify workspace ID is correctly retrieved when name/org are provided."""
    params = {
        "state": "present",
        "configuration_files_path": "/fake/path",
        "workspace": "my-workspace",
        "organization": "my-org",
        "auto_queue_runs": True, "speculative": False, "provisional": False, "interval": 1,
        "tf_hostname": "app.terraform.io", "tf_token": "token"
    }
    mocked_main_dependencies.return_value = EnhancedDummyModule(params=params)
    get_ws_mock = configuration_module.get_workspace

    with pytest.raises(SystemExit):
        configuration_module.main()

    get_ws_mock.assert_called_once_with(ANY, "my-org", "my-workspace")


def test_main_present_upload_fails(mocked_main_dependencies):
    """Verify main fails correctly if the upload step fails."""
    configuration_module.upload_configuration_version.side_effect = AssertionError("Upload failed")
    params = {"state": "present", "configuration_files_path": "/fake/path", "workspace_id": "ws-123"}
    dummy_module = EnhancedDummyModule(params=params)
    mocked_main_dependencies.return_value = dummy_module

    with pytest.raises(AssertionError) as exc_info:
        configuration_module.main()

    assert "Upload failed" in str(exc_info.value)


# <<< IMPROVEMENT: Test for the 'absent' state.
def test_main_absent_fails_with_message(mocked_main_dependencies):
    """Verify state=absent fails with the correct informational message."""
    params = {"state": "absent"}
    dummy_module = EnhancedDummyModule(params=params)
    mocked_main_dependencies.return_value = dummy_module

    with pytest.raises(AssertionError) as exc_info:
        configuration_module.main()

    assert "not yet supported" in str(exc_info.value)
    assert dummy_module.failed is True


def test_main_archive_success(mocked_main_dependencies):
    """Verify the happy path for state=archive."""
    params = {"state": "archive", "configuration_version_id": "cv-to-archive"}
    dummy_module = EnhancedDummyModule(params=params)
    mocked_main_dependencies.return_value = dummy_module
    archive_mock = configuration_module.archive_config

    with pytest.raises(SystemExit) as exc_info:
        configuration_module.main()

    archive_mock.assert_called_once_with(ANY, "cv-to-archive")
    result = exc_info.value.args[0]
    assert result["changed"] is True
    assert result["configuration_version_id"] == "cv-to-archive"
    assert "Configuration version archived successfully" in result["msg"]