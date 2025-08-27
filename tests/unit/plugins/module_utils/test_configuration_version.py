# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import re

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

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
    """Fixture providing mock clients and common test data for configuration version tests.

    Returns:
        dict: A dictionary containing:
            - tf_client: Mock Terraform client for API interactions
            - archivist_client: Mock Archivist client for file uploads
            - workspace_id: Sample workspace identifier
            - config_version_id: Sample configuration version identifier
            - attributes: Sample configuration version attributes
            - upload_url: Sample upload URL for archivist operations
            - file_path: Sample file path for configuration archives
    """
    return {
        "tf_client": Mock(),
        "archivist_client": Mock(),
        "workspace_id": "ws-123abc456def789",
        "config_version_id": "cv-123abc456def789",
        "attributes": {"auto-queue-runs": False, "speculative": True},
        "upload_url": "https://archivist.example.com/object/dummy-object-id",
        "file_path": "/fake/path/config.tar.gz",
    }


@patch("ansible_collections.hashicorp.terraform.plugins.module_utils.configuration_version.re", re)
class TestCreateConfigFunction:
    """Test suite for the create_config function.

    Tests the creation of Terraform configuration versions via the Terraform API.
    Covers success scenarios, error handling, and edge cases for configuration
    version creation with various attributes and response formats.
    """

    @pytest.mark.parametrize(
        "response_data,expected_result,description",
        [
            (
                {"data": {"id": "cv-123abc456def789", "type": "configuration-versions"}, "status": 201},
                {"id": "cv-123abc456def789", "type": "configuration-versions", "status": 201},
                "successful creation with full data",
            ),
            (
                {"data": {}, "status": 201},
                {"status": 201},
                "empty data section",
            ),
            (
                {"status": 201},
                {"status": 201},
                "no data key",
            ),
        ],
    )
    def test_create_config_success_scenarios(self, mock_clients, response_data, expected_result, description):
        """Test various successful create_config scenarios.

        This parameterized test verifies that create_config properly handles
        different API response formats including full data, empty data sections,
        and missing data keys, ensuring graceful degradation in all cases.

        Args:
            mock_clients: Fixture providing mock clients and test data
            response_data: Simulated API response from Terraform
            expected_result: Expected parsed result from create_config
            description: Test case description for clarity
        """
        mock_clients["tf_client"].post.return_value = response_data

        result = create_config(mock_clients["tf_client"], mock_clients["workspace_id"], mock_clients["attributes"])

        assert result == expected_result

        # Verify payload structure
        expected_payload = {
            "data": {
                "type": "configuration-versions",
                "attributes": mock_clients["attributes"],
            },
        }
        mock_clients["tf_client"].post.assert_called_once_with(
            f"/workspaces/{mock_clients['workspace_id']}/configuration-versions",
            data=expected_payload,
        )

    @pytest.mark.parametrize("status_code", [400, 500, 502, 503])
    def test_create_config_failure_scenarios(self, mock_clients, status_code):
        """Test create_config error handling for various HTTP error status codes.

        Verifies that create_config properly raises TerraformError exceptions
        when the Terraform API returns error status codes, ensuring proper
        error propagation to calling code.

        Args:
            mock_clients: Fixture providing mock clients and test data
            status_code: HTTP status code to simulate from the API
        """
        response = {"data": {}, "status": status_code}
        mock_clients["tf_client"].post.return_value = response

        with pytest.raises(TerraformError):
            create_config(mock_clients["tf_client"], mock_clients["workspace_id"], mock_clients["attributes"])

    def test_create_config_with_empty_attributes(self, mock_clients):
        """Test create_config behavior when provided with empty attributes.

        Verifies that create_config can handle empty attribute dictionaries
        gracefully, which may occur when no specific configuration version
        attributes need to be set.

        Args:
            mock_clients: Fixture providing mock clients and test data
        """
        expected_response = {"data": {"id": mock_clients["config_version_id"]}, "status": 201}
        mock_clients["tf_client"].post.return_value = expected_response
        empty_attributes = {}

        result = create_config(mock_clients["tf_client"], mock_clients["workspace_id"], empty_attributes)

        expected_result = {"id": mock_clients["config_version_id"], "status": 201}
        assert result == expected_result


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
        response = {"status": 202}
        mock_clients["tf_client"].post.return_value = response

        result = archive_config(mock_clients["tf_client"], mock_clients["config_version_id"])

        expected_result = {"status": 202}
        assert result == expected_result
        mock_clients["tf_client"].post.assert_called_once_with(
            f"/configuration-versions/{mock_clients['config_version_id']}/actions/archive",
        )

    def test_archive_config_404(self, mock_clients):
        """Test archive_config returns empty dict on 404."""
        response = {"status": 404}
        mock_clients["tf_client"].post.return_value = response

        result = archive_config(mock_clients["tf_client"], mock_clients["config_version_id"])

        assert result == {}

    @pytest.mark.parametrize("status_code", [400, 401, 403, 422, 500, 503])
    def test_archive_config_failure_scenarios(self, mock_clients, status_code):
        """Test archive_config raises HTTPError on various failure status codes."""
        response = {"status": status_code}
        mock_clients["tf_client"].post.return_value = response

        with pytest.raises(TerraformError):
            archive_config(mock_clients["tf_client"], mock_clients["config_version_id"])


