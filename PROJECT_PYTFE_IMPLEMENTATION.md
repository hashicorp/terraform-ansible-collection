# Project Resource Implementation - Python-TFE SDK Integration

## Overview

This document explains the implementation of the **Project resource** for the hashicorp.terraform Ansible collection using the **Python-TFE SDK** (pytfe). This implementation follows the same pattern as the Workspace resource and provides full CRUD (Create, Read, Update, Delete) operations.

---

## Architecture & Design

### Component Structure

```
┌─────────────────────────────────────────────────────────┐
│         Ansible Playbook / User                         │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  plugins/modules/project.py                             │
│  - DOCUMENTATION, EXAMPLES, RETURN                       │
│  - State handlers: present, absent                       │
│  - Change detection (dict_diff)                          │
│  - Module initialization                                 │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  plugins/module_utils/project.py (ProjectAdapter)       │
│  - CRUD operations using pytfe SDK                       │
│  - get_project_by_id()                                   │
│  - get_project_by_name()                                 │
│  - create_project()                                      │
│  - update_project()                                      │
│  - delete_project()                                      │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  pytfe SDK (Python-TFE)                                  │
│  - client.projects.read(id)                              │
│  - client.projects.list(org)                             │
│  - client.projects.create(org, options)                  │
│  - client.projects.update(id, options)                   │
│  - client.projects.delete(id)                            │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Terraform Cloud / Enterprise API                        │
└─────────────────────────────────────────────────────────┘
```

---

## CRUD Operations Implementation

### 1. CREATE Operation

**File:** `plugins/modules/project.py` → `state_present()`

**Flow:**
```python
1. User provides: organization, name, description, etc.
2. fetch_project() checks if project exists
3. If NOT found:
   - Call adapter.create_project(organization, **params)
   - ProjectAdapter builds ProjectCreateOptions with pytfe SDK
   - pytfe SDK calls: client.projects.create(org, options)
   - Returns created project data
4. If found: Proceed to UPDATE
```

**Code Example:**
```python
def state_present(adapter: ProjectAdapter, params: Dict[str, Any], check_mode: bool = False):
    """Create or update a project."""
    project = fetch_project(adapter, params)
    
    if not project:  # Project doesn't exist
        if not check_mode:
            response = adapter.create_project(
                organization=params.get("organization"),
                name=params.get("project"),
                description=params.get("description"),
                # ... other attributes
            )
            return {"changed": True, **response}
```

**ProjectAdapter.create_project():**
```python
def create_project(self, organization: str, **attributes) -> Dict[str, Any]:
    """Create a new project using pytfe SDK."""
    # Build options
    create_kwargs = {"name": attributes["name"]}
    create_kwargs.update(self._build_project_payload(attributes))
    
    # Create SDK options object
    create_options = ProjectCreateOptions(**create_kwargs)
    
    # Call pytfe SDK
    project = self.safe_api_call(
        self.client.projects.create,
        organization,
        create_options,
        error_context=f"Failed to create project {attributes['name']}"
    )
    
    return self.format_response(project)
```

**SDK Interaction:**
```python
# pytfe SDK internally does:
# POST /organizations/{organization}/projects
# With payload: {"data": {"type": "projects", "attributes": {...}}}
```

---

### 2. READ Operation

**File:** `plugins/module_utils/project.py` → `get_project_by_id()` / `get_project_by_name()`

**Flow - By ID:**
```python
1. adapter.get_project_by_id(project_id)
2. pytfe SDK: client.projects.read(project_id)
3. If found (200): Return project data
4. If not found (404): Catch NotFound exception, return None
5. Other errors: Raise TerraformError
```

**Code:**
```python
def get_project_by_id(self, project_id: str) -> Dict[str, Any] | None:
    """Read project by ID using pytfe SDK."""
    try:
        project = self.client.projects.read(project_id)
        return self.format_response(project)
    except NotFound:
        return None  # Gracefully handle 404
```

