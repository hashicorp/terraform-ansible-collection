# Hashicorp Terraform Ansible Collection - Development Guide

This guide covers setup, testing, and development workflows for the `hashicorp.terraform` Ansible collection.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Module Development](#module-development)
4. [Running Tests](#running-tests)
5. [Development Workflows](#development-workflows)
6. [Project Structure](#project-structure)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

```bash
# Python 3.9+ (recommended: 3.12 or 3.13)
python3 --version

# Git
git --version

# Ansible-core
ansible --version  # Should be 2.14+
```

### Verify Installation

```bash
# Check Python version
python3 --version

# Check Git
git --version

# After installing ansible-core
ansible --version
```

---

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/hashicorp.terraform.git
cd hashicorp.terraform
```

### 2. Create and Activate Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# On Windows, use:
# .venv\Scripts\activate
```

### 3. Upgrade pip

```bash
pip install --upgrade pip
```

### 4. Install Dependencies

#### Option A: Install Production + Test Dependencies

```bash
# Install both at once
pip install -r requirements.txt -r test-requirements.txt
```

#### Option B: Install Separately

```bash
# Production dependencies
pip install -r requirements.txt
# Installs: ansible-core, pytfe, requests, pydantic

# Test and development dependencies
pip install -r test-requirements.txt
# Installs: pytest, pytest-mock, pytest-xdist, black, flake8, isort, etc.
```

### 5. Install Collection Locally

```bash
# Install collection to Ansible's default location
ansible-galaxy collection install . --force

# Verify installation
ansible-galaxy collection list | grep hashicorp.terraform

# View module documentation
ansible-doc hashicorp.terraform.workspace
```

### 6. Verify Setup

```bash
# Check collection is discoverable
ansible-galaxy collection list | grep hashicorp.terraform

# List available modules
ansible-doc --list | grep hashicorp.terraform

# View specific module docs
ansible-doc hashicorp.terraform.workspace
```

---

## Module Development

### Adding a New Module

Follow this pattern to create a new Terraform resource module:

#### Step 1: Create Module File

```bash
# Create the module entry point
touch plugins/modules/new_resource.py
```

Reference [plugins/modules/workspace.py](plugins/modules/workspace.py) as a template.

**Key components:**
- `AnsibleModule` initialization
- State handlers (`present`, `absent`, `updated`)
- Error handling and response formatting

#### Step 2: Create Module Utils (Helper Functions)

```bash
# Create helper functions for CRUD operations
touch plugins/module_utils/new_resource.py
```

This file should contain:
- `list_resources()`
- `get_resource()`
- `create_resource()`
- `update_resource()`
- `delete_resource()`

#### Step 3: Create Pydantic Models (Optional)

If needed, add request/response models to `plugins/module_utils/models/`:

```bash
touch plugins/module_utils/models/new_resource.py
```

#### Step 4: Create Unit Tests

```bash
# Module unit tests
touch tests/unit/plugins/modules/test_new_resource.py

# Helper function unit tests
touch tests/unit/plugins/module_utils/test_new_resource.py
```

See [tests/unit/plugins/modules/test_workspace.py](tests/unit/plugins/modules/test_workspace.py) for examples.

#### Step 5: Create Integration Tests

```bash
# Create integration test directory
mkdir -p tests/integration/targets/new_resource/tasks

# Create main test file
touch tests/integration/targets/new_resource/tasks/main.yml
```

See [tests/integration/targets/workspace/tasks/main.yml](tests/integration/targets/workspace/tasks/main.yml) for examples.

---

## Running Tests

### Unit Tests with pytest

#### Run All Unit Tests

```bash
pytest tests/unit
```

#### Run Specific Module Tests

```bash
pytest tests/unit/plugins/modules/test_workspace.py -v
```

#### Run Specific Test Class

```bash
pytest tests/unit/plugins/modules/test_workspace.py::TestWorkspaceCreate -v
```

#### Run Specific Test Method

```bash
pytest tests/unit/plugins/modules/test_workspace.py::TestWorkspaceCreate::test_creates_workspace -vvv
```

#### Run with Coverage Report

```bash
# Generate coverage report
pytest tests/unit --cov=plugins --cov-report=html

# View the report
open htmlcov/index.html
```

#### Run Tests in Parallel

```bash
# Run with 4 parallel workers
pytest tests/unit -n 4
```

### Integration Tests (ansible-test)

Integration tests require Terraform Cloud/Enterprise credentials.

#### Method 1: Quick Local Test (Recommended for Development)

Create a local test playbook:

```bash
# Create integration test playbook
cat > tests/integration/test_workspace_local.yml << 'EOF'
- name: Test Workspace Module Locally
  hosts: localhost
  gather_facts: false
  tasks:
    # Include the actual integration tests
    - name: Run workspace integration tests
      ansible.builtin.include_tasks:
        file: targets/workspace/tasks/main.yml
EOF
```

Run the test:

```bash
# Navigate to integration tests directory
cd tests/integration

# Install collection dependencies
ansible-galaxy collection install -r requirements.yml

# Go back to project root
cd ../..

# Install your local collection
ansible-galaxy collection install . --force

# Return to integration tests
cd tests/integration

# Run the test playbook with credentials
ansible-playbook test_workspace_local.yml \
  -e "tfc_token=YOUR_TFC_TOKEN" \
  -e "organization=YOUR_ORG_NAME" \
  -vvv
```

#### Method 2: Using ansible-test (CI-style)

```bash
# 1. Install collection dependencies
cd tests/integration
ansible-galaxy collection install -r requirements.yml

# 2. Install your collection
cd ../..
ansible-galaxy collection install . --force

# 3. Navigate to installed collection
cd ~/.ansible/collections/ansible_collections/hashicorp/terraform

# 4. Set credentials as environment variables
export TFC_CI_TOKEN="your-token"

# Optional: override default organization (defaults to ANSIBLE-ENGINEERING-CI)
export TFC_ORG="your-org"

# 5. Run ansible-test for specific target
ansible-test integration workspace --python 3.12 -vvv

# Or run all integration targets
ansible-test integration --python 3.12 -vvv
```

#### Available Integration Targets

- `workspace` - Workspace CRUD operations
- `workspace_info` - Workspace information lookup
- `run` - Run CRUD operations
- `run_info` - Run information lookup
- `configuration_version` - Configuration version operations
- `configuration_version_info` - Configuration version lookup
- `project` - Project CRUD operations
- `project_info` - Project information lookup
- `output` - Output lookup

---

## Development Workflows

### Complete Development Loop

```bash
# 1. Create/edit your module
vim plugins/modules/workspace.py

# 2. Run unit tests
pytest tests/unit/plugins/modules/test_workspace.py -v

# 3. Check code formatting
make check_black
make check_isort
make check_flake8

# 4. Auto-fix formatting issues
make fix_black
make fix_isort

# 5. Reinstall collection locally
ansible-galaxy collection install . --force

# 6. Run integration tests (if needed)
cd tests/integration
ansible-playbook test_workspace_local.yml -e "tfc_token=$TFC_TOKEN" -e "organization=$ORG" -vvv
cd ../..
```

### Debug a Failing Test

```bash
# Run single test with maximum verbosity
pytest tests/unit/plugins/modules/test_workspace.py::TestWorkspaceCreate::test_creates_workspace -vvv

# Run with Python debugger
pytest tests/unit/plugins/modules/test_workspace.py::TestWorkspaceCreate::test_creates_workspace --pdb

# View test stdout (even if passing)
pytest tests/unit/plugins/modules/test_workspace.py -v -s
```

### Code Quality Checks

```bash
# Check all linting issues
make lint_all

# Fix black formatting
make fix_black

# Fix isort import ordering
make fix_isort

# Run flake8 checks
make check_flake8

# Generate collection documentation
make collection-docs

# Run ansible-lint on collection
make collection-lint
```

### Creating a Pull Request

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** (add modules, update tests, etc.)

3. **Run all checks locally:**
   ```bash
   pytest tests/unit -v
   make lint_all
   ```

4. **Push and create PR:**
   ```bash
   git push origin feature/your-feature-name
   ```

---

## Project Structure

```
hashicorp.terraform/
├── plugins/
│   ├── modules/                    # Ansible module entry points
│   │   ├── workspace.py           # Workspace lifecycle (state handlers)
│   │   ├── workspace_info.py      # Workspace information lookup
│   │   ├── run.py                 # Run lifecycle
│   │   ├── run_info.py            # Run information lookup
│   │   ├── project.py             # Project lifecycle
│   │   ├── project_info.py        # Project information lookup
│   │   ├── configuration_version.py
│   │   ├── configuration_version_info.py
│   │   ├── output.py              # Output lookup
│   │   └── view_plan.py           # Plan viewing/polling
│   ├── module_utils/               # Shared helper code
│   │   ├── client.py              # AnsibleTerraformModule, TerraformClient
│   │   ├── workspace.py           # Workspace CRUD (pytfe SDK)
│   │   ├── run.py                 # Run CRUD (REST API)
│   │   ├── plan.py                # Plan utilities
│   │   ├── project.py             # Project CRUD
│   │   ├── configuration_version.py
│   │   ├── state_version_output.py
│   │   ├── utils.py               # safe_api_call, format_response, dict_diff
│   │   ├── common.py              # Common utilities
│   │   ├── exceptions.py          # Custom exceptions
│   │   └── models/                # Pydantic request models
│   │       ├── workspace.py       # WorkspaceRequest
│   │       ├── run.py             # RunRequest
│   │       ├── plan.py            # PlanRequest
│   │       ├── project.py         # ProjectRequest
│   │       └── common.py          # Common models
│   ├── doc_fragments/
│   │   ├── common.py              # Shared tf_* auth documentation
│   │   └── __init__.py
│   ├── lookup/                    # Lookup plugins
│   │   ├── tf_output.py           # Output lookup
│   │   └── __init__.py
│   ├── filter/                    # Filter plugins
│   │   └── __init__.py
│   ├── inventory/                 # Inventory plugins
│   │   └── __init__.py
│   ├── action/                    # Action plugins
│   │   ├── view_plan.py
│   │   └── __init__.py
│   ├── cache/                     # Cache plugins
│   │   └── __init__.py
│   └── __init__.py
├── tests/
│   ├── unit/
│   │   ├── conftest.py            # Pytest fixtures
│   │   ├── constants.py           # Test constants
│   │   └── plugins/
│   │       ├── modules/           # Module behavior tests
│   │       │   ├── test_workspace.py
│   │       │   ├── test_run.py
│   │       │   ├── test_project.py
│   │       │   └── ...
│   │       ├── module_utils/      # Helper function unit tests
│   │       │   ├── test_workspace.py
│   │       │   ├── test_run.py
│   │       │   ├── test_utils.py
│   │       │   └── ...
│   │       └── lookup/            # Lookup plugin tests
│   │           └── test_tf_output.py
│   └── integration/
│       ├── config.yml             # ansible-test configuration
│       ├── requirements.yml       # Collection dependencies
│       └── targets/               # ansible-test targets
│           ├── workspace/
│           │   └── tasks/main.yml
│           ├── workspace_info/
│           │   └── tasks/main.yml
│           ├── run/
│           │   └── tasks/main.yml
│           └── ...
├── collections/                   # Collection metadata
│   └── ansible_collections/
│       └── hashicorp/
│           └── terraform/
├── changelogs/                    # Changelog management
│   ├── config.yaml
│   └── fragments/
├── docs/                          # Documentation
│   └── docsite/
│       └── links.yml
├── extensions/                    # EDA rules, etc.
├── meta/                          # Collection metadata
│   └── runtime.yml
├── tools/                         # Development tools
│   └── ci/
├── requirements.txt               # Production dependencies
├── test-requirements.txt          # Test/dev dependencies
├── pyproject.toml                 # Tool configuration
├── tox.ini                        # Tox configuration
├── tox-ansible.ini                # Ansible-specific tox config
├── Makefile                       # Common development commands
├── galaxy.yml                     # Collection metadata
├── README.md                      # Collection documentation
└── DEVELOPMENT.md                 # This file
```

---

## Troubleshooting

### Virtual Environment Issues

**Problem:** Module not found when running tests

```bash
# Solution: Ensure virtual environment is activated
source .venv/bin/activate

# Verify activation (should show .venv in prompt)
which python
```

### Ansible Collection Not Discovered

**Problem:** `ansible-doc hashicorp.terraform.workspace` fails

```bash
# Solution: Reinstall collection
ansible-galaxy collection install . --force

# Verify installation
ansible-galaxy collection list | grep hashicorp.terraform
```

### Import Errors in Tests

**Problem:** `ModuleNotFoundError` when running pytest

```bash
# Solution: Ensure test dependencies are installed
pip install -r test-requirements.txt

# Or run from project root with PYTHONPATH set
PYTHONPATH=/path/to/project pytest tests/unit
```

### Credential Issues in Integration Tests

**Problem:** Integration tests fail with authentication errors

```bash
# Verify TFC token is set
echo $TFC_CI_TOKEN

# Set token (temporary)
export TFC_CI_TOKEN="your-token-here"

# Verify organization is set (if needed)
echo $TFC_ORG
export TFC_ORG="your-org-name"
```

### Pytest Warnings

**Problem:** Warnings about AnsibleCollectionFinder

This is normal and expected. It's configured to be ignored in `pyproject.toml`:

```toml
filterwarnings = ['ignore:AnsibleCollectionFinder has already been configured']
```

### Formatting Conflicts

**Problem:** Black and isort disagreeing on formatting

```bash
# Solution: Run both in order
make fix_isort    # Fix imports first
make fix_black    # Then format
```

### Tox Issues

**Problem:** `tox` command not found

```bash
# Solution: Ensure test-requirements.txt is installed
pip install -r test-requirements.txt

# Verify tox is installed
which tox
```

---

## Additional Resources

- [Ansible Collection Developer Guide](https://docs.ansible.com/ansible/latest/dev_guide/developing_collections.html)
- [Ansible Modules Guide](https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_general.html)
- [pytest Documentation](https://docs.pytest.org/)
- [Terraform Cloud API Documentation](https://www.terraform.io/cloud-docs/api-docs)
- [pytfe Documentation](https://github.com/hashicorp/python-tfe)

---

## Getting Help

For issues or questions:

1. Check this DEVELOPMENT.md guide
2. Review existing module implementations in `plugins/modules/`
3. Check test examples in `tests/unit/plugins/modules/`
4. Open an issue with detailed error messages and steps to reproduce
