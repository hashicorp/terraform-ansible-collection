import re
import unittest

from unittest.mock import Mock, mock_open, patch


# Mock HTTPError class for testing - must inherit from BaseException
class MockHTTPError(Exception):
    def __init__(self, response=None):
        self.response = response
        super().__init__()


# Import the module under test
from ansible_collections.hashicorp.terraform.plugins.module_utils.configuration_version import (
    archive_config,
    create_config,
    get_config,
    upload_config,
)


@patch("ansible_collections.hashicorp.terraform.plugins.module_utils.configuration_version.re", re)
@patch("ansible_collections.hashicorp.terraform.plugins.module_utils.configuration_version.requests")
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

    # --- create_config ---

    def test_create_config_success(self, mock_requests):
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

    def test_create_config_failure_raises_error(self, mock_requests):
        """Test create_config raises HTTPError on non-201 status."""
        response = {"data": {}, "status": 400}
        mock_requests.HTTPError = MockHTTPError
        self.mock_tf_client.post.return_value = response

        with self.assertRaises(MockHTTPError):
            create_config(self.mock_tf_client, self.workspace_id, self.attributes)

    # --- archive_config ---

    def test_archive_config_success(self, mock_requests):
        """Test successful archiving of a configuration version."""
        response = {"status": 202}
        self.mock_tf_client.post.return_value = response

        result = archive_config(self.mock_tf_client, self.config_version_id)

        expected_result = {"status": 202}
        self.assertEqual(result, expected_result)
        self.mock_tf_client.post.assert_called_once_with(
            f"/configuration-versions/{self.config_version_id}/actions/archive",
        )

    def test_archive_config_404(self, mock_requests):
        """Test archive_config returns empty dict on 404."""
        response = {"status": 404}
        self.mock_tf_client.post.return_value = response

        result = archive_config(self.mock_tf_client, self.config_version_id)

        self.assertEqual(result, {})

    def test_archive_config_failure_raises_error(self, mock_requests):
        """Test archive_config raises HTTPError on non-202/non-404 status."""
        response = {"status": 500}
        mock_requests.HTTPError = MockHTTPError
        self.mock_tf_client.post.return_value = response

        with self.assertRaises(MockHTTPError):
            archive_config(self.mock_tf_client, self.config_version_id)

    # --- get_config ---

    def test_get_config_success(self, mock_requests):
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

    def test_get_config_404(self, mock_requests):
        """Test get_config returns empty dict on 404."""
        response = {"status": 404}
        self.mock_tf_client.get.return_value = response

        result = get_config(self.mock_tf_client, self.config_version_id)

        self.assertEqual(result, {})

    def test_get_config_failure_raises_error(self, mock_requests):
        """Test get_config raises HTTPError on non-200/non-404 status."""
        response = {"status": 500}
        mock_requests.HTTPError = MockHTTPError
        self.mock_tf_client.get.return_value = response

        with self.assertRaises(MockHTTPError):
            get_config(self.mock_tf_client, self.config_version_id)

    # --- upload_config ---

    @patch("builtins.open", new_callable=mock_open, read_data=b"file-content")
    def test_upload_config_success_full_url(self, mock_file, mock_requests):
        """Test successful upload when a full HTTPS URL is provided."""
        self.mock_archivist_client.base_url = "https://tfe.example.com"
        expected_response = {"status": 200}
        self.mock_archivist_client.put.return_value = expected_response
        mock_requests.HTTPError = MockHTTPError

        result = upload_config(self.mock_archivist_client, self.upload_url, self.file_path)

        self.assertEqual(result, expected_response)
        mock_file.assert_called_once_with(self.file_path, "rb")
        self.mock_archivist_client.put.assert_called_once_with(self.upload_url, mock_file.return_value)

    @patch("builtins.open", new_callable=mock_open, read_data=b"file-content")
    def test_upload_config_success_relative_path(self, mock_file, mock_requests):
        """Test successful upload when a relative path is constructed."""
        self.mock_archivist_client.base_url = "http://localhost:8080"
        relative_upload_path = "config.tar.gz"
        expected_response = {"status": 200}
        self.mock_archivist_client.put.return_value = expected_response
        mock_requests.HTTPError = MockHTTPError

        result = upload_config(self.mock_archivist_client, relative_upload_path, self.file_path)

        self.assertEqual(result, expected_response)
        mock_file.assert_called_once_with(self.file_path, "rb")
        self.mock_archivist_client.put.assert_called_once_with(f"/object/{relative_upload_path}", mock_file.return_value)

    @patch("builtins.open", new_callable=mock_open)
    def test_upload_config_failure_raises_error(self, mock_file, mock_requests):
        """Test upload_config raises HTTPError on non-200 status."""
        self.mock_archivist_client.base_url = "https://tfe.example.com"
        response = {"status": 500}
        mock_requests.HTTPError = MockHTTPError
        self.mock_archivist_client.put.return_value = response

        with self.assertRaises(MockHTTPError):
            upload_config(self.mock_archivist_client, self.upload_url, self.file_path)


if __name__ == "__main__":
    unittest.main()
