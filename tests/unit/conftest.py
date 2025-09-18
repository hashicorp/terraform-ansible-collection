# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pytest configuration and fixtures for Terraform collection unit tests.

This file provides common fixtures and configuration that can be used
across all unit tests in the collection.
"""

import json

from unittest.mock import Mock, patch

import pytest

from .constants import SAMPLE_TERRAFORM_RESPONSES


class DummyModule:
    """A basic mock Ansible module for testing."""

    def __init__(self, params=None, check_mode=False):
        self.params = params or {}
        self.failed = False
        self.exit_args = None
        self.fail_args = None
        self.check_mode = check_mode
        self.changed = False

    def fail_json(self, **kwargs):
        self.failed = True
        self.fail_args = kwargs
        msg = kwargs.get("msg", "fail_json called with no message")
        raise AssertionError(msg)

    def exit_json(self, **kwargs):
        self.exit_args = kwargs
        if "changed" in kwargs:
            self.changed = kwargs["changed"]
        raise SystemExit(kwargs)


class EnhancedDummyModule(DummyModule):
    """A mock Ansible module with enhanced tracking for better test inspection."""

    def __init__(self, params=None, check_mode=False):
        super().__init__(params, check_mode)
        self.call_history = []
        self.warnings = []
        self.deprecations = []
        self.debug_messages = []

    def warn(self, warning):
        self.warnings.append(warning)
        self.call_history.append(("warn", warning))

    def deprecate(self, msg, version=None):
        self.deprecations.append({"msg": msg, "version": version})
        self.call_history.append(("deprecate", msg, version))

    def debug(self, msg):
        self.debug_messages.append(msg)
        self.call_history.append(("debug", msg))

    def fail_json(self, **kwargs):
        self.call_history.append(("fail_json", kwargs))
        super().fail_json(**kwargs)

    def fail_from_exception(self, exception):
        self.call_history.append(("fail_from_exception", str(exception)))
        self.failed = True
        self.fail_args = {"msg": str(exception)}
        raise AssertionError(f"fail_from_exception called with: {exception}")

    def exit_json(self, **kwargs):
        self.call_history.append(("exit_json", kwargs))
        super().exit_json(**kwargs)


@pytest.fixture
def dummy_module():
    """Factory fixture to create DummyModule with custom parameters."""

    def _create_module(params=None, check_mode=False, enhanced=False):
        if enhanced:
            return EnhancedDummyModule(params, check_mode)
        return DummyModule(params, check_mode)

    return _create_module


@pytest.fixture
def enhanced_dummy_module():
    """Provide an EnhancedDummyModule instance for testing."""
    return EnhancedDummyModule()


@pytest.fixture
def mock_terraform_client():
    """
    Mock TerraformClient class fixture with pre-configured HTTP responses.

    Returns:
        Mock: A mock TerraformClient class that returns a fully configured mock instance
    """
    with patch("ansible_collections.hashicorp.terraform.plugins.module_utils.common.TerraformClient") as mock_class:
        mock_instance = Mock()
        mock_instance.hostname = "app.terraform.io"
        mock_instance.base_url = "https://app.terraform.io/api/v2"
        mock_instance.session = Mock()

        # Set up common session methods with default successful responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"id": "test-id"}}
        mock_response.raise_for_status.return_value = None

        mock_instance.session.get.return_value = mock_response
        mock_instance.session.post.return_value = mock_response
        mock_instance.session.patch.return_value = mock_response
        mock_instance.session.delete.return_value = mock_response

        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_ansible_terraform_module():
    """
    Mock AnsibleTerraformModule class fixture.

    Returns:
        Mock: A mock AnsibleTerraformModule class that returns a mock instance
    """
    with patch("ansible_collections.hashicorp.terraform.plugins.module_utils.common.AnsibleTerraformModule") as mock_class:
        mock_instance = Mock()
        mock_instance.params = {}
        mock_instance.check_mode = False
        mock_instance.changed = False
        mock_instance.fail_json = Mock(side_effect=SystemExit)
        mock_instance.exit_json = Mock(side_effect=SystemExit)
        mock_instance.warn = Mock()
        mock_instance.deprecate = Mock()
        mock_instance.debug = Mock()
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_function():
    """
    Flexible fixture to mock any function in any module.

    Returns:
        function: A factory function to create mocks for any module.function

    Usage:
        def test_something(mock_function):
            # Mock a single function
            mock_get_run = mock_function('ansible_collections.hashicorp.terraform.plugins.modules.run.get_run')
            mock_get_run.return_value = {"data": {"id": "test-123"}}

            # Mock multiple functions
            mocks = mock_function.multiple([
                'ansible_collections.hashicorp.terraform.plugins.modules.run.get_run',
                'ansible_collections.hashicorp.terraform.plugins.modules.run.create_run',
                'ansible_collections.hashicorp.terraform.plugins.modules.workspace.get_workspace'
            ])
            mocks['get_run'].return_value = {"data": {"id": "run-123"}}
            mocks['create_run'].return_value = {"data": {"id": "run-456"}}
    """
    active_patches = []

    def _mock_single_function(function_path, return_value=None, side_effect=None, **kwargs):
        """Mock a single function."""
        patcher = patch(function_path, **kwargs)
        mock_func = patcher.start()
        active_patches.append(patcher)

        if return_value is not None:
            mock_func.return_value = return_value
        if side_effect is not None:
            mock_func.side_effect = side_effect

        return mock_func

    def _mock_multiple_functions(function_paths, default_return_value=None):
        """Mock multiple functions and return a dictionary of mocks."""
        mocks = {}
        for path in function_paths:
            # Extract function name from path for dictionary key
            func_name = path.split(".")[-1]
            mocks[func_name] = _mock_single_function(path, return_value=default_return_value)
        return mocks

    # Add the multiple method to the main function
    _mock_single_function.multiple = _mock_multiple_functions

    yield _mock_single_function

    # Cleanup all patches
    for patcher in active_patches:
        try:
            patcher.stop()
        except RuntimeError:
            pass


@pytest.fixture
def mock_time():
    """
    Mock time.sleep and time.time for tests that involve timing.

    Returns:
        dict: Dictionary with 'sleep' and 'time' mock objects

    Usage:
        def test_timeout(mock_time):
            mock_time['time'].side_effect = [0, 30, 60]  # Simulate time progression
            mock_time['sleep'].return_value = None  # No actual sleeping
    """
    with patch("time.sleep") as mock_sleep, patch("time.time") as mock_time_func:

        mock_sleep.return_value = None  # Don't actually sleep
        mock_time_func.side_effect = range(1000)  # Incrementing time

        yield {"sleep": mock_sleep, "time": mock_time_func}


@pytest.fixture
def mock_requests_response():
    """
    Factory fixture to create mock HTTP responses.

    Returns:
        function: Factory function to create mock responses

    Usage:
        def test_api_call(mock_requests_response):
            # Create successful response
            response = mock_requests_response(
                status_code=200,
                json_data={"data": {"id": "test-123"}},
                headers={"Content-Type": "application/json"}
            )

            # Create error response
            error_response = mock_requests_response(
                status_code=404,
                json_data={"errors": [{"detail": "Not found"}]}
            )
    """

    def _create_response(status_code=200, json_data=None, text=None, headers=None, raise_for_status_side_effect=None):
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.headers = headers or {}

        if json_data is not None:
            mock_response.json.return_value = json_data
        else:
            mock_response.json.side_effect = ValueError("No JSON object could be decoded")

        mock_response.text = text or (json.dumps(json_data) if json_data else "")

        if raise_for_status_side_effect:
            mock_response.raise_for_status.side_effect = raise_for_status_side_effect
        elif status_code >= 400:
            from requests.exceptions import HTTPError

            mock_response.raise_for_status.side_effect = HTTPError(f"{status_code} Error")
        else:
            mock_response.raise_for_status.return_value = None

        return mock_response

    return _create_response


@pytest.fixture
def sample_terraform_responses():
    """
    Fixture providing sample Terraform API responses for testing.

    Returns:
        dict: Dictionary of common response structures

    Usage:
        def test_something(sample_terraform_responses):
            run_response = sample_terraform_responses['run']
            workspace_response = sample_terraform_responses['workspace']
    """
    return SAMPLE_TERRAFORM_RESPONSES
