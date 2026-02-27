# Project Development Setup - Complete

This document summarizes the complete development setup for the hashicorp.terraform Ansible collection.

**Setup Date:** February 27, 2026  
**Python Version:** 3.14.0  
**Status:** ✅ Ready for Development

---

## What Was Configured

### 1. **Production Dependencies** (`requirements.txt`)
Updated with:
- `ansible-core>=2.14` - Ansible framework
- `pytfe>=1.3.0` - Terraform Cloud/Enterprise Python SDK
- `requests>=2.28.0` - HTTP library
- `pydantic>=2.0.0` - Data validation

### 2. **Test/Development Dependencies** (`test-requirements.txt`)
Includes:
- **Testing:** pytest, pytest-mock, pytest-xdist, pytest-cov, pytest-ansible
- **Code Quality:** black, flake8, isort, tox
- **Linting:** ansible-lint

### 3. **Enhanced Makefile**
New targets added:
- `install` - Install all dependencies
- `collection-install` - Install collection locally
- `test-unit` - Run unit tests
- `test-coverage` - Generate coverage report
- `test-specific` - Run specific test
- `dev-setup` - Complete setup automation
- `dev-loop` - Test + lint cycle
- And more...

### 4. **Documentation Files Created**

#### DEVELOPMENT.md
Comprehensive development guide covering:
- Complete setup instructions
- Module development patterns
- Testing (unit and integration)
- Development workflows
- Troubleshooting guide
- Project structure reference

#### GETTING_STARTED.md
Quick start guide for new developers:
- 30-second quick start
- Automated setup instructions
- Manual setup steps
- Common commands
- First actions to take
- Troubleshooting

#### CONTRIBUTING.md
Contribution guidelines:
- Code of Conduct
- Development workflow
- Module creation guide
- Testing standards
- Submitting changes
- Code style guidelines

#### scripts/README.md
Scripts directory documentation:
- `setup.sh` - Automated setup
- `validate_setup.py` - Environment validation
- Usage instructions
- Troubleshooting

### 5. **Utility Scripts Created**

#### scripts/setup.sh
Automated setup script that:
- Checks Python version
- Creates virtual environment
- Upgrades pip
- Installs all dependencies
- Installs collection locally
- Runs validation
- Displays quick-start commands

**Usage:** `./scripts/setup.sh`

#### scripts/validate_setup.py
Environment validation script that checks:
- Python version (3.9+)
- Git installation
- Virtual environment status
- Python packages
- Collection structure
- Module files
- Test files
- Ansible installation
- Collection installation

**Usage:** `python3 scripts/validate_setup.py`

### 6. **Updated README.md**
Added developer section with:
- Separate installation instructions for users vs. developers
- Quick start for developers
- Link to DEVELOPMENT.md

---

## Project Structure

The collection is organized as:

```
hashicorp.terraform/
├── plugins/                          # Ansible plugins
│   ├── modules/                      # Module entry points
│   │   ├── workspace.py
│   │   ├── workspace_info.py
│   │   ├── run.py
│   │   ├── run_info.py
│   │   ├── project.py
│   │   ├── project_info.py
│   │   └── ... (more modules)
│   ├── module_utils/                 # Shared utilities
│   │   ├── client.py                 # Core client
│   │   ├── workspace.py
│   │   ├── run.py
│   │   ├── project.py
│   │   ├── common.py
│   │   ├── utils.py
│   │   ├── exceptions.py
│   │   └── models/                   # Pydantic models
│   ├── lookup/                       # Lookup plugins
│   ├── action/                       # Action plugins
│   ├── filter/                       # Filter plugins
│   ├── doc_fragments/                # Documentation
│   └── cache/                        # Cache plugins
├── tests/
│   ├── unit/                         # Unit tests (pytest)
│   │   ├── conftest.py
│   │   ├── constants.py
│   │   └── plugins/
│   │       ├── modules/              # Module tests
│   │       ├── module_utils/         # Helper tests
│   │       └── lookup/
│   └── integration/                  # Integration tests (ansible-test)
│       ├── config.yml
│       ├── requirements.yml
│       └── targets/
│           ├── workspace/
│           ├── run/
│           ├── project/
│           └── ... (more targets)
├── scripts/                          # Development scripts
│   ├── setup.sh                      # Automated setup
│   ├── validate_setup.py             # Validation
│   └── README.md                     # Scripts documentation
├── changelogs/                       # Changelog management
├── docs/                             # Documentation
├── meta/                             # Collection metadata
├── tools/                            # Development tools
├── GETTING_STARTED.md               # Quick start guide
├── DEVELOPMENT.md                   # Development guide
├── CONTRIBUTING.md                  # Contribution guidelines
├── DEVELOPMENT_SETUP.md             # This file
├── requirements.txt                 # Production deps
├── test-requirements.txt            # Test deps
├── pyproject.toml                   # Tool config
├── Makefile                         # Development commands
├── galaxy.yml                       # Collection metadata
├── README.md                        # Collection docs
└── ... (other files)
```

