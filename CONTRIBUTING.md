# Contributing to Hashicorp Terraform Collection

Thank you for your interest in contributing to the hashicorp.terraform collection! This guide explains how to contribute code, report issues, and participate in the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Creating a Module](#creating-a-module)
5. [Writing Tests](#writing-tests)
6. [Submitting Changes](#submitting-changes)
7. [Code Style Guidelines](#code-style-guidelines)
8. [Testing Standards](#testing-standards)

---

## Code of Conduct

This project adheres to the [Ansible Community Code of Conduct](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html). By participating, you agree to uphold this code.

---

## Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/hashicorp.terraform.git
cd hashicorp.terraform
```

### 2. Create a Feature Branch

```bash
# Create a descriptive branch name
git checkout -b feature/add-new-module
# or
git checkout -b fix/issue-123
# or
git checkout -b docs/improve-readme
```

### 3. Set Up Development Environment

```bash
# Run the automated setup
./scripts/setup.sh

# Or manually
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r test-requirements.txt
ansible-galaxy collection install . --force
```

---

## Development Workflow

### 1. Make Your Changes

Edit files as needed for your contribution.

### 2. Test Locally

```bash
# Run all unit tests
make test-unit

# Run specific test file
pytest tests/unit/plugins/modules/test_your_module.py -v

# Run with coverage
make test-coverage

# Check code quality
make lint_all
```

### 3. Format Code

```bash
# Auto-format with black
make fix_black

# Auto-fix imports
make fix_isort

# Check for linting issues
make check_flake8
```

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Write a clear commit message
git commit -m "feat: add new terraform module

- Implement workspace configuration management
- Add unit tests for new module
- Update documentation"

# Keep commits focused and logical
```

### 5. Push and Create PR

```bash
# Push to your fork
git push origin feature/add-new-module

# Create a Pull Request on GitHub
# - Fill in the PR template
# - Reference any related issues
# - Explain what and why
```

---

## Creating a Module

Follow this pattern for new modules:

### 1. Module File: `plugins/modules/my_resource.py`

```python
#!/usr/bin/env python3

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    AnsibleTerraformModule,
)

DOCUMENTATION = r'''
---
module: my_resource
short_description: Manage Terraform Cloud my resource
description:
  - Creates, updates, and deletes Terraform Cloud my resources
  
options:
  name:
    description: Name of the resource
    type: str
    required: true
    
author:
  - Ansible (https://github.com/ansible)
'''

EXAMPLES = r'''
- name: Create my resource
  hashicorp.terraform.my_resource:
    name: my-resource
    state: present
    tf_token: "{{ terraform_token }}"
'''

RETURN = r'''
resource:
  description: The created or updated resource
  type: dict
  returned: success
'''


def main():
    module = AnsibleTerraformModule(
        argument_spec={
            'name': {'type': 'str', 'required': True},
            'state': {'type': 'str', 'default': 'present', 'choices': ['present', 'absent']},
        }
    )

    # Get parameters
    name = module.params['name']
    state = module.params['state']

    # Implement state handlers
    if state == 'present':
        result = create_resource(module, name)
    elif state == 'absent':
        result = delete_resource(module, name)

    module.exit_json(**result)


def create_resource(module, name):
    """Create a new resource."""
    # Implementation here
    return {'changed': True, 'resource': {}}


def delete_resource(module, name):
    """Delete a resource."""
    # Implementation here
    return {'changed': True}


if __name__ == '__main__':
    main()
```

### 2. Helper Functions: `plugins/module_utils/my_resource.py`

```python
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    TerraformClient,
)


def create_resource(client: TerraformClient, name: str) -> dict:
    """Create a new resource."""
    # Use the Terraform Cloud API
    return client.api_call('POST', '/resources', {'name': name})


def delete_resource(client: TerraformClient, resource_id: str) -> dict:
    """Delete a resource."""
    return client.api_call('DELETE', f'/resources/{resource_id}')
```

### 3. Unit Tests: `tests/unit/plugins/modules/test_my_resource.py`

```python
import pytest
from ansible_collections.hashicorp.terraform.plugins.modules import my_resource


@pytest.fixture
def module_args():
    return {'name': 'test-resource', 'state': 'present'}


def test_create_resource(mocker, module_args):
    """Test resource creation."""
    # Mock the module and API calls
    mocker.patch.object(my_resource, 'AnsibleModule')
    mock_api = mocker.patch('ansible_collections.hashicorp.terraform.plugins.module_utils.my_resource.create_resource')
    mock_api.return_value = {'id': '123', 'name': 'test-resource'}

    # Run the module
    # Assert the result


def test_delete_resource(mocker, module_args):
    """Test resource deletion."""
    module_args['state'] = 'absent'
    # Similar test structure
```

### 4. Integration Tests: `tests/integration/targets/my_resource/tasks/main.yml`

```yaml
- name: Set up test variables
  set_fact:
    resource_name: "test-{{ ansible_date_time.iso8601_basic_short }}"

- name: Create my resource
  hashicorp.terraform.my_resource:
    name: "{{ resource_name }}"
    state: present
    tf_token: "{{ tfc_token }}"
  register: created_resource

- name: Verify resource was created
  assert:
    that:
      - created_resource.changed
      - created_resource.resource.name == resource_name

- name: Delete my resource
  hashicorp.terraform.my_resource:
    name: "{{ resource_name }}"
    state: absent
    tf_token: "{{ tfc_token }}"
  register: deleted_resource

- name: Verify resource was deleted
  assert:
    that:
      - deleted_resource.changed
```

---

## Writing Tests

### Unit Tests Best Practices

1. **Use fixtures** for common setups:
   ```python
   @pytest.fixture
   def module():
       return AnsibleModule(argument_spec={})
   ```

2. **Mock external calls**:
   ```python
   mocker.patch('module.api_call')
   ```

3. **Test both success and failure**:
   ```python
   def test_success(mocker):
       # Test successful case
   
   def test_error(mocker):
       # Test error handling
   ```

4. **Use meaningful assertions**:
   ```python
   assert result['changed'] is True
   assert 'error' not in result
   ```

### Run Tests

```bash
# All tests
make test-unit

# Specific file
pytest tests/unit/plugins/modules/test_my_resource.py -v

# Specific test
pytest tests/unit/plugins/modules/test_my_resource.py::test_create_resource -vvv

# With coverage
make test-coverage
```

---

## Submitting Changes

### Before You Submit

1. **Ensure all tests pass:**
   ```bash
   make test-unit
   ```

2. **Check code quality:**
   ```bash
   make lint_all
   ```

3. **Format code:**
   ```bash
   make fix_black
   make fix_isort
   ```

4. **Update documentation:**
   - Module docstrings (DOCUMENTATION string)
   - Examples in modules
   - README if adding new features
   - CHANGELOG if significant change

5. **Create a changelog fragment:**
   ```bash
   # Create file: changelogs/fragments/123_my_change.yml
   cat > changelogs/fragments/123_my_change.yml << 'EOF'
   ---
   major_changes:
     - "Added new my_resource module for managing Terraform resources"
   bugfixes:
     - "Fixed issue with workspace handling"
   EOF
   ```

### PR Guidelines

Your PR should include:

1. **Clear title:** Summarizes the change
2. **Description:** Explains what and why
3. **Issue reference:** Links to related issues
4. **Testing:** Describes how to test the change
5. **Documentation:** Updates to relevant docs

### Example PR Description

```markdown
## Description
Implements the new `my_resource` module for managing Terraform Cloud resources.

## Changes
- Added `my_resource.py` module with create/delete functionality
- Added unit tests with 95%+ coverage
- Added integration test
- Updated collection documentation

## Testing
```bash
make test-unit
pytest tests/unit/plugins/modules/test_my_resource.py -v
```

## Related Issues
Fixes #123
Relates to #456
```

---

## Code Style Guidelines

### Python Style

- **Follow PEP 8** with the following exceptions:
  - Line length: 160 characters (configured in pyproject.toml)
  - Use Black for formatting

- **Use the project's tools:**
  ```bash
  black --check plugins/          # Check formatting
  isort --check plugins/          # Check imports
  flake8 plugins/                 # Check style
  ```

### Import Organization

```python
# Standard library
import sys
from pathlib import Path

# Third-party
import pytest
from pydantic import BaseModel

# Local
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule
```

### Naming Conventions

- **Modules:** `snake_case.py` (e.g., `my_resource.py`)
- **Classes:** `PascalCase` (e.g., `MyResourceModule`)
- **Functions:** `snake_case` (e.g., `create_resource()`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`)
- **Private:** Leading underscore (e.g., `_internal_function()`)

### Documentation

```python
def create_resource(module: AnsibleModule, name: str) -> dict:
    """
    Create a new Terraform Cloud resource.
    
    Args:
        module: Ansible module instance
        name: Name of the resource to create
        
    Returns:
        Dict with 'changed' and 'resource' keys
        
    Raises:
        TerraformAPIError: If API call fails
    """
```

---

## Testing Standards

### Coverage Requirements

- Minimum 80% code coverage
- All public functions tested
- Error cases covered

### Test Organization

```
tests/
├── unit/
│   ├── plugins/
│   │   ├── modules/
│   │   │   └── test_my_resource.py     # Module tests
│   │   └── module_utils/
│   │       └── test_my_resource.py     # Helper tests
│   └── conftest.py                     # Pytest fixtures
└── integration/
    └── targets/
        └── my_resource/
            └── tasks/
                └── main.yml            # Integration tests
```

### Test Naming

```python
def test_create_resource_with_valid_input(mocker):
    """Test resource creation succeeds with valid parameters."""
    
def test_create_resource_fails_with_invalid_input(mocker):
    """Test resource creation fails with invalid parameters."""
    
def test_create_resource_api_error(mocker):
    """Test resource creation handles API errors gracefully."""
```

---

## Common Issues and Solutions

### Import Errors in Tests

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt -r test-requirements.txt

# Reinstall collection
ansible-galaxy collection install . --force
```

### Tests Fail Randomly

- Check for race conditions
- Avoid global state in tests
- Use proper pytest fixtures

### Coverage Report Issues

```bash
# Generate fresh coverage report
pytest tests/unit --cov=plugins --cov-report=html
open htmlcov/index.html
```

---

## Questions?

1. **Check [DEVELOPMENT.md](DEVELOPMENT.md)** - Comprehensive development guide
2. **Check [GETTING_STARTED.md](GETTING_STARTED.md)** - Quick start guide
3. **Review existing modules** - See patterns in `plugins/modules/`
4. **Open an issue** - Ask questions publicly

---

## Recognition

Contributors are recognized in:
- Git commit history
- Release notes
- MAINTAINERS file (for ongoing contributors)

Thank you for contributing to the hashicorp.terraform collection! 🙏