**Flow - By Name:**
```python
1. adapter.get_project_by_name(organization, project_name)
2. pytfe SDK: client.projects.list(organization=organization)
3. Iterate through projects, find by name
4. If found: Return formatted project data
5. If not found: Return None
```

**Code:**
```python
def get_project_by_name(self, organization: str, project_name: str) -> Dict[str, Any] | None:
    """Read project by name using pytfe SDK."""
    try:
        projects = self.client.projects.list(organization=organization)
        for project in projects:
            if project.name == project_name:
                return self.format_response(project)
        return None
    except NotFound:
        return None
```

---

### 3. UPDATE Operation

**File:** `plugins/modules/project.py` → `state_update()`

**Flow:**
```python
1. fetch_project() finds existing project
2. extract_comparable_attributes() gets current state
3. _build_desired_state() builds target state from params
4. dict_diff() compares: have vs want
5. If differences found:
   - Call adapter.update_project(project_id, **params)
   - ProjectAdapter builds ProjectUpdateOptions with pytfe SDK
   - pytfe SDK calls: client.projects.update(project_id, options)
   - Returns updated project data
6. If no differences: Return {"changed": False}
```

**Change Detection:**
```python
def state_update(adapter, params, project, check_mode=False):
    # Current state from API
    have = extract_comparable_attributes(project)
    # Desired state from user
    want = _build_desired_state(params)
    
    # Compare
    updates = dict_diff(have, want)
    
    if not updates:
        return {"changed": False}  # Idempotent!
    
    # Has changes, update it
    return adapter.update_project(project_id, **params)
```

**ProjectAdapter.update_project():**
```python
def update_project(self, project_id: str, **attributes) -> Dict[str, Any]:
    """Update existing project using pytfe SDK."""
    # Build options (name is required)
    update_kwargs = {"name": attributes["name"]}
    update_kwargs.update(self._build_project_payload(attributes))
    
    # Create SDK options object
    update_options = ProjectUpdateOptions(**update_kwargs)
    
    # Call pytfe SDK
    project = self.safe_api_call(
        self.client.projects.update,
        project_id,
        update_options,
        error_context=f"Failed to update project {project_id}"
    )
    
    return self.format_response(project)
```

**SDK Interaction:**
```python
# pytfe SDK internally does:
# PATCH /projects/{project_id}
# With payload: {"data": {"type": "projects", "attributes": {...}}}
```

---

### 4. DELETE Operation

**File:** `plugins/modules/project.py` → `state_absent()`

**Flow:**
```python
1. User provides: project_id or (project + organization)
2. fetch_project() finds existing project (if needed)
3. If project found:
   - Call adapter.delete_project(project_id)
   - pytfe SDK calls: client.projects.delete(project_id)
   - Returns success
4. If project not found:
   - Return {"changed": False, "msg": "Project not found"}
```

**Code:**
```python
def state_absent(adapter, params, check_mode=False):
    """Delete a project."""
    project_id = params.get("project_id")
    
    if not project_id:
        project = fetch_project(adapter, params)
        if project:
            project_id = project.get("id")
    
    if not project_id:
        return {"changed": False, "msg": "Project not found"}
    
    if not check_mode:
        adapter.delete_project(project_id)
        return {"changed": True, "msg": f"Project {project_id} deleted"}
```

**ProjectAdapter.delete_project():**
```python
def delete_project(self, project_id: str) -> None:
    """Delete a project using pytfe SDK."""
    self.safe_api_call(
        self.client.projects.delete,
        project_id,
        error_context=f"Failed to delete project {project_id}"
    )
```

**SDK Interaction:**
```python
# pytfe SDK internally does:
# DELETE /projects/{project_id}
```

---

## Supported Attributes

