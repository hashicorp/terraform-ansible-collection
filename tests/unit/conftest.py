# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pytest configuration and fixtures for Terraform collection unit tests.

This file provides common fixtures and configuration that can be used
across all unit tests in the collection.
"""

from unittest.mock import Mock, patch

import pytest

from .constants import (
    create_configuration_version_response,
    create_empty_response,
    create_error_response,
    create_list_response,
    create_plan_response,
    create_project_response,
    create_run_response,
    create_workspace_response,
)


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


# ============================================================================
# Payload Factory Fixtures
# ============================================================================


@pytest.fixture
def payload_factory():
    """
    Factory fixture providing functions to create API response payloads.

    Returns:
        dict: Dictionary of factory functions for creating test payloads

    Usage:
        def test_something(payload_factory):
            # Create a run response
            run = payload_factory['run'](run_id="run-123", status="applied")

            # Create a workspace response
            workspace = payload_factory['workspace'](name="my-workspace", locked=True)

            # Create a custom response
            custom_run = payload_factory['run'](
                run_id="run-custom",
                status="planned",
                message="Custom message"
            )

    Available factories:
        - run: Create run API responses
        - workspace: Create workspace API responses
        - configuration_version: Create configuration version API responses
        - plan: Create plan API responses
        - project: Create project API responses
        - error: Create error API responses
        - empty: Create empty API responses
        - list: Create list API responses
    """
    return {
        "run": create_run_response,
        "workspace": create_workspace_response,
        "configuration_version": create_configuration_version_response,
        "plan": create_plan_response,
        "project": create_project_response,
        "error": create_error_response,
        "empty": create_empty_response,
        "list": create_list_response,
    }


@pytest.fixture
def sample_run_response():
    """
    Fixture providing a standard run API response.

    Returns:
        dict: Standard run response with default values

    Usage:
        def test_something(sample_run_response):
            assert sample_run_response["data"]["id"] == "run-test123"
    """
    return create_run_response()


@pytest.fixture
def sample_workspace_response():
    """
    Fixture providing a standard workspace API response.

    Returns:
        dict: Standard workspace response with default values

    Usage:
        def test_something(sample_workspace_response):
            assert sample_workspace_response["data"]["attributes"]["name"] == "test-workspace"
    """
    return create_workspace_response()


@pytest.fixture
def sample_configuration_version_response():
    """
    Fixture providing a standard configuration version API response.

    Returns:
        dict: Standard configuration version response with default values

    Usage:
        def test_something(sample_configuration_version_response):
            assert sample_configuration_version_response["data"]["id"] == "cv-test123"
    """
    return create_configuration_version_response()


@pytest.fixture
def sample_plan_response():
    """
    Fixture providing a standard plan API response.

    Returns:
        dict: Standard plan response with default values

    Usage:
        def test_something(sample_plan_response):
            assert sample_plan_response["data"]["attributes"]["status"] == "finished"
    """
    return create_plan_response()


@pytest.fixture
def sample_project_response():
    """
    Fixture providing a standard project API response.

    Returns:
        dict: Standard project response with default values

    Usage:
        def test_something(sample_project_response):
            assert sample_project_response["data"]["type"] == "projects"
    """
    return create_project_response()


@pytest.fixture
def sample_error_response():
    """
    Fixture providing a standard error API response.

    Returns:
        dict: Standard error response with default values

    Usage:
        def test_something(sample_error_response):
            assert sample_error_response["errors"][0]["status"] == "404"
    """
    return create_error_response()
