# Project Resource Testing Guide

Follow the exact same pattern as the Workspace resource.

## Quick Start - Running Tests Locally

### Unit Tests (pytest)

```bash
# Run all unit tests
pytest tests/unit

# Run specific module tests
pytest tests/unit/plugins/modules/test_project.py -v

# Run specific test class
pytest tests/unit/plugins/modules/test_project.py::TestProjectCreate -v

# Run with coverage report
pytest tests/unit --cov=plugins --cov-report=html

# View coverage: open htmlcov/index.html
```

### Integration Tests (ansible-test)

Integration tests require Terraform Cloud/Enterprise credentials. The integration tests are structured for the ansible-test framework, not as standalone playbooks. The test file is at `tests/integration/targets/project/tasks/main.yml`.

#### Method 1: Quick Local Test (Recommended for Development)

Run the commands in the terminal:

```bash
# Navigate to integration tests
cd tests/integration

# Install collection dependencies (if any)
ansible-galaxy collection install -r requirements.yml

# Install your local collection
cd ../..
ansible-galaxy collection install . --force

# Go back to integration tests
cd tests/integration

# Run the test playbook
ansible-playbook test_project_local.yml \
  -e "tfc_token=YOUR_TFC_TOKEN" \
  -e "organization=YOUR_ORG_NAME" \
  -vvv
```

#### Method 2: Using ansible-test (Full Test Suite)

```bash
# Run all integration tests for project
ansible-test integration project -vvv

# Run with specific Python version
ansible-test integration project -vvv --python 3.11
```

---

## Test Structure

### Unit Tests

Location: `tests/unit/plugins/modules/test_project.py`

Tests:
- Module initialization
- Parameter validation
- State handlers (present/absent)
- Idempotency checks
- Error handling

### Integration Tests

Location: `tests/integration/targets/project/tasks/main.yml`

Tests:
- Create project with tags and all attributes
- Idempotency of create
- Update project attributes
- Idempotency of update
- Update using project_id
- Delete project
- Error scenarios

---

## Environment Variables

```bash
# Required
export TFE_TOKEN="your-terraform-cloud-token"
export TFC_ORGANIZATION="your-organization"

# Optional
export TFE_HOSTNAME="app.terraform.io"  # or your TFE hostname
```

---

## Common Test Scenarios

### Test Create Functionality
```bash
pytest tests/unit/plugins/modules/test_project.py::TestProjectCreate -v
```

### Test Update Functionality
```bash
pytest tests/unit/plugins/modules/test_project.py::TestProjectUpdate -v
```

### Test Delete Functionality
```bash
pytest tests/unit/plugins/modules/test_project.py::TestProjectDelete -v
```

### Full Integration Test
```bash
cd tests/integration
ansible-playbook test_project_local.yml \
  -e "tfc_token=$TFE_TOKEN" \
  -e "organization=$TFC_ORGANIZATION" \
  -vvv
```

### Integration Test with Check Mode
```bash
cd tests/integration
ansible-playbook test_project_local.yml \
  -e "tfc_token=$TFE_TOKEN" \
  -e "organization=$TFC_ORGANIZATION" \
  --check -vvv
```

---

## What Gets Tested

### Create Operations
- ✅ Create project with name, organization, description
- ✅ Create with all attributes (execution_mode, auto_destroy_activity_duration, tag_bindings)
- ✅ Idempotency (creating same project twice should not change)
- ✅ Verify all attributes in response

### Update Operations
- ✅ Update description
- ✅ Update execution mode
- ✅ Update auto_destroy_activity_duration
- ✅ Update tag bindings
- ✅ Update using project_id instead of name
- ✅ Idempotency (updating with same values should not change)

### Delete Operations
- ✅ Delete project by name and organization
- ✅ Delete project by project_id
- ✅ Error handling when project not found

### Assertions
- ✅ Verify changed flag is set correctly
- ✅ Verify returned attributes match expected values
- ✅ Verify idempotency (changed=false on repeat operations)
- ✅ Verify error handling

---

## Troubleshooting

### "Collection not found" error
```bash
# Make sure you're in the right directory
cd tests/integration

# Reinstall the collection
cd ../..
ansible-galaxy collection install . --force

# Go back
cd tests/integration
```

### "Authentication failed"
```bash
# Verify token is valid
curl -H "Authorization: Bearer $TFE_TOKEN" \
  https://app.terraform.io/api/v2/account/details

# Make sure organization exists
curl -H "Authorization: Bearer $TFE_TOKEN" \
  https://app.terraform.io/api/v2/organizations/$TFC_ORGANIZATION
```

### "Module not found: hashicorp.terraform"
```bash
# Reinstall collection locally
ansible-galaxy collection install . --force
```

### Tests timeout
- Check internet connectivity
- Verify TFE_HOSTNAME is correct
- Try with verbose output: `-vvv`

---

## CI/CD Integration

To run tests in CI/CD pipeline:

```bash
#!/bin/bash
set -e

# Install dependencies
pip install pytest pytest-mock pytest-cov ansible-core

# Run unit tests
pytest tests/unit --cov=plugins --cov-report=xml

# Run integration tests
cd tests/integration
ansible-galaxy collection install -r requirements.yml
cd ../..
ansible-galaxy collection install . --force
cd tests/integration

ansible-playbook test_project_local.yml \
  -e "tfc_token=$TFE_TOKEN" \
  -e "organization=$TFC_ORGANIZATION" \
  -vvv

echo "✅ All tests passed!"
```

---

## References

- [PROJECT_PYTFE_IMPLEMENTATION.md](../../PROJECT_PYTFE_IMPLEMENTATION.md) - Architecture & design
- [PROJECT_PYTFE_SUMMARY.md](../../PROJECT_PYTFE_SUMMARY.md) - Complete overview
- [DEVELOPMENT.md](../../DEVELOPMENT.md) - Development guide
- Integration tests: `tests/integration/targets/project/tasks/main.yml`