---

## Quick Reference

### Setup (First Time)

```bash
# Automated (recommended)
./scripts/setup.sh

# Or manual
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r test-requirements.txt
ansible-galaxy collection install . --force
```

### Validation

```bash
# Verify setup is correct
python3 scripts/validate_setup.py
```

### Testing

```bash
# Run all unit tests
make test-unit

# Run with coverage
make test-coverage

# Run specific test
make test-specific TEST=tests/unit/plugins/modules/test_workspace.py

# Run with verbose output
make test-unit-verbose
```

### Code Quality

```bash
# Check all linting
make lint_all

# Auto-format code
make fix_black

# Auto-fix imports
make fix_isort

# Check for linting issues
make check_flake8
```

### Collection Management

```bash
# Install collection locally
make collection-install

# View module documentation
make collection-docs

# Run ansible-lint
make collection-lint
```

### Development Loop

```bash
# Run tests and linting together
make dev-loop

# See all available commands
make help
```

---

## Key Files by Purpose

### For New Developers
- Start here → [GETTING_STARTED.md](GETTING_STARTED.md)
- Then read → [DEVELOPMENT.md](DEVELOPMENT.md)
- Before contributing → [CONTRIBUTING.md](CONTRIBUTING.md)

### For Setup & Validation
- Automated setup → `./scripts/setup.sh`
- Validate environment → `python3 scripts/validate_setup.py`
- Script documentation → [scripts/README.md](scripts/README.md)

### For Development
- Module examples → [plugins/modules/workspace.py](plugins/modules/workspace.py)
- Test examples → [tests/unit/plugins/modules/test_workspace.py](tests/unit/plugins/modules/test_workspace.py)
- Helper utilities → [plugins/module_utils/client.py](plugins/module_utils/client.py)

### For Tools & Configuration
- Make targets → [Makefile](Makefile)
- Tool config → [pyproject.toml](pyproject.toml)
- Pytest config → [pyproject.toml](pyproject.toml) (pytest section)
- Collection config → [galaxy.yml](galaxy.yml)

---

## Development Workflow

### Typical Development Session

1. **Activate environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **Create feature branch:**
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Make changes** to modules, tests, or docs

4. **Run tests locally:**
   ```bash
   make test-unit
   ```

5. **Check code quality:**
   ```bash
   make lint_all
   ```

6. **Auto-format if needed:**
   ```bash
   make fix_black && make fix_isort
   ```

7. **Commit and push:**
   ```bash
   git add .
   git commit -m "feat: describe your change"
   git push origin feature/my-feature
   ```

8. **Create Pull Request** on GitHub

---

## Testing Expectations

### Unit Tests
- Run with: `make test-unit`
- Framework: pytest
- Location: `tests/unit/`
- Coverage target: 80%+

### Integration Tests
- Run with: `ansible-test integration workspace`
- Requires: Terraform Cloud credentials
- Location: `tests/integration/targets/`

