# Project Resource Integration Testing Guide

## Overview

The project resource can be tested in two ways:

1. **Unit Tests** - Fast, offline tests using mocks
2. **Integration Tests** - Real pytfe SDK calls against TFC/TFE

## Unit Tests (Fast, No Credentials Needed)

### Run All Unit Tests
```bash
# Set PYTHONPATH to include local python-tfe
export PYTHONPATH="/Users/kshitijapurushottamchoudhari/Projects/python-tfe"

# Run just the project pytfe tests
python3 -m pytest tests/unit/plugins/module_utils/test_project_pytfe.py --override-ini="addopts=" -v

# Run with coverage
python3 -m pytest tests/unit/plugins/module_utils/test_project_pytfe.py \
  --override-ini="addopts=" \
  --cov=plugins/module_utils/project \
  --cov-report=html
```

### Test Coverage
- ✅ Get project by ID
- ✅ Get project by name
- ✅ Create project (basic, with execution mode, with auto-destroy)
- ✅ Update project (basic, execution mode)
- ✅ Delete project
- ✅ Payload building and filtering
- ✅ Full CRUD lifecycle integration

**Results:** 15/15 tests passing ✅

---

## Integration Tests (Real TFC/TFE)

### Prerequisites

1. **Terraform Cloud/Enterprise Account**
   - Organization with permissions to create projects
   - API token with appropriate scopes

2. **Environment Variables**
   ```bash
   export TFE_TOKEN="your-api-token-here"
   # Optional - defaults to app.terraform.io
   export TFE_HOSTNAME="your-tfe-hostname.example.com"
   ```

3. **Ansible Installed**
   ```bash
   pip install ansible-core>=2.14
   ```

4. **Collection Available**
   ```bash
   # Option A: Install locally for testing
   ansible-galaxy collection install . --force
   
   # Option B: Use PYTHONPATH
   export PYTHONPATH="/Users/kshitijapurushottamchoudhari/Projects/python-tfe:$PYTHONPATH"
   ```

### Running Integration Tests

#### Test 1: Basic CRUD Operations
```bash
# Run full integration test suite
export TFE_TOKEN="your-token"
ansible-playbook tests/integration/test_project_pytfe_integration.yml \
  -e tfe_org="your-organization" \
  -v

# With custom project name
ansible-playbook tests/integration/test_project_pytfe_integration.yml \
  -e tfe_org="your-organization" \
  -e test_project_name="my-custom-test-project" \
  -v
```

#### Test 2: Specific Scenario
```bash
# Test only CREATE
ansible-playbook tests/integration/test_project_pytfe_integration.yml \
  -e tfe_org="your-organization" \
  --tags "CREATE" \
  -v

# Test only UPDATE
ansible-playbook tests/integration/test_project_pytfe_integration.yml \
  -e tfe_org="your-organization" \
  --tags "UPDATE" \
  -v

# Test only DELETE
ansible-playbook tests/integration/test_project_pytfe_integration.yml \
  -e tfe_org="your-organization" \
  --tags "DELETE" \
  -v
```

#### Test 3: Check Mode (Dry Run)
```bash
# See what would change without making changes
ansible-playbook tests/integration/test_project_pytfe_integration.yml \
  -e tfe_org="your-organization" \
  --check \
  -v
```

#### Test 4: Verbose Output
```bash
# Extra verbose with all debug info
ansible-playbook tests/integration/test_project_pytfe_integration.yml \
  -e tfe_org="your-organization" \
  -vvv
```

### What Gets Tested

**CREATE Operations:**
- ✅ Basic project creation
- ✅ Idempotent create (should not change on second run)
- ✅ Read by project_id
- ✅ Verify all attributes set correctly

**UPDATE Operations:**
- ✅ Change description
- ✅ Change execution mode (remote)
- ✅ Change execution mode (local)
- ✅ Set auto-destroy duration (30d)
- ✅ Verify each change is detected and applied

**DELETE Operations:**
- ✅ Delete project
- ✅ Verify idempotency (second delete should not change)

---

## Test Results Interpretation

### Successful Test Run
```
TASK [CREATE: Verify project was created] **
ok: [localhost] => {
  "changed": false,
  "msg": "All assertions passed"
}

TASK [UPDATE: Verify description changed] **
changed: [localhost] => {
  "changed": true,
  "description": "Updated test project description",
  ...
}

TASK [DELETE: Verify project was deleted] **
changed: [localhost] => {
  "changed": true,
  "msg": "Project deleted successfully"
}
```