class TestGetConfigFunction:
    """Test suite for the get_config function.

    Tests the retrieval of Terraform configuration versions via the Terraform API.
    Covers successful retrieval with various response formats, 404 handling for
    non-existent configurations, and error scenarios with different HTTP status codes.
    """

    @pytest.mark.parametrize(
        "response_data,expected_result,description",
        [
            (
                {"data": {"attributes": {"status": "uploaded"}, "id": "cv-123abc456def789"}, "status": 200},
                {"attributes": {"status": "uploaded"}, "id": "cv-123abc456def789", "status": 200},
                "successful fetch with full data",
            ),
            (
                {"data": {}, "status": 200},
                {"status": 200},
                "empty data section",
            ),
            (
                {"status": 200},
                {"status": 200},
                "no data key",
            ),
        ],
    )
    def test_get_config_success_scenarios(self, mock_clients, response_data, expected_result, description):
        """Test various successful get_config scenarios."""
        mock_clients["tf_client"].get.return_value = response_data

        result = get_config(mock_clients["tf_client"], mock_clients["config_version_id"])

        assert result == expected_result
        mock_clients["tf_client"].get.assert_called_once_with(
            f"/configuration-versions/{mock_clients['config_version_id']}",
        )

    def test_get_config_404(self, mock_clients):
        """Test get_config returns empty dict on 404."""
        response = {"status": 404}
        mock_clients["tf_client"].get.return_value = response

        result = get_config(mock_clients["tf_client"], mock_clients["config_version_id"])

        assert result == {}

    @pytest.mark.parametrize("status_code", [400, 401, 403, 422, 500, 502, 503])
    def test_get_config_failure_scenarios(self, mock_clients, status_code):
        """Test get_config raises HTTPError on various failure status codes."""
        response = {"status": status_code}
        mock_clients["tf_client"].get.return_value = response

        with pytest.raises(TerraformError):
            get_config(mock_clients["tf_client"], mock_clients["config_version_id"])


class TestUploadConfigFunction:
    """Test suite for the upload_config function.

    Tests the uploading of configuration files to the Terraform Archivist service.
    Covers successful uploads with various URL formats, file handling scenarios,
    and error conditions during the upload process.
    """

    @patch("builtins.open", new_callable=mock_open, read_data=b"file-content")
    def test_upload_config_success_full_url(self, mock_file, mock_clients):
        """Test successful upload when a full HTTPS URL is provided."""
        mock_clients["archivist_client"].base_url = "https://tfe.example.com"
        expected_response = {"status": 200}
        mock_clients["archivist_client"].put.return_value = expected_response

        result = upload_config(mock_clients["archivist_client"], mock_clients["upload_url"], mock_clients["file_path"])

        assert result == expected_response
        mock_file.assert_called_once_with(mock_clients["file_path"], "rb")
        mock_clients["archivist_client"].put.assert_called_once_with(mock_clients["upload_url"], mock_file.return_value)

    @patch("builtins.open", new_callable=mock_open, read_data=b"testdata-content")
    def test_upload_config_success_with_testdata_archive(self, mock_file, mock_clients):
        """Test successful upload using valid testdata archive."""
        # Use actual testdata file path (but mock the file reading)
        testdata_file = Path(__file__).parent.parent.parent / "testdata" / "valid.tar.gz"

        # Verify testdata exists
        assert testdata_file.exists(), f"Testdata file not found: {testdata_file}"

        # Set a proper base_url for the mock client (needed for re.match)
        mock_clients["archivist_client"].base_url = "https://app.terraform.io"

        expected_response = {"status": 200}
        mock_clients["archivist_client"].put.return_value = expected_response

        result = upload_config(mock_clients["archivist_client"], mock_clients["upload_url"], str(testdata_file))

        assert result == expected_response
        mock_file.assert_called_once_with(str(testdata_file), "rb")
        mock_clients["archivist_client"].put.assert_called_once_with(mock_clients["upload_url"], mock_file.return_value)

    def test_upload_config_with_nonexistent_testdata_file(self, mock_clients):
        """Test upload failure when testdata file doesn't exist."""
        nonexistent_file = "/path/to/nonexistent/testdata.tar.gz"

        # Should raise FileNotFoundError when trying to open nonexistent file
        with pytest.raises(FileNotFoundError):
            upload_config(mock_clients["archivist_client"], mock_clients["upload_url"], nonexistent_file)

    @pytest.mark.parametrize(
        "base_url,upload_path,expected_call_url,description",
        [
            (
                "http://localhost:8080",
                "simple-path",
                "/object/simple-path",
                "HTTP base URL without /object in upload URL",
            ),
            (
                "https://app.terraform.io",
                "https://archivist.example.com/object/v1/config.tar.gz",
                "https://archivist.example.com/object/v1/config.tar.gz",
                "HTTPS with /object in upload path",
            ),
            (
                "ftp://example.com",
                "config.tar.gz",
                "/object/config.tar.gz",
                "non-HTTP base URL",
            ),
        ],
    )
    @patch("builtins.open", new_callable=mock_open, read_data=b"file-content")
    def test_upload_config_url_scenarios(self, mock_file, mock_clients, base_url, upload_path, expected_call_url, description):
        """Test upload_config with various URL scenarios."""
        mock_clients["archivist_client"].base_url = base_url
        expected_response = {"status": 200}
        mock_clients["archivist_client"].put.return_value = expected_response

        result = upload_config(mock_clients["archivist_client"], upload_path, mock_clients["file_path"])

        assert result == expected_response
        mock_clients["archivist_client"].put.assert_called_once_with(expected_call_url, mock_file.return_value)

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422, 500, 502, 503])
    @patch("builtins.open", new_callable=mock_open)
    def test_upload_config_failure_scenarios(self, mock_file, mock_clients, status_code):
        """Test upload_config raises HTTPError on various failure status codes."""
        mock_clients["archivist_client"].base_url = "https://tfe.example.com"
        response = {"status": status_code}
        mock_clients["archivist_client"].put.return_value = response

        with pytest.raises(TerraformError):
            upload_config(mock_clients["archivist_client"], mock_clients["upload_url"], mock_clients["file_path"])
