# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import re
import unittest

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

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


@patch("ansible_collections.hashicorp.terraform.plugins.module_utils.configuration_version.re", re)
class TestConfigFunctions(unittest.TestCase):
    """Unit tests for Terraform configuration helper functions."""

    def setUp(self):
        """Set up common test variables and mocks."""
        self.mock_tf_client = Mock()
        self.mock_archivist_client = Mock()
        self.workspace_id = "ws-123abc456def789"
        self.config_version_id = "cv-123abc456def789"
        self.attributes = {"auto-queue-runs": False, "speculative": True}
        self.upload_url = "https://archivist.example.com/object/config.tar.gz"
        self.file_path = "/fake/path/config.tar.gz"

    def test_create_config_success(self):
        """Test successful creation of a configuration version."""
        expected_response = {"data": {"id": self.config_version_id, "type": "configuration-versions"}, "status": 201}
        self.mock_tf_client.post.return_value = expected_response

        result = create_config(self.mock_tf_client, self.workspace_id, self.attributes)

        # Should return the data part with status added
        expected_result = {"id": self.config_version_id, "type": "configuration-versions", "status": 201}
        self.assertEqual(result, expected_result)

        # Verify the payload structure
        expected_payload = {
            "data": {
                "type": "configuration-versions",
                "attributes": self.attributes,
            },
        }
        self.mock_tf_client.post.assert_called_once_with(
            f"/workspaces/{self.workspace_id}/configuration-versions",
            data=expected_payload,
        )

    def test_create_config_empty_data_section(self):
        """Test create_config with empty data section."""
        expected_response = {"data": {}, "status": 201}
        self.mock_tf_client.post.return_value = expected_response

        result = create_config(self.mock_tf_client, self.workspace_id, self.attributes)

        # Should return empty data with status added
        expected_result = {"status": 201}
        self.assertEqual(result, expected_result)

    def test_create_config_no_data_key(self):
        """Test create_config with no data key."""
        expected_response = {"status": 201}
        self.mock_tf_client.post.return_value = expected_response

        result = create_config(self.mock_tf_client, self.workspace_id, self.attributes)

        # Should return empty dict with status added
        expected_result = {"status": 201}
        self.assertEqual(result, expected_result)

    def test_create_config_failure_raises_error(self):
        """Test create_config raises HTTPError on non-201 status."""
        response = {"data": {}, "status": 400}
        self.mock_tf_client.post.return_value = response

        with self.assertRaises(TerraformError):
            create_config(self.mock_tf_client, self.workspace_id, self.attributes)

    def test_create_config_with_empty_attributes(self):
        """Test create_config with empty attributes dict."""
        expected_response = {"data": {"id": self.config_version_id}, "status": 201}
        self.mock_tf_client.post.return_value = expected_response
        empty_attributes = {}

        result = create_config(self.mock_tf_client, self.workspace_id, empty_attributes)

        expected_result = {"id": self.config_version_id, "status": 201}
        self.assertEqual(result, expected_result)

    def test_archive_config_success(self):
        """Test successful archiving of a configuration version."""
        response = {"status": 202}
        self.mock_tf_client.post.return_value = response

        result = archive_config(self.mock_tf_client, self.config_version_id)

        expected_result = {"status": 202}
        self.assertEqual(result, expected_result)
        self.mock_tf_client.post.assert_called_once_with(
            f"/configuration-versions/{self.config_version_id}/actions/archive",
        )

    def test_archive_config_404(self):
        """Test archive_config returns empty dict on 404."""
        response = {"status": 404}
        self.mock_tf_client.post.return_value = response

        result = archive_config(self.mock_tf_client, self.config_version_id)

        self.assertEqual(result, {})

    def test_archive_config_failure_raises_error(self):
        """Test archive_config raises HTTPError on non-202/non-404 status."""
        response = {"status": 500}
        self.mock_tf_client.post.return_value = response

        with self.assertRaises(TerraformError):
            archive_config(self.mock_tf_client, self.config_version_id)

    def test_archive_config_alternative_failure_status(self):
        """Test archive_config with different failure status codes."""
        for status_code in [400, 401, 403, 422, 500, 503]:
            with self.subTest(status_code=status_code):
                response = {"status": status_code}
                self.mock_tf_client.post.return_value = response

                with self.assertRaises(TerraformError):
                    archive_config(self.mock_tf_client, self.config_version_id)

    def test_get_config_success(self):
        """Test successfully fetching a configuration version."""
        expected_response = {"data": {"attributes": {"status": "uploaded"}, "id": self.config_version_id}, "status": 200}
        self.mock_tf_client.get.return_value = expected_response

        result = get_config(self.mock_tf_client, self.config_version_id)

        # Should return the data part with status added
        expected_result = {"attributes": {"status": "uploaded"}, "id": self.config_version_id, "status": 200}
        self.assertEqual(result, expected_result)
        self.mock_tf_client.get.assert_called_once_with(
            f"/configuration-versions/{self.config_version_id}",
        )

    def test_get_config_empty_data_section(self):
        """Test get_config with empty data section."""
        expected_response = {"data": {}, "status": 200}
        self.mock_tf_client.get.return_value = expected_response

        result = get_config(self.mock_tf_client, self.config_version_id)

        expected_result = {"status": 200}
        self.assertEqual(result, expected_result)

    def test_get_config_no_data_key(self):
        """Test get_config with no data key."""
        expected_response = {"status": 200}
        self.mock_tf_client.get.return_value = expected_response

        result = get_config(self.mock_tf_client, self.config_version_id)

        expected_result = {"status": 200}
        self.assertEqual(result, expected_result)

    def test_get_config_404(self):
        """Test get_config returns empty dict on 404."""
        response = {"status": 404}
        self.mock_tf_client.get.return_value = response

        result = get_config(self.mock_tf_client, self.config_version_id)

        self.assertEqual(result, {})

    def test_get_config_failure_raises_error(self):
        """Test get_config raises HTTPError on non-200/non-404 status."""
        response = {"status": 500}
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(TerraformError):
            get_config(self.mock_tf_client, self.config_version_id)

    def test_get_config_various_failure_statuses(self):
        """Test get_config with various non-success status codes."""
        for status_code in [400, 401, 403, 422, 500, 502, 503]:
            with self.subTest(status_code=status_code):
                response = {"status": status_code}
                self.mock_tf_client.get.return_value = response

                with self.assertRaises(TerraformError):
                    get_config(self.mock_tf_client, self.config_version_id)

    @patch("builtins.open", new_callable=mock_open, read_data=b"file-content")
    def test_upload_config_success_full_url(self, mock_file):
        """Test successful upload when a full HTTPS URL is provided."""
        self.mock_archivist_client.base_url = "https://tfe.example.com"
        expected_response = {"status": 200}
        self.mock_archivist_client.put.return_value = expected_response

        result = upload_config(self.mock_archivist_client, self.upload_url, self.file_path)

        self.assertEqual(result, expected_response)
        mock_file.assert_called_once_with(self.file_path, "rb")
        self.mock_archivist_client.put.assert_called_once_with(self.upload_url, mock_file.return_value)

    @patch("builtins.open", new_callable=mock_open, read_data=b"testdata-content")
    def test_upload_config_success_with_testdata_archive(self, mock_file):
        """Test successful upload using valid testdata archive."""
        # Use actual testdata file path (but mock the file reading)
        testdata_file = Path(__file__).parent.parent.parent / "testdata" / "valid.tar.gz"

        # Verify testdata exists
        self.assertTrue(testdata_file.exists(), f"Testdata file not found: {testdata_file}")

        # Set a proper base_url for the mock client (needed for re.match)
        self.mock_archivist_client.base_url = "https://app.terraform.io"

        expected_response = {"status": 200}
        self.mock_archivist_client.put.return_value = expected_response

        result = upload_config(self.mock_archivist_client, self.upload_url, str(testdata_file))

        self.assertEqual(result, expected_response)
        mock_file.assert_called_once_with(str(testdata_file), "rb")
        self.mock_archivist_client.put.assert_called_once_with(self.upload_url, mock_file.return_value)

    def test_upload_config_with_nonexistent_testdata_file(self):
        """Test upload failure when testdata file doesn't exist."""
        nonexistent_file = "/path/to/nonexistent/testdata.tar.gz"

        # Should raise FileNotFoundError when trying to open nonexistent file
        with self.assertRaises(FileNotFoundError):
            upload_config(self.mock_archivist_client, self.upload_url, nonexistent_file)

    @patch("builtins.open", new_callable=mock_open, read_data=b"file-content")
    def test_upload_config_http_base_url_no_object_in_upload_url(self, mock_file):
        """Test upload with HTTP base URL and no /object in upload URL."""
        self.mock_archivist_client.base_url = "http://localhost:8080"
        upload_path = "simple-path"
        expected_response = {"status": 200}
        self.mock_archivist_client.put.return_value = expected_response

        result = upload_config(self.mock_archivist_client, upload_path, self.file_path)

        self.assertEqual(result, expected_response)
        self.mock_archivist_client.put.assert_called_once_with(f"/object/{upload_path}", mock_file.return_value)

    @patch("builtins.open", new_callable=mock_open, read_data=b"file-content")
    def test_upload_config_https_with_object_in_path(self, mock_file):
        """Test upload with HTTPS base URL and /object in upload path."""
        self.mock_archivist_client.base_url = "https://app.terraform.io"
        upload_url_with_object = "https://archivist.example.com/object/v1/config.tar.gz"
        expected_response = {"status": 200}
        self.mock_archivist_client.put.return_value = expected_response

        result = upload_config(self.mock_archivist_client, upload_url_with_object, self.file_path)

        self.assertEqual(result, expected_response)
        self.mock_archivist_client.put.assert_called_once_with(upload_url_with_object, mock_file.return_value)

    @patch("builtins.open", new_callable=mock_open, read_data=b"file-content")
    def test_upload_config_non_http_base_url(self, mock_file):
        """Test upload with non-HTTP base URL."""
        self.mock_archivist_client.base_url = "ftp://example.com"
        upload_path = "config.tar.gz"
        expected_response = {"status": 200}
        self.mock_archivist_client.put.return_value = expected_response

        result = upload_config(self.mock_archivist_client, upload_path, self.file_path)

        self.assertEqual(result, expected_response)
        self.mock_archivist_client.put.assert_called_once_with(f"/object/{upload_path}", mock_file.return_value)

    @patch("builtins.open", new_callable=mock_open)
    def test_upload_config_failure_raises_error(self, mock_file):
        """Test upload_config raises HTTPError on non-200 status."""
        self.mock_archivist_client.base_url = "https://tfe.example.com"
        response = {"status": 500}
        self.mock_archivist_client.put.return_value = response

        with self.assertRaises(TerraformError):
            upload_config(self.mock_archivist_client, self.upload_url, self.file_path)

    @patch("builtins.open", new_callable=mock_open)
    def test_upload_config_various_failure_statuses(self, mock_file):
        """Test upload_config with various non-200 status codes."""
        self.mock_archivist_client.base_url = "https://tfe.example.com"

        for status_code in [400, 401, 403, 404, 422, 500, 502, 503]:
            with self.subTest(status_code=status_code):
                response = {"status": status_code}
                self.mock_archivist_client.put.return_value = response

                with self.assertRaises(TerraformError):
                    upload_config(self.mock_archivist_client, self.upload_url, self.file_path)


if __name__ == "__main__":
    unittest.main()
