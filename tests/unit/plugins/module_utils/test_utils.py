import pytest
from unittest.mock import Mock
from pytfe.errors import AuthError, NotFound, ServerError, TFEError

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff, sort_list, handle_error, safe_api_call, format_response
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient


class TestUtils:
    """Parameterized test cases for DataUtils utility methods."""

    @pytest.mark.parametrize(
        "input_list,expected",
        [
            ([{"key2": "value2", "key1": "value1"}, {"key1": "value1", "key2": "value2"}]),
            ([{"name": "zeta", "code": "alpha"}, {"code": "alpha", "name": "zeta"}]),
        ],
    )
    def test_sort_list_with_dicts(self, input_list, expected):
        assert sort_list(input_list) == expected

    @pytest.mark.parametrize(
        "input_list",
        [
            [{"key1": "value1", "key2": "value2"}, {"key1": "value2", "key3": "value3"}],
            [{"foo": "bar"}, {"baz": "qux"}],
        ],
    )
    def test_sort_list_with_dicts_inconsistent_keys_raises(self, input_list):
        with pytest.raises(ValueError, match="dictionaries do not match"):
            sort_list(input_list)

    @pytest.mark.parametrize("input_val", ["just a string", {"key": "value"}, None])
    def test_sort_list_with_non_list_returns_input(self, input_val):
        assert sort_list(input_val) == input_val

    @pytest.mark.parametrize(
        "base,comparable,expected",
        [
            ({"key1": "value1", "key2": "value2"}, {"key1": "value1", "key2": "different_value"}, {"key2": "different_value"}),
            ({"key1": "value1", "key2": "value2"}, {"key1": "value1"}, {}),
            ({"key1": "value1"}, {"key1": "value1", "key2": "value2"}, {"key2": "value2"}),
            (
                {"key1": {"subkey1": "subvalue1", "subkey2": "subvalue2"}, "key2": "value3"},
                {"key1": {"subkey1": "subvalue1", "subkey2": "DIFFERENT"}, "key2": "value3"},
                {"key1": {"subkey2": "DIFFERENT"}},
            ),
            ({"key1": ["value1", "value2", "value3"]}, {"key1": ["value3", "value2", "value1"]}, {}),  # lists sorted equal, no diff
            ({"key1": ["value1", "value2", "value3"]}, {"key1": ["new1", "new2", "new3"]}, {"key1": ["new1", "new2", "new3"]}),
            ({}, {"newkey": "newvalue"}, {"newkey": "newvalue"}),
        ],
    )
    def test_dict_diff_valid_cases(self, base, comparable, expected):
        assert dict_diff(base, comparable) == expected

    @pytest.mark.parametrize(
        "base",
        [
            "not a dict",
            ["list"],
            None,
        ],
    )
    def test_dict_diff_base_not_dict_raises(self, base):
        with pytest.raises(TerraformError, match="`base` must be of type <dict>"):
            dict_diff(base, {"key1": "value1"})

    @pytest.mark.parametrize("comparable", ["not a dict", ["list"], 123])
    def test_dict_diff_comparable_not_dict_raises(self, comparable):
        with pytest.raises(TerraformError, match="`comparable` must be of type <dict>"):
            dict_diff({"key1": "value1"}, comparable)

    def test_dict_diff_comparable_none(self):
        base = {"key1": "value1"}
        assert dict_diff(base, None) == {}