### Expected Flow
1. Create project with description → `changed: true`
2. Create same project again → `changed: false` (idempotent)
3. Read by ID → returns project details
4. Update description → `changed: true`
5. Update execution mode → `changed: true`
6. Set auto-destroy → `changed: true`
7. Delete project → `changed: true`
8. Delete again → `changed: false` (idempotent)

---

## Troubleshooting

### "TFE_TOKEN environment variable must be set"
```bash
# Solution: Export the token
export TFE_TOKEN="your-token-here"

# Verify it's set
echo $TFE_TOKEN
```

### "Module not found: hashicorp.terraform"
```bash
# Solution A: Install collection locally
ansible-galaxy collection install . --force

# Solution B: Use PYTHONPATH
export PYTHONPATH="/Users/kshitijapurushottamchoudhari/Projects/python-tfe:$PYTHONPATH"
```

### "Authentication failed"
```bash
# Verify token is valid
curl -H "Authorization: Bearer $TFE_TOKEN" \
  https://app.terraform.io/api/v2/account/details

# Make sure organization exists
curl -H "Authorization: Bearer $TFE_TOKEN" \
  https://app.terraform.io/api/v2/organizations/YOUR-ORG
```

### "Project already exists"
- Delete manually in TFC/TFE UI, or
- Use unique project name: `--extra-vars test_project_name="test-$(date +%s)"`

### Tests hang or timeout
- Check internet connectivity
- Verify TFE_HOSTNAME is correct
- Try with `-vvv` for detailed output to see where it hangs

---

## Local Testing Without Real TFC

If you don't have TFC/TFE access, you can:

1. **Use unit tests** (already passing)
   ```bash
   pytest tests/unit/plugins/module_utils/test_project_pytfe.py -v
   ```

2. **Mock TFC/TFE responses** in a test playbook
   ```yaml
   - name: Test with mocked responses
     block:
       - name: Create project (mocked)
         hashicorp.terraform.project:
           name: "test-project"
           organization: "test-org"
           state: present
         environment:
           TFE_MOCK: "true"
   ```

3. **Use Docker to run TFC locally**
   ```bash
   docker run -it -p 8080:443 hashicorp/terraform-enterprise:latest
   export TFE_HOSTNAME="localhost:8080"
   export TFE_TOKEN="your-token"
   ```

---

## Next Steps

1. ✅ Unit tests validated - `15/15 passing`
2. 🔄 **Integration tests** - Run against your TFC/TFE instance
3. 📚 Update CI/CD pipeline to run these tests automatically
4. 📝 Document any custom execution modes or settings
5. 🚀 Deploy to production

---

## Quick Command Reference

| Task | Command |
|------|---------|
| Run unit tests | `pytest tests/unit/plugins/module_utils/test_project_pytfe.py -v` |
| Run integration tests | `ansible-playbook tests/integration/test_project_pytfe_integration.yml -e tfe_org="org-name"` |
| Dry run (check mode) | `ansible-playbook tests/integration/test_project_pytfe_integration.yml -e tfe_org="org-name" --check` |
| Verbose output | `ansible-playbook tests/integration/test_project_pytfe_integration.yml -e tfe_org="org-name" -vvv` |
| With coverage | `pytest tests/unit/plugins/module_utils/test_project_pytfe.py --cov=plugins/module_utils/project --cov-report=html` |

---

## Tips

- **Start with unit tests** - They're fast and don't require credentials
- **Use check mode first** - Verify what would change before actual changes
- **Run with -v or -vv** - See detailed progress and debugging info
- **Keep tokens safe** - Use environment variables, never hardcode
- **Test idempotency** - Verify operations don't change on second run
- **Clean up manually** - Delete test projects in TFC/TFE UI if tests fail

---

For more information, see:
- [PROJECT_PYTFE_IMPLEMENTATION.md](../../PROJECT_PYTFE_IMPLEMENTATION.md) - Architecture & design
- [PROJECT_PYTFE_SUMMARY.md](../../PROJECT_PYTFE_SUMMARY.md) - Complete overview
- [DEVELOPMENT.md](../../DEVELOPMENT.md) - Development guide