### Create/Update Parameters

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `project` / `name` | string | Project name | Yes (for create) |
| `organization` | string | Organization name | Yes (for create) |
| `project_id` | string | Project ID | For updates/delete |
| `description` | string | Project description | No |
| `execution_mode` | string | One of: remote, local, agent | No |
| `auto_destroy_activity_duration` | string | Duration like "30d" or "720h" | No |
| `default_agent_pool_id` | string | Agent pool ID when using agent mode | No |
| `setting_overwrites` | dict | Workspace setting overrides | No |
| `state` | string | present, absent | No (default: present) |

### Response Format

```python
{
    "changed": True,  # Whether changes were made
    "id": "prj-abc123",  # Project ID
    "type": "projects",  # Resource type
    "attributes": {
        "name": "my-project",
        "description": "My project",
        "execution-mode": "remote",
        "created-at": "2025-01-15T10:30:00Z",
        "updated-at": "2025-01-15T10:30:00Z"
    },
    "relationships": {
        "organization": {
            "data": {"id": "org-123", "type": "organizations"}
        }
    }
}
```

---

## Error Handling

### SDK Exceptions

The implementation uses pytfe SDK's exception handling:

```python
from pytfe.errors import NotFound, Unauthorized, BadRequest, ServerError

# NotFound (404) - Gracefully handled
try:
    project = client.projects.read(project_id)
except NotFound:
    return None  # Project doesn't exist, not an error

# Other errors - Raised as TerraformError
try:
    project = client.projects.create(org, options)
except Exception as e:
    raise TerraformError(f"Failed to create project: {e}")
```

### Safe API Call Wrapper

```python
def safe_api_call(func, *args, error_context="", **kwargs):
    """
    Wrapper for API calls with error handling.
    
    - Calls the function with provided arguments
    - On error: Raises TerraformError with context
    - Returns result on success
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        raise TerraformError(f"{error_context}: {str(e)}")
```

---

## Payload Building

### _build_project_payload()

Maps Ansible parameters to pytfe SDK options:

```python
def _build_project_payload(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
    """Build payload from attributes."""
    payload = {}
    
    # Simple attributes (direct pass-through)
    simple_attrs = [
        "description",
        "auto_destroy_activity_duration",
    ]
    for attr in simple_attrs:
        if attr in attributes and attributes[attr] is not None:
            payload[attr] = attributes[attr]
    
    # ExecutionMode enum
    if "execution_mode" in attributes and attributes["execution_mode"]:
        exec_mode = attributes["execution_mode"]
        try:
            payload["execution_mode"] = ExecutionMode(exec_mode)
        except ValueError:
            payload["execution_mode"] = exec_mode
    
    # Agent pool
    if "default_agent_pool_id" in attributes and attributes["default_agent_pool_id"]:
        payload["default_agent_pool_id"] = attributes["default_agent_pool_id"]
    
    # Setting overwrites
    if "setting_overwrites" in attributes and attributes["setting_overwrites"]:
        payload["setting_overwrites"] = attributes["setting_overwrites"]
    
    return payload
```

---

## Idempotency

The implementation ensures idempotent operations through:

### 1. Change Detection
```python
# Get current state from API
have = extract_comparable_attributes(project)

# Get desired state from params
want = _build_desired_state(params)

# Compare them
changes = dict_diff(have, want)

# Only update if there are changes
if changes:
    update_project(...)
else:
    return {"changed": False}
```

### 2. Attribute Normalization
```python
# Normalize API field names to module parameter names
field_mapping = {
    "auto-destroy-activity-duration": "auto_destroy_activity_duration",
    "execution-mode": "execution_mode",
}

# Ensures consistent comparison
```

### 3. Type Handling
```python
# Convert execution_mode string to ExecutionMode enum
if isinstance(exec_mode, str):
    payload["execution_mode"] = ExecutionMode(exec_mode)
```

---

## Testing

### Unit Tests - ProjectAdapter

**Location:** `tests/unit/plugins/module_utils/test_project_pytfe.py`

**Test Classes:**
- `TestProjectAdapterGetProject` - Read operations
- `TestProjectAdapterCreate` - Create operations
- `TestProjectAdapterUpdate` - Update operations
- `TestProjectAdapterDelete` - Delete operations
- `TestBuildProjectPayload` - Payload building
- `TestProjectAdapterIntegration` - Full CRUD lifecycle

