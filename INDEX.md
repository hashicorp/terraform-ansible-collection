# Documentation Index

## Quick Navigation

### 🚀 Getting Started
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - 30-second quick start and setup guide
- **[SETUP_SUMMARY.txt](SETUP_SUMMARY.txt)** - Overview of what was configured

### 📚 Development Guides
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Comprehensive development guide
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute to the project
- **[DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)** - Detailed setup configuration

### 🛠️ Scripts & Tools
- **[scripts/README.md](scripts/README.md)** - Development scripts documentation
- **[Makefile](Makefile)** - Available development commands

### 📖 Project Documentation
- **[README.md](README.md)** - Collection overview and usage
- **[galaxy.yml](galaxy.yml)** - Collection metadata

---

## By Role

### For New Developers
Start here and follow in order:
1. [GETTING_STARTED.md](GETTING_STARTED.md) - Setup your environment (5 minutes)
2. [DEVELOPMENT.md](DEVELOPMENT.md) - Learn the development workflow (15 minutes)
3. [CONTRIBUTING.md](CONTRIBUTING.md) - Understand contribution guidelines (10 minutes)

### For Developers Setting Up
- Quick setup: Run `./scripts/setup.sh`
- Validate: Run `python3 scripts/validate_setup.py`
- Learn: Read [GETTING_STARTED.md](GETTING_STARTED.md)

### For Contributors
1. Read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
2. Check [DEVELOPMENT.md](DEVELOPMENT.md) for technical details
3. Use [scripts/README.md](scripts/README.md) for script help

### For Collection Users
- Start with [README.md](README.md)
- View module docs: `ansible-doc hashicorp.terraform.workspace`
- Check examples in the documentation

---

## Common Tasks

### Setting Up Development Environment

**Option 1: Automated (Recommended)**
```bash
./scripts/setup.sh
```

**Option 2: Manual**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r test-requirements.txt
ansible-galaxy collection install . --force
```

**Option 3: Validate Existing Setup**
```bash
python3 scripts/validate_setup.py
```

**See:** [GETTING_STARTED.md](GETTING_STARTED.md)

### Running Tests

```bash
# All unit tests
make test-unit

# Specific test file
pytest tests/unit/plugins/modules/test_workspace.py -v

# With coverage
make test-coverage
```

**See:** [DEVELOPMENT.md](DEVELOPMENT.md#running-tests)

### Creating a New Module

1. Create module file: `plugins/modules/my_resource.py`
2. Create helper file: `plugins/module_utils/my_resource.py`
3. Create tests: `tests/unit/plugins/modules/test_my_resource.py`
4. Create integration tests: `tests/integration/targets/my_resource/tasks/main.yml`

**See:** [CONTRIBUTING.md](CONTRIBUTING.md#creating-a-module)

### Submitting a Change

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and test: `make test-unit && make lint_all`
3. Commit: `git commit -m "feat: description"`
4. Push: `git push origin feature/my-feature`
5. Create Pull Request on GitHub

**See:** [CONTRIBUTING.md](CONTRIBUTING.md#submitting-changes)

### Checking Code Quality

```bash
# Check all
make lint_all

# Auto-format
make fix_black && make fix_isort

# Check only
make check_black && make check_isort && make check_flake8
```

**See:** [DEVELOPMENT.md](DEVELOPMENT.md#code-quality-checks)

---

## File Organization

```
hashicorp.terraform/
├── Documentation
│   ├── README.md                 # Collection overview
│   ├── GETTING_STARTED.md       # Quick start guide ⭐
│   ├── DEVELOPMENT.md           # Complete dev guide ⭐
│   ├── CONTRIBUTING.md          # Contribution guide ⭐
│   ├── DEVELOPMENT_SETUP.md     # Setup details
│   ├── SETUP_SUMMARY.txt        # Setup overview
│   └── INDEX.md                 # This file
│
├── Scripts
│   ├── scripts/setup.sh              # Automated setup
│   ├── scripts/validate_setup.py    # Environment validation
│   └── scripts/README.md            # Scripts documentation
│
├── Configuration
│   ├── Makefile                  # Development commands
│   ├── pyproject.toml            # Tool configuration
│   ├── galaxy.yml                # Collection metadata
│   ├── requirements.txt          # Production dependencies
│   ├── test-requirements.txt    # Test dependencies
│   └── tox.ini                   # Tox configuration
│
├── Source Code
│   ├── plugins/
│   │   ├── modules/              # Module entry points
│   │   ├── module_utils/         # Helper utilities
│   │   ├── lookup/               # Lookup plugins
│   │   ├── action/               # Action plugins
│   │   └── filter/               # Filter plugins
│   │
│   └── tests/
│       ├── unit/                 # Unit tests
│       └── integration/          # Integration tests
│
└── Collection Metadata
    ├── changelogs/               # Changelog management
    ├── meta/runtime.yml          # Runtime metadata
    ├── docs/                     # Documentation
    └── extensions/               # EDA rules, etc.