class TestTerraformClientErrorHandling:
    """Test TerraformClient error handling methods."""

    def test_handle_error_with_not_found(self):
        """Test handle_error wraps NotFound exceptions."""
        client = TerraformClient(tfe_token="test-token")
        error = NotFound("Workspace not found")
        
        with pytest.raises(TerraformError) as excinfo:
            handle_error(error)
        
        assert "Resource not found" in str(excinfo.value)
        assert "Workspace not found" in str(excinfo.value)

    def test_handle_error_with_auth_error(self):
        """Test handle_error wraps AuthError exceptions."""
        client = TerraformClient(tfe_token="test-token")
        error = AuthError("Invalid credentials")
        
        with pytest.raises(TerraformError) as excinfo:
            handle_error(error)
        
        assert "Authentication error" in str(excinfo.value)
        assert "Invalid credentials" in str(excinfo.value)

    def test_handle_error_with_server_error(self):
        """Test handle_error wraps ServerError exceptions."""
        client = TerraformClient(tfe_token="test-token")
        error = ServerError("Internal server error")
        
        with pytest.raises(TerraformError) as excinfo:
            handle_error(error)
        
        assert "Server error" in str(excinfo.value)
        assert "Internal server error" in str(excinfo.value)

    def test_handle_error_with_generic_tfe_error(self):
        """Test handle_error wraps generic TFEError exceptions."""
        client = TerraformClient(tfe_token="test-token")
        error = TFEError("Generic TFE error")
        
        with pytest.raises(TerraformError) as excinfo:
            handle_error(error)
        
        assert "Generic TFE error" in str(excinfo.value)

    def test_handle_error_with_context(self):
        """Test handle_error includes context in error message."""
        client = TerraformClient(tfe_token="test-token")
        error = NotFound("Workspace not found")
        
        with pytest.raises(TerraformError) as excinfo:
            handle_error(error, context="Failed to retrieve workspace")
        
        assert "Failed to retrieve workspace" in str(excinfo.value)
        assert "Resource not found" in str(excinfo.value)

    def test_handle_error_with_details_attribute(self):
        """Test handle_error extracts details from TFEError if available."""
        client = TerraformClient(tfe_token="test-token")
        error = TFEError("Error occurred")
        error.details = {"field": "invalid value"}
        
        with pytest.raises(TerraformError) as excinfo:
            handle_error(error)
        
        assert "Details:" in str(excinfo.value)


class TestTerraformClientSafeApiCall:
    """Test TerraformClient safe_api_call method."""

    def test_safe_api_call_success(self):
        """Test safe_api_call executes operation successfully."""
        client = TerraformClient(tfe_token="test-token")
        mock_operation = Mock(return_value={"id": "ws-123", "name": "test"})
        
        result = safe_api_call(mock_operation, "arg1", kwarg1="value1")
        
        mock_operation.assert_called_once_with("arg1", kwarg1="value1")
        assert result == {"id": "ws-123", "name": "test"}

    def test_safe_api_call_with_tfe_error(self):
        """Test safe_api_call handles TFEError."""
        client = TerraformClient(tfe_token="test-token")
        mock_operation = Mock(side_effect=NotFound("Resource not found"))
        
        with pytest.raises(TerraformError) as excinfo:
            safe_api_call(mock_operation, error_context="Failed to get resource")
        
        assert "Failed to get resource" in str(excinfo.value)
        assert "Resource not found" in str(excinfo.value)

    def test_safe_api_call_with_generic_exception(self):
        """Test safe_api_call handles generic exceptions."""
        client = TerraformClient(tfe_token="test-token")
        mock_operation = Mock(side_effect=ValueError("Invalid input"))
        
        with pytest.raises(TerraformError) as excinfo:
            safe_api_call(mock_operation)
        
        assert "Unexpected error" in str(excinfo.value)
        assert "Invalid input" in str(excinfo.value)

    def test_safe_api_call_extracts_error_context_from_kwargs(self):
        """Test safe_api_call extracts and removes error_context from kwargs."""
        client = TerraformClient(tfe_token="test-token")
        mock_operation = Mock(return_value="success")
        
        result = safe_api_call(
            mock_operation,
            "arg1",
            kwarg1="value1",
            error_context="Custom context"
        )
        
        # error_context should not be passed to operation
        mock_operation.assert_called_once_with("arg1", kwarg1="value1")
        assert result == "success"


class TestTerraformClientFormatResponse:
    """Test TerraformClient format_response method."""

    def test_format_response_converts_to_dict(self):
        """Test format_response converts SDK response to dictionary."""
        client = TerraformClient(tfe_token="test-token")
        
        # Mock SDK response object with model_dump method
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "type": "workspaces",
        }
        
        result = format_response(mock_response)
        
        mock_response.model_dump.assert_called_once_with(mode="json", exclude_none=True)
        assert result["id"] == "ws-123"
        assert result["name"] == "test-workspace"
        assert result["type"] == "workspaces"

    def test_format_response_excludes_none_values(self):
        """Test format_response excludes None values."""
        client = TerraformClient(tfe_token="test-token")
        
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            "id": "ws-123",
            "name": "test-workspace",
            "description": None,  # Should be excluded
        }
        
        result = format_response(mock_response)
        
        # Verify exclude_none parameter was used
        mock_response.model_dump.assert_called_with(mode="json", exclude_none=True)