**Example Test:**
```python
def test_create_project_basic(self):
    """Test basic project creation using pytfe SDK."""
    adapter = ProjectAdapter(tf_token="test-token")
    organization = "test-org"
    
    # Mock pytfe SDK
    adapter.client = Mock()
    adapter.client.projects = Mock()
    mock_project = Mock()
    mock_project.id = "prj-created123"
    mock_project.name = "new-project"
    adapter.safe_api_call = Mock(return_value=mock_project)
    adapter.format_response = Mock(return_value={...})
    
    # Call create
    result = adapter.create_project(
        organization=organization,
        name="new-project"
    )
    
    # Verify
    assert result is not None
    assert result["name"] == "new-project"
```

### Module Tests

**Location:** `tests/unit/plugins/modules/test_project.py`

**Test Cases:**
- `TestProjectStatePresent` - Create/update functionality
- `TestProjectStateAbsent` - Delete functionality
- `TestProjectStateHandlers` - State machine
- `TestProjectAttributes` - Attribute handling

---

## Usage Examples

### Create a Project

```yaml
- name: Create a new project
  hashicorp.terraform.project:
    name: "production-infrastructure"
    organization: "my-org"
    description: "Production infrastructure project"
    execution_mode: "remote"
    auto_destroy_activity_duration: "30d"
    state: "present"
    tf_token: "{{ terraform_token }}"
```

### Update a Project

```yaml
- name: Update project description
  hashicorp.terraform.project:
    project_id: "prj-abc123"
    name: "production-infrastructure"
    description: "Updated production infrastructure"
    state: "present"
    tf_token: "{{ terraform_token }}"
```

### Delete a Project

```yaml
- name: Delete a project
  hashicorp.terraform.project:
    project_id: "prj-abc123"
    state: "absent"
    tf_token: "{{ terraform_token }}"
```

---

## Benefits of Python-TFE SDK

1. **Type Safety** - Pydantic models ensure valid data
2. **API Versioning** - SDK handles API changes
3. **Error Handling** - Built-in exception handling
4. **Code Reuse** - SDK is used by other tools
5. **Maintenance** - HashiCorp maintains SDK
6. **Future-proof** - New features added to SDK first

---

## Comparison: REST API vs. pytfe SDK

| Aspect | REST API (Old) | pytfe SDK (New) |
|--------|---|---|
| HTTP Calls | Manual with requests | SDK abstraction |
| Error Handling | Manual status checks | SDK exceptions |
| Payload Building | Manual dict construction | Pydantic models |
| Type Safety | None | Full with models |
| Code Lines | 150+ | 80+ |
| Maintainability | Lower | Higher |

---

## Future Enhancements

1. **Tag Bindings** - Full support for project tag bindings
2. **Team Access** - Team permissions management
3. **Policy Enforcement** - Policy set association
4. **Cost Estimation** - Cost estimate settings
5. **Webhooks** - Webhook management

---

## Files Modified/Created

### Modified Files
- `plugins/module_utils/project.py` - Enhanced ProjectAdapter
- `plugins/modules/project.py` - Already uses pytfe SDK

### New Test Files
- `tests/unit/plugins/module_utils/test_project_pytfe.py` - pytfe SDK integration tests

### Documentation
- This file: Implementation details and design

---

## See Also

- [Workspace Module](../DEVELOPMENT.md#module-development)
- [Python-TFE SDK Docs](https://github.com/hashicorp/python-tfe)
- [Terraform Cloud API Docs](https://www.terraform.io/cloud-docs/api-docs)
- [DEVELOPMENT.md](../DEVELOPMENT.md) - General development guide

---

**Last Updated:** February 27, 2026  
**Status:** Implementation Complete ✅  
**SDK Version:** pytfe >= 1.3.0  
**Python Version:** 3.9+