```

⭐ = Recommended starting points

---

## Key Commands

### Development
```bash
make help                    # See all available commands
make test-unit              # Run unit tests
make test-coverage          # Generate coverage report
make lint_all               # Check code quality
make fix_black && make fix_isort  # Auto-format code
make dev-loop               # Test + lint
```

### Setup & Validation
```bash
./scripts/setup.sh                      # Automated setup
python3 scripts/validate_setup.py      # Validate environment
make collection-install                # Install locally
make collection-docs                   # View modules
```

### Testing
```bash
pytest tests/unit -v                    # Run tests
pytest tests/unit/plugins/modules/test_workspace.py -v  # Specific file
make test-coverage                      # Coverage report
```

---

## Documentation Standards

### Module Documentation
- Inline docstrings (DOCUMENTATION, EXAMPLES, RETURN)
- Located in `plugins/modules/*.py`
- View with: `ansible-doc hashicorp.terraform.module_name`

### Development Documentation
- Markdown format
- Located in root directory
- Related: [DEVELOPMENT.md](DEVELOPMENT.md)

### Code Documentation
- Docstrings for functions and classes
- PEP 257 style
- Include type hints
- Example: [DEVELOPMENT.md](DEVELOPMENT.md#module-development)

---

## Project Status

### Setup Completed ✅
- [x] Dependencies configured
- [x] Makefile enhanced
- [x] Documentation created
- [x] Scripts provided
- [x] Project validated

### Current Capabilities
- [x] 6 core modules
- [x] 11+ unit test files
- [x] 11+ integration test targets
- [x] Complete test framework
- [x] Code quality tools

### Ready For
- ✅ Local development
- ✅ Unit testing
- ✅ Integration testing
- ✅ Contribution

---

## Support & Help

### Getting Help

1. **Quick Questions**
   - Check [GETTING_STARTED.md](GETTING_STARTED.md#troubleshooting)
   - Run: `python3 scripts/validate_setup.py`

2. **Development Questions**
   - See [DEVELOPMENT.md](DEVELOPMENT.md)
   - Check relevant module examples

3. **Contribution Questions**
   - Read [CONTRIBUTING.md](CONTRIBUTING.md)
   - Review existing PRs

4. **Script Issues**
   - See [scripts/README.md](scripts/README.md)
   - Check troubleshooting section

### Resources

- [Ansible Documentation](https://docs.ansible.com/)
- [Terraform Cloud API](https://www.terraform.io/cloud-docs/api-docs)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pytest Documentation](https://docs.pytest.org/)

---

## Next Steps

### As a New Developer
1. Read [GETTING_STARTED.md](GETTING_STARTED.md)
2. Run `./scripts/setup.sh` or `python3 scripts/validate_setup.py`
3. Run `make test-unit` to verify
4. Explore the codebase
5. Make your first change!

### As a Contributor
1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Create feature branch
3. Make changes with tests
4. Run `make dev-loop`
5. Submit pull request

### For Questions
1. Check relevant documentation
2. Run `python3 scripts/validate_setup.py`
3. Review similar examples in codebase
4. Open an issue if needed

---

## Document Legend

| Document | Purpose | Audience | Length |
|----------|---------|----------|--------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | Quick setup & common tasks | New developers | 5-10 min |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Complete development guide | Developers | 15-20 min |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines | Contributors | 10-15 min |
| [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) | Setup configuration details | Reference | 10 min |
| [scripts/README.md](scripts/README.md) | Scripts documentation | Tool users | 5 min |
| [SETUP_SUMMARY.txt](SETUP_SUMMARY.txt) | Setup overview | Reference | 5 min |
| [README.md](README.md) | Collection overview | Users | 5 min |

---

## File Size Reference

Quick estimates for reading/review time:

```
GETTING_STARTED.md      ~10 min read
DEVELOPMENT.md          ~20 min read
CONTRIBUTING.md         ~15 min read
DEVELOPMENT_SETUP.md    ~10 min read
scripts/README.md       ~5 min read
```

---

## Related Commands

```bash
# View this index
cat INDEX.md

# Setup/Validation
./scripts/setup.sh
python3 scripts/validate_setup.py

# Documentation
make help              # Show make targets
ansible-doc --list    # List modules
ansible-doc hashicorp.terraform.workspace  # Module docs

# Testing
make test-unit
make test-coverage
pytest tests/unit -v

# Code Quality
make lint_all
make fix_black
make fix_isort
```

---

**Last Updated:** February 27, 2026  
**Status:** Complete ✅  
**Version:** 1.0.0

For the latest information, see the individual documentation files.
