# Development Scripts

This directory contains utility scripts to help with development and testing of the hashicorp.terraform collection.

## Available Scripts

### setup.sh - Complete Environment Setup

**Purpose:** Automatically sets up the entire development environment from scratch.

**Features:**
- Creates Python virtual environment (.venv)
- Installs all production and test dependencies
- Installs the collection locally for testing
- Runs validation checks
- Provides quick-start commands

**Usage:**

```bash
# From the collection root directory
./scripts/setup.sh

# Or with bash explicitly
bash scripts/setup.sh
```

**What it does:**
1. Checks Python version (3.9+)
2. Creates `.venv` virtual environment
3. Upgrades pip
4. Installs production dependencies from `requirements.txt`
5. Installs test/dev dependencies from `test-requirements.txt`
6. Installs the collection locally via `ansible-galaxy`
7. Runs validation checks
8. Displays quick-start commands

**Output:** Success message with commands to get started

---

### validate_setup.py - Environment Validation

**Purpose:** Validates that the development environment is properly configured.

**Features:**
- Checks Python version compatibility
- Verifies Git installation
- Confirms virtual environment is active
- Validates all required Python packages
- Checks collection directory structure
- Verifies collection files exist
- Confirms module and test files
- Checks Ansible installation
- Verifies local collection installation

**Usage:**

```bash
# Run validation
python3 scripts/validate_setup.py

# Or if executable
./scripts/validate_setup.py
```

**Output Format:**
- ✓ for passed checks
- ✗ for failed checks
- ⚠ for warnings
- Detailed summary with pass/fail count
- Recommendations for fixing issues

**Example Output:**
```
════════════════════════════════════════════════════════
         Python Version Check
════════════════════════════════════════════════════════

Python version: 3.12.0
✓ Python 3.12.0 is supported

[Summary]
  [PASS] Python Version
  [PASS] Git Installation
  [PASS] Virtual Environment
  [PASS] Python Packages
  [PASS] Collection Structure
  ...

Result: 10/10 checks passed

✓ Environment is ready for development!
```

---

## Common Workflows

### First-Time Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/hashicorp.terraform.git
cd hashicorp.terraform

# 2. Run the setup script
./scripts/setup.sh

# 3. You're ready to develop!
make test-unit
```

### After Pulling Changes

```bash
# Activate your environment
source .venv/bin/activate

# Reinstall collection in case it changed
ansible-galaxy collection install . --force

# Run tests to ensure everything works
make test-unit
```

### Validate Your Environment

```bash
# Quick check
python3 scripts/validate_setup.py

# This will tell you if anything is misconfigured
```

### If Something Breaks

```bash
# 1. Run validation to identify issues
python3 scripts/validate_setup.py

# 2. Reactivate virtual environment
source .venv/bin/activate

# 3. Reinstall dependencies if needed
pip install -r requirements.txt -r test-requirements.txt

# 4. Reinstall collection
ansible-galaxy collection install . --force

# 5. Run validation again
python3 scripts/validate_setup.py
```

---

## System Requirements

Before running scripts, ensure:

- **Python 3.9+** (recommended 3.12 or 3.13)
- **Git** installed and configured
- **bash** or compatible shell (for setup.sh)
- Permission to create directories in the project folder

---

## Troubleshooting

### setup.sh Fails to Execute

```bash
# Ensure script is executable
chmod +x scripts/setup.sh

# Run with bash explicitly
bash scripts/setup.sh
```

### Permission Denied

```bash
# Make script executable
chmod +x scripts/validate_setup.py
chmod +x scripts/setup.sh

# Or run Python explicitly
python3 scripts/validate_setup.py
```

### Virtual Environment Issues

```bash
# If .venv is corrupted, remove and re-run setup
rm -rf .venv
./scripts/setup.sh
```

### Python Not Found

Ensure Python 3.9+ is installed:

```bash
# Check Python installation
python3 --version

# On macOS with Homebrew
brew install python@3.12

# On Linux (Ubuntu/Debian)
sudo apt-get install python3.12 python3.12-venv

# On Windows, download from python.org
```

---

## Related Documentation

- [DEVELOPMENT.md](../DEVELOPMENT.md) - Complete development guide
- [README.md](../README.md) - Collection overview
- [Makefile](../Makefile) - Available make targets

---

## Contributing

When adding new scripts:

1. **Use meaningful names** - Script names should indicate purpose
2. **Add help text** - Include usage instructions at the top
3. **Support bash** - Ensure compatibility across platforms
4. **Document thoroughly** - Add comments explaining what the script does
5. **Make executable** - Use `chmod +x` and update this README
6. **Handle errors** - Use `set -e` and provide clear error messages

---

## Script Development Guidelines

### Bash Scripts

```bash
#!/bin/bash
set -e  # Exit on any error

# Use functions for organization
my_function() {
    echo "Doing something..."
}

# Provide colored output
source "$(dirname "$0")/colors.sh"  # If available

# Document usage
if [ "$1" == "--help" ]; then
    echo "Usage: $0 [options]"
    exit 0
fi
```

### Python Scripts

```python
#!/usr/bin/env python3
"""
Script description here.

This module provides utility functions for development tasks.
"""

import sys
from pathlib import Path

def main() -> int:
    """Main entry point."""
    # Implementation
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

---

Last Updated: February 27, 2026
