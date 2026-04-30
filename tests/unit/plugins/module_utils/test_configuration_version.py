# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, mock_open, patch

import pytest
from pytfe.errors import NotFound, TFEError
from pytfe.models import ConfigurationVersionCreateOptions

# Import the module under test
from ansible_collections.hashicorp.terraform.plugins.module_utils.configuration_version import (
    archive_config,
    create_config,
    get_config,
    upload_config,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)


@pytest.fixture
def mock_clients():
    """Fixture providing mock clients and common test data for configuration version tests."""
    adapter = Mock()
    adapter.client.configuration_versions.create = Mock()
    adapter.client.configuration_versions.read = Mock()
    adapter.client.configuration_versions.archive = Mock()
    adapter.client.configuration_versions.upload_tar_gzip = Mock()

    return {
        "adapter": adapter,
        "workspace_id": "ws-123abc456def789",
        "config_version_id": "cv-123abc456def789",
        "attributes": {"auto-queue-runs": False, "speculative": True},
        "upload_url": "https://archivist.example.com/object/dummy-object-id",
        "file_path": "/fake/path/dummy-object-id",
    }


class TestCreateConfigFunction:
    """Test suite for the create_config function.

    Tests the creation of Terraform configuration versions via the Terraform API.
    Covers success scenarios, error handling, and edge cases for configuration
    version creation with various attributes and response formats.
    """

    def test_create_config_success(self, mock_clients):
        """Test create_config returns formatted response from SDK."""
        response_obj = Mock()
        response_obj.model_dump.return_value = {"id": "cv-123abc456def789", "status": "pending"}
        mock_clients["adapter"].client.configuration_versions.create.return_value = response_obj

        result = create_config(mock_clients["adapter"], mock_clients["workspace_id"], mock_clients["attributes"])

        assert result == {"id": "cv-123abc456def789", "status": "pending"}
        args, _kwargs = mock_clients["adapter"].client.configuration_versions.create.call_args
        assert args[0] == mock_clients["workspace_id"]
        assert isinstance(args[1], ConfigurationVersionCreateOptions)

    def test_create_config_error(self, mock_clients):
        """Test create_config wraps SDK errors in TerraformError."""
        mock_clients["adapter"].client.configuration_versions.create.side_effect = TFEError("boom")

        with pytest.raises(TerraformError):
            create_config(mock_clients["adapter"], mock_clients["workspace_id"], mock_clients["attributes"])


class TestArchiveConfigFunction:
    """Test suite for the archive_config function.

    Tests the archiving of Terraform configuration versions via the Terraform API.
    Covers successful archiving, 404 handling for non-existent configurations,
    and error scenarios with various HTTP status codes.
    """

    def test_archive_config_success(self, mock_clients):
        """Test successful archiving of a configuration version.

        Verifies that archive_config properly handles successful API responses
        and returns the expected status information when archiving a configuration
        version that exists and can be archived.

        Args:
            mock_clients: Fixture providing mock clients and test data
        """
        mock_clients["adapter"].client.configuration_versions.archive.return_value = None

        result = archive_config(mock_clients["adapter"], mock_clients["config_version_id"])

        expected_result = {"status": 202}
        assert result == expected_result
        mock_clients["adapter"].client.configuration_versions.archive.assert_called_once_with(
            mock_clients["config_version_id"],
        )

    def test_archive_config_404(self, mock_clients):
        """Test archive_config raises TerraformError on 404 from SDK."""
        mock_clients["adapter"].client.configuration_versions.archive.side_effect = NotFound("missing")

        with pytest.raises(TerraformError):
            archive_config(mock_clients["adapter"], mock_clients["config_version_id"])

    def test_archive_config_failure_scenario(self, mock_clients):
        """Test archive_config raises TerraformError on SDK failures."""
        mock_clients["adapter"].client.configuration_versions.archive.side_effect = TFEError("boom")

        with pytest.raises(TerraformError):
            archive_config(mock_clients["adapter"], mock_clients["config_version_id"])


class TestGetConfigFunction:
    """Test suite for the get_config function.

    Tests the retrieval of Terraform configuration versions via the Terraform API.
    Covers successful retrieval with various response formats, 404 handling for
    non-existent configurations, and error scenarios with different HTTP status codes.
    """

    def test_get_config_success(self, mock_clients):
        """Test get_config returns formatted response from SDK."""
        response_obj = Mock()
        response_obj.model_dump.return_value = {"id": "cv-123abc456def789", "status": "uploaded"}
        mock_clients["adapter"].client.configuration_versions.read.return_value = response_obj

        result = get_config(mock_clients["adapter"], mock_clients["config_version_id"])

        assert result == {"id": "cv-123abc456def789", "status": "uploaded"}
        mock_clients["adapter"].client.configuration_versions.read.assert_called_once_with(
            mock_clients["config_version_id"],
        )

    def test_get_config_404(self, mock_clients):
        """Test get_config returns empty dict on 404."""
        mock_clients["adapter"].client.configuration_versions.read.side_effect = NotFound("missing")

        result = get_config(mock_clients["adapter"], mock_clients["config_version_id"])

        assert result == {}

    def test_get_config_failure_scenario(self, mock_clients):
        """Test get_config propagates SDK failures."""
        mock_clients["adapter"].client.configuration_versions.read.side_effect = TFEError("boom")

        with pytest.raises(TFEError):
            get_config(mock_clients["adapter"], mock_clients["config_version_id"])


class TestUploadConfigFunction:
    """Test suite for the upload_config function.

    Tests the uploading of configuration files to the Terraform Archivist service.
    Covers successful uploads with various URL formats, file handling scenarios,
    and error conditions during the upload process.
    """

    @patch("builtins.open", new_callable=mock_open, read_data=b"file-content")
    def test_upload_config_success_full_url(self, mock_file, mock_clients):
        """Test successful upload when a full HTTPS URL is provided."""
        mock_clients["adapter"].client.configuration_versions.upload_tar_gzip.return_value = None

        result = upload_config(mock_clients["adapter"], mock_clients["upload_url"], mock_clients["file_path"])

        assert result is None
        mock_file.assert_called_once_with(mock_clients["file_path"], "rb")
        mock_clients["adapter"].client.configuration_versions.upload_tar_gzip.assert_called_once_with(
            mock_clients["upload_url"],
            mock_file.return_value,
        )

    def test_upload_config_with_nonexistent_file(self, mock_clients):
        """Test upload failure when archive file does not exist."""
        nonexistent_file = "/path/to/nonexistent/testdata.tar.gz"

        with pytest.raises(FileNotFoundError):
            upload_config(mock_clients["adapter"], mock_clients["upload_url"], nonexistent_file)

    @patch("builtins.open", new_callable=mock_open)
    def test_upload_config_failure_scenario(self, mock_file, mock_clients):
        """Test upload_config raises TerraformError on SDK failures."""
        mock_clients["adapter"].client.configuration_versions.upload_tar_gzip.side_effect = TFEError("boom")

        with pytest.raises(TerraformError):
            upload_config(mock_clients["adapter"], mock_clients["upload_url"], mock_clients["file_path"])
