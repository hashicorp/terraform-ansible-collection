# Sample Terraform API Response Payloads
SAMPLE_RUN_RESPONSE = {
    "data": {
        "id": "run-test123",
        "type": "runs",
        "attributes": {"status": "applied", "message": "Test run", "created-at": "2025-01-15T10:00:00.000Z", "is-destroy": False, "auto-apply": False},
        "relationships": {"workspace": {"data": {"id": "ws-test123", "type": "workspaces"}}},
    }
}

SAMPLE_WORKSPACE_RESPONSE = {
    "data": {
        "id": "ws-test123",
        "type": "workspaces",
        "attributes": {
            "name": "test-workspace",
            "description": "Test workspace",
            "created-at": "2025-01-15T09:00:00.000Z",
            "locked": False,
            "execution-mode": "remote",
        },
        "relationships": {"organization": {"data": {"id": "org-test123", "type": "organizations"}}},
    }
}

SAMPLE_CONFIGURATION_VERSION_RESPONSE = {
    "data": {
        "id": "cv-test123",
        "type": "configuration-versions",
        "attributes": {"status": "uploaded", "upload-url": "https://example.com/upload", "created-at": "2025-01-15T10:30:00.000Z"},
    }
}

SAMPLE_ERROR_RESPONSE = {"errors": [{"status": "404", "title": "Not Found", "detail": "Resource not found"}]}

# Consolidated dictionary for easy access
SAMPLE_TERRAFORM_RESPONSES = {
    "run": SAMPLE_RUN_RESPONSE,
    "workspace": SAMPLE_WORKSPACE_RESPONSE,
    "configuration_version": SAMPLE_CONFIGURATION_VERSION_RESPONSE,
    "error": SAMPLE_ERROR_RESPONSE,
}

# Common test IDs and values
TEST_RUN_ID = "run-test123"
TEST_WORKSPACE_ID = "ws-test123"
TEST_ORGANIZATION_ID = "org-test123"
TEST_CONFIGURATION_VERSION_ID = "cv-test123"

# Common test attributes
TEST_WORKSPACE_NAME = "test-workspace"
TEST_ORGANIZATION_NAME = "test-org"
TEST_RUN_MESSAGE = "Test run"
