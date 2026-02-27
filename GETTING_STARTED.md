# Getting Started - Hashicorp Terraform Ansible Collection

Welcome to the hashicorp.terraform collection! This guide will help you get up and running in just a few minutes.

## 30-Second Quick Start

```bash
# 1. Navigate to the project
cd hashicorp.terraform

# 2. Run the automated setup
./scripts/setup.sh

# 3. You're done! Try running tests
make test-unit
```

That's it! Continue reading for more detailed information.

---

## Prerequisites

Before you start, make sure you have:

- **Python 3.9+** (recommended: 3.12 or 3.13)
  ```bash
  python3 --version  # Should be 3.9+
  ```

- **Git**
  ```bash
  git --version
  ```

- **macOS, Linux, or WSL2 on Windows**

## Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/hashicorp.terraform.git
cd hashicorp.terraform
```

## Step 2: Run Automated Setup (Recommended)

The `setup.sh` script handles everything automatically:

```bash
./scripts/setup.sh
```

**What it does:**
- ✓ Creates a Python virtual environment
- ✓ Installs all dependencies
- ✓ Installs the collection locally
- ✓ Validates your setup
- ✓ Shows quick-start commands

**Output:** You'll see a success message with available commands.

---

## Step 3 (Alternative): Manual Setup

If you prefer to set up manually:

### 3a. Create Virtual Environment

```bash
# Create the environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# On Windows, use:
# .venv\Scripts\activate
```

Verify it's active (you should see `(.venv)` in your prompt):
```bash
which python  # Should show .venv/bin/python
```

### 3b. Upgrade pip

```bash
pip install --upgrade pip
```

### 3c. Install Dependencies

```bash
# Install everything
pip install -r requirements.txt -r test-requirements.txt
```

### 3d. Install Collection Locally

```bash
# Install for local testing
ansible-galaxy collection install . --force

# Verify it worked
ansible-galaxy collection list | grep hashicorp.terraform
```

---

## Step 4: Verify Your Setup

Run the validation script to ensure everything is configured correctly:

```bash
python3 scripts/validate_setup.py
```

You should see:
```
Result: 10/10 checks passed

✓ Environment is ready for development!
```

If you see failures, the script will tell you how to fix them.

---

## Your First Actions

Now that setup is complete, here are some recommended next steps:

### 1. Run Unit Tests

```bash
# Run all tests
make test-unit

# Run tests for a specific module
make test-specific TEST=tests/unit/plugins/modules/test_workspace.py
```

### 2. Check Code Quality

```bash
# Run all linting checks
make lint_all

# Auto-fix formatting issues
make fix_black
make fix_isort
```

### 3. View Available Modules

```bash
# See all available modules
make collection-docs

# View documentation for a specific module
ansible-doc hashicorp.terraform.workspace
```

### 4. Explore the Codebase

Key files to understand:

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Complete development guide
- **[plugins/modules/workspace.py](plugins/modules/workspace.py)** - Module example
- **[tests/unit/plugins/modules/test_workspace.py](tests/unit/plugins/modules/test_workspace.py)** - Test example
- **[plugins/module_utils/client.py](plugins/module_utils/client.py)** - Core utilities

---

## Common Commands

Save these for quick reference:

```bash
# Testing
make test-unit              # Run all unit tests
make test-coverage          # Generate coverage report
make test-unit-verbose      # Verbose test output
make test-specific TEST=path # Run specific test

# Code Quality
make lint_all               # Run all linting
make fix_black              # Auto-format code
make fix_isort              # Auto-fix imports
make check_flake8           # Check for linting issues

# Collection Management
make collection-install     # Install locally
make collection-docs        # View available modules
make collection-lint        # Run ansible-lint

# Development Workflow
make dev-loop               # Run tests + linting
make help                   # See all available targets
```

---

## Project Structure

Here's what you're working with:

```
hashicorp.terraform/
├── plugins/
│   ├── modules/              # Module entry points (main code)
│   └── module_utils/         # Helper functions and utilities
├── tests/
│   ├── unit/                 # Unit tests (pytest)
│   └── integration/          # Integration tests (ansible-test)
├── scripts/
│   ├── setup.sh             # Automated setup
│   └── validate_setup.py    # Environment validation
├── DEVELOPMENT.md           # Complete dev guide
├── requirements.txt         # Production dependencies
├── test-requirements.txt    # Test dependencies
└── Makefile                 # Development commands
```

---

## Important Concepts

### Modules vs. Module Utils

- **Modules** (`plugins/modules/`) - Entry points that users call
- **Module Utils** (`plugins/module_utils/`) - Shared helper code and functions

### Virtual Environment

Always activate the virtual environment before working:

```bash
source .venv/bin/activate

# You'll see (.venv) in your prompt
# To deactivate: deactivate
```

### Collection Installation

The collection must be installed for local testing:

```bash
# Install locally (required for testing)
ansible-galaxy collection install . --force

# This makes modules discoverable by Ansible
# It installs to ~/.ansible/collections/ansible_collections/hashicorp/terraform/
```

---

## Troubleshooting

### I get "command not found: python3"

- **macOS:** `brew install python@3.12`
- **Ubuntu:** `sudo apt-get install python3.12`
- **Windows:** Download from [python.org](https://python.org)

### The virtual environment won't activate

```bash
# Try creating a fresh one
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
```

### Setup script has permission issues

```bash
# Make it executable
chmod +x scripts/setup.sh

# Or run with bash
bash scripts/setup.sh
```

### Tests fail with "module not found"

```bash
# Make sure venv is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt -r test-requirements.txt
```

### Collection isn't discoverable

```bash
# Reinstall the collection
ansible-galaxy collection install . --force

# Verify
ansible-galaxy collection list | grep hashicorp.terraform
```

---

## Need Help?

1. **Setup issues?** → Run `python3 scripts/validate_setup.py`
2. **Development questions?** → See [DEVELOPMENT.md](DEVELOPMENT.md)
3. **Script help?** → See [scripts/README.md](scripts/README.md)
4. **Stuck?** → Open an issue with error messages and steps

---

## Next Steps

Once you're comfortable with the basics:

1. **Read [DEVELOPMENT.md](DEVELOPMENT.md)** - Deep dive into workflows
2. **Study existing modules** - Look at `plugins/modules/workspace.py` for patterns
3. **Review test examples** - Check `tests/unit/plugins/modules/test_workspace.py`
4. **Create your first change** - Edit a module and run tests
5. **Submit a pull request** - When ready to contribute

---

## Quick Reference

| Task | Command |
|------|---------|
| Setup | `./scripts/setup.sh` |
| Validate | `python3 scripts/validate_setup.py` |
| Test | `make test-unit` |
| Coverage | `make test-coverage` |
| Lint | `make lint_all` |
| Format | `make fix_black` |
| Docs | `make collection-docs` |
| Help | `make help` |

---

**Happy developing!** 🚀

For questions or issues, check [DEVELOPMENT.md](DEVELOPMENT.md) or the [scripts directory](scripts/README.md).
