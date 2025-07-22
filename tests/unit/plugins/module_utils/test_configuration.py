import unittest
from unittest.mock import Mock, patch, mock_open
import re


# Mock HTTPError class for testing
class MockHTTPError(Exception):
    def __init__(self, response=None):
        self.response = response
        super().__init__()


# Import the module under test
from ansible_collections.hashicorp.terraform.plugins.module_utils.configuration import (
    create_config,
    archive_config,
    upload_config,
    get_config,
)

@patch('ansible_collections.hashicorp.terraform.plugins.module_utils.configuration.requests')
@patch('ansible_collections.hashicorp.terraform.plugins.module_utils.configuration.re', re)
class TestConfigFunctions(unittest.TestCase):
    """Unit tests for Terraform configuration helper functions."""

    def setUp(self):
        """Set up common test variables and mocks."""
        self.mock_tf_client = Mock()
        self.mock_archivist_client = Mock()
        self.workspace_id = "ws-123abc456def789"
        self.config_version_id = "cv-123abc456def789"
        self.payload = {"data": {"attributes": {"auto-queue-runs": False}}}
        self.upload_url = "https://archivist.example.com/object/config.tar.gz"
        self.file_path = "/fake/path/config.tar.gz"

    # --- create_config ---

    def test_create_config_success(self, mock_re, mock_requests):
        """Test successful creation of a configuration version."""
        expected_response = {"data": {"id": self.config_version_id}}
        self.mock_tf_client.post.return_value = expected_response
        
        result = create_config(self.mock_tf_client, self.workspace_id, self.payload)
        
        self.assertEqual(result, expected_response)
        self.mock_tf_client.post.assert_called_once_with(
            f"/workspaces/{self.workspace_id}/configuration-versions",
            data=self.payload
        )

    def test_create_config_404(self, mock_re, mock_requests):
        """Test create_config returns None on a 404 HTTPError."""
        response = Mock(status_code=404)
        mock_requests.HTTPError = MockHTTPError
        self.mock_tf_client.post.side_effect = MockHTTPError(response=response)
        
        result = create_config(self.mock_tf_client, self.workspace_id, self.payload)
        
        self.assertIsNone(result)

    def test_create_config_other_error(self, mock_re, mock_requests):
        """Test create_config raises other HTTPErrors."""
        response = Mock(status_code=500)
        mock_requests.HTTPError = MockHTTPError
        self.mock_tf_client.post.side_effect = MockHTTPError(response=response)
        
        with self.assertRaises(MockHTTPError):
            create_config(self.mock_tf_client, self.workspace_id, self.payload)

    # --- archive_config ---

    def test_archive_config_success(self, mock_re, mock_requests):
        """Test successful archiving of a configuration version."""
        expected_response = {"status": "archived"}
        self.mock_tf_client.post.return_value = expected_response
        
        result = archive_config(self.mock_tf_client, self.config_version_id)
        
        self.assertEqual(result, expected_response)
        self.mock_tf_client.post.assert_called_once_with(
            f"/configuration-versions/{self.config_version_id}/actions/archive"
        )

    def test_archive_config_404(self, mock_re, mock_requests):
        """Test archive_config returns None on a 404 HTTPError."""
        response = Mock(status_code=404)
        mock_requests.HTTPError = MockHTTPError
        self.mock_tf_client.post.side_effect = MockHTTPError(response=response)
        
        result = archive_config(self.mock_tf_client, self.config_version_id)
        
        self.assertIsNone(result)

    # --- get_config ---

    def test_get_config_success(self, mock_re, mock_requests):
        """Test successfully fetching a configuration version."""
        expected_response = {"data": {"attributes": {"status": "uploaded"}}}
        self.mock_tf_client.get.return_value = expected_response
        
        result = get_config(self.mock_tf_client, self.config_version_id)
        
        self.assertEqual(result, expected_response)
        self.mock_tf_client.get.assert_called_once_with(
            f"/configuration-versions/{self.config_version_id}"
        )

    def test_get_config_404(self, mock_re, mock_requests):
        """Test get_config returns None on a 404 HTTPError."""
        response = Mock(status_code=404)
        mock_requests.HTTPError = MockHTTPError
        self.mock_tf_client.get.side_effect = MockHTTPError(response=response)
        
        result = get_config(self.mock_tf_client, self.config_version_id)
        
        self.assertIsNone(result)

    # --- upload_config ---

    @patch("builtins.open", new_callable=mock_open, read_data=b"file-content")
    def test_upload_config_success_full_url(self, mock_file, mock_re, mock_requests):
        """Test successful upload when a full HTTPS URL is provided."""
        self.mock_archivist_client.base_url = "https://tfe.example.com"
        expected_response = {"status": "uploaded"}
        self.mock_archivist_client.put.return_value = expected_response
        # Ensure HTTPError is properly set up as an exception class
        mock_requests.HTTPError = MockHTTPError
        
        result = upload_config(self.mock_archivist_client, self.upload_url, self.file_path)
        
        self.assertEqual(result, expected_response)
        mock_file.assert_called_once_with(self.file_path, "rb")
        self.mock_archivist_client.put.assert_called_once_with(self.upload_url, mock_file())

    @patch("builtins.open", new_callable=mock_open, read_data=b"file-content")
    def test_upload_config_success_relative_path(self, mock_file, mock_re, mock_requests):
        """Test successful upload when a relative path is constructed."""
        self.mock_archivist_client.base_url = "http://localhost:8080"
        relative_upload_path = "config.tar.gz"
        expected_response = {"status": "uploaded"}
        self.mock_archivist_client.put.return_value = expected_response
        # Ensure HTTPError is properly set up as an exception class
        mock_requests.HTTPError = MockHTTPError
        
        result = upload_config(self.mock_archivist_client, relative_upload_path, self.file_path)
        
        self.assertEqual(result, expected_response)
        mock_file.assert_called_once_with(self.file_path, "rb")
        self.mock_archivist_client.put.assert_called_once_with(f"/object/{relative_upload_path}", mock_file())

    @patch("builtins.open", new_callable=mock_open)
    def test_upload_config_404(self, mock_file, mock_re, mock_requests):
        """Test upload_config returns None on a 404 HTTPError."""
        self.mock_archivist_client.base_url = "https://tfe.example.com"
        response = Mock(status_code=404)
        mock_requests.HTTPError = MockHTTPError
        self.mock_archivist_client.put.side_effect = MockHTTPError(response=response)
        
        result = upload_config(self.mock_archivist_client, self.upload_url, self.file_path)
        
        self.assertIsNone(result)

    @patch("builtins.open", new_callable=mock_open)
    def test_upload_config_other_error(self, mock_file, mock_re, mock_requests):
        """Test upload_config raises other HTTPErrors."""
        self.mock_archivist_client.base_url = "https://tfe.example.com"
        response = Mock(status_code=500)
        mock_requests.HTTPError = MockHTTPError
        self.mock_archivist_client.put.side_effect = MockHTTPError(response=response)
        
        with self.assertRaises(MockHTTPError):
            upload_config(self.mock_archivist_client, self.upload_url, self.file_path)

if __name__ == "__main__":
    unittest.main()