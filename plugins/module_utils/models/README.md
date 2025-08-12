# Terraform Cloud/Enterprise API Models

This package contains Pydantic models for interacting with the Terraform Cloud/Enterprise API. The models are organized by resource type for better maintainability and clarity.

## Structure

```
models/
├── __init__.py                   # Package initialization with all imports
├── common.py                     # Common base models and utilities
├── runs.py                       # Run-specific models
├── workspaces.py                 # Workspace-specific models  
├── configuration_versions.py     # Configuration version-specific models
├── examples.py                   # Usage examples
└── README.md                     # This file
```

## Files Overview

### `common.py`
Contains shared base models and utility functions used across all resource types:
- `ResourceData` - Base model for resource references
- `Relationship` - Generic relationship model
- `Links` - Common links structure
- `BaseTerraformResource` - Generic base for all TF resources
- `BaseRequest` - Base model for API requests
- `BaseAttributes` - Base attributes with common fields
- `BaseRelationships` - Base relationships model
- `TerraformAPIResponse` - Generic API response model
- Utility functions for creating resource references

### `runs.py`
Models specific to Terraform runs:
- `RunAttributes` - Run-specific attributes
- `RunRelationships` - Run-specific relationships
- `RunData` - Complete run data model
- `RunRequest` - Request model for run operations
- `RunStates` - Helper class for run state management

### `workspaces.py`
Models specific to Terraform workspaces:
- `WorkspaceAttributes` - Workspace-specific attributes
- `WorkspaceRelationships` - Workspace-specific relationships
- `WorkspaceData` - Complete workspace data model
- `WorkspaceRequest` - Request model for workspace operations

### `configuration_versions.py`
Models specific to configuration versions:
- `ConfigurationVersionAttributes` - Config version attributes
- `ConfigurationVersionRelationships` - Config version relationships  
- `ConfigurationVersionData` - Complete config version data model
- `ConfigurationVersionRequest` - Request model for config version operations
- `ConfigurationVersionStates` - Helper class for config version state management

## Usage Examples

### Import Options

```python
# Recommended: Import specific models from their modules
from .runs import RunRequest
from .workspaces import WorkspaceRequest
from .configuration_versions import ConfigurationVersionRequest

# Import common utilities
from .common import create_workspace_reference, create_organization_reference

# Import with full path (most explicit)
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.runs import RunRequest

# Import all from specific module (use sparingly)
from .runs import *
```

### Creating Requests

```python
# Create a workspace request
workspace_request = WorkspaceRequest.create(
    name="my-workspace",
    organization_name="my-org",
    auto_apply=True,
    terraform_version="1.5.0"
)

# Create a run request
run_request = RunRequest.create(
    workspace_id="ws-123456789",
    message="Deploy changes",
    auto_apply=False,
    plan_only=True
)

# Create a configuration version request
config_request = ConfigurationVersionRequest.create(
    auto_queue_runs=True,
    speculative=False,
    provisional=False
)
```

### Converting to API Payloads

```python
# Convert models to dict for API requests
payload = request.model_dump(by_alias=True, exclude_unset=True)
```

### Using Utility Functions

```python
from .common import (
    create_workspace_reference,
    create_configuration_version_reference,
    create_organization_reference,
    create_run_reference
)

# Create references for relationships
workspace_ref = create_workspace_reference("ws-123456789")
config_ref = create_configuration_version_reference("cv-987654321")
org_ref = create_organization_reference("my-organization")
run_ref = create_run_reference("run-123456789")
```

## Benefits of This Structure

1. **Separation of Concerns** - Each resource type has its own file
2. **Maintainability** - Easier to update models for specific resources
3. **Reusability** - Common components are shared via `common.py`
4. **Type Safety** - Full Pydantic validation and type hints
5. **API Compatibility** - Proper field aliasing for Terraform API
6. **Convenience** - Helper methods for creating requests
7. **Documentation** - Clear structure and examples

## Field Aliasing

The models use Pydantic's field aliasing to match the Terraform Cloud/Enterprise API naming conventions (kebab-case) while providing Pythonic field names (snake_case):

```python
auto_apply: Optional[StrictBool] = Field(None, alias="auto-apply")
```

When serializing to JSON for API requests, use `by_alias=True`:

```python
payload = model.model_dump(by_alias=True, exclude_unset=True)
```

## State Management

The package includes helper classes for managing resource states:

- `RunStates` - For run state validation and checking
- `ConfigurationVersionStates` - For configuration version state validation

These provide methods like `is_success_state()`, `is_failure_state()`, etc.