### Coverage Reports
- Generate: `make test-coverage`
- View: Open `htmlcov/index.html`
- Target: 80%+ coverage

---

## Common Development Tasks

### Adding a New Module

Follow the pattern in [CONTRIBUTING.md](CONTRIBUTING.md#creating-a-module):

1. Create `plugins/modules/my_resource.py`
2. Create `plugins/module_utils/my_resource.py`
3. Create `tests/unit/plugins/modules/test_my_resource.py`
4. Create `tests/integration/targets/my_resource/tasks/main.yml`
5. Update documentation

### Running a Specific Test

```bash
# Run single test file
pytest tests/unit/plugins/modules/test_workspace.py -v

# Run single test class
pytest tests/unit/plugins/modules/test_workspace.py::TestWorkspaceCreate -v

# Run single test method
pytest tests/unit/plugins/modules/test_workspace.py::TestWorkspaceCreate::test_creates_workspace -vvv
```

### Debugging a Test

```bash
# Run with Python debugger
pytest tests/unit/plugins/modules/test_workspace.py::TestWorkspaceCreate::test_creates_workspace --pdb

# Run with verbose output and print statements
pytest tests/unit/plugins/modules/test_workspace.py -vvv -s
```

### Checking Code Before Commit

```bash
# Check all tools
make lint_all

# Auto-fix formatting
make fix_black && make fix_isort

# Verify tests pass
make test-unit

# Check coverage
make test-coverage
```

---

## Dependencies Summary

### Production (requirements.txt)
```
ansible-core>=2.14
pytfe>=1.3.0
requests>=2.28.0
pydantic>=2.0.0
```

### Development (test-requirements.txt)
```
pytest, pytest-mock, pytest-xdist, pytest-cov, pytest-ansible
black, flake8, isort, tox, ansible-lint
```

---

## IDE Configuration

### VS Code
Recommended extensions:
- Python
- Pylance
- Black Formatter
- isort
- Ansible
- Test Explorer UI

### PyCharm
Settings:
- Python: 3.12+
- Project venv: `.venv`
- Code style: Black
- Run → Edit Configurations → pytest

---

## Troubleshooting

### Environment Issues
```bash
# Validate entire setup
python3 scripts/validate_setup.py

# Recreate virtual environment
rm -rf .venv
./scripts/setup.sh
```

### Test Failures
```bash
# Run with maximum verbosity
pytest tests/unit -vvv -s

# Check imports are working
python3 -c "from ansible_collections.hashicorp.terraform.plugins.modules import workspace"
```

### Collection Not Found
```bash
# Reinstall collection
ansible-galaxy collection install . --force

# Verify
ansible-galaxy collection list | grep hashicorp.terraform
```

See [DEVELOPMENT.md](DEVELOPMENT.md#troubleshooting) for more solutions.

---

## Next Steps

1. ✅ **Setup complete!** Review the status above
2. 📖 **Read [GETTING_STARTED.md](GETTING_STARTED.md)** for a guided walkthrough
3. 🚀 **Run `make test-unit`** to verify everything works
4. 💻 **Explore the codebase** starting with `plugins/modules/workspace.py`
5. 🤝 **Start contributing!** See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Support & Resources

| Resource | Purpose |
|----------|---------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | Quick start for new developers |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Comprehensive development guide |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [scripts/README.md](scripts/README.md) | Development scripts documentation |
| `make help` | Available development commands |
| `python3 scripts/validate_setup.py` | Environment validation |

---

## Summary

Your development environment is now fully configured with:

✅ Python 3.14 with virtual environment  
✅ All production and test dependencies installed  
✅ Collection installed locally for testing  
✅ Automated setup and validation scripts  
✅ Comprehensive documentation  
✅ Ready-to-use Makefile targets  
✅ Example modules and tests  
✅ Testing infrastructure  

You're ready to start developing! 🎉

**For immediate help:** Run `./scripts/validate_setup.py` or check `make help`

---

**Last Updated:** February 27, 2026  
**Status:** Complete ✅  
**Ready for Development:** Yes ✅
